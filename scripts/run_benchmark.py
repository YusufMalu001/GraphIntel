import os
import logging
from neo4j import GraphDatabase
from dotenv import load_dotenv

from graphrag.embedder import GraphEmbedder
from evaluation.benchmark import BenchmarkRunner
from evaluation.metrics import compute_metrics

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def main():
    neo4j_uri = os.getenv("NEO4J_URI", "neo4j+s://xxxx.databases.neo4j.io")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j123")
    
    driver = GraphDatabase.driver(
        neo4j_uri, 
        auth=(neo4j_user, neo4j_password),
        max_connection_lifetime=3600
    )
    
    embedder = GraphEmbedder()
    embeddings = embedder.load_embeddings("results/entity_embeddings.npy")
    
    runner = BenchmarkRunner(driver, embedder, embeddings)
    
    # Change limit to None for full run. User requested testing 5 first.
    # Set limit=5 for the test run.
    runner.run("evaluation/questions.json", "results/benchmark_results.json", limit=5)
    
    compute_metrics("results/benchmark_results.json", "results/final_metrics.json")
    
    driver.close()

if __name__ == "__main__":
    main()
