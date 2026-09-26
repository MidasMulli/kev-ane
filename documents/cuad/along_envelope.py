"""A-long envelope (Astra-signed plan, step 1 precondition): FULL 27B requests on real long CUAD contracts at ascending lengths
(~41k, ~62k, then the longest, 82k Qwen tokens), GATE 0 sampled every second during each; stop at the first non-GREEN sample or a
Splash rejection. Cap = longest length whose request stayed GREEN throughout. Questions = that contract's value questions."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, random, re, subprocess, threading, time, urllib.request, numpy as np
from cuad_common import *
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
S = json.load(open("splits.json")); C = {c["id"]: c for c in load()[0]}
L = sorted(S["excluded_over_32k"], key=lambda c: S["ntok"][c]); nt = [S["ntok"][c] for c in L]
pick = [L[int(np.argmin([abs(x - 41000) for x in nt]))], L[int(np.argmin([abs(x - 62000) for x in nt]))], L[-1]]
log = open("along_envelope.jsonl", "w")
def emit(**r): print(json.dumps(r)[:300], flush=True); log.write(json.dumps(r) + "\n"); log.flush()
cap = 0
for cid in pick:
    g = sh(GATE0).splitlines()[-1]
    if not g.startswith("gate=GREEN"): emit(event="stop_pre", cid=cid, gate0=g); break
    samples = []; stop = threading.Event()
    def sampler():
        while not stop.is_set(): samples.append(sh(GATE0).splitlines()[-1]); time.sleep(1)
    th = threading.Thread(target=sampler); th.start()
    qs = [t for t, _ in items(C[cid])] or ["Governing Law"]
    body = {"model": LLM_MODEL, "stream": False, "temperature": 0, "reasoning_effort": "none", "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt(qs, context=C[cid]["context"], nonce=f"[env {random.random():.12f}]")}]}
    t0 = time.monotonic(); err = None; out = None
    try:
        j = json.load(urllib.request.urlopen(urllib.request.Request(LLM_URL, json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=1200))
        out = dict(prompt_tokens=j["usage"]["prompt_tokens"], response=j["choices"][0]["message"]["content"])
    except Exception as e: err = repr(e)[:300]
    dt = time.monotonic() - t0; stop.set(); th.join()
    green = all(s.startswith("gate=GREEN") for s in samples)
    av = [float(re.search(r"avail_ram=([\d.]+)GB", s).group(1)) for s in samples if "avail_ram=" in s]
    emit(event="request", cid=cid, qwen06_tokens=S["ntok"][cid], seconds=dt, error=err, all_green=green, n_samples=len(samples),
         min_avail_gb=min(av) if av else None, non_green=[s for s in samples if not s.startswith("gate=GREEN")][:3], **(out or {}))
    if err or not green: break
    cap = S["ntok"][cid]
emit(event="ENVELOPE_RESULT", cap_qwen06_tokens=cap)
