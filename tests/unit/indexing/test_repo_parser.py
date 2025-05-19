from openhands_aci.indexing.locagent.repo.chunk_index.code_retriever import (
    build_code_retriever_from_repo as build_code_retriever
)

retriever = build_code_retriever(
    repo_path='/home/czl/workspace/projects/LocAgent',
    persist_path='/home/czl/workspace/projects/try/index',
    similarity_top_k=10,
)