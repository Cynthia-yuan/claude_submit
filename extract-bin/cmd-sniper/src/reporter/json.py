"""
JSON export module for cmd-sniper.
"""
import json
from datetime import datetime
from typing import List, Any, Optional
from pathlib import Path

from storage import Database
from analyzer import CommandStats, PatternDetector


class JSONReporter:
    """Export command data to JSON format."""

    def __init__(self, db: Database):
        self.db = db
        self.stats = CommandStats(db)
        self.pattern = PatternDetector(db)

    def export(
        self,
        output_path: str,
        include_commands: bool = True,
        include_stats: bool = True,
        include_patterns: bool = True,
        limit: int = 100000,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> str:
        """
        Export data to JSON file.

        Returns the path to the exported file.
        """
        data = {
            "exported_at": datetime.now().isoformat(),
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
        }

        if include_stats:
            data["overview"] = self._get_overview()

        if include_commands:
            data["commands"] = self._get_commands(limit, start_time, end_time)

        if include_stats:
            data["top_commands"] = self.stats.get_top_commands(1000, start_time=start_time, end_time=end_time)
            data["top_users"] = self.stats.get_top_users(100, start_time=start_time, end_time=end_time)
            data["categories"] = self.stats.get_command_categories(start_time, end_time)
            data["time_series"] = self.stats.get_time_series("hour", start_time, end_time)

        if include_patterns:
            data["risk_commands"] = self.stats.get_risk_commands(100, start_time, end_time)
            data["sequences"] = self.stats.get_command_sequences(50)
            data["recurring_tasks"] = self.pattern.detect_recurring_tasks(5)

        # Write to file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        return output_path

    def _get_overview(self) -> dict:
        """Get overview statistics."""
        return self.stats.get_overview()

    def _get_commands(
        self,
        limit: int,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> List[dict]:
        """Get command records."""
        return self.db.get_commands(
            limit=limit,
            start_time=start_time,
            end_time=end_time,
        )

    def export_commands_only(
        self,
        output_path: str,
        user: Optional[int] = None,
        command: Optional[str] = None,
        limit: int = 100000,
        format: str = "json",
    ) -> str:
        """
        Export only command records in various formats.

        Args:
            output_path: Output file path
            user: Filter by user ID
            command: Filter by command name
            limit: Maximum number of records
            format: Output format (json, jsonl, csv)
        """
        commands = self.db.get_commands(
            limit=limit,
            user=user,
            command=command,
        )

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            with open(output_path, "w") as f:
                json.dump(commands, f, indent=2, default=str)

        elif format == "jsonl":
            with open(output_path, "w") as f:
                for cmd in commands:
                    json.dump(cmd, f, default=str)
                    f.write("\n")

        elif format == "csv":
            import csv
            with open(output_path, "w", newline="") as f:
                if commands:
                    writer = csv.DictWriter(f, fieldnames=commands[0].keys())
                    writer.writeheader()
                    writer.writerows(commands)

        return output_path

    def export_summary(self, output_path: str) -> str:
        """Export a concise summary report."""
        data = {
            "generated_at": datetime.now().isoformat(),
            "overview": self.stats.get_overview(),
            "top_10_commands": self.stats.get_top_commands(10),
            "top_10_users": self.stats.get_top_users(10),
            "command_categories": self.stats.get_command_categories(),
            "peak_hours": self.stats.get_peak_hours()[:10],
            "high_risk_commands": self.stats.get_risk_commands(20),
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        return output_path

    def export_user_report(self, uid: int, output_path: str) -> str:
        """Export detailed report for a specific user."""
        data = {
            "generated_at": datetime.now().isoformat(),
            "user_stats": self.stats.get_command_for_user(uid),
            "user_patterns": self.pattern.detect_learning_curve(uid),
            "time_patterns": self.pattern.detect_time_patterns(uid),
            "recent_commands": self.db.get_commands(limit=1000, user=uid),
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        return output_path

    def to_string(self, data: dict) -> str:
        """Convert data to JSON string."""
        return json.dumps(data, indent=2, default=str)
