"""A'' DEVELOPMENT (Astra-signed): policy pick on USED data only (A3 TEST contracts with value questions + A-long gated 31), ANE only.
P1 top-2 · P2 top-3 · P3 top-4 · P4 top-2 + neighbours +-1 · P5 top-2 + windows 0-2 · P6 top-3 + windows 0-1 (same policy all 4 types).
Pick: highest location hit; ties within 0.005 -> fewer median evidence tokens per contract; median > 3,000 tokens excluded."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, numpy as np
from transformers import AutoTokenizer
from cuad_common import *; from cuad_windows import windows, overlaps
from ane_run import Ane, sh, MD
S = json.load(open("splits.json")); TO = S["type_order"]; C = {c["id"]: c for c in load()[0]}
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base")
DEV = [c for c in S["test"] if items(C[c])] + json.load(open("along_set.json"))["gated"]
ane = Ane("CUA", dict(np.load("run_CUA/head.npz"))); m0 = sh(f"sudo -n md5 -q {MD}/weights/weight.bin")
def pol(name, sc, k, n):
    order = [int(j) for j in np.argsort(-sc[:, k])]
    if name == "P1": return set(order[:2])
    if name == "P2": return set(order[:3])
    if name == "P3": return set(order[:4])
    if name == "P4": return {x for j in order[:2] for x in (j - 1, j, j + 1) if 0 <= x < n}
    if name == "P5": return set(order[:2]) | {x for x in (0, 1, 2) if x < n}
    if name == "P6": return set(order[:3]) | {x for x in (0, 1) if x < n}
P = ["P1", "P2", "P3", "P4", "P5", "P6"]; hit = {p: [] for p in P}; toks = {p: [] for p in P}; per = {p: {t: [] for t in VALUE_TYPES} for p in P}
out = open("a2p_dev_raw.jsonl", "w")
for cid in DEV:
    ws = windows(C[cid], tok, TO); sc = np.stack([ane.window(w["ids"])[0] for w in ws]); its = items(C[cid])
    for p in P:
        union = set()
        for t, _ in its:
            s = pol(p, sc, TO.index(t), len(ws)); union |= s
            h = any(overlaps(C[cid]["spans"][t], ws[j]["a"], ws[j]["b"]) for j in s); hit[p].append(h); per[p][t].append(h)
        toks[p].append(sum(len(ws[j]["ids"]) for j in union))
    out.write(json.dumps(dict(cid=cid, n=len(ws), top5={t: [int(j) for j in np.argsort(-sc[:, TO.index(t)])[:5]] for t, _ in its})) + "\n"); out.flush()
ane.close()
res = {p: dict(hit=float(np.mean(hit[p])), n=len(hit[p]), median_tokens=float(np.median(toks[p])), per_type={t: [float(np.mean(v)), len(v)] for t, v in per[p].items()}) for p in P}
ok = [p for p in P if res[p]["median_tokens"] <= 3000]; best = max(res[p]["hit"] for p in ok)
tied = [p for p in ok if best - res[p]["hit"] <= 0.005]; pick = min(tied, key=lambda p: res[p]["median_tokens"])
print(json.dumps(dict(event="A2P_DEV_RESULT", results=res, eligible=ok, pick=pick, base_md5_unchanged=sh(f"sudo -n md5 -q {MD}/weights/weight.bin") == m0), indent=1))
json.dump(dict(pick=pick, results=res), open("a2p_policy.json", "w"), indent=1)
