"""
Base capture class for cmd-sniper.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime
import signal
import sys

from ..storage import Database, CommandRecord


class CaptureBase(ABC):
    """Abstract base class for command capture methods."""

    def __init__(self, db: Database, config=None):
        self.db = db
        self.config = config
        self.running = False
        self.session_id: Optional[int] = None

    @abstractmethod
    def start(self):
        """Start capturing commands."""
        pass

    @abstractmethod
    def stop(self):
        """Stop capturing commands."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this capture method is available on the system."""
        pass

    def _create_session(self) -> int:
        """Create a new capture session in the database."""
        self.session_id = self.db.create_session(self.get_method_name())
        return self.session_id

    def _close_session(self, status: str = "stopped"):
        """Close the current capture session."""
        if self.session_id:
            self.db.end_session(self.session_id, status)
            self.session_id = None

    @abstractmethod
    def get_method_name(self) -> str:
        """Return the name of this capture method."""
        pass

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)


class CaptureError(Exception):
    """Base exception for capture errors."""
    pass


class CaptureNotAvailableError(CaptureError):
    """Raised when a capture method is not available."""
    pass
