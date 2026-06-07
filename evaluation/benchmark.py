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

from groq import Groq

logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_answer(context: str, question: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system", 
                "content": "Answer the question using only the provided context. Be concise. Answer in 1-5 words maximum."
            },
            {
                "role": "user",
                "content": f"Context: {context}\n\nQuestion: {question}\nAnswer:"
            }
        ],
        max_tokens=50,
        temperature=0.1
    )
    return response.choices[0].message.content.strip()

def judge_faithfulness(context: str, question: str, answer: str) -> bool:
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": "Answer only Yes or No."
            },
            {
                "role": "user", 
                "content": f"Context: {context}\nQuestion: {question}\nAnswer: {answer}\n\nIs this answer supported by the context? Yes or No:"
            }
        ],
        max_tokens=5,
        temperature=0.0
    )
    result = response.choices[0].message.content.strip()
    return result.lower().startswith('yes')

class BenchmarkRunner:
    def __init__(self, driver, embedder, embeddings_cache):
        self.graph_retriever = GraphRAGRetriever(driver, embedder, embeddings_cache)
        self.flat_retriever = FlatRAGRetriever(driver, embedder, embeddings_cache)
        self.embedder = embedder
        self.timeout_count = 0
        
    def evaluate_answer(self, generated: str, ground_truth: str, context: str, question: str) -> dict:
        if generated == "api_timeout" or not generated:
            return {"exact_match": False, "semantic_match": False, "faithfulness": False}
            
        from evaluation.metrics import score_answer
        exact_match = score_answer(ground_truth, generated)
        
        # Semantic match > 0.8
        gen_emb = self.embedder.embed_query(generated)
        gt_emb = self.embedder.embed_query(ground_truth)
        
        # reshape for cosine_similarity
        sim = float(np.dot(gen_emb, gt_emb) / (np.linalg.norm(gen_emb) * np.linalg.norm(gt_emb)))
        semantic_match = sim > 0.8
        
        # Faithfulness check via LLM judge
        try:
            faithfulness = judge_faithfulness(context, question, generated)
        except Exception as e:
            logger.warning(f"Faithfulness judge error: {e}")
            faithfulness = False
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
            try:
                graph_ans = generate_answer(graph_res.graph_context_str, question_text)
            except Exception as e:
                logger.warning(f"Groq API Error: {e}")
                graph_ans = "api_timeout"
                self.timeout_count += 1
            graph_eval = self.evaluate_answer(graph_ans, gt_answer, graph_res.graph_context_str, question_text)
            
            # FlatRAG
            flat_res = self.flat_retriever.retrieve(question_text)
            try:
                flat_ans = generate_answer(flat_res.graph_context_str, question_text)
            except Exception as e:
                logger.warning(f"Groq API Error: {e}")
                flat_ans = "api_timeout"
                self.timeout_count += 1
            flat_eval = self.evaluate_answer(flat_ans, gt_answer, flat_res.graph_context_str, question_text)
            
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
