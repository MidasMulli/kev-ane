"""A4b scoring (adds PIPE_A4 paired control, flags). Adapted from: A4 scoring (Astra-signed v2 + rulings): run only after a4_test.py finishes. Graded against PwC gold (numeric, rel 1e-3), no adjudication.
Admission: acc(FULL) on feasible questions >= 0.60 else VOID. G-E2E: acc(PIPE) - acc(FULL) lower 95% >= -0.05 (paper-clustered bootstrap,
feasible papers). G-LAT: median per-paper (PIPE - FULL) seconds, upper 95% < 0. G-SWAP from the run. Reported: BM25 and NONE, coverage, tokens."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, numpy as np
L = [json.loads(l) for l in open("a4b_test_raw.jsonl")]; P = [x for x in L if x["event"] == "paper"]; done = [x for x in L if x["event"] == "A4B_RUN_DONE"]
assert done, "run not finished"
swap = next(x for x in L if x["event"] == "swap")
F = [p for p in P if p["arms"]["FULL"] is not None]
def acc(ps, arm): return sum(sum(p["arms"][arm]["ok"]) for p in ps) / sum(len(p["arms"][arm]["ok"]) for p in ps)
rng = np.random.default_rng(0)
def boot(ps, f, n=10000):
    return [float(np.percentile(v, q)) for v in [np.array([f([ps[i] for i in rng.integers(0, len(ps), len(ps))]) for _ in range(n)])] for q in (2.5, 97.5)]
d = acc(F, "PIPE") - acc(F, "FULL"); dci = boot(F, lambda s: acc(s, "PIPE") - acc(s, "FULL"))
lat = lambda s: float(np.median([p["arms"]["PIPE"]["seconds"] - p["arms"]["FULL"]["seconds"] for p in s])); lci = boot(F, lat, 5000)
full_acc = acc(F, "FULL"); admit = full_acc >= 0.60; g_e2e = dci[0] >= -0.05; g_lat = lci[1] < 0; g_swap = bool(swap["G_SWAP"] and done[0]["base_md5_unchanged"])
bm = acc(P, "PIPE") - acc(P, "BM25"); bmci = boot(P, lambda s: acc(s, "PIPE") - acc(s, "BM25"))
pa = acc(P, "PIPE") - acc(P, "PIPE_A4"); paci = boot(P, lambda s: acc(s, "PIPE") - acc(s, "PIPE_A4"))
def flag_acc(arm, fl):
    v = [ok for p in P for ok, f in zip(p["arms"][arm]["ok"], p["gold_table_flag"]) if f == fl]; return (round(sum(v) / len(v), 4), len(v)) if v else None
cov = lambda k: float(np.mean([c for p in P for c in p[k]]))
med = lambda arm, k, ps: float(np.median([p["arms"][arm][k] for p in ps]))
print(json.dumps(dict(event="A4B_RESULT", papers=len(P), questions=sum(len(p["gold"]) for p in P), feasible_papers=len(F), feasible_questions=sum(len(p["gold"]) for p in F),
    acc_all=dict((a, round(acc(P, a), 4)) for a in ("PIPE", "PIPE_A4", "BM25", "NONE")), acc_feasible=dict((a, round(acc(F, a), 4)) for a in ("PIPE", "PIPE_A4", "FULL", "BM25", "NONE")),
    ADMISSION=admit, diff_pipe_full=round(d, 4), diff_ci=dci, G_E2E=g_e2e, lat_median_diff=lat(F), lat_ci=lci, G_LAT=g_lat, G_SWAP=g_swap,
    pipe_minus_bm25=round(bm, 4), pipe_minus_bm25_ci=bmci, pipe_minus_pipeA4=round(pa, 4), pipe_minus_pipeA4_ci=paci, by_flag=dict((f, dict(PIPE=flag_acc("PIPE", f), PIPE_A4=flag_acc("PIPE_A4", f))) for f in ("OK", "TRUNCATED")),
    pipe_cover=cov("pipe_cover"), pipeA4_cover=cov("pipeA4_cover"), dropped_pipe=sum(p["dropped_pipe"] for p in P), bm25_cover=cov("bm25_cover"),
    median_s=dict(PIPE=med("PIPE", "seconds", F), FULL=med("FULL", "seconds", F)), median_prompt_tokens=dict(PIPE=med("PIPE", "prompt_tokens", F), FULL=med("FULL", "prompt_tokens", F), BM25=med("BM25", "prompt_tokens", P)),
    verdict="VOID (admission)" if not admit else ("PASS" if g_e2e and g_lat and g_swap else "NOT PASS")), indent=1))
