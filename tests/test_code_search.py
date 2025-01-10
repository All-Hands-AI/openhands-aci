import os
import tempfile
from pathlib import Path

import pytest
from git import Repo

from openhands_aci.code_search import (
    CodeSearchIndex,
    initialize_code_search,
    search_code,
)


@pytest.fixture
def test_repo():
    """Create a temporary git repository with some test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Initialize git repo
        repo = Repo.init(temp_dir)

        # Create test files
        files = {
            'main.py': 'def hello():\n    print("Hello, World!")',
            'utils/helper.py': 'def add(a, b):\n    return a + b',
            'README.md': '# Test Repository\nThis is a test.',
        }

        for path, content in files.items():
            file_path = Path(temp_dir) / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)

        # Add and commit files
        repo.index.add('*')
        repo.index.commit('Initial commit')

        yield temp_dir


def test_initialize_code_search(test_repo):
    """Test initializing code search for a repository."""
    with tempfile.TemporaryDirectory() as save_dir:
        # Initialize with only Python files
        result = initialize_code_search(
            test_repo,
            save_dir,
            extensions=['.py'],
            embedding_model='BAAI/bge-base-en-v1.5',
        )

        assert result['status'] == 'success'
        assert result['num_documents'] == 2  # main.py and helper.py

        # Check that index files were created
        assert os.path.exists(os.path.join(save_dir, 'index.faiss'))
        assert os.path.exists(os.path.join(save_dir, 'documents.pkl'))


def test_search_code(test_repo):
    """Test searching code in an indexed repository."""
    with tempfile.TemporaryDirectory() as save_dir:
        # First initialize
        initialize_code_search(
            test_repo,
            save_dir,
            extensions=['.py'],
            embedding_model='BAAI/bge-base-en-v1.5',
        )

        # Test search
        result = search_code(save_dir, 'function that adds two numbers')

        assert result['status'] == 'success'
        assert len(result['results']) > 0

        # The add function should be in the results
        found_add = False
        for doc in result['results']:
            if 'add' in doc['content']:
                found_add = True
                break
        assert found_add


def test_code_search_index():
    """Test the CodeSearchIndex class directly."""
    # Create test documents
    docs = [
        {'id': '1', 'content': 'def add(a, b): return a + b'},
        {'id': '2', 'content': 'def subtract(a, b): return a - b'},
        {'id': '3', 'content': 'print("Hello, World!")'},
    ]

    # Create index
    index = CodeSearchIndex(embedding_model='BAAI/bge-base-en-v1.5')
    index.add_documents(docs)

    # Test search
    results = index.search('function that adds numbers')
    assert len(results) > 0
    assert any('add' in doc['content'] for doc in results)

    # Test save and load
    with tempfile.TemporaryDirectory() as temp_dir:
        index.save(temp_dir)
        loaded_index = CodeSearchIndex.load(temp_dir)

        # Search with loaded index
        loaded_results = loaded_index.search('function that adds numbers')
        assert len(loaded_results) == len(results)


def test_error_handling():
    """Test error handling in the tools."""
    # Test with non-existent repository
    result = initialize_code_search(
        '/path/that/does/not/exist', '/tmp/save', extensions=['.py']
    )
    assert result['status'] == 'error'
    assert 'Error' in result['message']

    # Test search with non-existent index
    result = search_code('/path/that/does/not/exist', 'query')
    assert result['status'] == 'error'
    assert 'Error' in result['message']
