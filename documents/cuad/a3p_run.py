"""A''' HARDEN (PREREG_2026-09-24_A3prime_harden.md): identical to the A'' TEST except the set (fresh/fresh200.json), kill at 50, file names.
A'' TEST (Astra-signed 2026-09-24): 60 fresh Pile-of-Law atticus contracts (fresh/fresh60.json, 30113583867e), frozen adapter CUA,
frozen policy P2 (top-3 windows per asked value type; a2p_policy.json), all four value questions per contract, NONE allowed.
PIPE vs FULL, cold, alternating order. Per-question normalized comparison (A-long parsers, years = 12 months). Kill after 20 contracts if
agreement < 0.80. Disagreements are written to adjudication packets by a2p_packets.py (blind X/Y); CC adjudicates nothing."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, random, subprocess, time, urllib.request, hashlib, numpy as np
from transformers import AutoTokenizer
from cuad_common import *
from cuad_windows import windows
from ane_run import Ane, sh, MD
log = open("a3p_raw.jsonl", "w")
def emit(**r): print(json.dumps(r)[:300], flush=True); log.write(json.dumps(r) + "\n"); log.flush()
g0 = sh(GATE0).splitlines()[-1]; assert g0.startswith("gate=GREEN"), g0
sent = subprocess.Popen([SENTINEL, str(os.getpid()), os.path.abspath("a3p_red_sentinel.log")])
time.sleep(3); assert sent.poll() is None
assert hashlib.sha256(open("fresh/fresh200.json", "rb").read()).hexdigest().startswith(os.environ["A3P_SHA"])
POL = json.load(open("a2p_policy.json")); assert POL["pick"] == "P2"; K = 3
S = json.load(open("splits.json")); TO = S["type_order"]
F = json.load(open("fresh/fresh200.json"))["contracts"]
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base")
ane = Ane("CUA", dict(np.load("run_CUA/head.npz"))); md5_0 = sh(f"sudo -n md5 -q {MD}/weights/weight.bin")
emit(event="launch", gate0=g0, bind=ane.bind, n=len(F), policy="P2 top-3")
def mo(v): return None if v is None else ((v[0] * 12, "month") if v[1] == "year" else v)
def norm(t, p):
    v = PRED_PARSE[t](p) if p else None
    if t in ("Renewal Term", "Notice Period To Terminate Renewal"): v = mo(v)
    if v is None and p: return ("RAW", p.strip().lower())
    return v
def ask(text):
    body = {"model": LLM_MODEL, "stream": False, "temperature": 0, "reasoning_effort": "none", "max_tokens": 200,
            "messages": [{"role": "user", "content": text}]}
    req = urllib.request.Request(LLM_URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.monotonic(); j = json.load(urllib.request.urlopen(req, timeout=1800)); dt = time.monotonic() - t0
    u = j["usage"]; cache = (j.get("metrics") or {}).get("cache", {}).get("status")
    assert (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) == 0 and cache in (None, "miss"), (u, cache)
    return j["choices"][0]["message"]["content"], u["prompt_tokens"], dt
agree_all = []; lat = {}
for n, f in enumerate(F):
    c = dict(context=f["text"], spans={t: [] for t in TO}); qs = list(VALUE_TYPES)
    t0 = time.monotonic(); ws = windows(c, tok, TO); sc = np.stack([ane.window(w["ids"])[0] for w in ws]); chosen = set(); sel = {}
    for t in qs: sel[t] = [int(j) for j in np.argsort(-sc[:, TO.index(t)])[:K]]; chosen |= set(sel[t])
    ev = [f["text"][ws[j]["a"]:ws[j]["b"]] for j in sorted(chosen)]; ane_s = time.monotonic() - t0
    res = {}
    for arm in (("PIPE", "FULL") if n % 2 == 0 else ("FULL", "PIPE")):
        text = prompt(qs, nonce=f"[req {random.random():.12f}]", **(dict(evidence=ev) if arm == "PIPE" else dict(context=f["text"])))
        out, ptok, dt = ask(text); preds = parse_lines(out, len(qs))
        res[arm] = dict(preds=preds, seconds=dt + (ane_s if arm == "PIPE" else 0), prompt_tokens=ptok, response=out)
        emit(event="req", cid=f["id"], arm=arm, response=out, preds=preds, prompt_tokens=ptok, llm_seconds=dt, ane_seconds=ane_s if arm == "PIPE" else None,
             selected=sel if arm == "PIPE" else None, n_windows=len(ws))
    ag = [norm(t, a) == norm(t, b) for t, a, b in zip(qs, res["PIPE"]["preds"], res["FULL"]["preds"])]
    agree_all += ag; lat[f["id"]] = res["PIPE"]["seconds"] - res["FULL"]["seconds"]
    emit(event="compare", cid=f["id"], agree=ag, pipe=res["PIPE"]["preds"], full=res["FULL"]["preds"], lat_diff=lat[f["id"]],
         pipe_s=res["PIPE"]["seconds"], full_s=res["FULL"]["seconds"], pipe_tok=res["PIPE"]["prompt_tokens"], full_tok=res["FULL"]["prompt_tokens"])
    if n == 49 and np.mean(agree_all) < 0.80: emit(event="A2P_KILL", agreement=float(np.mean(agree_all))); break
ane.close()
emit(event="A2P_RUN_DONE", contracts=len(lat), agreement=float(np.mean(agree_all)), n_questions=len(agree_all), disagreements=int(len(agree_all) - sum(agree_all)),
     base_md5_unchanged=sh(f"sudo -n md5 -q {MD}/weights/weight.bin") == md5_0)
sent.terminate()
