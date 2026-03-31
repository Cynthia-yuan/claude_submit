"""
Audit log parser utilities.
"""
import re
from datetime import datetime
from typing import List, Optional, Tuple


# Audit log line patterns
AUDIT_TYPE_PATTERN = re.compile(r'type=(\w+)')
AUDIT_MSG_PATTERN = re.compile(r'msg=audit\((\d+\.\d+):(\d+)\):')
AUDIT_SYSCALL_PATTERN = re.compile(
    r'syscall=(\d+).*?success=(yes|no).*?exit=(-?\d+).*?'
    r'item=\d+.*?pid=(\d+).*?auid=(\d+).*?uid=(\d+).*?euid=(\d+).*?'
)
AUDIT_EXECVE_PATTERN = re.compile(r'argc=(\d+)(.*)')
AUDIT_CWD_PATTERN = re.compile(r'cwd="([^"]*)"')
AUDIT_ARG_PATTERN = re.compile(r'a(\d+)="([^"]*)"')


class AuditEvent:
    """Represents a single audit event."""

    def __init__(self):
        self.timestamp: Optional[float] = None
        self.event_id: Optional[int] = None
        self.type: Optional[str] = None
        self.pid: Optional[int] = None
        self.uid: Optional[int] = None
        self.euid: Optional[int] = None
        self.auid: Optional[int] = None
        self.cwd: Optional[str] = None
        self.argv: List[str] = []
        self.exit_code: Optional[int] = None
        self.success: bool = True

    def is_complete(self) -> bool:
        """Check if event has all required fields."""
        return bool(self.argv and self.uid is not None)

    def to_dict(self) -> dict:
        """Convert event to dictionary."""
        return {
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp) if self.timestamp else None,
            "event_id": self.event_id,
            "type": self.type,
            "pid": self.pid,
            "uid": self.uid,
            "euid": self.euid,
            "auid": self.auid,
            "cwd": self.cwd,
            "argv": self.argv,
            "exit_code": self.exit_code,
            "success": self.success,
        }


class AuditLogParser:
    """
    Parser for auditd log files.

    Handles the multi-line format of audit events, combining
    related lines (SYSCALL, CWD, EXECVE) into complete events.
    """

    def __init__(self):
        self._current_event: Optional[AuditEvent] = None
        self._events: List[AuditEvent] = []

    def parse_line(self, line: str) -> Optional[AuditEvent]:
        """
        Parse a single audit log line.

        Returns a complete AuditEvent if the current event is complete,
        otherwise returns None.
        """
        line = line.strip()
        if not line:
            return self._finish_event()

        # Extract timestamp and event ID (present in all lines)
        msg_match = AUDIT_MSG_PATTERN.search(line)
        if msg_match:
            timestamp = float(msg_match.group(1))
            event_id = int(msg_match.group(2))

            # If this is a new event, finish the previous one
            if self._current_event and (
                self._current_event.event_id != event_id
                or abs(self._current_event.timestamp - timestamp) > 1
            ):
                complete_event = self._finish_event()
                if complete_event:
                    return complete_event

            # Start or continue current event
            if not self._current_event:
                self._current_event = AuditEvent()
                self._current_event.timestamp = timestamp
                self._current_event.event_id = event_id

        # Extract type
        type_match = AUDIT_TYPE_PATTERN.search(line)
        if type_match and self._current_event:
            self._current_event.type = type_match.group(1)

        # Parse SYSCALL line
        if "type=SYSCALL" in line and self._current_event:
            self._parse_syscall(line)

        # Parse CWD line
        elif "type=CWD" in line and self._current_event:
            self._parse_cwd(line)

        # Parse EXECVE line
        elif "type=EXECVE" in line and self._current_event:
            self._parse_execve(line)

        return None

    def _parse_syscall(self, line: str):
        """Parse SYSCALL line."""
        match = AUDIT_SYSCALL_PATTERN.search(line)
        if match:
            self._current_event.pid = int(match.group(4))
            self._current_event.auid = int(match.group(5))
            self._current_event.uid = int(match.group(6))
            self._current_event.euid = int(match.group(7))
            self._current_event.exit_code = int(match.group(3))
            self._current_event.success = match.group(2) == "yes"

    def _parse_cwd(self, line: str):
        """Parse CWD (current working directory) line."""
        match = AUDIT_CWD_PATTERN.search(line)
        if match:
            self._current_event.cwd = match.group(1)

    def _parse_execve(self, line: str):
        """Parse EXECVE line with arguments."""
        match = AUDIT_EXECVE_PATTERN.search(line)
        if match:
            argc = int(match.group(1))
            args_str = match.group(2)

            # Parse all arguments
            args = {}
            for arg_match in AUDIT_ARG_PATTERN.finditer(args_str):
                idx = int(arg_match.group(1))
                args[idx] = arg_match.group(2)

            # Reconstruct argv in order
            self._current_event.argv = [args[i] for i in range(argc) if i in args]

    def _finish_event(self) -> Optional[AuditEvent]:
        """Finish current event and return if complete."""
        event = self._current_event
        self._current_event = None

        if event and event.is_complete():
            return event
        return None

    def parse_file(self, path: str) -> List[AuditEvent]:
        """Parse entire audit log file."""
        events = []
        try:
            with open(path, "r", errors="replace") as f:
                for line in f:
                    event = self.parse_line(line)
                    if event:
                        events.append(event)

                # Don't forget the last event
                final_event = self._finish_event()
                if final_event:
                    events.append(final_event)
        except (IOError, OSError):
            pass

        return events

    def parse_text(self, text: str) -> List[AuditEvent]:
        """Parse audit log text."""
        events = []
        for line in text.split("\n"):
            event = self.parse_line(line)
            if event:
                events.append(event)

        # Don't forget the last event
        final_event = self._finish_event()
        if final_event:
            events.append(final_event)

        return events


class AusearchParser:
    """
    Parser for ausearch output (interpreted format).

    Ausearch outputs human-readable format with ---- separators.
    """

    EVENT_SEPARATOR =----

    def __init__(self):
        self._current_lines: List[str] = []
        self._events: List[dict] = []

    def parse_line(self, line: str) -> Optional[dict]:
        """
        Parse a line from ausearch output.

        Returns complete event dict when separator is encountered.
        """
        line = line.strip()

        if not line:
            return None

        if line.startswith(self.EVENT_SEPARATOR):
            return self._finish_event()

        self._current_lines.append(line)
        return None

    def _finish_event(self) -> Optional[dict]:
        """Finish current event and parse it."""
        if not self._current_lines:
            return None

        event = self._parse_event(self._current_lines)
        self._current_lines = []
        return event

    def _parse_event(self, lines: List[str]) -> Optional[dict]:
        """Parse event from accumulated lines."""
        event = {
            "timestamp": None,
            "type": None,
            "pid": None,
            "uid": None,
            "euid": None,
            "auid": None,
            "cwd": None,
            "argv": [],
            "exit_code": None,
            "success": True,
        }

        for line in lines:
            # Parse timestamp
            if line.startswith("time->"):
                time_str = line.split("->")[1].strip()
                try:
                    # Format like: Mon Jan 01 12:00:00 2024
                    event["timestamp"] = datetime.strptime(
                        time_str, "%a %b %d %H:%M:%S %Y"
                    ).timestamp()
                except ValueError:
                    pass

            # Parse type
            elif "type=" in line:
                type_match = AUDIT_TYPE_PATTERN.search(line)
                if type_match:
                    event["type"] = type_match.group(1)

            # Parse SYSCALL data
            elif "SYSCALL" in line:
                self._parse_ausearch_syscall(line, event)

            # Parse CWD
            elif "CWD" in line:
                cwd_match = re.search(r'cwd="([^"]*)"', line)
                if cwd_match:
                    event["cwd"] = cwd_match.group(1)

            # Parse EXECVE
            elif "EXECVE" in line:
                self._parse_ausearch_execve(line, event)

        # Validate and return
        if event["argv"]:
            return event
        return None

    def _parse_ausearch_syscall(self, line: str, event: dict):
        """Parse syscall info from ausearch output."""
        # ausearch format: SYSCALL arch=... syscall=... success=yes exit=0 ...
        parts = line.split()
        for part in parts:
            if part.startswith("pid="):
                event["pid"] = int(part.split("=")[1])
            elif part.startswith("auid="):
                event["auid"] = int(part.split("=")[1])
            elif part.startswith("uid="):
                event["uid"] = int(part.split("=")[1])
            elif part.startswith("euid="):
                event["euid"] = int(part.split("=")[1])
            elif part.startswith("exit="):
                try:
                    event["exit_code"] = int(part.split("=")[1])
                except ValueError:
                    pass
            elif part.startswith("success="):
                event["success"] = "yes" in part

    def _parse_ausearch_execve(self, line: str, event: dict):
        """Parse execve args from ausearch output."""
        # Format: argc=1 a0="ls" a1="-la" ...
        match = re.search(r'argc=(\d+)', line)
        if match:
            argc = int(match.group(1))
            args = {}

            for arg_match in AUDIT_ARG_PATTERN.finditer(line):
                idx = int(arg_match.group(1))
                args[idx] = arg_match.group(2)

            event["argv"] = [args[i] for i in range(argc) if i in args]

    def parse_text(self, text: str) -> List[dict]:
        """Parse ausearch output text."""
        events = []
        for line in text.split("\n"):
            event = self.parse_line(line)
            if event:
                events.append(event)

        # Don't forget last event
        final_event = self._finish_event()
        if final_event:
            events.append(final_event)

        return events
