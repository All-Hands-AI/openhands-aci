import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from git import Repo
from git.exc import InvalidGitRepositoryError

from .core import CodeSearchIndex


def _get_files_from_repo(
    repo_path: str, extensions: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Get all files from a git repository.

    Args:
        repo_path: Path to the git repository
        extensions: List of file extensions to include (e.g. ['.py', '.js'])
                  If None, includes all files

    Returns:
        List of document dictionaries with 'id' and 'content' keys
    """
    try:
        # Verify it's a git repo
        _ = Repo(repo_path)
    except InvalidGitRepositoryError:
        raise ValueError(f'{repo_path} is not a valid git repository')

    documents = []
    repo_path_obj = Path(repo_path)

    for root, _, files in os.walk(repo_path_obj):
        if '.git' in root:
            continue

        for file in files:
            if extensions and not any(file.endswith(ext) for ext in extensions):
                continue

            file_path = Path(root) / file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (UnicodeDecodeError, IOError):
                continue

            rel_path = file_path.relative_to(repo_path_obj)
            documents.append(
                {'id': str(rel_path), 'content': content, 'path': str(rel_path)}
            )

    return documents


def initialize_code_search(
    repo_path: str,
    save_dir: str,
    extensions: Optional[List[str]] = None,
    embedding_model: Optional[str] = None,
    batch_size: int = 32,
) -> Dict[str, Any]:
    """Initialize code search for a repository.

    Args:
        repo_path: Path to the git repository
        save_dir: Directory to save the search index
        extensions: List of file extensions to include
        embedding_model: Name or path of the embedding model to use
        batch_size: Batch size for embedding generation

    Returns:
        Dictionary with status and message
    """
    try:
        # Get all files from repo
        documents = _get_files_from_repo(repo_path, extensions)
        if not documents:
            return {
                'status': 'error',
                'message': f'No files found in repository {repo_path}',
            }

        # Create and save index
        index = CodeSearchIndex(embedding_model=embedding_model)
        index.add_documents(documents, batch_size=batch_size)
        index.save(save_dir)

        return {
            'status': 'success',
            'message': f'Successfully indexed {len(documents)} files from {repo_path}',
            'num_documents': len(documents),
        }

    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error initializing code search: {str(e)}',
        }


def search_code(save_dir: str, query: str, k: int = 5) -> Dict[str, Any]:
    """Search code in an indexed repository.

    Args:
        save_dir: Directory containing the search index
        query: Search query
        k: Number of results to return

    Returns:
        Dictionary with status and search results
    """
    try:
        # Load index
        index = CodeSearchIndex.load(save_dir)

        # Search
        results = index.search(query, k=k)

        return {'status': 'success', 'results': results}

    except Exception as e:
        return {'status': 'error', 'message': f'Error searching code: {str(e)}'}
