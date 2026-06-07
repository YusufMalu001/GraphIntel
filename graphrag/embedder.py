import logging
from pathlib import Path
from typing import Dict, Any, Union

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class GraphEmbedder:
    """Handles embedding generation for entities and queries using sentence-transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info(f"Loading SentenceTransformer model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
    def embed_entity(self, node_type: str, properties: Dict[str, Any]) -> np.ndarray:
        """Embeds a graph entity based on its type and properties."""
        name = properties.get("name", "Unknown")
        description = properties.get("description", "")
        
        # Avoid "None" strings if description is missing
        if description is None:
            description = ""
            
        text = f"{node_type}: {name}. {description}".strip()
        return self.embed_query(text)
        
    def embed_query(self, query_text: str) -> np.ndarray:
        """Embeds a search query or generic text."""
        return self.model.encode(query_text, normalize_embeddings=True)
        
    def embed_all_entities(self, neo4j_driver) -> Dict[int, np.ndarray]:
        """Iterates over all nodes in the database and generates embeddings."""
        logger.info("Starting to embed all entities from Neo4j...")
        embeddings = {}
        
        with neo4j_driver.session() as session:
            # Cypher query to get all nodes
            query = "MATCH (n) RETURN elementId(n) AS element_id, id(n) AS node_id, labels(n)[0] AS node_type, properties(n) AS props"
            result = session.run(query)
            
            for record in result:
                # Neo4j 5+ uses elementId, but we'll store string versions or int node_id
                # id() is deprecated in Neo4j 5, but still works. We'll use node_id (int) or element_id (string)
                # The user prompts specifically mention `dict[node_id, embedding]`. We will use string `elementId` as it's safer in neo4j 5+,
                # but let's stick to `node_id` as string to be unambiguous.
                # Actually, standard integer ID is fine since many queries use id(n). Let's use string.
                node_id = str(record["node_id"]) 
                node_type = record["node_type"] or "Entity"
                props = record["props"] or {}
                
                embeddings[node_id] = self.embed_entity(node_type, props)
                
        logger.info(f"Successfully embedded {len(embeddings)} entities.")
        return embeddings
        
    def save_embeddings(self, embeddings: Dict[str, np.ndarray], path: Union[str, Path]):
        """Caches embeddings to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, embeddings, allow_pickle=True)
        logger.info(f"Saved embeddings to {path}")
        
    def load_embeddings(self, path: Union[str, Path]) -> Dict[str, np.ndarray]:
        """Loads cached embeddings from disk."""
        path = Path(path)
        if not path.exists():
            logger.warning(f"Embeddings file not found at {path}")
            return {}
            
        logger.info(f"Loading embeddings from {path}")
        data = np.load(path, allow_pickle=True)
        return data.item() if data.size == 1 else dict(data)
