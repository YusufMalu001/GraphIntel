import json

res = json.load(open('results/benchmark_results.json'))
qs = json.load(open('evaluation/questions.json'))
q_map = {q['id']: q['question'] for q in qs}

print('| Question | Expected | Flat Answer | Graph Answer | Flat Correct | Graph Correct |')
print('|---|---|---|---|---|---|')
for i, r in enumerate(res[:10]):
    q_text = q_map.get(r["id"], "")
    expected = qs[i]["answer"]
    f_ans = r["flatrag"]["answer"]
    g_ans = r["graphrag"]["answer"]
    f_corr = r["flatrag"]["exact_match"] or r["flatrag"]["semantic_match"]
    g_corr = r["graphrag"]["exact_match"] or r["graphrag"]["semantic_match"]
    print(f'| {q_text} | {expected} | {f_ans} | {g_ans} | {f_corr} | {g_corr} |')
