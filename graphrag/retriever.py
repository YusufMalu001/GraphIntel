import time
import logging
import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Any

from .embedder import GraphEmbedder
from .flat_retriever import RetrievalResult

logger = logging.getLogger(__name__)

class GraphRAGRetriever:
    """Graph RAG Retriever. Uses semantic similarity for seed nodes, then graph traversal."""
    
    def __init__(self, neo4j_driver, embedder: GraphEmbedder, embeddings_cache: Dict[str, np.ndarray]):
        self.driver = neo4j_driver
        self.embedder = embedder
        self.embeddings_cache = embeddings_cache
        
        self.node_ids = list(self.embeddings_cache.keys())
        if self.node_ids:
            self.embeddings_matrix = np.vstack([self.embeddings_cache[nid] for nid in self.node_ids])
        else:
            self.embeddings_matrix = np.array([])
            
    def _get_top_k_seeds(self, query: str, top_k: int) -> List[int]:
        if len(self.node_ids) == 0:
            return []
            
        query_embedding = self.embedder.embed_query(query)
        similarities = cosine_similarity([query_embedding], self.embeddings_matrix)[0]
        top_k_indices = np.argsort(similarities)[-top_k:][::-1]
        
        return [int(self.node_ids[idx]) for idx in top_k_indices]

    def retrieve(self, query: str, top_k: int = 5, max_hops: int = 2) -> RetrievalResult:
        start_time = time.time()
        
        seed_ids = self._get_top_k_seeds(query, top_k)
        if not seed_ids:
            return RetrievalResult([], "No data available.", 0, 0, 0)
            
        seed_nodes = []
        nodes_traversed_set = set(seed_ids)
        
        # 1. Embed query for similarity comparison
        query_embedding = self.embedder.embed_query(query)
        
        with self.driver.session() as session:
            # Get seed node details
            seed_res = session.run("MATCH (n) WHERE id(n) IN $seed_ids RETURN id(n) AS id, n.name AS name", seed_ids=seed_ids)
            for record in seed_res:
                seed_nodes.append({"id": record["id"], "name": record["name"]})
                
            # Traverse graph and get distinct neighbors
            query_cypher = f"""
            MATCH (seed)
            WHERE id(seed) IN $seed_ids
            MATCH (seed)-[*0..{max_hops}]-(neighbor)
            WITH DISTINCT neighbor
            MATCH (neighbor)-[r]-(conn)
            WITH neighbor, type(r) + ' ' + coalesce(conn.name, '') AS conn_str
            WITH neighbor, collect(conn_str) AS connections
            RETURN id(neighbor) AS n_id, neighbor.name AS n_name, labels(neighbor)[0] AS n_type, neighbor.description AS n_desc, connections
            """
            
            result = session.run(query_cypher, seed_ids=seed_ids)
            
            neighbor_data = []
            for record in result:
                n_id = record["n_id"]
                n_name = record["n_name"] or "Unknown"
                n_type = record["n_type"] or "Entity"
                n_desc = record["n_desc"] or ""
                
                # Rank connections by word overlap with query
                connections = record["connections"]
                query_words = set(query.lower().split())
                connections.sort(key=lambda c: len(set(c.lower().split()) & query_words), reverse=True)
                connections = connections[:3]
                
                nodes_traversed_set.add(n_id)
                
                if str(n_id) in self.embeddings_cache:
                    n_emb = self.embeddings_cache[str(n_id)]
                else:
                    text_to_embed = f"{n_name} {n_desc}".strip()
                    if not text_to_embed:
                        continue
                    n_emb = self.embedder.embed_query(text_to_embed)
                    
                sim = float(cosine_similarity([query_embedding], [n_emb])[0][0])
                if sim > 0.25:
                    neighbor_data.append({
                        "sim": sim,
                        "name": n_name,
                        "type": n_type,
                        "desc": n_desc,
                        "connections": connections
                    })
                    
        neighbor_data.sort(key=lambda x: x["sim"], reverse=True)
        top_neighbors = neighbor_data[:8]
        
        if not top_neighbors:
            graph_context_str = "No relevant graph relationships found."
        else:
            context_lines = ["Key entities related to your query:"]
            for i, n in enumerate(top_neighbors, 1):
                conn_str = ", ".join(n["connections"])
                context_lines.append(f"{i}. {n['name']} ({n['type']}): {n['desc']}")
                if conn_str:
                    context_lines.append(f"   Connected to: {conn_str}")
                    
            graph_context_str = "\n".join(context_lines)
            
            words = graph_context_str.split()
            if len(words) > 600:
                graph_context_str = " ".join(words[:600]) + "..."
            
        latency_ms = int((time.time() - start_time) * 1000)
        
        return RetrievalResult(
            seed_nodes=seed_nodes,
            graph_context_str=graph_context_str,
            hop_count=max_hops,
            nodes_traversed=len(nodes_traversed_set),
            latency_ms=latency_ms
        )

    def multi_hop_retrieve(self, query: str, reasoning_chain: bool = True) -> RetrievalResult:
        """Decompose query into sub-queries, retrieve for each, and merge contexts."""
        start_time = time.time()
        
        # Simple heuristic decomposition
        sub_queries = [query]
        words = query.split()
        for i, w in enumerate(words):
            if w.lower() in ["who", "what", "where", "when"] and i > 0:
                sub_q = " ".join(words[i:])
                if len(sub_q.split()) > 2:
                    sub_queries.append(sub_q)
                    
        # Also split by " and "
        parts = re.split(r'\band\b', query, flags=re.IGNORECASE)
        if len(parts) > 1:
            sub_queries.extend([p.strip() for p in parts if len(p.strip()) > 3])
            
        sub_queries = list(set(sub_queries))
        logger.info(f"Decomposed query into: {sub_queries}")
        
        all_seed_nodes = []
        all_contexts = set()
        total_nodes_traversed = set()
        
        for sub_q in sub_queries:
            # use max_hops=1 or 2 per sub-query
            res = self.retrieve(sub_q, top_k=3, max_hops=2)
            
            # merge seed nodes
            for seed in res.seed_nodes:
                if seed not in all_seed_nodes:
                    all_seed_nodes.append(seed)
                    
            if res.graph_context_str != "No data available." and res.graph_context_str != "No relevant graph relationships found.":
                for line in res.graph_context_str.split("\n"):
                    if not line.startswith("Key entities"):
                        all_contexts.add(line)
                    
            # simulate traversing nodes
            # We don't have the exact IDs traversed here without changing retrieve return signature,
            # but we'll approximate with res.nodes_traversed
            pass 
            
        merged_context = "\n".join(sorted(list(all_contexts)))
        if not merged_context:
            merged_context = "No context found."
            
        latency_ms = int((time.time() - start_time) * 1000)
        
        return RetrievalResult(
            seed_nodes=all_seed_nodes,
            graph_context_str=merged_context,
            hop_count=2, # max hops used
            nodes_traversed=len(all_contexts) * 2, # Approximation
            latency_ms=latency_ms
        )
