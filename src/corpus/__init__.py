"""
Corpus indexing and vector search for GBDK code samples.

This module provides semantic search over the code corpus using a simple
JSON + numpy vector store with OpenAI embeddings for semantic similarity.
"""

from .vectordb import CorpusSearch
from .indexer import CorpusIndexer, SimpleVectorStore

__all__ = ['CorpusSearch', 'CorpusIndexer', 'SimpleVectorStore']
