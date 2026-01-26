"""
Corpus indexer for GBDK code samples.

Parses all sample files, extracts meaningful chunks, and stores them
with embeddings for semantic search.

Uses a simple JSON + numpy-based vector store with OpenAI embeddings
for maximum compatibility.
"""

import json
import hashlib
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import numpy as np
from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai not installed. Run: pip install openai")

from .chunkers import (
    extract_all_chunks,
    CodeChunk
)
from .visualizers import sprite_array_to_ascii


# Paths
CORPUS_ROOT = PROJECT_ROOT / "games"
SAMPLES_DIR = CORPUS_ROOT / "samples"
DB_PATH = CORPUS_ROOT / "corpus_db"
MANIFEST_PATH = CORPUS_ROOT / "manifest.json"

# Embedding settings
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536


class SimpleVectorStore:
    """
    A simple JSON + numpy-based vector store.
    
    Stores documents with embeddings and metadata, supports cosine similarity search.
    """
    
    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        
        self.documents: Dict[str, Dict] = {}  # id -> {text, embedding, metadata}
        self.embeddings: Optional[np.ndarray] = None
        self.ids: List[str] = []
        
        self._load()
    
    def _load(self):
        """Load existing data from disk."""
        docs_path = self.path / "documents.json"
        embeddings_path = self.path / "embeddings.npy"
        
        if docs_path.exists():
            with open(docs_path, 'r') as f:
                self.documents = json.load(f)
            self.ids = list(self.documents.keys())
        
        if embeddings_path.exists() and self.ids:
            self.embeddings = np.load(embeddings_path)
    
    def _save(self):
        """Save data to disk."""
        docs_path = self.path / "documents.json"
        embeddings_path = self.path / "embeddings.npy"
        
        with open(docs_path, 'w') as f:
            json.dump(self.documents, f)
        
        if self.embeddings is not None and len(self.embeddings) > 0:
            np.save(embeddings_path, self.embeddings)
    
    def add(self, id: str, text: str, embedding: List[float], metadata: Dict):
        """Add a document with its embedding."""
        self.documents[id] = {
            'text': text,
            'metadata': metadata
        }
        
        # Update embeddings array
        emb_array = np.array(embedding, dtype=np.float32)
        
        if id in self.ids:
            # Update existing
            idx = self.ids.index(id)
            self.embeddings[idx] = emb_array
        else:
            # Add new
            self.ids.append(id)
            if self.embeddings is None:
                self.embeddings = emb_array.reshape(1, -1)
            else:
                self.embeddings = np.vstack([self.embeddings, emb_array])
    
    def search(self, query_embedding: List[float], n_results: int = 5, 
               filter_fn: Optional[callable] = None) -> List[Dict]:
        """
        Search for similar documents using cosine similarity.
        
        Args:
            query_embedding: Query vector
            n_results: Number of results to return
            filter_fn: Optional function to filter results by metadata
            
        Returns:
            List of {id, text, metadata, similarity} dicts
        """
        if self.embeddings is None or len(self.embeddings) == 0:
            return []
        
        query = np.array(query_embedding, dtype=np.float32)
        
        # Compute cosine similarities
        # Normalize vectors
        query_norm = query / (np.linalg.norm(query) + 1e-8)
        embeddings_norm = self.embeddings / (np.linalg.norm(self.embeddings, axis=1, keepdims=True) + 1e-8)
        
        similarities = np.dot(embeddings_norm, query_norm)
        
        # Apply filter if provided
        if filter_fn:
            valid_indices = [
                i for i, id in enumerate(self.ids)
                if filter_fn(self.documents[id]['metadata'])
            ]
            if not valid_indices:
                return []
            
            # Filter to valid indices
            filtered_similarities = [(i, similarities[i]) for i in valid_indices]
            filtered_similarities.sort(key=lambda x: x[1], reverse=True)
            top_indices = [i for i, _ in filtered_similarities[:n_results]]
        else:
            top_indices = np.argsort(similarities)[::-1][:n_results]
        
        results = []
        for idx in top_indices:
            id = self.ids[idx]
            doc = self.documents[id]
            results.append({
                'id': id,
                'text': doc['text'],
                'metadata': doc['metadata'],
                'similarity': float(similarities[idx])
            })
        
        return results
    
    def count(self) -> int:
        """Return number of documents."""
        return len(self.documents)
    
    def clear(self):
        """Clear all documents."""
        self.documents = {}
        self.embeddings = None
        self.ids = []
        self._save()
    
    def save(self):
        """Explicitly save to disk."""
        self._save()


class CorpusIndexer:
    """
    Indexes GBDK code samples for semantic search.
    
    Creates separate stores for:
    - functions: Code functions with their implementations
    - sprites: Sprite data arrays with ASCII previews
    - structs: Type definitions
    - constants: #define blocks
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize the indexer.
        
        Args:
            db_path: Path to database storage (default: games/corpus_db)
        """
        if not OPENAI_AVAILABLE:
            raise RuntimeError("openai not installed. Run: pip install openai")
        
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize OpenAI client
        self.openai = openai.OpenAI()
        
        # Initialize stores for each type
        self.stores = {
            'functions': SimpleVectorStore(self.db_path / 'functions'),
            'sprites': SimpleVectorStore(self.db_path / 'sprites'),
            'structs': SimpleVectorStore(self.db_path / 'structs'),
            'constants': SimpleVectorStore(self.db_path / 'constants'),
        }
        
        # Track indexing stats
        self.stats = {
            'files_processed': 0,
            'functions_indexed': 0,
            'sprites_indexed': 0,
            'structs_indexed': 0,
            'constants_indexed': 0,
            'errors': []
        }
        
        # Cache for embeddings to avoid duplicate API calls
        self._embedding_cache: Dict[str, List[float]] = {}
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text, using cache when possible."""
        cache_key = hashlib.md5(text.encode()).hexdigest()
        
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]
        
        response = self.openai.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        embedding = response.data[0].embedding
        
        self._embedding_cache[cache_key] = embedding
        return embedding
    
    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts in a batch."""
        # Filter out cached ones
        uncached_texts = []
        uncached_indices = []
        results = [None] * len(texts)
        
        for i, text in enumerate(texts):
            cache_key = hashlib.md5(text.encode()).hexdigest()
            if cache_key in self._embedding_cache:
                results[i] = self._embedding_cache[cache_key]
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        if uncached_texts:
            # Batch API call
            response = self.openai.embeddings.create(
                model=EMBEDDING_MODEL,
                input=uncached_texts
            )
            
            for j, emb_data in enumerate(response.data):
                idx = uncached_indices[j]
                embedding = emb_data.embedding
                results[idx] = embedding
                
                # Cache it
                cache_key = hashlib.md5(uncached_texts[j].encode()).hexdigest()
                self._embedding_cache[cache_key] = embedding
        
        return results
    
    def clear_all(self):
        """Clear all stores and start fresh."""
        for store in self.stores.values():
            store.clear()
        print("All stores cleared.")
    
    def index_file(self, file_path: Path, sample_id: str) -> int:
        """
        Index a single source file.
        
        Args:
            file_path: Path to the .c or .h file
            sample_id: Sample identifier (e.g., "pong", "runner")
            
        Returns:
            Number of chunks indexed
        """
        try:
            content = file_path.read_text()
        except Exception as e:
            self.stats['errors'].append(f"Error reading {file_path}: {e}")
            return 0
        
        chunks = extract_all_chunks(content, str(file_path))
        if not chunks:
            return 0
        
        # Prepare texts for batch embedding
        doc_texts = [self._create_document_text(chunk, sample_id) for chunk in chunks]
        
        # Get embeddings in batch
        embeddings = self._get_embeddings_batch(doc_texts)
        
        indexed = 0
        for chunk, doc_text, embedding in zip(chunks, doc_texts, embeddings):
            try:
                self._index_chunk(chunk, sample_id, file_path.name, doc_text, embedding)
                indexed += 1
            except Exception as e:
                self.stats['errors'].append(f"Error indexing {chunk.name} from {file_path}: {e}")
        
        self.stats['files_processed'] += 1
        return indexed
    
    def _index_chunk(self, chunk: CodeChunk, sample_id: str, filename: str, 
                     doc_text: str, embedding: List[float]):
        """Index a single code chunk."""
        # Generate unique ID
        chunk_id = self._generate_id(sample_id, filename, chunk.name, chunk.chunk_type)
        
        # Prepare metadata
        metadata = {
            "sample_id": sample_id,
            "file": filename,
            "name": chunk.name,
            "chunk_type": chunk.chunk_type,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "code": chunk.code[:4000],
            "description": chunk.description[:500],
        }
        
        # Add type-specific metadata
        if chunk.metadata:
            for key, value in chunk.metadata.items():
                if key == 'hex_bytes':
                    metadata['ascii_preview'] = sprite_array_to_ascii(
                        value, tiles_per_row=4, max_tiles=4, use_unicode=False
                    )[:1000]
                elif isinstance(value, (str, int, float, bool)):
                    metadata[key] = value
                elif isinstance(value, list) and all(isinstance(x, str) for x in value):
                    metadata[key] = ', '.join(value[:10])
        
        # Get the appropriate store
        store_name = self._get_store_for_chunk(chunk)
        store = self.stores.get(store_name)
        
        if store:
            store.add(chunk_id, doc_text, embedding, metadata)
            self.stats[f'{store_name}_indexed'] = self.stats.get(f'{store_name}_indexed', 0) + 1
    
    def _generate_id(self, sample_id: str, filename: str, name: str, chunk_type: str) -> str:
        """Generate a unique ID for a chunk."""
        key = f"{sample_id}:{filename}:{chunk_type}:{name}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def _create_document_text(self, chunk: CodeChunk, sample_id: str) -> str:
        """Create the text that will be embedded for semantic search."""
        parts = [chunk.description]
        
        if chunk.chunk_type == 'function':
            parts.append(f"Function {chunk.name} from {sample_id}")
            
            category = chunk.metadata.get('category', '')
            if category:
                parts.append(f"Category: {category}")
            
            code_lower = chunk.code.lower()
            operations = []
            if 'move_sprite' in code_lower:
                operations.append('sprite movement')
            if 'collision' in code_lower or 'check' in chunk.name.lower():
                operations.append('collision detection')
            if 'joypad' in code_lower:
                operations.append('input handling')
            if 'velocity' in code_lower or 'gravity' in code_lower:
                operations.append('physics')
            if 'score' in code_lower:
                operations.append('score tracking')
            if operations:
                parts.append(f"Implements: {', '.join(operations)}")
                
        elif chunk.chunk_type == 'sprite':
            parts.append(f"Sprite data {chunk.name} from {sample_id}")
            
            num_tiles = chunk.metadata.get('num_tiles', 0)
            if num_tiles:
                parts.append(f"{num_tiles} tiles")
            
            frame_count = chunk.metadata.get('frame_count', 0)
            if frame_count > 1:
                parts.append(f"{frame_count} animation frames")
                
        elif chunk.chunk_type == 'struct':
            parts.append(f"Struct/type {chunk.name}")
            fields = chunk.metadata.get('fields', [])
            if fields:
                parts.append(f"Fields: {', '.join(fields[:10])}")
                
        elif chunk.chunk_type == 'constant':
            parts.append(f"Constants from {sample_id}")
            names = chunk.metadata.get('names', [])
            if names:
                parts.append(f"Defines: {', '.join(names[:10])}")
        
        return ' | '.join(parts)
    
    def _get_store_for_chunk(self, chunk: CodeChunk) -> str:
        """Determine which store a chunk belongs to."""
        type_to_store = {
            'function': 'functions',
            'sprite': 'sprites',
            'struct': 'structs',
            'constant': 'constants'
        }
        return type_to_store.get(chunk.chunk_type, 'functions')
    
    def index_sample(self, sample_id: str) -> Dict:
        """Index all files from a single sample."""
        sample_path = SAMPLES_DIR / sample_id / "src"
        
        if not sample_path.exists():
            return {'error': f"Sample path not found: {sample_path}"}
        
        sample_stats = {'files': 0, 'chunks': 0}
        
        for pattern in ['*.c', '*.h']:
            for file_path in sample_path.glob(pattern):
                chunks = self.index_file(file_path, sample_id)
                sample_stats['files'] += 1
                sample_stats['chunks'] += chunks
        
        return sample_stats
    
    def index_all_samples(self, clear_first: bool = False) -> Dict:
        """Index all samples in the corpus."""
        if clear_first:
            self.clear_all()
        
        if MANIFEST_PATH.exists():
            with open(MANIFEST_PATH) as f:
                manifest = json.load(f)
            sample_ids = [s['id'] for s in manifest.get('samples', [])]
        else:
            sample_ids = [d.name for d in SAMPLES_DIR.iterdir() if d.is_dir()]
        
        print(f"Indexing {len(sample_ids)} samples...")
        
        for i, sample_id in enumerate(sample_ids):
            print(f"  [{i+1}/{len(sample_ids)}] {sample_id}...", end=' ')
            result = self.index_sample(sample_id)
            print(f"({result.get('chunks', 0)} chunks)")
        
        # Save all stores
        for store in self.stores.values():
            store.save()
        
        self._save_index_metadata()
        
        return self.stats
    
    def _save_index_metadata(self):
        """Save indexing metadata."""
        metadata = {
            'indexed_at': datetime.now().isoformat(),
            'stats': self.stats,
            'stores': {
                name: store.count() 
                for name, store in self.stores.items()
            }
        }
        
        metadata_path = self.db_path / 'index_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def get_stats(self) -> Dict:
        """Get current index statistics."""
        return {
            'stores': {
                name: store.count() 
                for name, store in self.stores.items()
            },
            'total_chunks': sum(store.count() for store in self.stores.values()),
            'db_path': str(self.db_path)
        }


def build_index(clear: bool = False):
    """Build or rebuild the corpus index."""
    print("=" * 50)
    print("GBDK Corpus Indexer")
    print("=" * 50)
    
    indexer = CorpusIndexer()
    
    if clear:
        print("\nClearing existing index...")
    
    print("\nIndexing samples...")
    stats = indexer.index_all_samples(clear_first=clear)
    
    print("\n" + "=" * 50)
    print("Indexing Complete!")
    print("=" * 50)
    print(f"\nFiles processed: {stats['files_processed']}")
    print(f"Functions indexed: {stats.get('functions_indexed', 0)}")
    print(f"Sprites indexed: {stats.get('sprites_indexed', 0)}")
    print(f"Structs indexed: {stats.get('structs_indexed', 0)}")
    print(f"Constants indexed: {stats.get('constants_indexed', 0)}")
    
    if stats['errors']:
        print(f"\nErrors ({len(stats['errors'])}):")
        for err in stats['errors'][:5]:
            print(f"  - {err}")
    
    final_stats = indexer.get_stats()
    print(f"\nTotal chunks in database: {final_stats['total_chunks']}")
    print(f"Database path: {final_stats['db_path']}")


if __name__ == "__main__":
    import sys
    
    clear = '--clear' in sys.argv or '--rebuild' in sys.argv
    build_index(clear=clear)
