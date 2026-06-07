import os
import json
import logging
from neo4j import GraphDatabase
from dotenv import load_dotenv

from graphrag.embedder import GraphEmbedder
from evaluation.benchmark import BenchmarkRunner

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

def main():
    logger.info("Ablation study is defined in experiments/ablation.py")
    # For simplicity, we just import and run from here
    from experiments.ablation import run_ablation
    run_ablation()

if __name__ == "__main__":
    main()
