from pathlib import Path

from .logger import oh_aci_logger as logger
from .path import get_depth_of_rel_path, has_image_extension


class GitRepoUtils:
    def __init__(self, abs_repo_path: str) -> None:
        from git import Repo

        if not Path(abs_repo_path).is_absolute():
            raise ValueError('The path must be absolute')

        self.repo_path = Path(abs_repo_path)
        try:
            self.repo = Repo(self.repo_path)
        except Exception:
            logger.warning(f'Could not find git repository at {abs_repo_path}.')
            raise Exception(
                'Could not find any git repository in the working directory.'
            )

    def get_all_absolute_tracked_files(self, depth: int | None = None) -> list[str]:
        return [
            str(self.repo_path / item.path)
            for item in self.repo.tree().traverse()
            if item.type == 'blob'
            and (not depth or get_depth_of_rel_path(item.path) <= depth)
        ]

    def get_all_relative_tracked_files(self, depth: int | None = None) -> list[str]:
        return [
            item.path
            for item in self.repo.tree().traverse()
            if item.type == 'blob'
            and (not depth or get_depth_of_rel_path(item.path) <= depth)
        ]

    def get_all_absolute_staged_files(self) -> list[str]:
        return [
            str(self.repo_path / item.a_path) for item in self.repo.index.diff('HEAD')
        ]

    def get_absolute_tracked_files_in_directory(
        self, rel_dir_path: str, depth: int | None = None
    ) -> list[str]:
        rel_dir_path = rel_dir_path.rstrip('/')
        return [
            str(self.repo_path / item.path)
            for item in self.repo.tree().traverse()
            if item.path.startswith(rel_dir_path + '/')
            and item.type == 'blob'
            and (not depth or get_depth_of_rel_path(item.path) <= depth)
        ]


def get_modified_time(abs_path: str) -> int:
    if not Path(abs_path).exists():
        return -1

    return int(Path(abs_path).stat().st_mtime)


def read_text(abs_path: str) -> str:
    if has_image_extension(abs_path):
        return ''  # Not support image files yet!

    with open(abs_path, 'r') as f:
        return f.read()
