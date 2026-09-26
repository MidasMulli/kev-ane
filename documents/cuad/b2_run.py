"""B2 (Astra-signed 2026-09-24): SEQ vs PIPE on the first 24 A3-TEST contracts with value questions. Top-2 windows per asked value type
(no NULL), adapter CUA, T=256. SEQ: ANE map then 27B per contract. PIPE: an ANE thread maps ahead into a queue; the main thread serves.
5 reps, order alternating. Response identity SEQ vs PIPE checked per contract (>2/24 mismatches voids the rep).
Gain = wall(SEQ)/wall(PIPE) - 1, paired bootstrap over reps: lower >= 0.05 raises throughput; upper < 0.05 no practical gain.
Kill after 2 reps if PIPE slower in both."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, queue, random, re, subprocess, threading, time, urllib.request, numpy as np
from transformers import AutoTokenizer
from cuad_common import *
from cuad_windows import windows
from ane_run import Ane, sh, MD
log = open("b2_raw.jsonl", "w")
def emit(**r): print(json.dumps(r)[:300], flush=True); log.write(json.dumps(r) + "\n"); log.flush()
g0 = sh(GATE0).splitlines()[-1]; assert g0.startswith("gate=GREEN"), g0
sent = subprocess.Popen([SENTINEL, str(os.getpid()), os.path.abspath("b2_red_sentinel.log")])
time.sleep(3); assert sent.poll() is None
S = json.load(open("splits.json")); TO = S["type_order"]; C = {c["id"]: c for c in load()[0]}
CIDS = [c for c in S["test"] if items(C[c])][:24]
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base")
WS = {cid: windows(C[cid], tok, TO) for cid in CIDS}                            # tokenization precomputed for both modes alike
PW = []; pm_stop = threading.Event()
def pm():
    p = subprocess.Popen(["sudo", "-n", "powermetrics", "-i", "250", "--samplers", "cpu_power,gpu_power,ane_power"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
    cur = {}
    for line in p.stdout:
        if pm_stop.is_set(): p.terminate(); break
        m = re.match(r"(CPU|GPU|ANE) Power:\s*(\d+) mW", line)
        if m: cur[m.group(1)] = int(m.group(2))
        if len(cur) == 3: PW.append((time.monotonic(), cur["CPU"], cur["GPU"], cur["ANE"])); cur = {}
threading.Thread(target=pm, daemon=True).start()
def watts(t0, t1):
    w = [x for x in PW if t0 <= x[0] <= t1]
    return {k: (float(np.mean([x[i] for x in w])) if w else None) for k, i in (("cpu_mW", 1), ("gpu_mW", 2), ("ane_mW", 3))}
head = dict(np.load("run_CUA/head.npz")); md5_0 = sh(f"sudo -n md5 -q {MD}/weights/weight.bin"); ane = Ane("CUA", head)
emit(event="launch", gate0=g0, bind=ane.bind, n_contracts=len(CIDS))

def ane_map(cid):
    t0 = time.monotonic(); ws = WS[cid]; sc = np.stack([ane.window(w["ids"])[0] for w in ws]); c = C[cid]; chosen = set()
    for t, _ in items(c): chosen |= {int(j) for j in np.argsort(-sc[:, TO.index(t)])[:2]}
    return [c["context"][ws[j]["a"]:ws[j]["b"]] for j in sorted(chosen)], time.monotonic() - t0
def ask(cid, ev):
    qs = [t for t, _ in items(C[cid])]; text = prompt(qs, evidence=ev, nonce=f"[req {random.random():.12f}]")
    body = {"model": LLM_MODEL, "stream": False, "temperature": 0, "reasoning_effort": "none", "max_tokens": 200,
            "messages": [{"role": "user", "content": text}]}
    req = urllib.request.Request(LLM_URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.monotonic(); j = json.load(urllib.request.urlopen(req, timeout=900)); dt = time.monotonic() - t0
    u = j["usage"]; cache = (j.get("metrics") or {}).get("cache", {}).get("status")
    assert (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) == 0 and cache in (None, "miss"), (u, cache)
    return j["choices"][0]["message"]["content"], dt, u["prompt_tokens"]

def run(mode, rep):
    per = {}; t0 = time.monotonic()
    if mode == "SEQ":
        for cid in CIDS:
            ev, a = ane_map(cid); out, d, pt = ask(cid, ev); per[cid] = dict(ane_s=a, llm_s=d, prompt_tokens=pt, response=out)
    else:
        q = queue.Queue(); amap = {}
        def producer():
            for cid in CIDS: ev, a = ane_map(cid); amap[cid] = a; q.put((cid, ev))
        th = threading.Thread(target=producer); th.start()
        for _ in CIDS:
            cid, ev = q.get(); out, d, pt = ask(cid, ev); per[cid] = dict(ane_s=amap[cid], llm_s=d, prompt_tokens=pt, response=out)
        th.join()
    wall = time.monotonic() - t0
    r = dict(mode=mode, rep=rep, wall_s=wall, sum_ane_s=sum(p["ane_s"] for p in per.values()), sum_llm_s=sum(p["llm_s"] for p in per.values()),
             **watts(t0, t0 + wall), per=per)
    emit(event="mode", **{k: v for k, v in r.items() if k != "per"}); log.write(json.dumps({"event": "per", "mode": mode, "rep": rep, "per": per}) + "\n"); log.flush()
    return r

R = []; killed = False
for rep in range(5):
    pair = {}
    for mode in (("SEQ", "PIPE") if rep % 2 == 0 else ("PIPE", "SEQ")): pair[mode] = run(mode, rep)
    mism = sum(pair["SEQ"]["per"][c]["response"] != pair["PIPE"]["per"][c]["response"] for c in CIDS)
    R.append(dict(rep=rep, seq=pair["SEQ"]["wall_s"], pipe=pair["PIPE"]["wall_s"], mismatches=mism, void=mism > 2,
                  llm_slow=float(np.median([pair["PIPE"]["per"][c]["llm_s"] / pair["SEQ"]["per"][c]["llm_s"] for c in CIDS])),
                  ceiling=(pair["SEQ"]["sum_ane_s"] + pair["SEQ"]["sum_llm_s"]) / max(pair["SEQ"]["sum_ane_s"], pair["SEQ"]["sum_llm_s"]) - 1))
    emit(event="rep", **R[-1], gain=R[-1]["seq"] / R[-1]["pipe"] - 1)
    if rep == 1 and all(x["pipe"] > x["seq"] for x in R): killed = True; emit(event="B2_KILL", note="PIPE slower in both of the first 2 reps"); break
pm_stop.set(); ane.close()
if not killed:
    V = [x for x in R if not x["void"]]; g = np.array([x["seq"] / x["pipe"] - 1 for x in V]); rng = np.random.default_rng(0)
    bs = np.sort([rng.choice(g, len(g)).mean() for _ in range(10000)]); ci = [float(bs[250]), float(bs[9750])]
    verdict = "pipelining RAISES throughput" if ci[0] >= 0.05 else ("NO practical gain at 5%" if ci[1] < 0.05 else "INCONCLUSIVE")
    emit(event="B2_RESULT", reps_valid=len(V), gain_mean=float(g.mean()), gain_ci=ci, verdict=verdict,
         ceiling_mean=float(np.mean([x["ceiling"] for x in V])), llm_slowdown_median=float(np.median([x["llm_slow"] for x in V])),
         mismatches=[x["mismatches"] for x in R], base_md5_unchanged=sh(f"sudo -n md5 -q {MD}/weights/weight.bin") == md5_0)
sent.terminate()
