from code_retriever import build_code_retriever_from_repo as build_code_retriever
retriever = build_code_retriever(
    '/home/gangda/workspace/czl/projects/LocAgent_anom',
    persist_path='/home/gangda/workspace/czl/projects/try/index',
    similarity_top_k=10,
)