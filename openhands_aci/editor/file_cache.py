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
        return self.directory / key

    def set(self, key: str, value: Any) -> None:
        file_path = self._get_file_path(key)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump({"value": value}, f)

    def get(self, key: str, default: Any = None) -> Any:
        file_path = self._get_file_path(key)
        if not file_path.exists():
            return default
        with open(file_path, 'r') as f:
            data = json.load(f)
            return data["value"]

    def delete(self, key: str) -> None:
        file_path = self._get_file_path(key)
        if file_path.exists():
            os.remove(file_path)
            # Remove empty parent directories
            parent = file_path.parent
            while parent != self.directory and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent

    def clear(self) -> None:
        for item in sorted(self.directory.glob('**/*'), key=lambda x: len(str(x.relative_to(self.directory))), reverse=True):
            if item.is_file():
                os.remove(item)
            elif item.is_dir() and item != self.directory:
                os.rmdir(item)

    def __contains__(self, key: str) -> bool:
        return self._get_file_path(key).exists()

    def __len__(self) -> int:
        return sum(1 for _ in self.directory.glob('**/*') if _.is_file())

    def __iter__(self):
        for file in self.directory.glob('**/*'):
            if file.is_file():
                yield str(file.relative_to(self.directory))