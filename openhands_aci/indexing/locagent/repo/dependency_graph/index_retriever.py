import pickle
import re

# from ..chunk_index.index.epic_split import EpicSplitter
import warnings
from typing import Optional

import networkx as nx
import Stemmer
from llama_index.core import Document
from llama_index.core.node_parser import SimpleFileNodeParser
from llama_index.retrievers.bm25 import BM25Retriever
from rapidfuzz import fuzz, process

from .build_graph import (
    NODE_TYPE_CLASS,
    NODE_TYPE_DIRECTORY,
    NODE_TYPE_FILE,
    NODE_TYPE_FUNCTION,
    VALID_NODE_TYPES,
)
from .traverse_graph import RepoEntitySearcher, is_test_file

warnings.simplefilter('ignore', FutureWarning)

NTYPES = [
    NODE_TYPE_DIRECTORY,
    NODE_TYPE_FILE,
    NODE_TYPE_FUNCTION,
    NODE_TYPE_CLASS,
]


def build_retriever_from_persist_dir(path: str):
    retriever = BM25Retriever.from_persist_dir(path)
    return retriever


def build_module_retriever_from_graph(
    graph_path: Optional[str] = None,
    entity_searcher: Optional[RepoEntitySearcher] = None,
    search_scope: str = 'all',
    # enum = {'function', 'class', 'file', 'all'}
    similarity_top_k: int = 10,
):
    assert search_scope in NTYPES or search_scope == 'all'
    assert graph_path or isinstance(entity_searcher, RepoEntitySearcher)

    if graph_path:
        G = pickle.load(open(graph_path, 'rb'))
        entity_searcher = RepoEntitySearcher(G)
    else:
        G = entity_searcher.G

    selected_nodes = list()
    for nid in G:
        if is_test_file(nid):
            continue

        ndata = entity_searcher.get_node_data([nid])[0]
        ndata['nid'] = nid  # add `nid` property
        if search_scope == 'all':  # and ndata['type'] in NTYPES[2:]
            selected_nodes.append(ndata)
        elif ndata['type'] == search_scope:
            selected_nodes.append(ndata)

    # initialize node parser
    splitter = SimpleFileNodeParser()
    documents = [Document(text=t['nid']) for t in selected_nodes]
    nodes = splitter.get_nodes_from_documents(documents)

    # We can pass in the index, docstore, or list of nodes to create the retriever
    retriever = BM25Retriever.from_defaults(
        nodes=nodes,
        similarity_top_k=similarity_top_k,
        stemmer=Stemmer.Stemmer('english'),
        language='english',
    )

    return retriever


def fuzzy_retrieve_from_graph_nodes(
    keyword: str,
    graph_path: Optional[str] = None,
    graph: Optional[nx.MultiDiGraph] = None,
    search_scope: str = 'all',  # enum = {'function', 'class', 'file', 'all'}
    include_files: Optional[str] = None,
    similarity_top_k: int = 5,
    return_score: bool = False,
):
    assert graph_path or isinstance(graph, nx.MultiDiGraph)
    assert search_scope in VALID_NODE_TYPES or search_scope == 'all'

    if graph_path:
        graph = pickle.load(open(graph_path, 'rb'))

    selected_nids = list()
    filter_nids = list()
    for nid in graph:
        if is_test_file(nid):
            continue
        ndata = graph.nodes[nid]
        if search_scope == 'all' and ndata['type'] in [
            NODE_TYPE_FILE,
            NODE_TYPE_CLASS,
            NODE_TYPE_FUNCTION,
        ]:
            nfile = nid.split(':')[0]
            if not include_files or nfile in include_files:
                filter_nids.append(nid)
            selected_nids.append(nid)
        elif ndata['type'] == search_scope:
            nfile = nid.split(':')[0]
            if not include_files or nfile in include_files:
                filter_nids.append(nid)
            selected_nids.append(nid)

    if not filter_nids:
        filter_nids = selected_nids

    # Custom function to split tokens on underscores and hyphens
    def custom_tokenizer(s):
        return re.findall(r'\b\w+\b', s.replace('_', ' ').replace('-', ' '))

    # Use token_set_ratio with custom tokenizer
    matches = process.extract(
        keyword,
        filter_nids,
        scorer=fuzz.token_set_ratio,
        processor=lambda s: ' '.join(custom_tokenizer(s)),
        limit=similarity_top_k,
    )
    if not return_score:
        return_nids = [match[0] for match in matches]
        return return_nids

    # matches: List[Tuple(nid, score)]
    return matches
