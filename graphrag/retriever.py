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
        context_triplets = set()
        nodes_traversed_set = set(seed_ids)
        
        with self.driver.session() as session:
            # Get seed node details
            seed_res = session.run("MATCH (n) WHERE id(n) IN $seed_ids RETURN id(n) AS id, n.name AS name", seed_ids=seed_ids)
            seed_names = {}
            for record in seed_res:
                seed_nodes.append({"id": record["id"], "name": record["name"]})
                seed_names[record["id"]] = record["name"]
                
            # Traverse graph up to max_hops
            # We collect all distinct relationships in the paths
            query_cypher = f"""
            MATCH (seed)
            WHERE id(seed) IN $seed_ids
            MATCH p=(seed)-[*1..{max_hops}]-(neighbor)
            WITH seed, p LIMIT 200
            UNWIND relationships(p) AS r
            RETURN DISTINCT id(seed) AS seed_id, seed.name AS seed_name,
                   startNode(r).name AS source_name, type(r) AS relation, endNode(r).name AS target_name,
                   id(startNode(r)) AS source_id, id(endNode(r)) AS target_id
            """
            
            result = session.run(query_cypher, seed_ids=seed_ids)
            
            for record in result:
                s_name = record["seed_name"] or "Unknown"
                src = record["source_name"] or "Unknown"
                rel = record["relation"]
                tgt = record["target_name"] or "Unknown"
                
                nodes_traversed_set.add(record["source_id"])
                nodes_traversed_set.add(record["target_id"])
                
                # Build structured context: "Seed: {node}. Related: {neighbor} via {relationship}."
                # It's cleaner to express as triples associated with the seed.
                triplet_str = f"Seed: {s_name}. Related: {src} -> {rel} -> {tgt}."
                context_triplets.add(triplet_str)
                
        # Deduplicate and rank (by simple presence for now, as it's a set)
        graph_context_str = "\n".join(sorted(list(context_triplets)))
        if not graph_context_str:
            graph_context_str = "No graph relationships found for seeds."
            
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
                    
            if res.graph_context_str != "No data available." and res.graph_context_str != "No graph relationships found for seeds.":
                for line in res.graph_context_str.split("\n"):
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
