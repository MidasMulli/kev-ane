"""A4b prep (Astra-signed v2). (1) FRESH TEST: papers qualifying under frozen rule v4 in the never-walked pool tail (seeded positions
10,455-12,743), questions min(3, anchored) seed 20260941. (2) k on DEV only: AX on the ANE over the 30 DEV papers; coverage (anchored rows
inside top-k + neighbours) for k in {6,8,10,12,16}; k = smallest with coverage >= 0.95, else 16."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, itertools, random, sys, os, numpy as np
import pyarrow.parquet as pq
from transformers import AutoTokenizer
sys.path.insert(0, ROOT + "/cuad")
from a4_common import units2, anchor4
from a4b_common import policy
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base")
R = pq.read_table("pwc_results_arxiv.parquet").to_pylist(); by = {}
for r in R: by.setdefault(r["arxiv"], {})[(r["model"], r["dataset"], r["metric"], r["value"])] = r["task"]
fresh = []; n = 0
for l in itertools.chain(open("a4_raw_hf.jsonl"), open("a4_raw_hf2.jsonl"), open("a4_raw_hf3.jsonl")):
    n += 1
    if n <= 10454: continue
    d = json.loads(l)
    if not d["ok"]: continue
    t = d["tex"]; k = len(tok(t, add_special_tokens=False)["input_ids"])
    if not 8000 <= k <= 40000: continue
    U = units2(t); res = []
    for (M, D, Rm, V), task in sorted(by[d["arxiv"]].items()):
        st, info = anchor4(t, U, M, D, Rm, V)
        if st == "ok": res.append(dict(model=M, dataset=D, metric=Rm, value=V, task=task, span=[info[0], info[1]], kind=info[2]))
    if len(res) >= 2: fresh.append(dict(arxiv=d["arxiv"], text=t, tokens=k, results=res))
used = {c["arxiv"] for c in json.load(open("a4_corpus.json"))}; assert not used & {f["arxiv"] for f in fresh}
rng = random.Random(20260941); Qs = []
for i, c in enumerate(fresh):
    for kk in rng.sample(range(len(c["results"])), min(3, len(c["results"]))):
        Qs.append(dict(doc=i, arxiv=c["arxiv"], ridx=kk, **{x: c["results"][kk][x] for x in ("model", "dataset", "metric", "value")}))
json.dump(fresh, open("a4b_fresh.json", "w")); json.dump(Qs, open("a4b_questions.json", "w"))
print(json.dumps(dict(fresh_papers=len(fresh), questions=len(Qs))), flush=True)
# ---- k on DEV via the ANE ----
from ane_run import Ane, TRUST
C = json.load(open("a4_corpus.json")); S = json.load(open("a4_split.json"))
head = dict(np.load("run_AX/head.npz")); ane = Ane("AX", head); r = ane.cmd(f"BIND {TRUST}/AX.bin"); assert r.startswith("BOUND"), r
def windows(text):
    enc = tok(text, return_offsets_mapping=True, add_special_tokens=False); ids, offs = enc["input_ids"], enc["offset_mapping"]; out = []
    for s0 in range(0, max(1, len(ids) - 32), 224):
        w = ids[s0:s0 + 256]; out.append(dict(ids=w, a=offs[s0][0], b=offs[s0 + len(w) - 1][1]))
        if s0 + 256 >= len(ids): break
    return out
KS = [6, 8, 10, 12, 16]; cov = {k: [] for k in KS}
for i in S["dev"]:
    ws = windows(C[i]["text"]); sc = np.stack([ane.window(w["ids"])[0] for w in ws])[:, 0]; order = np.argsort(-sc, kind="stable")
    for k in KS:
        P = policy(order, len(ws), k)
        cov[k] += [any(ws[j]["a"] < e[1] and ws[j]["b"] > e[0] for j in P) for e in [r["span"] for r in C[i]["results"]]]
ane.close()
cv = {k: float(np.mean(v)) for k, v in cov.items()}; K = next((k for k in KS if cv[k] >= 0.95), 16)
json.dump(dict(dev_coverage=cv, k=K), open("a4b_k.json", "w")); print(json.dumps(dict(dev_coverage=cv, k=K)))
