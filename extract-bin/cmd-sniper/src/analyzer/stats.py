"""
Statistical analysis module for captured commands.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Any
from collections import Counter, defaultdict
import statistics

from storage import Database
from parser import CommandParser


class CommandStats:
    """Statistical analysis of command execution data."""

    def __init__(self, db: Database):
        self.db = db
        self.parser = CommandParser()

    def get_overview(self) -> dict[str, Any]:
        """Get overall statistics overview."""
        stats = self.db.get_stats()

        # Calculate timespan
        if stats["first_command"] and stats["last_command"]:
            first = datetime.fromisoformat(stats["first_command"])
            last = datetime.fromisoformat(stats["last_command"])
            stats["timespan_days"] = (last - first).days
            stats["timespan_hours"] = (last - first).total_seconds() / 3600
        else:
            stats["timespan_days"] = 0
            stats["timespan_hours"] = 0

        # Calculate average commands per day
        if stats["timespan_days"] > 0:
            stats["avg_commands_per_day"] = stats["total_commands"] / stats["timespan_days"]
        else:
            stats["avg_commands_per_day"] = stats["total_commands"]

        return stats

    def get_top_commands(
        self,
        limit: int = 100,
        user: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[dict]:
        """Get most frequently executed commands."""
        return self.db.get_command_frequency(limit, user, start_time, end_time)

    def get_top_users(
        self,
        limit: int = 50,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[dict]:
        """Get most active users."""
        return self.db.get_user_activity(limit, start_time, end_time)

    def get_command_categories(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict[str, int]:
        """Get command distribution by category."""
        commands = self.db.get_commands(
            limit=100000,
            start_time=start_time,
            end_time=end_time,
        )

        categories = Counter()
        for cmd in commands:
            category = self.parser.classify(cmd["command"])
            categories[category] += 1

        return dict(categories)

    def get_time_series(
        self,
        granularity: str = "hour",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[dict]:
        """Get command execution time distribution."""
        return self.db.get_time_distribution(granularity, start_time, end_time)

    def get_hourly_heatmap(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict[int, dict[int, int]]:
        """
        Get activity heatmap by hour and day of week.

        Returns: {day_of_week: {hour: count}}
        """
        commands = self.db.get_commands(
            limit=1000000,
            start_time=start_time,
            end_time=end_time,
        )

        heatmap = defaultdict(lambda: defaultdict(int))

        for cmd in commands:
            try:
                ts = datetime.fromisoformat(cmd["timestamp"])
                hour = ts.hour
                day_of_week = ts.weekday()  # 0 = Monday
                heatmap[day_of_week][hour] += 1
            except (ValueError, KeyError):
                continue

        return dict(heatmap)

    def get_command_for_user(self, uid: int) -> dict:
        """Get detailed statistics for a specific user."""
        # Get user's commands
        commands = self.db.get_commands(limit=1000000, user=uid)

        if not commands:
            return {
                "uid": uid,
                "username": None,
                "total_commands": 0,
                "unique_commands": 0,
                "top_commands": [],
                "categories": {},
                "most_active_hours": [],
            }

        username = commands[0]["username"]

        # Count commands
        total = len(commands)
        unique = len(set(c["command"] for c in commands))

        # Top commands
        command_counts = Counter(c["command"] for c in commands)
        top_commands = [
            {"command": cmd, "count": count}
            for cmd, count in command_counts.most_common(20)
        ]

        # Categories
        categories = Counter()
        for cmd in commands:
            cat = self.parser.classify(cmd["command"])
            categories[cat] += 1

        # Most active hours
        hour_counts = Counter()
        for cmd in commands:
            try:
                ts = datetime.fromisoformat(cmd["timestamp"])
                hour_counts[ts.hour] += 1
            except (ValueError, KeyError):
                pass

        most_active_hours = [
            {"hour": h, "count": c}
            for h, c in hour_counts.most_common(5)
        ]

        return {
            "uid": uid,
            "username": username,
            "total_commands": total,
            "unique_commands": unique,
            "top_commands": top_commands,
            "categories": dict(categories),
            "most_active_hours": most_active_hours,
        }

    def get_risk_commands(
        self,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[dict]:
        """Get potentially risky commands."""
        commands = self.db.get_commands(
            limit=100000,
            start_time=start_time,
            end_time=end_time,
        )

        risk_commands = []

        for cmd in commands:
            risk_level = self.parser.get_risk_level(cmd["full_command"])
            if risk_level:
                risk_commands.append({
                    "timestamp": cmd["timestamp"],
                    "uid": cmd["uid"],
                    "username": cmd["username"],
                    "command": cmd["command"],
                    "full_command": cmd["full_command"],
                    "risk_level": risk_level,
                })

        # Sort by risk level (critical first) and time
        risk_order = {"critical": 0, "high": 1, "medium": 2}
        risk_commands.sort(
            key=lambda x: (risk_order.get(x["risk_level"], 3), x["timestamp"])
        )

        return risk_commands[:limit]

    def get_command_variance(self) -> dict[str, Any]:
        """
        Analyze command diversity/variance.

        Measures how diverse the command usage is.
        """
        commands = self.db.get_commands(limit=1000000)
        total = len(commands)

        if total == 0:
            return {"entropy": 0, "unique_ratio": 0, "dominant_command": None}

        # Count unique commands
        unique_commands = set(c["command"] for c in commands)
        unique_count = len(unique_commands)

        # Calculate unique ratio
        unique_ratio = unique_count / total

        # Find dominant command
        command_counts = Counter(c["command"] for c in commands)
        dominant_cmd, dominant_count = command_counts.most_common(1)[0]
        dominant_ratio = dominant_count / total

        # Calculate entropy (simplified)
        entropy = 0
        for count in command_counts.values():
            p = count / total
            entropy -= p * (p and __import__("math").log2(p) or 0)

        return {
            "entropy": entropy,
            "unique_ratio": unique_ratio,
            "unique_commands": unique_count,
            "total_commands": total,
            "dominant_command": dominant_cmd,
            "dominant_ratio": dominant_ratio,
        }

    def get_command_sequences(
        self,
        user: Optional[int] = None,
        limit: int = 50,
    ) -> List[dict]:
        """
        Find common command sequences (chains).

        Useful for identifying workflows.
        """
        window_size = 3
        sequences = defaultdict(int)

        # Get commands sorted by time
        commands = self.db.get_commands(
            limit=100000,
            user=user,
        )
        commands.sort(key=lambda x: x["timestamp"])

        # Group by user
        user_commands = defaultdict(list)
        for cmd in commands:
            user_commands[cmd["uid"]].append(cmd)

        # Find sequences for each user
        for uid, user_cmds in user_commands.items():
            for i in range(len(user_cmds) - window_size + 1):
                sequence = tuple(
                    user_cmds[i + j]["command"]
                    for j in range(window_size)
                )
                sequences[sequence] += 1

        # Return top sequences
        top_sequences = [
            {
                "sequence": " -> ".join(seq),
                "count": count,
            }
            for seq, count in sorted(
                sequences.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:limit]
        ]

        return top_sequences

    def get_peak_hours(
        self,
        user: Optional[int] = None,
    ) -> List[dict]:
        """Get peak activity hours."""
        commands = self.db.get_commands(
            limit=1000000,
            user=user,
        )

        hour_counts = Counter()
        for cmd in commands:
            try:
                ts = datetime.fromisoformat(cmd["timestamp"])
                hour_counts[ts.hour] += 1
            except (ValueError, KeyError):
                pass

        return [
            {"hour": h, "count": c}
            for h, c in hour_counts.most_common()
        ]

    def compare_users(self, uid1: int, uid2: int) -> dict:
        """Compare command patterns between two users."""
        stats1 = self.get_command_for_user(uid1)
        stats2 = self.get_command_for_user(uid2)

        # Get command overlap
        cmds1 = set(c["command"] for c in self.db.get_commands(limit=1000000, user=uid1))
        cmds2 = set(c["command"] for c in self.db.get_commands(limit=1000000, user=uid2))

        overlap = cmds1 & cmds2
        unique1 = cmds1 - cmds2
        unique2 = cmds2 - cmds1

        # Jaccard similarity
        jaccard = len(overlap) / len(cmds1 | cmds2) if (cmds1 | cmds2) else 0

        return {
            "user1": stats1,
            "user2": stats2,
            "overlap_count": len(overlap),
            "unique_to_user1": len(unique1),
            "unique_to_user2": len(unique2),
            "jaccard_similarity": jaccard,
            "common_commands": list(overlap)[:20],
        }

    def get_command_trend(
        self,
        command: str,
        days: int = 30,
    ) -> List[dict]:
        """Get usage trend for a specific command over time."""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        commands = self.db.get_commands(
            limit=100000,
            command=command,
            start_time=start_time,
            end_time=end_time,
        )

        # Group by day
        daily_counts = defaultdict(int)
        for cmd in commands:
            try:
                ts = datetime.fromisoformat(cmd["timestamp"])
                day = ts.date().isoformat()
                daily_counts[day] += 1
            except (ValueError, KeyError):
                pass

        # Fill in missing days
        trend = []
        current = start_time.date()
        while current <= end_time.date():
            trend.append({
                "date": current.isoformat(),
                "count": daily_counts.get(current.isoformat(), 0),
            })
            current += timedelta(days=1)

        return trend

    def get_summary_report(self) -> str:
        """Generate a text summary report."""
        overview = self.get_overview()
        top_commands = self.get_top_commands(10)
        top_users = self.get_top_users(10)
        categories = self.get_command_categories()
        risk_commands = self.get_risk_commands(10)

        lines = [
            "=" * 60,
            "CMD-SNIPER COMMAND ANALYSIS REPORT",
            "=" * 60,
            "",
            "OVERVIEW",
            "-" * 40,
            f"Total Commands: {overview['total_commands']:,}",
            f"Unique Commands: {overview['unique_commands']:,}",
            f"Unique Users: {overview['unique_users']}",
            f"Timespan: {overview['timespan_days']:.1f} days",
            f"Avg Commands/Day: {overview['avg_commands_per_day']:.1f}",
            "",
            "TOP 10 COMMANDS",
            "-" * 40,
        ]

        for i, cmd in enumerate(top_commands, 1):
            lines.append(f"{i:2}. {cmd['command']:20} ({cmd['count']:>5}x)")

        lines.extend([
            "",
            "TOP 10 USERS",
            "-" * 40,
        ])

        for i, user in enumerate(top_users, 1):
            lines.append(
                f"{i:2}. {user['username']:15} ({user['command_count']:>5} commands, "
                f"{user['unique_commands']} unique)"
            )

        lines.extend([
            "",
            "COMMAND CATEGORIES",
            "-" * 40,
        ])

        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            lines.append(f"  {cat:15}: {count:>5}")

        if risk_commands:
            lines.extend([
                "",
                "RECENT RISKY COMMANDS",
                "-" * 40,
            ])
            for cmd in risk_commands[:10]:
                lines.append(
                    f"  [{cmd['risk_level'].upper()}] {cmd['username']}: {cmd['full_command'][:60]}"
                )

        lines.append("")
        return "\n".join(lines)
