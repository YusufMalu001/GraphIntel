import os
import json
import time
import logging
from pathlib import Path
from tqdm import tqdm
import requests
import numpy as np

from dotenv import load_dotenv
load_dotenv()

from graphrag.retriever import GraphRAGRetriever
from graphrag.flat_retriever import FlatRAGRetriever

logger = logging.getLogger(__name__)

HF_TOKEN = os.getenv("HF_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-72B-Instruct" 

def call_hf_api(prompt: str) -> str:
    """Call HF inference API with exponential backoff."""
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 100, "temperature": 0.1, "return_full_text": False}
    }
    
    retries = [10, 30, 60]
    
    for i in range(4):
        try:
            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "").strip()
                return ""
            elif response.status_code == 429:
                logger.warning(f"Rate limit hit. Status {response.status_code}")
            else:
                logger.warning(f"API Error {response.status_code}: {response.text}")
        except Exception as e:
            logger.warning(f"API Request Exception: {str(e)}")
            
        if i < 3:
            wait_time = retries[i]
            logger.info(f"Retrying in {wait_time}s...")
            time.sleep(wait_time)
            
    return "api_timeout"

class BenchmarkRunner:
    def __init__(self, driver, embedder, embeddings_cache):
        self.graph_retriever = GraphRAGRetriever(driver, embedder, embeddings_cache)
        self.flat_retriever = FlatRAGRetriever(driver, embedder, embeddings_cache)
        self.embedder = embedder
        self.timeout_count = 0
        
    def evaluate_answer(self, generated: str, ground_truth: str, context: str) -> dict:
        if generated == "api_timeout":
            return {"exact_match": False, "semantic_match": False, "faithfulness": False}
            
        exact_match = ground_truth.lower() in generated.lower()
        
        # Semantic match > 0.8
        gen_emb = self.embedder.embed_query(generated)
        gt_emb = self.embedder.embed_query(ground_truth)
        
        # reshape for cosine_similarity
        sim = float(np.dot(gen_emb, gt_emb) / (np.linalg.norm(gen_emb) * np.linalg.norm(gt_emb)))
        semantic_match = sim > 0.8
        
        # Faithfulness check via LLM judge
        judge_prompt = f"Context: {context}\nQuestion: Is this answer supported by the context? Answer '{generated}'. Reply with only 'Yes' or 'No':"
        judge_res = call_hf_api(judge_prompt)
        
        faithfulness = False
        if judge_res != "api_timeout":
            faithfulness = "yes" in judge_res.lower()
        else:
            self.timeout_count += 1
            
        return {"exact_match": exact_match, "semantic_match": semantic_match, "faithfulness": faithfulness}

    def run(self, questions_file: str, results_file: str, limit: int = None):
        with open(questions_file, 'r') as f:
            questions = json.load(f)
            
        if limit:
            questions = questions[:limit]
            
        results_path = Path(results_file)
        results_path.parent.mkdir(parents=True, exist_ok=True)
        
        if results_path.exists():
            with open(results_path, 'r') as f:
                try:
                    results = json.load(f)
                except json.JSONDecodeError:
                    results = []
        else:
            results = []
            
        completed_ids = {r["id"] for r in results}
        
        for q in tqdm(questions, desc="Running Benchmark"):
            if q["id"] in completed_ids:
                continue
                
            question_text = q["question"]
            gt_answer = q["answer"]
            
            # GraphRAG
            graph_res = self.graph_retriever.retrieve(question_text)
            graph_prompt = f"Using only this context, answer the question.\nContext: {graph_res.graph_context_str}\nQuestion: {question_text}\nAnswer concisely:"
            graph_ans = call_hf_api(graph_prompt)
            if graph_ans == "api_timeout": self.timeout_count += 1
            graph_eval = self.evaluate_answer(graph_ans, gt_answer, graph_res.graph_context_str)
            
            # FlatRAG
            flat_res = self.flat_retriever.retrieve(question_text)
            flat_prompt = f"Using only this context, answer the question.\nContext: {flat_res.graph_context_str}\nQuestion: {question_text}\nAnswer concisely:"
            flat_ans = call_hf_api(flat_prompt)
            if flat_ans == "api_timeout": self.timeout_count += 1
            flat_eval = self.evaluate_answer(flat_ans, gt_answer, flat_res.graph_context_str)
            
            result_record = {
                "id": q["id"],
                "category": q["category"],
                "hops_required": q["hops_required"],
                "graphrag": {
                    "answer": graph_ans,
                    "exact_match": graph_eval["exact_match"],
                    "semantic_match": graph_eval["semantic_match"],
                    "faithfulness": graph_eval["faithfulness"],
                    "latency_ms": graph_res.latency_ms,
                    "nodes_traversed": graph_res.nodes_traversed,
                    "hops_used": graph_res.hop_count
                },
                "flatrag": {
                    "answer": flat_ans,
                    "exact_match": flat_eval["exact_match"],
                    "semantic_match": flat_eval["semantic_match"],
                    "faithfulness": flat_eval["faithfulness"],
                    "latency_ms": flat_res.latency_ms,
                    "nodes_traversed": flat_res.nodes_traversed,
                    "hops_used": flat_res.hop_count
                }
            }
            
            results.append(result_record)
            
            # Save incrementally
            with open(results_path, 'w') as f:
                json.dump(results, f, indent=2)
                
        logger.info(f"Benchmark complete. Total API timeouts: {self.timeout_count}")
