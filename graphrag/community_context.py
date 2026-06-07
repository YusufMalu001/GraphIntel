import logging
from typing import Any

logger = logging.getLogger(__name__)

class CommunityContextBuilder:
    """Builds and manages community-level context for graph entities."""
    
    def __init__(self, neo4j_driver):
        self.driver = neo4j_driver
        
    def get_community_context(self, node_id: str) -> str:
        """Returns a summary of the node's community."""
        with self.driver.session() as session:
            # 1. Find the community of this node
            result = session.run("""
                MATCH (n) WHERE id(n) = $node_id
                RETURN n.community AS community
            """, node_id=int(node_id))
            
            record = result.single()
            if not record or record.get("community") is None:
                return "No community information available."
                
            community_id = record["community"]
            
            # 2. Find other members of this community
            members_result = session.run("""
                MATCH (n) WHERE n.community = $community_id
                RETURN n.name AS name
                LIMIT 15
            """, community_id=community_id)
            
            members = [r["name"] for r in members_result if r["name"]]
            member_names = ", ".join(members)
            if not member_names:
                member_names = "Unknown members"
            
            # 3. Get top relationships within this community
            rel_result = session.run("""
                MATCH (a)-[r]->(b)
                WHERE a.community = $community_id AND b.community = $community_id
                RETURN type(r) AS rel_type, count(r) AS count
                ORDER BY count DESC
                LIMIT 3
            """, community_id=community_id)
            
            top_rels = [r["rel_type"] for r in rel_result]
            top_rels_str = ", ".join(top_rels) if top_rels else "None"
            
            return f"Community {community_id} contains: {member_names}. Key relationships: {top_rels_str}."

    def augment_retrieval(self, retrieval_result: Any) -> Any:
        """
        Add community context for each seed node in the retrieval result.
        Increases recall for 'who else is connected to X' queries.
        """
        added_context = []
        # Expecting retrieval_result to have a list of dicts for seed_nodes, or list of IDs
        for seed_node in retrieval_result.seed_nodes:
            # Check if seed_node is a dict with 'id' or just an id
            node_id = seed_node.get("id") if isinstance(seed_node, dict) else seed_node
            
            if node_id is not None:
                community_info = self.get_community_context(str(node_id))
                name = seed_node.get("name", f"Node {node_id}") if isinstance(seed_node, dict) else f"Node {node_id}"
                added_context.append(f"Community context for {name}: {community_info}")
            
        if added_context:
            retrieval_result.graph_context_str += "\n\n--- Community Context ---\n" + "\n".join(added_context)
            
        return retrieval_result
