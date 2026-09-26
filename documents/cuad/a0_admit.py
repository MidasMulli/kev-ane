"""Program A / A0 admission (Astra-signed 2026-09-24). 27B only. ADMIT contracts (60); per contract ONE request per arm with all of its
gradeable value questions. Arms FULL (whole contract), GOLD (annotated spans of the asked types, doc order), NONE (questions only).
Cold (nonce first, cache miss asserted), reasoning_effort none, temperature 0. ADMIT iff GOLD acc >= 0.50 AND GOLD - NONE lower 95% >= 0.15
(contract-clustered paired bootstrap). Raw per request written live."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, random, subprocess, time, urllib.request, hashlib, numpy as np
from cuad_common import *
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
g0 = sh(GATE0).splitlines()[-1]; assert g0.startswith("gate=GREEN"), g0
S = json.load(open("splits.json")); assert hashlib.sha256(open("cuad_common.py", "rb").read()).hexdigest()[:12] == S["cuad_common_sha"]
sent = subprocess.Popen([SENTINEL, str(os.getpid()), os.path.abspath("a0_red_sentinel.log")])
time.sleep(3); assert sent.poll() is None
log = open("a0_raw.jsonl", "w")
def emit(**r): print(json.dumps(r)[:300], flush=True); log.write(json.dumps(r) + "\n"); log.flush()
emit(event="launch", gate0=g0, splits_sha=hashlib.sha256(open("splits.json", "rb").read()).hexdigest()[:12])

def ask(text):
    body = {"model": LLM_MODEL, "stream": False, "temperature": 0, "reasoning_effort": "none", "max_tokens": 200,
            "messages": [{"role": "user", "content": text}]}
    req = urllib.request.Request(LLM_URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.monotonic(); j = json.load(urllib.request.urlopen(req, timeout=1800)); dt = time.monotonic() - t0
    u = j["usage"]; cache = (j.get("metrics") or {}).get("cache", {}).get("status")
    assert (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) == 0 and cache in (None, "miss"), (u, cache)
    return j["choices"][0]["message"]["content"], u["prompt_tokens"], dt

C = {c["id"]: c for c in load()[0]}
rows = []
for cid in S["admit"]:
    c = C[cid]; its = items(c); qs = [t for t, _ in its]
    ev = sorted({(s, txt) for t in qs for s, txt in c["spans"][t]}); ev = [txt for _, txt in ev]
    for arm, kw in (("FULL", dict(context=c["context"])), ("GOLD", dict(evidence=ev)), ("NONE", {})):
        text = prompt(qs, nonce=f"[req {random.random():.12f}]", **kw)
        out, ptok, dt = ask(text); preds = parse_lines(out, len(qs))
        for (t, g), p in zip(its, preds):
            ok = correct(t, g, PRED_PARSE[t](p)); rows.append(dict(cid=cid, arm=arm, type=t, ok=ok))
        emit(event="req", cid=cid, arm=arm, types=qs, gold=[c["gold"][t] for t in qs], response=out, preds=preds,
             ok=[r["ok"] for r in rows[-len(qs):]], prompt_tokens=ptok, seconds=dt, prompt=text if arm != "FULL" else text[:400])

def acc(arm): return float(np.mean([r["ok"] for r in rows if r["arm"] == arm]))
cids = S["admit"]; rng = np.random.default_rng(0)
def per(arm): return {cid: [r["ok"] for r in rows if r["arm"] == arm and r["cid"] == cid] for cid in cids}
G, N, F = per("GOLD"), per("NONE"), per("FULL")
def boot(a, b):
    v = []
    for _ in range(10000):
        s = rng.choice(cids, len(cids)); x = sum(sum(a[c]) for c in s); y = sum(sum(b[c]) for c in s); n = sum(len(a[c]) for c in s)
        v.append((x - y) / n)
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
ci = boot(G, N); fg = boot(F, G)
per_type = {t: {arm: float(np.mean([r["ok"] for r in rows if r["arm"] == arm and r["type"] == t])) for arm in ("FULL", "GOLD", "NONE")} | {"n": sum(1 for r in rows if r["arm"] == "GOLD" and r["type"] == t)} for t in VALUE_TYPES}
admit = acc("GOLD") >= 0.50 and ci[0] >= 0.15
emit(event="A0_RESULT", n_questions=sum(1 for r in rows if r["arm"] == "GOLD"), FULL=acc("FULL"), GOLD=acc("GOLD"), NONE=acc("NONE"),
     gold_minus_none_ci=ci, full_minus_gold_ci=fg, per_type=per_type, verdict="ADMITTED" if admit else "NOT ADMITTED")
sent.terminate()
