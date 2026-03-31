"""
Pattern recognition module for command analysis.
"""
import re
from datetime import datetime, timedelta
from typing import List, Optional, Set, Tuple, Any
from collections import defaultdict
from difflib import SequenceMatcher

from storage import Database
from parser import CommandParser


class PatternDetector:
    """Detect patterns in command execution behavior."""

    def __init__(self, db: Database):
        self.db = db
        self.parser = CommandParser()

    def detect_recurring_tasks(self, min_occurrences: int = 5) -> List[dict]:
        """
        Detect tasks that run repeatedly.

        Looks for commands with similar patterns at regular intervals.
        """
        commands = self.db.get_commands(limit=1000000)

        # Group by normalized command
        normalized_groups = defaultdict(list)
        for cmd in commands:
            normalized = self.parser.normalize(cmd["full_command"])
            normalized_groups[normalized].append(cmd)

        # Look for time patterns
        recurring = []
        for normalized, cmds in normalized_groups.items():
            if len(cmds) < min_occurrences:
                continue

            # Analyze timing
            timestamps = []
            for cmd in cmds:
                try:
                    ts = datetime.fromisoformat(cmd["timestamp"])
                    timestamps.append(ts)
                except (ValueError, KeyError):
                    pass

            if len(timestamps) < min_occurrences:
                continue

            timestamps.sort()

            # Check for regular intervals
            intervals = []
            for i in range(1, len(timestamps)):
                diff = (timestamps[i] - timestamps[i - 1]).total_seconds()
                intervals.append(diff)

            if not intervals:
                continue

            # Calculate average interval and variance
            avg_interval = sum(intervals) / len(intervals)
            variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
            std_dev = variance ** 0.5

            # Coefficient of variation - lower means more regular
            cv = (std_dev / avg_interval) if avg_interval > 0 else 0

            if cv < 0.5:  # Low variation = regular pattern
                recurring.append({
                    "pattern": normalized,
                    "count": len(cmds),
                    "avg_interval_seconds": avg_interval,
                    "avg_interval_hours": avg_interval / 3600,
                    "regularity_cv": cv,
                    "first_seen": timestamps[0],
                    "last_seen": timestamps[-1],
                    "users": list(set(c["username"] for c in cmds)),
                })

        return sorted(recurring, key=lambda x: x["count"], reverse=True)

    def detect_workflow_patterns(self, user: Optional[int] = None) -> List[dict]:
        """
        Detect common workflow patterns (command sequences).

        Identifies commonly repeated sequences of commands.
        """
        # Get commands sorted by time
        commands = self.db.get_commands(limit=1000000, user=user)
        commands.sort(key=lambda x: x["timestamp"])

        # Group by user
        user_commands = defaultdict(list)
        for cmd in commands:
            user_commands[cmd["uid"]].append(cmd)

        # Find sequences of various lengths
        sequences = defaultdict(int)

        for uid, cmds in user_commands.items():
            # Try sequence lengths from 2 to 5
            for seq_len in range(2, 6):
                for i in range(len(cmds) - seq_len + 1):
                    # Extract sequence
                    sequence = []
                    valid = True

                    for j in range(seq_len):
                        cmd = cmds[i + j]
                        try:
                            ts = datetime.fromisoformat(cmd["timestamp"])
                        except (ValueError, KeyError):
                            valid = False
                            break

                        if sequence:
                            # Check if commands are within a reasonable time window
                            prev_ts = datetime.fromisoformat(cmds[i + j - 1]["timestamp"])
                            if (ts - prev_ts).total_seconds() > 300:  # 5 minutes max
                                valid = False
                                break

                        sequence.append((cmd["username"], cmd["command"]))

                    if valid:
                        seq_key = " -> ".join(f"{u}:{c}" for u, c in sequence)
                        sequences[seq_key] += 1

        # Return top sequences
        return [
            {"sequence": seq, "count": count}
            for seq, count in sorted(
                sequences.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:50]
        ]

    def detect_anomalies(
        self,
        user: Optional[int] = None,
        z_threshold: float = 2.0,
    ) -> List[dict]:
        """
        Detect anomalous command usage.

        Flags commands that deviate significantly from user's normal behavior.
        """
        # Get user's command history
        commands = self.db.get_commands(limit=1000000, user=user)

        # Build baseline for each user
        user_baselines = defaultdict(lambda: {"commands": Counter(), "total": 0})

        for cmd in commands:
            uid = cmd["uid"]
            user_baselines[uid]["commands"][cmd["command"]] += 1
            user_baselines[uid]["total"] += 1

        anomalies = []

        # Check each user's recent commands against baseline
        for uid, baseline in user_baselines.items():
            if baseline["total"] < 50:  # Not enough data
                continue

            # Calculate mean and std for each command frequency
            frequencies = list(baseline["commands"].values())
            if not frequencies:
                continue

            mean_freq = sum(frequencies) / len(frequencies)
            variance = sum((f - mean_freq) ** 2 for f in frequencies) / len(frequencies)
            std_freq = variance ** 0.5

            # Find rare commands (less than mean - z_threshold * std)
            rare_threshold = max(1, mean_freq - z_threshold * std_freq)
            common_threshold = mean_freq + z_threshold * std_freq

            for cmd, count in baseline["commands"].items():
                if count <= rare_threshold and count > 0:
                    anomalies.append({
                        "type": "rare_command",
                        "uid": uid,
                        "command": cmd,
                        "count": count,
                        "expected_min": int(rare_threshold),
                    })

        return sorted(anomalies, key=lambda x: x["count"])[:100]

    def detect_command_families(self) -> dict[str, List[str]]:
        """
        Group similar commands into families.

        Uses command parsing and similarity detection.
        """
        commands = self.db.get_commands(limit=100000)

        # Get unique commands
        unique_commands = set(c["command"] for c in commands)

        # Group by base command
        families = defaultdict(set)

        for cmd in unique_commands:
            base = self.parser.get_base_command(cmd)
            families[base].add(cmd)

        return {k: list(v) for k, v in families.items()}

    def detect_similar_commands(
        self,
        command: str,
        threshold: float = 0.7,
        limit: int = 20,
    ) -> List[dict]:
        """
        Find commands similar to the given command.

        Uses string similarity and command structure comparison.
        """
        commands = self.db.get_commands(limit=100000)
        unique_commands = set(c["full_command"] for c in commands)

        similarities = []

        for cmd in unique_commands:
            if cmd == command:
                continue

            # Calculate similarity
            similarity = SequenceMatcher(None, command, cmd).ratio()

            if similarity >= threshold:
                similarities.append({
                    "command": cmd,
                    "similarity": similarity,
                })

        return sorted(similarities, key=lambda x: x["similarity"], reverse=True)[:limit]

    def detect_learning_curve(self, uid: int) -> dict:
        """
        Analyze a user's command usage evolution over time.

        Detects patterns like:
        - Moving from basic to advanced commands
        - Decreasing use of sudo over time
        - Increasing command diversity
        """
        commands = self.db.get_commands(limit=1000000, user=uid)

        if len(commands) < 100:
            return {"error": "Not enough data"}

        # Split into time periods
        commands.sort(key=lambda x: x["timestamp"])

        n_periods = 5
        period_size = len(commands) // n_periods
        periods = []

        for i in range(n_periods):
            start_idx = i * period_size
            end_idx = start_idx + period_size if i < n_periods - 1 else len(commands)
            period_cmds = commands[start_idx:end_idx]

            unique_commands = len(set(c["command"] for c in period_cmds))
            sudo_count = sum(1 for c in period_cmds if "sudo" in c["full_command"])

            # Categorize commands
            categories = Counter()
            for cmd in period_cmds:
                cat = self.parser.classify(cmd["command"])
                categories[cat] += 1

            periods.append({
                "period": i + 1,
                "total": len(period_cmds),
                "unique": unique_commands,
                "diversity": unique_commands / len(period_cmds),
                "sudo_ratio": sudo_count / len(period_cmds),
                "top_category": categories.most_common(1)[0][0] if categories else None,
            })

        return {
            "uid": uid,
            "periods": periods,
            "trend_diversity": periods[-1]["diversity"] > periods[0]["diversity"],
            "trend_sudo": periods[-1]["sudo_ratio"] < periods[0]["sudo_ratio"],
        }

    def detect_time_patterns(self, uid: Optional[int] = None) -> List[dict]:
        """
        Detect temporal patterns in command usage.

        Identifies:
        - Working hours preference
        - Day of week preferences
        - Command types by time of day
        """
        commands = self.db.get_commands(limit=1000000, user=uid)

        # Analyze by hour and day
        hour_dist = defaultdict(int)
        day_dist = defaultdict(int)
        hour_category = defaultdict(lambda: defaultdict(int))

        for cmd in commands:
            try:
                ts = datetime.fromisoformat(cmd["timestamp"])
                hour_dist[ts.hour] += 1
                day_dist[ts.weekday()] += 1

                category = self.parser.classify(cmd["command"])
                hour_category[ts.hour][category] += 1
            except (ValueError, KeyError):
                pass

        # Find peak hours
        peak_hours = sorted(hour_dist.items(), key=lambda x: x[1], reverse=True)[:5]

        # Find peak days
        peak_days = sorted(day_dist.items(), key=lambda x: x[1], reverse=True)[:3]

        # Most common category per hour
        hour_top_category = {}
        for hour, categories in hour_category.items():
            if categories:
                hour_top_category[hour] = max(categories.items(), key=lambda x: x[1])[0]

        return {
            "peak_hours": [{"hour": h, "count": c} for h, c in peak_hours],
            "peak_days": [{"day": d, "count": c} for d, c in peak_days],
            "hour_categories": hour_top_category,
        }

    def detect_error_patterns(self) -> List[dict]:
        """
        Detect patterns in failed commands.

        Analyzes commands with non-zero exit codes.
        """
        commands = self.db.get_commands(
            limit=100000,
        )

        # Get failed commands
        failed = [c for c in commands if c.get("exit_code", 0) != 0]

        if not failed:
            return []

        # Group by command
        failed_by_command = defaultdict(list)
        for cmd in failed:
            failed_by_command[cmd["command"]].append(cmd)

        # Analyze failure patterns
        patterns = []
        for command, failures in failed_by_command.items():
            if len(failures) < 3:  # Minimum threshold
                continue

            # Users who failed
            users = set(f["username"] for f in failures)

            # Exit codes
            exit_codes = Counter(f.get("exit_code") for f in failures)

            patterns.append({
                "command": command,
                "failure_count": len(failures),
                "unique_users": len(users),
                "common_exit_codes": dict(exit_codes.most_common(5)),
                "users": list(users),
            })

        return sorted(patterns, key=lambda x: x["failure_count"], reverse=True)

    def detect_ssh_patterns(self) -> List[dict]:
        """
        Detect SSH connection patterns.

        Analyzes who connects where and how frequently.
        """
        commands = self.db.get_commands(limit=1000000)

        # Filter SSH commands
        ssh_commands = []
        for cmd in commands:
            if cmd["command"] in ("ssh", "scp", "sftp"):
                ssh_commands.append(cmd)

        if not ssh_commands:
            return []

        # Parse destinations
        destinations = Counter()
        user_destinations = defaultdict(Counter)

        for cmd in ssh_commands:
            full = cmd["full_command"]
            # Extract host from ssh user@host or ssh host
            match = re.search(r'ssh\s+(?:\w+@)?([\w.-]+)', full)
            if match:
                host = match.group(1)
                destinations[host] += 1
                user_destinations[cmd["username"]][host] += 1

        return [
            {
                "destination": dest,
                "count": count,
            }
            for dest, count in destinations.most_common(20)
        ]
