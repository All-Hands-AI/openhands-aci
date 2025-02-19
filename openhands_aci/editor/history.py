"""History management for file edits with disk-based storage and memory constraints."""

import tempfile
import json
import os
from pathlib import Path
from typing import Optional, List, Dict
import logging


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
        self.history_dir = history_dir
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def _get_metadata_path(self, file_path: Path) -> Path:
        """Get the path for the metadata file."""
        return self.history_dir / f"{file_path.name}.metadata.json"

    def _get_history_path(self, file_path: Path, counter: int) -> Path:
        """Get the path for a history file."""
        return self.history_dir / f"{file_path.name}.{counter}.history"

    def _load_metadata(self, file_path: Path) -> Dict[str, List[int]]:
        """Load metadata for a file."""
        metadata_path = self._get_metadata_path(file_path)
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                return json.load(f)
        return {"entries": [], "counter": 0}

    def _save_metadata(self, file_path: Path, metadata: Dict[str, List[int]]):
        """Save metadata for a file."""
        metadata_path = self._get_metadata_path(file_path)
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

    def add_history(self, file_path: Path, content: str):
        """Add a new history entry for a file."""
        metadata = self._load_metadata(file_path)
        counter = metadata["counter"]

        # Add new entry
        history_path = self._get_history_path(file_path, counter)
        with open(history_path, 'w') as f:
            f.write(content)

        metadata["entries"].append(counter)
        metadata["counter"] += 1

        # Keep only last N entries
        if len(metadata["entries"]) > self.max_history_per_file:
            old_counter = metadata["entries"].pop(0)
            old_history_path = self._get_history_path(file_path, old_counter)
            if old_history_path.exists():
                os.remove(old_history_path)

        self._save_metadata(file_path, metadata)

    def get_last_history(self, file_path: Path) -> Optional[str]:
        """Get the most recent history entry for a file."""
        metadata = self._load_metadata(file_path)
        entries = metadata["entries"]

        if not entries:
            return None

        # Get the last entry without removing it
        last_counter = entries[-1]
        history_path = self._get_history_path(file_path, last_counter)
        
        if not history_path.exists():
            self.logger.warning(f"History file not found: {history_path}")
            return None

        with open(history_path, 'r') as f:
            content = f.read()

        return content

    def clear_history(self, file_path: Path):
        """Clear history for a given file."""
        metadata = self._load_metadata(file_path)

        # Delete all history files
        for counter in metadata["entries"]:
            history_path = self._get_history_path(file_path, counter)
            if history_path.exists():
                os.remove(history_path)

        # Clear metadata
        metadata_path = self._get_metadata_path(file_path)
        if metadata_path.exists():
            os.remove(metadata_path)
