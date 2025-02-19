"""History management for file edits with disk-based storage and memory constraints."""

import tempfile
from pathlib import Path
from typing import Optional
import logging
from .file_cache import FileCache

class FileHistoryManager:
    """Manages file edit history with disk-based storage and memory constraints."""

    def __init__(
        self, max_history_per_file: int = 5, history_dir: Optional[Path] = None
    ):
        """Initialize the history manager.

        Args:
            max_history_per_file: Maximum number of history entries to keep per file (default: 5)
            history_dir: Directory to store history files. If None, uses a temp directory

        Notes:
            - Each file's history is limited to the last N entries to conserve memory
            - Older entries are automatically removed when limits are exceeded
        """
        self.max_history_per_file = max_history_per_file
        if history_dir is None:
            history_dir = Path(tempfile.mkdtemp(prefix='oh_editor_history_'))
        self.cache = FileCache(str(history_dir))
        self.logger = logging.getLogger(__name__)

    def add_history(self, file_path: Path, content: str):
        """Add a new history entry for a file."""
        key = str(file_path)
        metadata = self.cache.get(f"{key}:metadata", {"entries": [], "counter": 0})
        counter = metadata["counter"]

        # Add new entry
        self.cache.set(f"{key}:{counter}", content)

        metadata["entries"].append(counter)
        metadata["counter"] += 1

        # Keep only last N entries
        if len(metadata["entries"]) > self.max_history_per_file:
            old_counter = metadata["entries"].pop(0)
            self.cache.delete(f"{key}:{old_counter}")

        self.cache.set(f"{key}:metadata", metadata)

    def get_last_history(self, file_path: Path) -> Optional[str]:
        """Get the most recent history entry for a file."""
        key = str(file_path)
        metadata = self.cache.get(f"{key}:metadata", {"entries": [], "counter": 0})
        entries = metadata["entries"]

        if not entries:
            return None

        # Get the last entry without removing it
        last_counter = entries[-1]
        content = self.cache.get(f"{key}:{last_counter}")

        if content is None:
            self.logger.warning(f"History entry not found for {file_path}")
            return None

        return content

    def clear_history(self, file_path: Path):
        """Clear history for a given file."""
        key = str(file_path)
        metadata = self.cache.get(f"{key}:metadata", {"entries": [], "counter": 0})

        # Delete all history entries
        for counter in metadata["entries"]:
            self.cache.delete(f"{key}:{counter}")

        # Clear metadata
        self.cache.delete(f"{key}:metadata")
