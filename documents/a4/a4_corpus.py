"""A4 corpus (Astra-signed v2): walk a4_raw_hf.jsonl in its SEEDED fetch order (seed 20260935); keep a paper iff LaTeX ok, 8k-40k Qwen tokens,
>= 2 ANCHORED results (a4_common.anchor4 = rule v4, final (Astra ruling after gate v3 failed); 390 = TRAIN 280 / DEV 30 / TEST 80; ambiguous dropped). First 390 kept: positions 0-279 TRAIN, 280-309 DEV, 310-389 TEST
(the order is already the seeded random order). TEST questions: up to 3 anchored results per TEST paper, seeded (20260938).
Writes a4_corpus.json + a4_split.json + a4_test_questions.json. Prints the funnel."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, random, sys
import pyarrow.parquet as pq
from transformers import AutoTokenizer
from a4_common import units2 as units, anchor4 as anchor
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 390
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base")
R = pq.read_table("pwc_results_arxiv.parquet").to_pylist(); by = {}
for r in R: by.setdefault(r["arxiv"], {})[(r["model"], r["dataset"], r["metric"], r["value"])] = r["task"]
fun = dict(fetched=0, no_latex=0, fetch_err=0, too_short=0, too_long=0, lt2_anchored=0, kept=0); keep = []
import itertools
for l in itertools.chain(open("a4_raw_hf.jsonl"), open("a4_raw_hf2.jsonl"), open("a4_raw_hf3.jsonl")):
    d = json.loads(l); fun["fetched"] += 1
    if not d["ok"]: fun["no_latex" if d["why"] == "no_latex" else "fetch_err"] += 1; continue
    t = d["tex"]; n = len(tok(t, add_special_tokens=False)["input_ids"])
    if n < 8000: fun["too_short"] += 1; continue
    if n > 40000: fun["too_long"] += 1; continue
    U = units(t); res = []
    for (M, D, Rm, V), task in sorted(by[d["arxiv"]].items()):
        st, info = anchor(t, U, M, D, Rm, V)
        if st == "ok": res.append(dict(model=M, dataset=D, metric=Rm, value=V, task=task, span=[info[0], info[1]], kind=info[2]))
    if len(res) < 2: fun["lt2_anchored"] += 1; continue
    keep.append(dict(arxiv=d["arxiv"], text=t, tokens=n, results=res)); fun["kept"] += 1
    if len(keep) >= TARGET: break
print(json.dumps(fun))
assert len(keep) >= TARGET, f"only {len(keep)} kept; fetch more"
split = dict(train=list(range(280)), dev=list(range(280, 310)), test=list(range(310, 390)))
json.dump(keep, open("a4_corpus.json", "w")); json.dump(split, open("a4_split.json", "w"))
rng = random.Random(20260938); Qs = []
for i in split["test"]:
    rs = keep[i]["results"]; pick = rng.sample(range(len(rs)), min(3, len(rs)))
    for k in pick: Qs.append(dict(doc=i, arxiv=keep[i]["arxiv"], ridx=k, **{x: rs[k][x] for x in ("model", "dataset", "metric", "value")}))
json.dump(Qs, open("a4_test_questions.json", "w"))
print(json.dumps(dict(papers=len(keep), test_questions=len(Qs), results_total=sum(len(k["results"]) for k in keep),
                      row=sum(r["kind"] == "row" for k in keep for r in k["results"]), sent=sum(r["kind"] == "sent" for k in keep for r in k["results"]))))
