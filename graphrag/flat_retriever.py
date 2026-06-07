import logging
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, Any

from .embedder import GraphEmbedder

logger = logging.getLogger(__name__)

class RetrievalResult:
    """Standardized retrieval result to be returned by all retrievers."""
    def __init__(self, seed_nodes, graph_context_str, hop_count, nodes_traversed, latency_ms):
        self.seed_nodes = seed_nodes
        self.graph_context_str = graph_context_str
        self.hop_count = hop_count
        self.nodes_traversed = nodes_traversed
        self.latency_ms = latency_ms

class FlatRAGRetriever:
    """Baseline Flat RAG Retriever. Uses semantic similarity with no graph traversal."""
    
    def __init__(self, neo4j_driver, embedder: GraphEmbedder, embeddings_cache: Dict[str, np.ndarray]):
        self.driver = neo4j_driver
        self.embedder = embedder
        self.embeddings_cache = embeddings_cache
        
        # Pre-compute matrices for fast cosine similarity
        self.node_ids = list(self.embeddings_cache.keys())
        if self.node_ids:
            self.embeddings_matrix = np.vstack([self.embeddings_cache[nid] for nid in self.node_ids])
        else:
            self.embeddings_matrix = np.array([])
            
    def retrieve(self, query: str, top_k: int = 5) -> RetrievalResult:
        """
        Embed query, compute cosine similarity against all entity embeddings,
        and return top_k entities as flat text chunks.
        """
        import time
        start_time = time.time()
        
        if len(self.node_ids) == 0:
            logger.warning("No embeddings found in cache. Cannot retrieve.")
            return RetrievalResult([], "No data available.", 0, 0, 0)
            
        # 1. Embed query
        query_embedding = self.embedder.embed_query(query)
        
        # 2. Cosine similarity
        # reshape query_embedding to 2D
        similarities = cosine_similarity([query_embedding], self.embeddings_matrix)[0]
        
        # 3. Get top_k indices
        top_k_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # 4. Fetch entities from Neo4j to get flat text chunks
        top_node_ids = [int(self.node_ids[idx]) for idx in top_k_indices]
        
        seed_nodes = []
        flat_chunks = []
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n) WHERE id(n) IN $node_ids
                RETURN id(n) AS id, labels(n)[0] AS type, n.name AS name, n.description AS description
            """, node_ids=top_node_ids)
            
            for record in result:
                n_id = record["id"]
                n_type = record["type"] or "Entity"
                n_name = record["name"] or "Unknown"
                n_desc = record["description"] or ""
                
                seed_nodes.append({"id": n_id, "name": n_name})
                chunk = f"{n_type}: {n_name}. {n_desc}".strip()
                flat_chunks.append(chunk)
                
        context_str = "\n".join(flat_chunks)
        latency_ms = int((time.time() - start_time) * 1000)
        
        return RetrievalResult(
            seed_nodes=seed_nodes,
            graph_context_str=context_str,
            hop_count=0, # No hops
            nodes_traversed=len(seed_nodes),
            latency_ms=latency_ms
        )
