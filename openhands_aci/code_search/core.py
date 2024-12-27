import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer


class CodeSearchIndex:
    def __init__(self, embedding_model: Optional[str] = None):
        """Initialize the code search index.

        Args:
            embedding_model: Name or path of the sentence transformer model to use.
                           If None, will use the model specified in EMBEDDING_MODEL env var.
        """
        self.embedding_model = embedding_model or os.getenv(
            'EMBEDDING_MODEL', 'BAAI/bge-base-en-v1.5'
        )
        self.model = SentenceTransformer(self.embedding_model)
        self.index: Optional[faiss.IndexFlatIP] = None
        self.documents: List[Dict[str, Any]] = []
        self.doc_ids: List[str] = []

    def _embed_text(self, text: str) -> np.ndarray:
        """Embed a single text string."""
        with torch.no_grad():
            embedding = self.model.encode(text, convert_to_tensor=True)
            return embedding.cpu().numpy()

    def _embed_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Embed a batch of text strings."""
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            with torch.no_grad():
                batch_embeddings = self.model.encode(batch, convert_to_tensor=True)
                embeddings.append(batch_embeddings.cpu().numpy())
        return np.vstack(embeddings)

    def add_documents(self, documents: List[Dict[str, Any]], batch_size: int = 32):
        """Add documents to the index.

        Args:
            documents: List of document dictionaries with 'id' and 'content' keys
            batch_size: Batch size for embedding generation
        """
        texts = [doc['content'] for doc in documents]
        embeddings = self._embed_batch(texts, batch_size)

        if self.index is None:
            self.index = faiss.IndexFlatIP(embeddings.shape[1])

        self.index.add(embeddings)
        self.documents.extend(documents)
        self.doc_ids.extend([doc['id'] for doc in documents])

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search the index with a query string.

        Args:
            query: The search query
            k: Number of results to return

        Returns:
            List of document dictionaries with scores
        """
        query_embedding = self._embed_text(query)
        if self.index is None:
            raise ValueError('Index is not initialized. Add documents first.')
        scores, indices = self.index.search(query_embedding.reshape(1, -1), k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.documents):
                continue
            doc = self.documents[idx].copy()
            doc['score'] = float(score)
            results.append(doc)

        return results

    def save(self, directory: str):
        """Save the index and documents to disk.

        Args:
            directory: Directory to save the index in
        """
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)

        # Save the Faiss index
        if self.index is not None:
            faiss.write_index(self.index, str(dir_path / 'index.faiss'))

        # Save documents and metadata
        with open(dir_path / 'documents.pkl', 'wb') as f:
            pickle.dump(
                {
                    'documents': self.documents,
                    'doc_ids': self.doc_ids,
                    'embedding_model': self.embedding_model,
                },
                f,
            )

    @classmethod
    def load(cls, directory: str) -> 'CodeSearchIndex':
        """Load an index from disk.

        Args:
            directory: Directory containing the saved index

        Returns:
            Loaded CodeSearchIndex instance
        """
        dir_path = Path(directory)

        # Load metadata
        with open(dir_path / 'documents.pkl', 'rb') as f:
            data = pickle.load(f)

        # Create instance with same model
        instance = cls(embedding_model=data['embedding_model'])
        instance.documents = data['documents']
        instance.doc_ids = data['doc_ids']

        # Load Faiss index
        instance.index = faiss.read_index(str(dir_path / 'index.faiss'))

        return instance
