import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()
driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD')))

with driver.session() as session:
    res = session.run('MATCH (n)-[r]-() WHERE n.name CONTAINS "Joffrey" RETURN n.name, count(r)')
    for r in res:
        print(r["n.name"], r["count(r)"])
    
    print("---")
    res = session.run('MATCH (n)-[r]-() WHERE n.name CONTAINS "Cersei" RETURN n.name, count(r)')
    for r in res:
        print(r["n.name"], r["count(r)"])
        
    print("---")
    res = session.run('MATCH (n)-[r]-() WHERE n.name CONTAINS "Tywin" RETURN n.name, count(r)')
    for r in res:
        print(r["n.name"], r["count(r)"])
