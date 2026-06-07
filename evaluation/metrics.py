import json
import logging
from collections import defaultdict
from pathlib import Path
import re
from difflib import SequenceMatcher

def normalize(text: str) -> str:
    return re.sub(r'[^a-z0-9\s]', '', text.lower()).strip()

def score_answer(expected: str, generated: str) -> bool:
    if not generated or len(generated.strip()) < 2:
        return False
    exp_norm = normalize(expected)
    gen_norm = normalize(generated)
    if exp_norm in gen_norm:
        return True
        
    exp_words = [w for w in exp_norm.split() if len(w) > 2]
    for w in exp_words:
        if w in gen_norm.split():
            return True
            
    ratio = SequenceMatcher(None, exp_norm, gen_norm).ratio()
    return ratio > 0.7

logger = logging.getLogger(__name__)

def compute_metrics(results_file: str, output_file: str):
    path = Path(results_file)
    if not path.exists():
        logger.error(f"Results file {results_file} not found.")
        return
        
    with open(path, 'r') as f:
        results = json.load(f)
        
    total = len(results)
    if total == 0:
        logger.warning("No results to compute metrics for.")
        return
        
    g_correct = 0
    f_correct = 0
    g_hallucinations = 0
    f_hallucinations = 0
    g_latency_total = 0
    f_latency_total = 0
    
    hops_data = {
        1: {"g_correct": 0, "f_correct": 0, "total": 0},
        2: {"g_correct": 0, "f_correct": 0, "total": 0},
        "3+": {"g_correct": 0, "f_correct": 0, "total": 0}
    }
    
    category_data = defaultdict(lambda: {"g_correct": 0, "f_correct": 0, "total": 0})
    
    for r in results:
        g = r["graphrag"]
        fl = r["flatrag"]
        
        g_acc = g["exact_match"] or g["semantic_match"]
        f_acc = fl["exact_match"] or fl["semantic_match"]
        
        if g_acc: g_correct += 1
        if f_acc: f_correct += 1
        
        g_ans = normalize(g.get("answer", ""))
        fl_ans = normalize(fl.get("answer", ""))
        g_is_unknown = (g_ans == "unknown" or "unknown" in g_ans)
        fl_is_unknown = (fl_ans == "unknown" or "unknown" in fl_ans)
        
        if not g_acc and not g_is_unknown and len(g_ans) > 2:
            g_hallucinations += 1
        if not f_acc and not fl_is_unknown and len(fl_ans) > 2:
            f_hallucinations += 1
        
        g_latency_total += g["latency_ms"]
        f_latency_total += fl["latency_ms"]
        
        hops = r["hops_required"]
        hop_key = hops if hops in [1, 2] else "3+"
        
        hops_data[hop_key]["total"] += 1
        if g_acc: hops_data[hop_key]["g_correct"] += 1
        if f_acc: hops_data[hop_key]["f_correct"] += 1
        
        cat = r["category"]
        category_data[cat]["total"] += 1
        if g_acc: category_data[cat]["g_correct"] += 1
        if f_acc: category_data[cat]["f_correct"] += 1
        
    metrics = {
        "overall": {
            "graphrag_accuracy": g_correct / total,
            "flatrag_accuracy": f_correct / total,
            "accuracy_delta": (g_correct - f_correct) / total,
            "graphrag_hallucination_rate": g_hallucinations / total,
            "flatrag_hallucination_rate": f_hallucinations / total,
            "graphrag_avg_latency_ms": g_latency_total / total,
            "flatrag_avg_latency_ms": f_latency_total / total
        },
        "by_hop": {},
        "by_category": {}
    }
    
    for k, v in hops_data.items():
        if v["total"] > 0:
            metrics["by_hop"][k] = {
                "graphrag_accuracy": v["g_correct"] / v["total"],
                "flatrag_accuracy": v["f_correct"] / v["total"]
            }
            
    for k, v in category_data.items():
        if v["total"] > 0:
            metrics["by_category"][k] = {
                "graphrag_accuracy": v["g_correct"] / v["total"],
                "flatrag_accuracy": v["f_correct"] / v["total"]
            }
            
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(metrics, f, indent=2)
        
    # Print comparison table
    print("\n--- RESULTS ---")
    print(f"{'Metric':<25} | {'Flat RAG':<10} | {'GraphRAG':<10} | {'Delta':<10}")
    print("-" * 65)
    
    ov = metrics["overall"]
    print(f"{'Overall Accuracy':<25} | {ov['flatrag_accuracy']*100:5.1f}%     | {ov['graphrag_accuracy']*100:5.1f}%     | {(ov['graphrag_accuracy'] - ov['flatrag_accuracy'])*100:+5.1f}%")
    
    for k in [1, 2, "3+"]:
        if k in metrics["by_hop"]:
            h = metrics["by_hop"][k]
            print(f"{str(k) + '-hop Accuracy':<25} | {h['flatrag_accuracy']*100:5.1f}%     | {h['graphrag_accuracy']*100:5.1f}%     | {(h['graphrag_accuracy'] - h['flatrag_accuracy'])*100:+5.1f}%")
            
    print(f"{'Hallucination Rate':<25} | {ov['flatrag_hallucination_rate']*100:5.1f}%     | {ov['graphrag_hallucination_rate']*100:5.1f}%     | {(ov['graphrag_hallucination_rate'] - ov['flatrag_hallucination_rate'])*100:+5.1f}%")
    print(f"{'Avg Latency (ms)':<25} | {ov['flatrag_avg_latency_ms']:<10.0f} | {ov['graphrag_avg_latency_ms']:<10.0f} | -")
    print("-----------------------------------------------------------------")
    
if __name__ == "__main__":
    compute_metrics("results/benchmark_results.json", "results/final_metrics.json")
