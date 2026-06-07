from graphrag.embedder import GraphEmbedder
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

embedder = GraphEmbedder()
emb = embedder.load_embeddings('results/entity_embeddings.npy')
q = embedder.embed_query('Who is the maternal grandfather of Joffrey Baratheon?')

sim = cosine_similarity([q], np.vstack(list(emb.values())))[0]
ids = list(emb.keys())

driver = GraphDatabase.driver(os.getenv('NEO4J_URI'), auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD')))
res = driver.session().run('MATCH (n {name: "Tywin Lannister"}) RETURN id(n) AS id').single()
tywin_id = str(res["id"])

print("Tywin sim:", sim[ids.index(tywin_id)])
