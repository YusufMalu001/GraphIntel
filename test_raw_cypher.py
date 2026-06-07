import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD')))

query_cypher = """
MATCH (seed)
WHERE id(seed) IN $seed_ids
MATCH (seed)-[*0..2]-(n)
WITH DISTINCT n AS all_neighbors
WITH collect(all_neighbors) AS all_n_list

UNWIND all_n_list AS neighbor
OPTIONAL MATCH (neighbor)-[r]-(conn)
WITH neighbor, conn, type(r) AS rel_type, startNode(r) = neighbor AS is_start, all_n_list
WITH neighbor, conn, rel_type, is_start, conn IN all_n_list AS in_subgraph
ORDER BY in_subgraph DESC
WITH neighbor, 
     CASE 
        WHEN conn IS NULL THEN null
        WHEN is_start THEN '-> ' + rel_type + ' -> ' + coalesce(conn.name, '')
        ELSE '<- ' + rel_type + ' <- ' + coalesce(conn.name, '') 
     END AS conn_str
WITH neighbor, collect(conn_str) AS all_conns
WITH neighbor, [c IN all_conns WHERE c IS NOT NULL] AS connections
RETURN id(neighbor) AS n_id, neighbor.name AS n_name, labels(neighbor)[0] AS n_type, neighbor.description AS n_desc, connections
"""

with driver.session() as session:
    result = session.run(query_cypher, seed_ids=[1980, 397])
    for record in result:
        print(record["n_name"], record["connections"][:3])
