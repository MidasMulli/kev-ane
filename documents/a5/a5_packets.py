"""A5 adjudication packets (usage: a5_packets.py OUTDIR MAX_N: papers with n < MAX_N). Derived from: A'' adjudication packets (Astra-signed design): one packet per PIPE/FULL disagreement. Answers shown as X/Y in per-item random order;
the arm mapping is written ONLY to adjudication/SEALED_mapping.json (CC does not open it until every verdict is filed). Contract texts
written to adjudication/texts/<cid>.txt. Prints counts only."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, random, hashlib, sys

D = sys.argv[1]; MAXN = int(sys.argv[2]); os.makedirs(f"{D}/texts", exist_ok=True); os.makedirs(f"{D}/packets", exist_ok=True)
from a5_common import Q
P = json.load(open("a5_corpus.json")); F = {f"P{i}": dict(text=p["text"]) for i, p in enumerate(P)}
FIELDS = {n: (q, None) for n, q in Q}
R = [json.loads(l) for l in open("a5_test_raw.jsonl")]; MINN = int(sys.argv[3]) if len(sys.argv) > 3 else 0; cmp_ = [r for r in R if r["event"] == "compare" and MINN <= r["n"] < MAXN]
RUBRIC = """Rubric (fixed in advance; apply it exactly). The document is the LaTeX source of a research paper.
1. Find and QUOTE the paper's own text that answers the question (search the whole paper, including appendix; ignore the bibliography
   and descriptions of OTHER papers' methods).
2. The correct answer is what the paper states about ITS OWN work. For list questions (datasets, baselines) any stated item is acceptable
   and a partial list is acceptable. For numbers, the stated number (units as stated). NONE is correct only if the paper does not state it.
3. Verdict, exactly one of: "X", "Y", "both_wrong", "both_acceptable" (both correct, e.g. different wording or different correct items)."""
rng = random.Random(20260956); sealed = {}; n = 0
for c in cmp_:
    open(f"{D}/texts/{c['cid']}.txt", "w").write(F[c["cid"]]["text"])
    for i, t in enumerate(FIELDS):
        if c["agree"][i]: continue
        pid = f"item{n:03d}"; n += 1
        p, f_ = c["pipe"][i] or "NONE", c["full"][i] or "NONE"
        if rng.random() < 0.5: X, Y, m = p, f_, {"X": "PIPE", "Y": "FULL"}
        else: X, Y, m = f_, p, {"X": "FULL", "Y": "PIPE"}
        sealed[pid] = dict(cid=c["cid"], type=t, **m)
        json.dump(dict(item=pid, contract_file=os.path.abspath(f"{D}/texts/{c['cid']}.txt"), question=FIELDS[t][0].split(" Answer")[0],
                       X=X, Y=Y, rubric=RUBRIC), open(f"{D}/packets/{pid}.json", "w"), indent=1)
json.dump(sealed, open(f"{D}/SEALED_mapping.json", "w"))
print(json.dumps(dict(packets=n, contracts_with_disagreement=len({v["cid"] for v in sealed.values()}),
                      sealed_sha=hashlib.sha256(open(f"{D}/SEALED_mapping.json", "rb").read()).hexdigest()[:12])))
