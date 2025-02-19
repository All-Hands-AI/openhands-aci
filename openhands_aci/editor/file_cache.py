import os
import json
import hashlib
from pathlib import Path
from typing import Any, Optional
import time

class FileCache:
    def __init__(self, directory: str, size_limit: Optional[int] = None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.size_limit = size_limit
        self.current_size = 0
        self._update_current_size()

    def _get_file_path(self, key: str) -> Path:
        hashed_key = hashlib.sha256(key.encode()).hexdigest()
        return self.directory / f"{hashed_key}.json"

    def _update_current_size(self):
        self.current_size = sum(f.stat().st_size for f in self.directory.glob('*.json') if f.is_file())

    def set(self, key: str, value: Any) -> None:
        file_path = self._get_file_path(key)
        content = json.dumps({"key": key, "value": value})
        content_size = len(content.encode('utf-8'))

        if self.size_limit is not None:
            while self.current_size + content_size > self.size_limit and len(self) > 1:
                self._evict_oldest()

        if file_path.exists():
            self.current_size -= file_path.stat().st_size

        with open(file_path, 'w') as f:
            f.write(content)

        self.current_size += content_size
        os.utime(file_path, (time.time(), time.time()))  # Update access and modification time

    def _evict_oldest(self):
        oldest_file = min((f for f in self.directory.glob('*.json') if f.is_file()), key=os.path.getctime)
        self.current_size -= oldest_file.stat().st_size
        os.remove(oldest_file)

    def get(self, key: str, default: Any = None) -> Any:
        file_path = self._get_file_path(key)
        if not file_path.exists():
            return default
        with open(file_path, 'r') as f:
            data = json.load(f)
            os.utime(file_path, (time.time(), time.time()))  # Update access time
            return data["value"]

    def delete(self, key: str) -> None:
        file_path = self._get_file_path(key)
        if file_path.exists():
            self.current_size -= file_path.stat().st_size
            os.remove(file_path)

    def clear(self) -> None:
        for item in self.directory.glob('*.json'):
            if item.is_file():
                os.remove(item)
        self.current_size = 0

    def __contains__(self, key: str) -> bool:
        return self._get_file_path(key).exists()

    def __len__(self) -> int:
        return sum(1 for _ in self.directory.glob('*.json') if _.is_file())

    def __iter__(self):
        for file in self.directory.glob('*.json'):
            if file.is_file():
                with open(file, 'r') as f:
                    data = json.load(f)
                    yield data["key"]

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)