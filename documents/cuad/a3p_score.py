"""A'' scoring (Astra-signed): run ONLY after every a1/a2 (and needed a3) verdict is filed. Majority of three where 1 and 2 differ;
a three-way split counts AGAINST PIPE. Unseals the mapping, computes diff = (PIPE-only-correct - FULL-only-correct) / all questions with a
contract-clustered bootstrap, kappa(a1, a2), and the latency gate. Usage: python a2p_score.py [--need-a3]"""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, sys, glob, collections, numpy as np
D = "adjudication3"; items = sorted(os.path.basename(p)[:-5] for p in glob.glob(f"{D}/packets/*.json"))
V = {a: {i: json.load(open(f"{D}/{a}/{i}.json"))["verdict"] for i in items if os.path.exists(f"{D}/{a}/{i}.json")} for a in ("a1", "a2", "a3")}
assert all(i in V["a1"] and i in V["a2"] for i in items), "a1/a2 verdicts incomplete"
need = [i for i in items if V["a1"][i] != V["a2"][i]]
if "--need-a3" in sys.argv: print(json.dumps(dict(need_a3=need))); sys.exit(0)
assert all(i in V["a3"] for i in need), f"arbitration missing for {need}"
cats = ["X", "Y", "both_wrong", "both_acceptable"]
po = np.mean([V["a1"][i] == V["a2"][i] for i in items])
pe = sum((sum(V["a1"][i] == c for i in items) / len(items)) * (sum(V["a2"][i] == c for i in items) / len(items)) for c in cats)
kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
M = json.load(open(f"{D}/SEALED_mapping.json"))                        # UNSEALED here, after all verdicts are filed
final = {}
for i in items:
    if i not in need: final[i] = V["a1"][i]; continue
    votes = collections.Counter([V["a1"][i], V["a2"][i], V["a3"][i]]); top, cnt = votes.most_common(1)[0]
    final[i] = top if cnt >= 2 else "SPLIT"
def arm_of(i, v): return M[i][v] if v in ("X", "Y") else v
R = [json.loads(l) for l in open("a3p_raw.jsonl")]; cmp_ = [r for r in R if r["event"] == "compare"]
per = {c["cid"]: 0 for c in cmp_}; nq = {c["cid"]: len(c["agree"]) for c in cmp_}; table = []
for i in items:
    a = arm_of(i, final[i]); cid = M[i]["cid"]
    s = 1 if a == "PIPE" else (-1 if a in ("FULL", "SPLIT") else 0); per[cid] += s
    table.append(dict(item=i, type=M[i]["type"], a1=V["a1"][i], a2=V["a2"][i], a3=V["a3"].get(i), final=final[i], winner=a, score=s))
cids = list(per); N = sum(nq.values()); diff = sum(per.values()) / N; rng = np.random.default_rng(0); bs = []
for _ in range(10000):
    s = rng.choice(cids, len(cids)); bs.append(sum(per[c] for c in s) / sum(nq[c] for c in s))
ci = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
lat = np.array([c["lat_diff"] for c in cmp_]); lb = [np.median(rng.choice(lat, len(lat))) for _ in range(10000)]
lci = [float(np.percentile(lb, 2.5)), float(np.percentile(lb, 97.5))]
g_e2e, g_lat = ci[0] >= -0.05, lci[1] < 0
print(json.dumps(dict(event="A3P_RESULT", n_questions=N, agreement=float(np.mean([x for c in cmp_ for x in c["agree"]])), disagreements=len(items),
                      kappa_a1_a2=round(float(kappa), 3), raw_agreement_a1_a2=round(float(po), 3), arbitrated=need, table=table,
                      pipe_only_correct=sum(1 for t in table if t["winner"] == "PIPE"), full_only_correct=sum(1 for t in table if t["winner"] == "FULL"),
                      split_against_pipe=sum(1 for t in table if t["winner"] == "SPLIT"), diff=diff, diff_ci=ci, G_E2E=g_e2e,
                      lat_median_diff=float(np.median(lat)), lat_ci=lci, G_LAT=g_lat, verdict="PASS" if g_e2e and g_lat else "NOT PASS"), indent=1))
