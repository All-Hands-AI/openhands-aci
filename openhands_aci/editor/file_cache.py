import os
import json
from pathlib import Path
from typing import Any, Optional

class FileCache:
    def __init__(self, directory: str, size_limit: Optional[int] = None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.size_limit = size_limit

    def _get_file_path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def set(self, key: str, value: Any) -> None:
        file_path = self._get_file_path(key)
        with open(file_path, 'w') as f:
            json.dump(value, f)

    def get(self, key: str, default: Any = None) -> Any:
        file_path = self._get_file_path(key)
        if not file_path.exists():
            return default
        with open(file_path, 'r') as f:
            return json.load(f)

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
            yield file.stem