import os
import json
import hashlib
from pathlib import Path
from typing import Any, Optional

class FileCache:
    def __init__(self, directory: str, size_limit: Optional[int] = None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.size_limit = size_limit

    def _hash_key(self, key: str) -> str:
        return hashlib.md5(key.encode()).hexdigest()

    def _get_file_path(self, key: str) -> Path:
        hashed_key = self._hash_key(key)
        return self.directory / f"{hashed_key}.json"

    def set(self, key: str, value: Any) -> None:
        file_path = self._get_file_path(key)
        with open(file_path, 'w') as f:
            json.dump({"key": key, "value": value}, f)

    def get(self, key: str, default: Any = None) -> Any:
        file_path = self._get_file_path(key)
        if not file_path.exists():
            return default
        with open(file_path, 'r') as f:
            data = json.load(f)
            return data["value"] if data["key"] == key else default

    def delete(self, key: str) -> None:
        file_path = self._get_file_path(key)
        if file_path.exists():
            os.remove(file_path)

    def clear(self) -> None:
        for file in self.directory.glob("*.json"):
            os.remove(file)

    def __contains__(self, key: str) -> bool:
        return self._get_file_path(key).exists()

    def __len__(self) -> int:
        return len(list(self.directory.glob("*.json")))

    def __iter__(self):
        for file in self.directory.glob("*.json"):
            with open(file, 'r') as f:
                data = json.load(f)
                yield data["key"]