"""
Vector database search API for GBDK corpus.

Provides semantic search over indexed code samples using a simple
JSON + numpy vector store with OpenAI embeddings.
"""

from pathlib import Path
from typing import List, Dict, Optional, Literal
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .indexer import SimpleVectorStore, EMBEDDING_MODEL


# Paths
DB_PATH = PROJECT_ROOT / "games" / "corpus_db"


@dataclass
class SearchResult:
    """A single search result."""
    sample_id: str
    file: str
    name: str
    chunk_type: str
    code: str
    description: str
    relevance: float
    metadata: Dict
    
    def __str__(self):
        return f"[{self.relevance:.2f}] {self.sample_id}/{self.file} - {self.name}"


class CorpusSearch:
    """
    Semantic search over the GBDK corpus.
    
    Provides methods to search for:
    - Functions by description or behavior
    - Sprites by visual description
    - Structs by field names or purpose
    - Constants by name or value
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize the search client.
        
        Args:
            db_path: Path to vector store storage
        """
        if not OPENAI_AVAILABLE:
            raise RuntimeError("openai not installed. Run: pip install openai")
        
        self.db_path = Path(db_path) if db_path else DB_PATH
        
        if not self.db_path.exists():
            raise RuntimeError(f"Corpus database not found at {self.db_path}. Run indexer first.")
        
        # Initialize OpenAI client
        self.openai = openai.OpenAI()
        
        # Load stores
        self.stores = {}
        for name in ['functions', 'sprites', 'structs', 'constants']:
            store_path = self.db_path / name
            if store_path.exists():
                self.stores[name] = SimpleVectorStore(store_path)
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for query text."""
        response = self.openai.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    
    def _format_results(self, results: List[Dict], collection_name: str) -> List[SearchResult]:
        """Convert store results to SearchResult objects."""
        formatted = []
        
        if not results:
            return formatted
        
        for result in results:
            meta = result.get('metadata', {})
            
            formatted.append(SearchResult(
                sample_id=meta.get('sample_id', 'unknown'),
                file=meta.get('file', 'unknown'),
                name=meta.get('name', 'unknown'),
                chunk_type=meta.get('chunk_type', collection_name),
                code=meta.get('code', ''),
                description=meta.get('description', ''),
                relevance=result.get('similarity', 0.0),
                metadata=meta
            ))
        
        return formatted
    
    def search_functions(self, 
                         query: str, 
                         n_results: int = 5,
                         category: str = None,
                         sample_id: str = None) -> List[SearchResult]:
        """
        Search for function implementations.
        
        Args:
            query: Natural language description of what you're looking for
            n_results: Maximum results to return
            category: Filter by category (game_logic, collision, rendering, etc.)
            sample_id: Filter to a specific sample
            
        Returns:
            List of SearchResult objects ordered by relevance
        """
        store = self.stores.get('functions')
        if not store:
            return []
        
        query_embedding = self._get_embedding(query)
        
        # Build filter function
        filter_fn = None
        if category or sample_id:
            def filter_fn(meta):
                if category and meta.get('category') != category:
                    return False
                if sample_id and meta.get('sample_id') != sample_id:
                    return False
                return True
        
        results = store.search(query_embedding, n_results, filter_fn)
        return self._format_results(results, 'functions')
    
    def search_sprites(self,
                       query: str,
                       n_results: int = 5,
                       sample_id: str = None) -> List[SearchResult]:
        """
        Search for sprite definitions.
        
        Args:
            query: Description of sprite (e.g., "cat walking animation")
            n_results: Maximum results to return
            sample_id: Filter to a specific sample
            
        Returns:
            List of SearchResult objects with ASCII previews in metadata
        """
        store = self.stores.get('sprites')
        if not store:
            return []
        
        query_embedding = self._get_embedding(query)
        
        filter_fn = None
        if sample_id:
            filter_fn = lambda meta: meta.get('sample_id') == sample_id
        
        results = store.search(query_embedding, n_results, filter_fn)
        return self._format_results(results, 'sprites')
    
    def search_structs(self,
                       query: str,
                       n_results: int = 5) -> List[SearchResult]:
        """
        Search for struct/type definitions.
        
        Args:
            query: Description or field names
            n_results: Maximum results
            
        Returns:
            List of SearchResult objects
        """
        store = self.stores.get('structs')
        if not store:
            return []
        
        query_embedding = self._get_embedding(query)
        results = store.search(query_embedding, n_results)
        return self._format_results(results, 'structs')
    
    def search_constants(self,
                         query: str,
                         n_results: int = 5) -> List[SearchResult]:
        """
        Search for constant definitions.
        
        Args:
            query: Constant names or descriptions
            n_results: Maximum results
            
        Returns:
            List of SearchResult objects
        """
        store = self.stores.get('constants')
        if not store:
            return []
        
        query_embedding = self._get_embedding(query)
        results = store.search(query_embedding, n_results)
        return self._format_results(results, 'constants')
    
    def search_all(self,
                   query: str,
                   n_results: int = 3,
                   chunk_types: List[str] = None) -> Dict[str, List[SearchResult]]:
        """
        Search across all collections.
        
        Args:
            query: Search query
            n_results: Max results per collection
            chunk_types: Limit to specific types (functions, sprites, structs, constants)
            
        Returns:
            Dict mapping collection name to results
        """
        if chunk_types is None:
            chunk_types = ['functions', 'sprites', 'structs', 'constants']
        
        all_results = {}
        
        for ctype in chunk_types:
            if ctype == 'functions':
                all_results[ctype] = self.search_functions(query, n_results)
            elif ctype == 'sprites':
                all_results[ctype] = self.search_sprites(query, n_results)
            elif ctype == 'structs':
                all_results[ctype] = self.search_structs(query, n_results)
            elif ctype == 'constants':
                all_results[ctype] = self.search_constants(query, n_results)
        
        return all_results
    
    def get_similar_code(self,
                         code: str,
                         chunk_type: str = 'functions',
                         n_results: int = 5) -> List[SearchResult]:
        """
        Find similar code to a given snippet.
        
        Args:
            code: Code snippet to find similar examples for
            chunk_type: Type of code to search
            n_results: Maximum results
            
        Returns:
            List of similar code chunks
        """
        # Use the code itself as the query
        # The embedding will capture semantic meaning
        search_methods = {
            'functions': self.search_functions,
            'sprites': self.search_sprites,
            'structs': self.search_structs,
            'constants': self.search_constants
        }
        
        method = search_methods.get(chunk_type, self.search_functions)
        return method(code, n_results)
    
    def get_context_for_task(self, 
                             description: str,
                             max_results: int = 10) -> str:
        """
        Get relevant code context for a task description.
        
        This is a convenience method for the planner to get relevant
        examples in a formatted string.
        
        Args:
            description: Task or game description
            max_results: Total max results across all types
            
        Returns:
            Formatted context string with relevant code examples
        """
        parts = []
        
        # Determine what types of code might be relevant
        desc_lower = description.lower()
        
        search_types = []
        if any(w in desc_lower for w in ['sprite', 'character', 'player', 'enemy', 'animation', 'visual']):
            search_types.append(('sprites', 4))
        if any(w in desc_lower for w in ['collision', 'hit', 'overlap', 'touch']):
            search_types.append(('functions', 3))
        if any(w in desc_lower for w in ['move', 'jump', 'physics', 'gravity', 'velocity']):
            search_types.append(('functions', 3))
        if any(w in desc_lower for w in ['input', 'button', 'control']):
            search_types.append(('functions', 2))
        if any(w in desc_lower for w in ['state', 'data', 'struct']):
            search_types.append(('structs', 2))
        
        # Default to functions if nothing specific
        if not search_types:
            search_types = [('functions', 5)]
        
        # Search and format results
        for chunk_type, n in search_types:
            if chunk_type == 'functions':
                results = self.search_functions(description, n)
            elif chunk_type == 'sprites':
                results = self.search_sprites(description, n)
            elif chunk_type == 'structs':
                results = self.search_structs(description, n)
            else:
                continue
            
            if results:
                parts.append(f"\n## Relevant {chunk_type.title()}\n")
                
                for r in results:
                    parts.append(f"### {r.name} (from {r.sample_id})")
                    parts.append(f"*Relevance: {r.relevance:.2f}*\n")
                    
                    if chunk_type == 'sprites' and r.metadata.get('ascii_preview'):
                        parts.append("Preview:")
                        parts.append(f"```\n{r.metadata['ascii_preview']}\n```")
                    
                    # Truncate code if too long
                    code = r.code
                    if len(code) > 1500:
                        code = code[:1500] + "\n// ... truncated"
                    
                    parts.append(f"```c\n{code}\n```\n")
        
        return '\n'.join(parts) if parts else "No relevant examples found."
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        return {
            'stores': {
                name: store.count() if store else 0
                for name, store in self.stores.items()
            },
            'total': sum(store.count() if store else 0 for store in self.stores.values()),
            'db_path': str(self.db_path)
        }


def test_search():
    """Test the search functionality."""
    print("=" * 50)
    print("Corpus Search Test")
    print("=" * 50)
    
    try:
        search = CorpusSearch()
    except RuntimeError as e:
        print(f"Error: {e}")
        print("Run the indexer first: python -m src.corpus.indexer")
        return
    
    stats = search.get_stats()
    print(f"\nDatabase stats: {stats['total']} total chunks")
    for name, count in stats['stores'].items():
        print(f"  {name}: {count}")
    
    # Test function search
    print("\n" + "-" * 50)
    print("Searching functions: 'collision detection between sprites'")
    print("-" * 50)
    results = search.search_functions("collision detection between sprites", n_results=3)
    for r in results:
        print(f"\n{r}")
        print(f"  Category: {r.metadata.get('category', 'unknown')}")
        print(f"  Code preview: {r.code[:100]}...")
    
    # Test sprite search
    print("\n" + "-" * 50)
    print("Searching sprites: 'player character animation'")
    print("-" * 50)
    results = search.search_sprites("player character animation", n_results=3)
    for r in results:
        print(f"\n{r}")
        if r.metadata.get('ascii_preview'):
            print("  Preview:")
            for line in r.metadata['ascii_preview'].split('\n')[:5]:
                print(f"    {line}")
    
    # Test context generation
    print("\n" + "-" * 50)
    print("Getting context for: 'cat running and jumping game'")
    print("-" * 50)
    context = search.get_context_for_task("cat running and jumping game")
    print(context[:2000])


if __name__ == "__main__":
    test_search()
