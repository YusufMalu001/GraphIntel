from graphrag.embedder import GraphEmbedder
from sklearn.metrics.pairwise import cosine_similarity

embedder = GraphEmbedder()
q = embedder.embed_query('Who is the maternal grandfather of Joffrey Baratheon?')
n_emb = embedder.embed_query('Tywin Lannister Person')

sim = cosine_similarity([q], [n_emb])[0][0]
print("Sim:", sim)
