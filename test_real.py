import sys
import numpy as np

# Create dummy module BEFORE any graphrag imports
class DummyEmbedder:
    def __init__(self):
        self.embeddings_cache = np.load('results/entity_embeddings.npy', allow_pickle=True).item()
    def embed_query(self, text):
        return np.ones(384)
    def load_embeddings(self, path):
        return self.embeddings_cache

import graphrag.embedder
graphrag.embedder.GraphEmbedder = DummyEmbedder

from graphrag.retriever import GraphRAGRetriever
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD')))

retriever = GraphRAGRetriever(driver, DummyEmbedder(), DummyEmbedder().embeddings_cache)

# Bypass getting seeds - MUST be integers
retriever._get_top_k_seeds = lambda q, k: [1980, 397]

# Bypass similarity so all traversed nodes pass
import sklearn.metrics.pairwise
sklearn.metrics.pairwise.cosine_similarity = lambda a, b: [[1.0]]

res = retriever.retrieve("Who is the maternal grandfather of Joffrey Baratheon?")
print("CONTEXT START")
print(res.graph_context_str)
print("CONTEXT END")
