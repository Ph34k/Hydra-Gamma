import uuid
import os
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel, Field
from app.logger import logger
from app.config import config

class SemanticMemory:
    """
    Manages long-term semantic memory using a vector database (ChromaDB) and embeddings.
    """
    def __init__(self, collection_name: str = "manus_memory", persist_directory: str = "workspace/db"):
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # Ensure directory exists
        os.makedirs(self.persist_directory, exist_ok=True)

        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(path=self.persist_directory)

            # Initialize Embedding Model (lightweight)
            # We use a singleton pattern for the model if possible to avoid reloading
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

            # Get or create collection
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
            logger.info(f"Semantic Memory initialized at {self.persist_directory}")
        except Exception as e:
            logger.error(f"Failed to initialize Semantic Memory: {e}")
            raise

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a given text."""
        return self.embedding_model.encode(text).tolist()

    def index_document(self, text: str, metadata: Dict[str, Any] = None, source: str = "unknown") -> str:
        """
        Index a document (text) into the vector database.
        Automatically chunks text if too large (simplified chunking for now).
        """
        if not text:
            return ""

        # Simple chunking (can be improved)
        chunk_size = 1000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

        ids = []
        embeddings = []
        metadatas = []
        documents = []

        for i, chunk in enumerate(chunks):
            chunk_id = str(uuid.uuid4())
            embedding = self._generate_embedding(chunk)

            meta = metadata.copy() if metadata else {}
            meta.update({
                "source": source,
                "chunk_index": i,
                "timestamp": str(uuid.uuid1().time) # accurate enough for sorting
            })

            ids.append(chunk_id)
            embeddings.append(embedding)
            metadatas.append(meta)
            documents.append(chunk)

        try:
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            logger.info(f"Indexed {len(chunks)} chunks from source '{source}'")
            return f"Indexed {len(chunks)} chunks."
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            return f"Error indexing document: {e}"

    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant documents based on semantic similarity.
        """
        try:
            query_embedding = self._generate_embedding(query)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )

            # Format results
            formatted_results = []
            if results['ids']:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        "id": results['ids'][0][i],
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "distance": results['distances'][0][i] if results['distances'] else None
                    })
            return formatted_results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def prune(self, max_items: int = 1000):
        """
        Prune old memories if exceeding capacity.
        (This is a placeholder for more complex logic like LRU or importance-based pruning)
        """
        count = self.collection.count()
        if count > max_items:
            # Naive pruning: remove random or oldest (Chroma doesn't easily support 'oldest' without querying all)
            # For now, we log a warning.
            logger.warning(f"Memory size {count} exceeds limit {max_items}. Pruning not fully implemented.")
