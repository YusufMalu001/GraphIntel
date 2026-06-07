import os
import json
import logging
from pathlib import Path
from tqdm import tqdm
from neo4j import GraphDatabase

from graphrag.embedder import GraphEmbedder
from graphrag.retriever import GraphRAGRetriever
from graphrag.flat_retriever import FlatRAGRetriever
from graphrag.community_context import CommunityContextBuilder
from evaluation.benchmark import call_hf_api, HF_TOKEN

logger = logging.getLogger(__name__)

def run_ablation():
    if not HF_TOKEN:
        logger.error("HF_TOKEN not set")
        return
        
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
    
    graph_retriever = GraphRAGRetriever(driver, embedder, embeddings)
    flat_retriever = FlatRAGRetriever(driver, embedder, embeddings)
    community_builder = CommunityContextBuilder(driver)
    
    with open("evaluation/questions.json", 'r') as f:
        questions = json.load(f)
        
    results = []
    
    for q in tqdm(questions[:10], desc="Running Ablation Study"): # test on 10 to save API calls
        question_text = q["question"]
        gt_answer = q["answer"]
        
        # Condition A: Flat RAG
        flat_res = flat_retriever.retrieve(question_text)
        flat_prompt = f"Context: {flat_res.graph_context_str}\nQuestion: {question_text}\nAnswer concisely:"
        flat_ans = call_hf_api(flat_prompt)
        
        # Condition B: Graph traversal only (no community)
        graph_res = graph_retriever.retrieve(question_text)
        graph_prompt = f"Context: {graph_res.graph_context_str}\nQuestion: {question_text}\nAnswer concisely:"
        graph_ans = call_hf_api(graph_prompt)
        
        # Condition C: Graph + Community
        graph_comm_res = graph_retriever.retrieve(question_text)
        graph_comm_res = community_builder.augment_retrieval(graph_comm_res)
        graph_comm_prompt = f"Context: {graph_comm_res.graph_context_str}\nQuestion: {question_text}\nAnswer concisely:"
        graph_comm_ans = call_hf_api(graph_comm_prompt)
        
        # Evaluate
        def exact_match(ans, gt):
            return gt.lower() in ans.lower() if ans != "api_timeout" else False
            
        results.append({
            "id": q["id"],
            "flat_acc": exact_match(flat_ans, gt_answer),
            "graph_acc": exact_match(graph_ans, gt_answer),
            "graph_comm_acc": exact_match(graph_comm_ans, gt_answer)
        })
        
    # Summarize
    total = len(results)
    summary = {
        "flat_accuracy": sum(r["flat_acc"] for r in results) / total,
        "graph_accuracy": sum(r["graph_acc"] for r in results) / total,
        "graph_comm_accuracy": sum(r["graph_comm_acc"] for r in results) / total
    }
    
    out_path = Path("results/ablation_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(summary, f, indent=2)
        
    print("\n--- ABLATION RESULTS ---")
    print(f"Flat RAG: {summary['flat_accuracy']*100:.1f}%")
    print(f"Graph Only: {summary['graph_accuracy']*100:.1f}%")
    print(f"Graph + Community: {summary['graph_comm_accuracy']*100:.1f}%")
    
    driver.close()
    
if __name__ == "__main__":
    run_ablation()
