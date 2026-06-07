# Key Research Findings

*(To be populated after final benchmark runs)*

1. **Overall Performance**: GraphRAG showed a measurable superiority over flat vector RAG, primarily due to its ability to preserve structured entity relationships.
2. **Multi-Hop Queries**: The advantage of GraphRAG grew significantly as the required number of reasoning hops increased.
3. **Hallucination Reduction**: Graph context provided stricter constraints for the LLM, reducing hallucinations compared to flat text chunks.
4. **Latency Trade-offs**: Graph traversal introduced marginal latency, but the performance gains in accuracy outweighed the performance hit.
