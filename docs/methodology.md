# Evaluation Methodology

## Dataset Design
We utilize a curated set of 50 multi-hop reasoning questions covering 5 categories based strictly on the Game of Thrones wiki data scraped into the Neo4j knowledge graph.
1. **Family Lineage**: Questions requiring traversal of family trees.
2. **Political Allegiance**: House allegiances and loyalties.
3. **Conflict Causality**: Event to consequence chains.
4. **Geographic Political**: Location + ruler + house chains.
5. **Cross Domain**: Requires combining 3+ node types.

## Metrics
- **Accuracy**: Exact string match + Semantic match (Cosine Similarity > 0.8 on embedded strings).
- **Faithfulness**: LLM-as-a-judge prompt to ensure answers are strictly grounded in retrieved context, penalizing hallucinations.
- **Latency**: Average milliseconds spent in the retrieval step per query.
- **Efficiency**: Number of nodes traversed.
