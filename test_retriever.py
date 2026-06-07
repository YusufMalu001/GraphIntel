import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
pw = os.getenv('NEO4J_PASSWORD')
driver = GraphDatabase.driver(uri, auth=(user, pw))

def test_query(seed_name):
    max_hops = 2
    with driver.session() as session:
        # We will manually mock seed_ids for Joffrey Baratheon
        seed_res = session.run("MATCH (n) WHERE n.name = $name RETURN id(n) AS id", name=seed_name)
        seed_ids = [record["id"] for record in seed_res]
        
        if not seed_ids:
            print("Seed not found")
            return
            
        query_cypher = f"""
        MATCH (seed)
        WHERE id(seed) IN $seed_ids
        MATCH p=(seed)-[*0..{max_hops}]-(neighbor)
        WITH DISTINCT neighbor, collect(nodes(p)) AS paths
        MATCH (neighbor)-[r]-(conn)
        WITH neighbor, conn, type(r) AS rel_type, startNode(r) = neighbor AS is_start, paths
        // Check if conn is in any of the traversal paths
        WITH neighbor, conn, rel_type, is_start,
             any(path IN paths WHERE conn IN path) AS in_path
        ORDER BY in_path DESC
        WITH neighbor, 
             CASE WHEN is_start THEN '-> ' + rel_type + ' -> ' + coalesce(conn.name, '')
             ELSE '<- ' + rel_type + ' <- ' + coalesce(conn.name, '') END AS conn_str
        WITH neighbor, collect(conn_str) AS connections
        RETURN id(neighbor) AS n_id, neighbor.name AS n_name, labels(neighbor)[0] AS n_type, neighbor.description AS n_desc, connections
        """
        
        result = session.run(query_cypher, seed_ids=seed_ids)
        for record in result:
            n_name = record["n_name"] or "Unknown"
            n_type = record["n_type"] or "Entity"
            n_desc = record["n_desc"] or ""
            connections = record["connections"][:3]
            
            print(f"{n_name} ({n_type}): {n_desc}")
            print("Connected to:", ", ".join(connections))
            print("----")

test_query("Joffrey Baratheon")
