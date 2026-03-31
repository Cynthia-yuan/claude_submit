"""
Database storage layer for cmd-sniper.
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Any
from contextlib import contextmanager
from dataclasses import dataclass, asdict


@dataclass
class CommandRecord:
    """Represents a captured command execution."""
    timestamp: datetime
    uid: int
    username: str
    pid: int
    ppid: int
    cwd: str
    command: str
    full_command: str
    exit_code: Optional[int] = None
    capture_method: str = "auditd"
    hostname: str = ""
    argv: Optional[List[str]] = None
    env: Optional[dict[str, str]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        if self.argv:
            d["argv"] = json.dumps(self.argv)
        if self.env:
            d["env"] = json.dumps(self.env)
        return d


class Database:
    """SQLite database for storing command records."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL,
        uid INTEGER NOT NULL,
        username TEXT NOT NULL,
        pid INTEGER NOT NULL,
        ppid INTEGER NOT NULL,
        cwd TEXT,
        command TEXT NOT NULL,
        full_command TEXT NOT NULL,
        exit_code INTEGER,
        capture_method TEXT NOT NULL,
        hostname TEXT NOT NULL,
        argv TEXT,
        env TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_timestamp ON commands(timestamp);
    CREATE INDEX IF NOT EXISTS idx_user ON commands(uid);
    CREATE INDEX IF NOT EXISTS idx_command ON commands(command);
    CREATE INDEX IF NOT EXISTS idx_method ON commands(capture_method);
    CREATE INDEX IF NOT EXISTS idx_hostname ON commands(hostname);

    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        start_time DATETIME NOT NULL,
        end_time DATETIME,
        capture_method TEXT NOT NULL,
        status TEXT NOT NULL,
        events_count INTEGER DEFAULT 0
    );
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Create database file and schema if they don't exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self.get_connection() as conn:
            conn.executescript(self.SCHEMA)

    @contextmanager
    def get_connection(self):
        """Get a database connection with proper row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def insert_command(self, record: CommandRecord) -> int:
        """Insert a command record and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO commands (
                    timestamp, uid, username, pid, ppid, cwd, command,
                    full_command, exit_code, capture_method, hostname, argv, env
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.timestamp.isoformat(),
                    record.uid,
                    record.username,
                    record.pid,
                    record.ppid,
                    record.cwd,
                    record.command,
                    record.full_command,
                    record.exit_code,
                    record.capture_method,
                    record.hostname,
                    json.dumps(record.argv) if record.argv else None,
                    json.dumps(record.env) if record.env else None,
                ),
            )
            return cursor.lastrowid

    def insert_commands_batch(self, records: List[CommandRecord]) -> int:
        """Insert multiple command records efficiently."""
        if not records:
            return 0

        data = [
            (
                r.timestamp.isoformat(),
                r.uid,
                r.username,
                r.pid,
                r.ppid,
                r.cwd,
                r.command,
                r.full_command,
                r.exit_code,
                r.capture_method,
                r.hostname,
                json.dumps(r.argv) if r.argv else None,
                json.dumps(r.env) if r.env else None,
            )
            for r in records
        ]

        with self.get_connection() as conn:
            cursor = conn.executemany(
                """
                INSERT INTO commands (
                    timestamp, uid, username, pid, ppid, cwd, command,
                    full_command, exit_code, capture_method, hostname, argv, env
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data,
            )
            return cursor.rowcount

    def get_command_by_id(self, cmd_id: int) -> Optional[dict]:
        """Get a single command by ID."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM commands WHERE id = ?", (cmd_id,)).fetchone()
            if row:
                return dict(row)
            return None

    def get_commands(
        self,
        limit: int = 1000,
        offset: int = 0,
        user: Optional[int] = None,
        command: Optional[str] = None,
        method: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        search: Optional[str] = None,
    ) -> List[dict]:
        """Query commands with filters."""
        query = "SELECT * FROM commands WHERE 1=1"
        params = []

        if user is not None:
            query += " AND uid = ?"
            params.append(user)

        if command:
            query += " AND command = ?"
            params.append(command)

        if method:
            query += " AND capture_method = ?"
            params.append(method)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        if search:
            query += " AND (full_command LIKE ? OR command LIKE ?)"
            pattern = f"%{search}%"
            params.extend([pattern, pattern])

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_command_frequency(
        self,
        limit: int = 100,
        user: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[dict]:
        """Get command execution frequency statistics."""
        query = """
            SELECT command, full_command, COUNT(*) as count,
                   COUNT(DISTINCT uid) as unique_users
            FROM commands WHERE 1=1
        """
        params = []

        if user is not None:
            query += " AND uid = ?"
            params.append(user)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        query += " GROUP BY command, full_command ORDER BY count DESC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_user_activity(
        self,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[dict]:
        """Get user activity statistics."""
        query = """
            SELECT uid, username, COUNT(*) as command_count,
                   COUNT(DISTINCT command) as unique_commands,
                   MIN(timestamp) as first_seen,
                   MAX(timestamp) as last_seen
            FROM commands WHERE 1=1
        """
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        query += " GROUP BY uid, username ORDER BY command_count DESC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_time_distribution(
        self,
        granularity: str = "hour",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[dict]:
        """Get command distribution over time."""
        if granularity == "hour":
            fmt = "%Y-%m-%d %H:00"
        elif granularity == "day":
            fmt = "%Y-%m-%d"
        elif granularity == "month":
            fmt = "%Y-%m"
        else:
            fmt = "%Y-%m-%d %H:00"

        query = """
            SELECT strftime(?, timestamp) as time_bucket,
                   COUNT(*) as count
            FROM commands WHERE 1=1
        """
        params = [fmt]

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        query += " GROUP BY time_bucket ORDER BY time_bucket"

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_stats(self) -> dict:
        """Get overall database statistics."""
        with self.get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) as count FROM commands").fetchone()["count"]
            users = conn.execute("SELECT COUNT(DISTINCT uid) as count FROM commands").fetchone()["count"]
            unique_commands = conn.execute("SELECT COUNT(DISTINCT command) as count FROM commands").fetchone()["count"]

            first = conn.execute("SELECT MIN(timestamp) as ts FROM commands").fetchone()["ts"]
            last = conn.execute("SELECT MAX(timestamp) as ts FROM commands").fetchone()["ts"]

            # Method breakdown
            methods = conn.execute(
                "SELECT capture_method, COUNT(*) as count FROM commands GROUP BY capture_method"
            ).fetchall()
            method_breakdown = {m["capture_method"]: m["count"] for m in methods}

            return {
                "total_commands": total,
                "unique_users": users,
                "unique_commands": unique_commands,
                "first_command": first,
                "last_command": last,
                "method_breakdown": method_breakdown,
            }

    def cleanup_old_records(self, retention_days: int) -> int:
        """Remove records older than retention_days."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM commands
                WHERE timestamp < datetime('now', '-' || ? || ' days')
                """,
                (retention_days,),
            )
            return cursor.rowcount

    def set_metadata(self, key: str, value: str):
        """Set a metadata key-value pair."""
        with self.get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                (key, value),
            )

    def get_metadata(self, key: str) -> Optional[str]:
        """Get a metadata value by key."""
        with self.get_connection() as conn:
            row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else None

    def create_session(self, capture_method: str) -> int:
        """Create a new capture session."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions (start_time, capture_method, status)
                VALUES (datetime('now'), ?, 'running')
                """,
                (capture_method,),
            )
            return cursor.lastrowid

    def end_session(self, session_id: int, status: str = "stopped"):
        """End a capture session."""
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET end_time = datetime('now'), status = ?
                WHERE id = ?
                """,
                (status, session_id),
            )

    def get_active_sessions(self) -> List[dict]:
        """Get all active sessions."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE status = 'running'",
            ).fetchall()
            return [dict(row) for row in rows]

    def vacuum(self):
        """Vacuum the database to reclaim space."""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
