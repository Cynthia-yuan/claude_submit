"""
Configuration management for cmd-sniper.
"""
import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class CaptureConfig:
    """Capture module configuration."""
    method: str = "auditd"  # 'auditd', 'ebpf', or 'both'
    auditd_log_path: str = "/var/log/audit/audit.log"
    ebpf_buffer_size: int = 1024
    filter_uids: Optional[List[int]] = None  # None means all users
    capture_env: bool = False  # Whether to capture environment variables


@dataclass
class StorageConfig:
    """Storage module configuration."""
    db_path: str = "/var/lib/cmd-sniper/commands.db"
    max_size_mb: int = 1000
    retention_days: int = 90


@dataclass
class AnalysisConfig:
    """Analysis module configuration."""
    min_command_length: int = 1
    exclude_commands: List[str] = field(default_factory=lambda: [
        "", "ls", "cd", "pwd", "history"
    ])
    risk_patterns: List[str] = field(default_factory=lambda: [
        r"sudo.*rm",
        r"rm\s+-rf\s+/",
        r">\s*/dev/sd[a-z]",
        r"dd\s+if=.*of=/dev/sd",
        r"chmod\s+000\s+",
        r"chattr\s+\+i",
    ])


@dataclass
class ReportConfig:
    """Report module configuration."""
    output_dir: str = "/var/lib/cmd-sniper/reports"
    top_n: int = 100
    include_time_series: bool = True
    include_user_heatmap: bool = True


@dataclass
class Config:
    """Main configuration class."""
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    report: ReportConfig = field(default_factory=ReportConfig)

    # Paths
    config_dir: str = "/etc/cmd-sniper"
    runtime_dir: str = "/run/cmd-sniper"
    log_dir: str = "/var/log/cmd-sniper"

    @classmethod
    def from_file(cls, path: str) -> "Config":
        """Load configuration from YAML file."""
        config_file = Path(path)
        if not config_file.exists():
            return cls()

        with open(config_file, "r") as f:
            data = yaml.safe_load(f) or {}

        return cls(
            capture=CaptureConfig(**data.get("capture", {})),
            storage=StorageConfig(**data.get("storage", {})),
            analysis=AnalysisConfig(**data.get("analysis", {})),
            report=ReportConfig(**data.get("report", {})),
            config_dir=data.get("config_dir", "/etc/cmd-sniper"),
            runtime_dir=data.get("runtime_dir", "/run/cmd-sniper"),
            log_dir=data.get("log_dir", "/var/log/cmd-sniper"),
        )

    def to_file(self, path: str):
        """Save configuration to YAML file."""
        config_file = Path(path)
        config_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "capture": self.capture.__dict__,
            "storage": self.storage.__dict__,
            "analysis": self.analysis.__dict__,
            "report": self.report.__dict__,
            "config_dir": self.config_dir,
            "runtime_dir": self.runtime_dir,
            "log_dir": self.log_dir,
        }

        with open(config_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        for path in [self.config_dir, self.runtime_dir, self.log_dir]:
            Path(path).mkdir(parents=True, exist_ok=True)

        # Storage parent dir
        Path(self.storage.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Reports dir
        Path(self.report.output_dir).mkdir(parents=True, exist_ok=True)


def get_default_config_path() -> str:
    """Get default configuration file path."""
    # Check for user-local config first
    user_config = Path.home() / ".config" / "cmd-sniper" / "config.yaml"
    if user_config.exists():
        return str(user_config)

    # System-wide config
    system_config = "/etc/cmd-sniper/config.yaml"
    if Path(system_config).exists():
        return system_config

    # Fall back to creating default in user directory
    return str(user_config)


def load_config(path: Optional[str] = None) -> Config:
    """Load configuration from file or return default."""
    config_path = path or get_default_config_path()
    return Config.from_file(config_path)
