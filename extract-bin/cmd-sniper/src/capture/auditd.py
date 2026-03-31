"""
auditd-based command capture module.
"""
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Generator
import pwd

from .base import CaptureBase, CaptureError, CaptureNotAvailableError


class AuditdCapture(CaptureBase):
    """
    Capture commands using the Linux auditd system.

    This method uses auditd rules to monitor execve system calls.
    It provides stable and comprehensive capture but requires auditd to be running.
    """

    # auditd execve event parsing pattern
    AUDIT_EXECVE_PATTERN = re.compile(
        r'type=EXECVE.*?msg=audit\((\d+\.\d+):\d+\):.*?argc=(\d+).*?'
    )
    AUDIT_ARG_PATTERN = re.compile(r'CWD="\{([^}"]+)\}"')
    AUDIT_PID_PATTERN = re.compile(r'type=SYSCALL.*?pid=(\d+).*?uid=(\d+)')
    AUDIT_EUID_PATTERN = re.compile(r'euid=(\d+)')

    # Custom rules file identifier
    RULE_IDENTIFIER = "cmd-sniper"

    def __init__(self, db, config=None):
        super().__init__(db, config)
        self.log_path = getattr(config, "auditd_log_path", "/var/log/audit/audit.log") if config else "/var/log/audit/audit.log"
        self._log_file_handle: Optional[object] = None
        self._log_file_pos: int = 0
        self._rule_added = False

    def get_method_name(self) -> str:
        return "auditd"

    def is_available(self) -> bool:
        """Check if auditd is available and we have the required permissions."""
        try:
            # Check if auditd is running
            result = subprocess.run(
                ["systemctl", "is-active", "auditd"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return False

            # Check if we have permission to read audit logs
            if not os.access(self.log_path, os.R_OK):
                return False

            # Check if aureport or ausearch is available
            result = subprocess.run(
                ["which", "ausearch"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except (FileNotFoundError, PermissionError):
            return False

    def check_permissions(self) -> bool:
        """Check if running with required privileges."""
        return os.geteuid() == 0

    def install_rules(self) -> bool:
        """
        Install auditd rules for execve monitoring.

        Adds rules to monitor all execve system calls.
        Requires root privileges.
        """
        if not self.check_permissions():
            raise CaptureError("Root privileges required to install auditd rules")

        try:
            # Check if rules already exist
            existing_rules = subprocess.run(
                ["auditctl", "-l"],
                capture_output=True,
                text=True,
            )

            if self.RULE_IDENTIFIER in existing_rules.stdout:
                self._rule_added = True
                return True

            # Add rule to monitor execve
            # We use a unique key to identify our rules
            rules = [
                # Monitor all execve calls
                f"-a exit,always -F arch=b64 -S execve -F key={self.RULE_IDENTIFIER}",
                f"-a exit,always -F arch=b32 -S execve -F key={self.RULE_IDENTIFIER}",
            ]

            for rule in rules:
                subprocess.run(
                    ["auditctl", *rule.split()],
                    check=True,
                    capture_output=True,
                )

            self._rule_added = True
            return True

        except subprocess.CalledProcessError as e:
            raise CaptureError(f"Failed to install auditd rules: {e.stderr}")

    def remove_rules(self) -> bool:
        """Remove auditd rules added by cmd-sniper."""
        if not self._rule_added:
            return True

        try:
            # Remove rules by key
            subprocess.run(
                ["auditctl", "-d", "exit,always", "-F", f"key={self.RULE_IDENTIFIER}"],
                capture_output=True,
            )
            self._rule_added = False
            return True
        except subprocess.CalledProcessError:
            return False

    def _open_log_file(self):
        """Open the audit log file and seek to the end."""
        self._log_file_handle = open(self.log_path, "r", errors="replace")
        self._log_file_handle.seek(0, 2)  # Seek to end
        self._log_file_pos = self._log_file_handle.tell()

    def _read_new_logs(self) -> List[str]:
        """Read new log entries since last read."""
        if not self._log_file_handle:
            return []

        self._log_file_handle.seek(self._log_file_pos)
        new_lines = []
        for line in self._log_file_handle:
            new_lines.append(line.rstrip("\n"))
        self._log_file_pos = self._log_file_handle.tell()
        return new_lines

    def _parse_execve_event(self, event_lines: List[str]) -> Optional[Dict]:
        """
        Parse an execve event from audit log lines.

        An execve event spans multiple lines:
        - type=SYSCALL: contains pid, uid, etc.
        - type=CWD: contains current working directory
        - type=EXECVE: contains argc and argv

        Returns a dict with parsed data or None if incomplete.
        """
        event = {
            "pid": None,
            "uid": None,
            "euid": None,
            "cwd": None,
            "argc": 0,
            "argv": [],
            "timestamp": None,
        }

        for line in event_lines:
            # Parse timestamp from any line (format: 1234567890.123:123)
            ts_match = re.search(r'msg=audit\((\d+\.\d+):\d+\)', line)
            if ts_match:
                event["timestamp"] = float(ts_match.group(1))

            # Parse SYSCALL line
            if "type=SYSCALL" in line:
                pid_match = re.search(r'pid=(\d+)', line)
                if pid_match:
                    event["pid"] = int(pid_match.group(1))

                uid_match = re.search(r'uid=(\d+)', line)
                if uid_match:
                    event["uid"] = int(uid_match.group(1))

                euid_match = re.search(r'euid=(\d+)', line)
                if euid_match:
                    event["euid"] = int(euid_match.group(1))

            # Parse CWD line
            if "type=CWD" in line:
                cwd_match = re.search(r'cwd="([^"]*)"', line)
                if cwd_match:
                    event["cwd"] = cwd_match.group(1)

            # Parse EXECVE line
            if "type=EXECVE" in line:
                argc_match = re.search(r'argc=(\d+)', line)
                if argc_match:
                    event["argc"] = int(argc_match.group(1))

                # Parse arguments (format: a0="xxx" a1="xxx" ...)
                arg_pattern = re.compile(r'a(\d+)="([^"]*)"')
                args = {}
                for arg_match in arg_pattern.finditer(line):
                    idx = int(arg_match.group(1))
                    args[idx] = arg_match.group(2)

                # Reconstruct argv in order
                event["argv"] = [args[i] for i in sorted(args.keys()) if i in args]

        # Validate we have the minimum required data
        if not event["argv"] or event["uid"] is None:
            return None

        # Get timestamp as datetime
        if event["timestamp"]:
            event["datetime"] = datetime.fromtimestamp(event["timestamp"])

        return event

    def _group_lines_by_event(self, lines: List[str]) -> Generator[List[str], None, None]:
        """
        Group audit log lines by event.

        Audit events share the same timestamp and event ID in the msg field.
        """
        current_event = []
        current_event_id = None

        for line in lines:
            # Extract event ID (format: 1234567890.123:456)
            event_match = re.search(r'msg=audit\((\d+\.\d+):\d+\)', line)
            if event_match:
                event_id = event_match.group(1)
                if event_id != current_event_id:
                    if current_event:
                        yield current_event
                    current_event = [line]
                    current_event_id = event_id
                else:
                    current_event.append(line)
            elif current_event:
                current_event.append(line)

        if current_event:
            yield current_event

    def _record_to_command(self, event: Dict) -> Optional:
        """Convert a parsed event to a CommandRecord."""
        from storage import CommandRecord

        if not event["argv"]:
            return None

        command = event["argv"][0]
        full_command = " ".join(event["argv"])

        # Get username from uid
        try:
            username = pwd.getpwuid(event["uid"]).pw_name
        except KeyError:
            username = f"uid_{event['uid']}"

        return CommandRecord(
            timestamp=event["datetime"],
            uid=event["uid"],
            username=username,
            pid=event.get("pid", 0),
            ppid=0,  # Not available in execve event
            cwd=event.get("cwd", ""),
            command=command,
            full_command=full_command,
            argv=event["argv"],
            capture_method="auditd",
        )

    def start(self):
        """Start capturing commands from auditd."""
        if not self.is_available():
            raise CaptureNotAvailableError("auditd is not available")

        # Install rules if not already present
        self.install_rules()

        # Create session
        self._create_session()

        # Open log file
        self._open_log_file()

        self.running = True

    def stop(self):
        """Stop capturing commands."""
        self.running = False

        if self._log_file_handle:
            self._log_file_handle.close()
            self._log_file_handle = None

        self._close_session("stopped")

    def capture_once(self) -> int:
        """
        Capture new commands once.

        Returns the number of commands captured.
        """
        if not self.running:
            raise CaptureError("Capture not started")

        new_lines = self._read_new_logs()
        count = 0

        for event_lines in self._group_lines_by_event(new_lines):
            # Only process events that contain EXECVE
            if not any("type=EXECVE" in line for line in event_lines):
                continue

            event = self._parse_execve_event(event_lines)
            if event:
                record = self._record_to_command(event)
                if record:
                    self.db.insert_command(record)
                    count += 1

        return count

    def capture_forever(self, interval: float = 1.0, callback=None):
        """
        Continuously capture commands.

        Args:
            interval: Seconds between polling checks
            callback: Optional function to call for each captured command
        """
        self.setup_signal_handlers()
        total_captured = 0

        try:
            while self.running:
                count = self.capture_once()
                total_captured += count

                if callback and count > 0:
                    callback(count)

                time.sleep(interval)
        except KeyboardInterrupt:
            self.stop()

        return total_captured

    def replay_logs(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> int:
        """
        Replay historical logs to populate the database.

        Useful for initial setup or backfilling data.
        """
        # Use ausearch for efficient historical log parsing
        cmd = ["ausearch", "-i", "-m", "EXECVE"]

        if start_time:
            cmd.extend(["-ts", start_time.strftime("%Y%m%d %H:%M:%S")])
        if end_time:
            cmd.extend(["-te", end_time.strftime("%Y%m%d %H:%M:%S")])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            count = 0
            current_event = []

            for line in result.stdout.split("\n"):
                line = line.strip()
                if not line:
                    continue

                if line.startswith("----"):
                    if current_event:
                        event = self._parse_execve_event(current_event)
                        if event:
                            record = self._record_to_command(event)
                            if record:
                                self.db.insert_command(record)
                                count += 1
                    current_event = []
                else:
                    current_event.append(line)

            return count

        except subprocess.CalledProcessError as e:
            if "No matches" in str(e.output):
                return 0
            raise CaptureError(f"Failed to replay logs: {e}")
