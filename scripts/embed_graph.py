import os
import logging
from neo4j import GraphDatabase
from dotenv import load_dotenv

from graphrag.embedder import GraphEmbedder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def main():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j123")
    
    logger.info("Connecting to Neo4j...")
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    embedder = GraphEmbedder()
    embeddings = embedder.embed_all_entities(driver)
    
    embedder.save_embeddings(embeddings, "results/entity_embeddings.npy")
    logger.info("Finished embedding graph entities.")
    
    driver.close()

if __name__ == "__main__":
    main()
