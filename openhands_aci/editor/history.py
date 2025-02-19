"""History management for file edits with disk-based storage and memory constraints."""

import logging
import tempfile
from pathlib import Path
from typing import List, Optional

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
            - The file cache is limited to prevent excessive disk usage
            - Older entries are automatically removed when limits are exceeded
        """
        self.max_history_per_file = max_history_per_file
        if history_dir is None:
            history_dir = Path(tempfile.mkdtemp(prefix='oh_editor_history_'))
        self.cache = FileCache(str(history_dir))
        self.logger = logging.getLogger(__name__)
        print(f"Available methods: {[method for method in dir(self) if not method.startswith('_')]}")
        print(f"pop_last_history in dir(self): {'pop_last_history' in dir(self)}")
        print(f"pop_last_history method: {getattr(self, 'pop_last_history', None)}")

    def _get_metadata_key(self, file_path: Path) -> str:
        return f'{file_path}.metadata'

    def _get_history_key(self, file_path: Path, counter: int) -> str:
        return f'{file_path}.{counter}'

    def add_history(self, file_path: Path, content: str):
        """Add a new history entry for a file."""
        metadata_key = self._get_metadata_key(file_path)
        metadata = self.cache.get(metadata_key, {'entries': [], 'counter': 0})
        counter = metadata['counter']

        self.logger.debug(f"add_history: Initial metadata for {file_path}: {metadata}")

        # Add new entry
        history_key = self._get_history_key(file_path, counter)
        self.cache.set(history_key, content)

        metadata['entries'].append(counter)
        metadata['counter'] += 1

        self.logger.debug(f"add_history: After adding new entry: {metadata}")

        # Keep only last N entries
        while len(metadata['entries']) > self.max_history_per_file:
            old_counter = metadata['entries'].pop(0)
            old_history_key = self._get_history_key(file_path, old_counter)
            self.cache.delete(old_history_key)
            self.logger.debug(f"add_history: Removed old entry: {old_counter}")

        self.cache.set(metadata_key, metadata)
        self.logger.debug(f"add_history: Final metadata for {file_path}: {metadata}")

    def pop_last_history(self, file_path: Path) -> Optional[str]:
        """Pop and return the most recent history entry for a file."""
        metadata_key = self._get_metadata_key(file_path)
        metadata = self.cache.get(metadata_key, {'entries': [], 'counter': 0})
        entries = metadata['entries']

        self.logger.debug(f"pop_last_history: Initial metadata for {file_path}: {metadata}")

        if not entries:
            self.logger.debug("pop_last_history: No entries found")
            return None

        # Pop and remove the last entry
        last_counter = entries.pop()
        history_key = self._get_history_key(file_path, last_counter)
        content = self.cache.get(history_key)

        self.logger.debug(f"pop_last_history: Removed entry with counter {last_counter}")

        if content is None:
            self.logger.warning(f'History entry not found for {file_path}')
        else:
            # Remove the entry from the cache
            self.cache.delete(history_key)
            self.logger.debug(f"pop_last_history: Deleted history key {history_key}")

        # Update metadata
        metadata['entries'] = entries
        self.cache.set(metadata_key, metadata)

        self.logger.debug(f"pop_last_history: Updated metadata for {file_path}: {metadata}")
        self.logger.debug(f"pop_last_history: Remaining entries: {len(entries)}")

        return content

    def get_metadata(self, file_path: Path):
        """Get metadata for a file (for testing purposes)."""
        metadata_key = self._get_metadata_key(file_path)
        metadata = self.cache.get(metadata_key, {'entries': [], 'counter': 0})
        self.logger.debug(f"get_metadata: Retrieved metadata for {file_path}: {metadata}")
        return metadata  # Return the actual metadata, not a copy

    def clear_history(self, file_path: Path):
        """Clear history for a given file."""
        metadata_key = self._get_metadata_key(file_path)
        metadata = self.cache.get(metadata_key, {'entries': [], 'counter': 0})

        # Delete all history entries
        for counter in metadata['entries']:
            history_key = self._get_history_key(file_path, counter)
            self.cache.delete(history_key)

        # Clear metadata
        self.cache.set(metadata_key, {'entries': [], 'counter': 0})

    def get_all_history(self, file_path: Path) -> List[str]:
        """Get all history entries for a file."""
        metadata_key = self._get_metadata_key(file_path)
        metadata = self.cache.get(metadata_key, {'entries': [], 'counter': 0})
        entries = metadata['entries']

        history = []
        for counter in entries:
            history_key = self._get_history_key(file_path, counter)
            content = self.cache.get(history_key)
            if content is not None:
                history.append(content)

        return history

    def get_metadata(self, file_path: Path):
        """Get metadata for a file (for testing purposes)."""
        metadata_key = self._get_metadata_key(file_path)
        return self.cache.get(metadata_key, {'entries': [], 'counter': 0})
