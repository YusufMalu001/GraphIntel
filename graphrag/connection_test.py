import os
import sys
from neo4j import GraphDatabase
from dotenv import load_dotenv

def test_connection():
    load_dotenv()
    
    uri = os.getenv("NEO4J_URI", "neo4j+s://xxxx.databases.neo4j.io")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    print(f"Testing connection to: {uri}")
    
    try:
        driver = GraphDatabase.driver(
            uri, 
            auth=(user, password),
            max_connection_lifetime=3600
        )
        with driver.session() as session:
            # Test simple query
            res = session.run("RETURN 1 as test").single()
            if res and res["test"] == 1:
                print("Connection successful")
            else:
                print("Connection failed: RETURN 1 did not work")
                sys.exit(1)
                
            # Get counts
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            
            print(f"Node count: {node_count}")
            print(f"Relationship count: {rel_count}")
            
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    test_connection()
