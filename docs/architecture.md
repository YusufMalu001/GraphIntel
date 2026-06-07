# System Architecture

## Overview
GraphIntel integrates a Neo4j knowledge graph built from Game of Thrones wiki data with a custom GraphRAG retrieval pipeline.

## Component Design

### 1. Embedder (`graphrag/embedder.py`)
- Uses `sentence-transformers` (`all-MiniLM-L6-v2`) entirely offline.
- Caches node embeddings to a numpy array for fast cosine similarity lookups.

### 2. Community Context (`graphrag/community_context.py`)
- Interfaces with the output of `community_detection.py`.
- Enriches seed node retrieval with community-level insights (e.g., related house members).

### 3. Flat Retriever (`graphrag/flat_retriever.py`)
- The baseline RAG. Maps a user query directly to entity flat text properties via cosine similarity.

### 4. Graph Retriever (`graphrag/retriever.py`)
- Employs semantic search to find initial seed nodes.
- Traverses the Neo4j graph up to `max_hops` to gather structured context.

## Retrieval Architecture Diagram

```
         User Query
             |
             v
      [ Query Embedding ]
             |
      +------+------+
      |             |
[Flat RAG]     [Graph RAG]
      |             |
 (Cosine Sim)  (Cosine Sim for Seeds)
      |             |
  (Top K)       (Top K Seeds)
      |             |
      |        [Graph Traversal]
      |             |
      |        [Community Context]
      |             |
[LLM Answer]   [LLM Answer]
```
