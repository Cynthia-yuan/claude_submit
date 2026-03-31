"""
Command line parsing utilities.
"""
import re
import shlex
from typing import List, Tuple, Optional, Set
from pathlib import Path


class CommandParser:
    """
    Parse command line strings to extract meaningful components.

    Handles shell quoting, pipes, redirections, and command chaining.
    """

    # Command categories for classification
    CATEGORY_PATTERNS = {
        "system": [
            "systemctl", "service", "init", "shutdown", "reboot",
            "mount", "umount", "systemd", "journalctl",
        ],
        "network": [
            "ip", "ifconfig", "netstat", "ss", "ping", "traceroute",
            "nslookup", "dig", "curl", "wget", "ssh", "scp", "rsync",
            "iptables", "nft", "tcpdump", "wireshark",
        ],
        "file": [
            "ls", "cd", "pwd", "mkdir", "rmdir", "rm", "cp", "mv",
            "find", "locate", "touch", "chmod", "chown", "ln",
        ],
        "text": [
            "cat", "less", "more", "head", "tail", "grep", "sed",
            "awk", "cut", "sort", "uniq", "wc", "diff", "vim", "nano",
        ],
        "archive": [
            "tar", "gzip", "gunzip", "zip", "unzip", "xz", "bzip2",
        ],
        "process": [
            "ps", "top", "htop", "kill", "killall", "pgrep", "pkill",
            "nice", "renice", "nohup", "screen", "tmux",
        ],
        "user": [
            "who", "w", "id", "su", "sudo", "useradd", "userdel",
            "usermod", "groupadd", "passwd",
        ],
        "package": [
            "apt", "apt-get", "yum", "dnf", "pacman", "zypper",
            "pip", "npm", "yum", "apk",
        ],
        "docker": [
            "docker", "podman", "kubectl", "helm", "docker-compose",
        ],
        "git": [
            "git", "svn", "hg",
        ],
        "build": [
            "make", "cmake", "gcc", "g++", "clang", "javac",
            "mvn", "gradle", "cargo", "go",
        ],
        "database": [
            "mysql", "postgres", "psql", "mongosh", "redis-cli",
            "sqlite3",
        ],
    }

    # Risk patterns for security monitoring
    RISK_PATTERNS = {
        "critical": [
            r"rm\s+-rf\s+/",
            r">\s*/dev/sd[a-z]",
            r"dd\s+if=/dev/zero",
            r"dd\s+of=/dev/sd",
            r":\(\)\{\s*:\|:&\s*;\s*\}",  # Fork bomb
            r"chmod\s+000\s+/",
            r"chattr\s+\+i\s+/",
        ],
        "high": [
            r"rm\s+-rf",
            r"sudo\s+rm",
            r"mkfs\.",  # Format filesystem
            r"fdisk",
            r"parted",
            r"crontab\s+-r",
        ],
        "medium": [
            r"sudo",
            r"su\s+-",
            r"\.ssh/",
            r"\.gnupg/",
            r"/etc/shadow",
            r"/etc/passwd",
        ],
    }

    def __init__(self):
        # Compile risk patterns
        self._compiled_risk = {}
        for level, patterns in self.RISK_PATTERNS.items():
            self._compiled_risk[level] = [
                re.compile(p) for p in patterns
            ]

    def parse(self, command: str) -> dict:
        """
        Parse a command string into components.

        Returns:
            dict with:
                - base_command: The main executable (e.g., "sudo" -> "apt")
                - command: The first argument (actual command)
                - arguments: List of arguments
                - flags: List of flags (options starting with -)
                - pipes: Whether command contains pipes
                - redirects: List of redirections
                - background: Whether command runs in background (&)
                - category: Command category
        """
        result = {
            "base_command": "",
            "command": "",
            "arguments": [],
            "flags": [],
            "pipes": False,
            "redirects": [],
            "background": False,
            "category": "other",
        }

        try:
            # Split on pipes first
            pipe_sections = command.split("|")
            result["pipes"] = len(pipe_sections) > 1

            # Parse the first section (main command)
            main_cmd = pipe_sections[0].strip()

            # Check for background
            if main_cmd.endswith("&"):
                main_cmd = main_cmd[:-1].strip()
                result["background"] = True

            # Parse redirects
            main_cmd, redirects = self._parse_redirects(main_cmd)
            result["redirects"] = redirects

            # Tokenize (handle quotes properly)
            try:
                tokens = shlex.split(main_cmd)
            except ValueError:
                # Fallback for unmatched quotes
                tokens = main_cmd.split()

            if not tokens:
                return result

            # Handle sudo prefix
            if tokens[0] in ("sudo", "doas"):
                result["base_command"] = tokens[0]
                if len(tokens) > 1:
                    result["command"] = tokens[1]
                    # The rest are args to the actual command
                    tokens = tokens[1:]
                else:
                    return result
            else:
                result["command"] = tokens[0]

            # Extract flags and arguments
            for token in tokens[1:]:
                if token.startswith("-"):
                    result["flags"].append(token)
                else:
                    result["arguments"].append(token)

            # Classify command
            result["category"] = self.classify(result["command"])

        except Exception:
            result["command"] = command.split()[0] if command.split() else ""

        return result

    def _parse_redirects(self, command: str) -> Tuple[str, List[str]]:
        """Extract and return redirects from command."""
        redirects = []

        # Common redirect patterns
        patterns = [
            (r">\s*\S+", "output"),
            (r">>\s*\S+", "append"),
            (r"<\s*\S+", "input"),
            (r"2>\s*\S+", "error"),
            (r"2>>\s*\S+", "error_append"),
            (r"&>\s*\S+", "all"),
        ]

        remaining = command
        for pattern, redirect_type in patterns:
            matches = re.findall(pattern, remaining)
            redirects.extend([(redirect_type, m.strip()) for m in matches])
            remaining = re.sub(pattern, "", remaining)

        return remaining.strip(), redirects

    def classify(self, command: str) -> str:
        """Classify a command into a category."""
        cmd_base = Path(command).name.lower()

        for category, commands in self.CATEGORY_PATTERNS.items():
            if cmd_base in commands:
                return category

        return "other"

    def get_risk_level(self, command: str) -> Optional[str]:
        """
        Assess the risk level of a command.

        Returns: 'critical', 'high', 'medium', or None
        """
        for level in ("critical", "high", "medium"):
            for pattern in self._compiled_risk[level]:
                if pattern.search(command):
                    return level
        return None

    def get_base_command(self, command: str) -> str:
        """Get the base command (strips sudo, path, etc.)."""
        parsed = self.parse(command)

        # If sudo, get the actual command
        if parsed["base_command"] in ("sudo", "doas"):
            return parsed["command"]

        # Get just the command name without path
        return Path(parsed["command"]).name

    def is_similar(self, cmd1: str, cmd2: str, ignore_args: bool = True) -> bool:
        """
        Check if two commands are similar.

        Args:
            ignore_args: If True, compare only base commands
        """
        base1 = self.get_base_command(cmd1)
        base2 = self.get_base_command(cmd2)

        if ignore_args:
            return base1 == base2

        # Compare arguments too, ignoring specific values
        parsed1 = self.parse(cmd1)
        parsed2 = self.parse(cmd2)

        return (
            parsed1["command"] == parsed2["command"]
            and set(parsed1["flags"]) == set(parsed2["flags"])
        )

    def extract_patterns(self, commands: List[str]) -> dict[str, int]:
        """
        Extract common command patterns from a list of commands.

        Groups similar commands (same base command) and counts occurrences.
        """
        patterns = {}

        for cmd in commands:
            base = self.get_base_command(cmd)
            patterns[base] = patterns.get(base, 0) + 1

        return patterns

    def normalize(self, command: str) -> str:
        """
        Normalize a command for comparison.

        Removes:
        - Specific file paths
        - Specific IDs
        - Timestamps
        """
        parsed = self.parse(command)
        normalized_parts = [parsed["command"]]

        # Add flags
        normalized_parts.extend(parsed["flags"])

        # Add arguments but normalize certain patterns
        for arg in parsed["arguments"]:
            # Skip paths
            if "/" in arg:
                normalized_parts.append("<path>")
            # Skip IDs/numbers
            elif arg.isdigit():
                normalized_parts.append("<id>")
            else:
                normalized_parts.append(arg)

        return " ".join(normalized_parts)


class CommandChain:
    """
    Analyze command chains (sequences of commands).

    Useful for detecting patterns like: build -> test -> deploy
    """

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self._chains: dict[str, int] = {}

    def add_command(self, command: str, previous_commands: List[str]):
        """
        Add a command and track its chain with previous commands.

        Args:
            command: The new command
            previous_commands: List of recent commands (most recent last)
        """
        if not previous_commands:
            return

        # Create chain key from recent commands
        window = previous_commands[-self.window_size:] + [command]
        chain_key = " -> ".join(window)

        self._chains[chain_key] = self._chains.get(chain_key, 0) + 1

    def get_common_chains(self, limit: int = 20) -> List[Tuple[str, int]]:
        """Get the most common command chains."""
        return sorted(
            self._chains.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:limit]

    def clear(self):
        """Clear all recorded chains."""
        self._chains.clear()


def shell_quote(s: str) -> str:
    """Quote a string for safe shell usage."""
    return shlex.quote(s)


def shell_unquote(s: str) -> str:
    """Unquote a shell-quoted string."""
    try:
        return shlex.split(s)[0] if shlex.split(s) else s
    except ValueError:
        return s
