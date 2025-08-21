import os
import shutil
import subprocess
import tempfile

import pytest

# Check if indexing dependencies are available
try:
    from openhands_aci.indexing.locagent.repo.chunk_index.code_retriever import (
        build_code_retriever_from_repo as build_code_retriever,
    )
    INDEXING_AVAILABLE = True
except ImportError:
    INDEXING_AVAILABLE = False


@pytest.fixture(scope='module')
def cloned_repo():
    repo_url = 'https://github.com/gersteinlab/LocAgent'
    temp_dir = tempfile.mkdtemp()
    try:
        subprocess.run(['git', 'clone', repo_url, temp_dir], check=True)
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)


@pytest.fixture(scope='module')
def persist_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)


@pytest.mark.skipif(
    os.getenv('CI') == 'true', reason='Skip resource-intensive test in CI'
)
@pytest.mark.skipif(
    not INDEXING_AVAILABLE, reason='Indexing dependencies not available'
)
def test_build_code_retriever(cloned_repo, persist_dir):
    retriever = build_code_retriever(
        repo_path=cloned_repo,
        persist_path=persist_dir,
        similarity_top_k=10,
    )

    assert retriever is not None
