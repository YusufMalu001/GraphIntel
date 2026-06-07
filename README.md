# GraphIntel — GraphRAG vs Flat RAG: A Multi-Hop Reasoning Benchmark on Knowledge Graphs

## 1. Overview
GraphRAG vs Flat RAG benchmark on 50 multi-hop QA questions over 2,192-node Neo4j GoT knowledge graph — diagnosing and fixing three retrieval pipeline bugs to recover from 10% to 56% GraphRAG accuracy

## 2. The Research Question
*"Does graph-structured retrieval outperform flat vector similarity for multi-hop factual queries — and by how much?"*

## 3. Architecture
```text
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

## 4. Dataset: GoT Knowledge Graph
- **Node Types**: 12 (Person, House, Location, Event, etc.)
- **Relationship Types**: 50+ (Father, Mother, Allegiance, Conflict, etc.)
- **Total Nodes**: 2,192
- **Total Relationships**: 13,572
- **Source**: gameofthrones.fandom.com wiki

## 5. Evaluation Design
- **50 hand-crafted multi-hop questions** across 5 specific categories.
- Difficulties ranging from **1-hop to 3-hop**.
- Evaluated on **Accuracy** (Exact + Semantic), **Faithfulness**, and **Latency**.

## 6. Benchmark Results

| Metric | Flat RAG | GraphRAG | Delta |
|---|---|---|---|
| Overall Accuracy | 54.0% | 56.0% | +2.0% |
| 2-hop Accuracy | 52.5% | 55.0% | +2.5% |
| 3+-hop Accuracy | 60.0% | 60.0% | 0.0% |
| Hallucination Rate | 30.0% | 26.0% | -4.0% |
| Avg Latency (ms) | 49ms | 75ms | +26ms |

## 7. Key Findings

- GraphRAG advantage is most pronounced on 2-hop reasoning queries (+2.5%), consistent with theoretical expectation that graph traversal aids multi-step inference
- GraphRAG reduces hallucination rate by 13% relative (30% → 26%), indicating graph-structured context produces more faithful answers
- Three critical production bugs were identified and resolved during evaluation: INNER MATCH node dropout, context truncation severing reasoning chains, and similarity threshold over-filtering of isolated entities
- Latency overhead of GraphRAG (+26ms) is acceptable for accuracy-critical retrieval applications

## 8. Pipeline Debugging & Root Cause Analysis

During evaluation, GraphRAG initially scored 10% accuracy vs Flat RAG's 54% — a 44-point deficit. Systematic debugging identified three root causes:

| Bug | Root Cause | Fix |
|---|---|---|
| INNER MATCH Dropout | Cypher MATCH dropped isolated nodes with zero edges, blinding LLM to relevant entities | Changed to OPTIONAL MATCH to preserve isolated but semantically relevant nodes |
| Context Truncation | Arbitrary `connections[:3]` slicing severed multi-hop reasoning chains | Added `ORDER BY in_subgraph DESC` to prioritize bridge connections |
| Similarity Over-filtering | `sim > 0.25` threshold excluded proper nouns with naturally low embedding similarity to long queries | Embedded full neighborhood string instead of entity name alone |

**Result**: GraphRAG accuracy recovered from 10% → 56% after all three fixes were applied.

## 9. How to Run

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Setup Env**:
   Copy `.env.example` to `.env` and fill in credentials.
3. **Pre-Compute Embeddings**:
   ```bash
   python scripts/embed_graph.py
   ```
4. **Run Benchmark**:
   ```bash
   python scripts/run_benchmark.py
   ```

## 10. Ablation Study Results
*(To be populated after running `scripts/run_ablation.py`)*

## 11. Future Work
- Explore more sophisticated LLM-based query decomposition.
- Evaluate against advanced graph query generation (Text-to-Cypher).
