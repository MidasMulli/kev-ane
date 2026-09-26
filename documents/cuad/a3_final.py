"""Program A / A3 final (Astra-signed). TEST (96 contracts, frozen; one run, no re-tuning). Per contract:
  ANE stage (measured wall): tokenize -> windows -> kevd predict per window -> host head -> per value type top-2 windows, NULL if max < tau.
  PIPE = the question list + the selected windows (deduped, document order) -> 27B.   FULL = the whole contract -> 27B.
  Arm order alternates per contract (ABBA). Both cold (nonce first, cache miss asserted). PIPE latency = ANE stage + 27B; FULL = 27B.
G-E2E: acc(PIPE) - acc(FULL) paired by question, contract-clustered bootstrap, lower 95% >= -0.05.
G-LAT: median over contracts of (PIPE - FULL) seconds, contract bootstrap, upper 95% < 0.   PASS = both.
Reported: G-SEL value-type hit@2 with CI; NULL false-positive rate on absent types; descriptive 41-type presence F1 (micro and per type; no CI)."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, random, time, hashlib, subprocess, urllib.request, numpy as np
from transformers import AutoTokenizer
from cuad_common import *
from cuad_windows import windows, overlaps
from ane_run import Ane, sh, MD, W2D
log = open("a3_raw.jsonl", "w")
def emit(**r): print(json.dumps(r)[:300], flush=True); log.write(json.dumps(r) + "\n"); log.flush()
g0 = sh(GATE0).splitlines()[-1]; assert g0.startswith("gate=GREEN"), g0
S = json.load(open("splits.json")); assert hashlib.sha256(open("cuad_common.py", "rb").read()).hexdigest()[:12] == S["cuad_common_sha"]
TO = S["type_order"]; SEL = json.load(open("a1_selection.json")); tau = SEL["tau"]
sent = subprocess.Popen([SENTINEL, str(os.getpid()), os.path.abspath("a3_red_sentinel.log")])
time.sleep(3); assert sent.poll() is None
import numpy as _np
head = dict(_np.load("run_CUA/head.npz")); md5_0 = sh(f"sudo -n md5 -q {MD}/weights/weight.bin")
ane = Ane("CUA", head)
emit(event="launch", gate0=g0, bind=ane.bind, base_md5=md5_0, adapter_md5=sh(f"md5 -q {W2D}/_out/adapter_CUA.bin"),
     splits_sha=hashlib.sha256(open("splits.json", "rb").read()).hexdigest()[:12], a1_selection=SEL)
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base"); C = {c["id"]: c for c in load()[0]}

def ask(text):
    body = {"model": LLM_MODEL, "stream": False, "temperature": 0, "reasoning_effort": "none", "max_tokens": 200,
            "messages": [{"role": "user", "content": text}]}
    req = urllib.request.Request(LLM_URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.monotonic(); j = json.load(urllib.request.urlopen(req, timeout=1800)); dt = time.monotonic() - t0
    u = j["usage"]; cache = (j.get("metrics") or {}).get("cache", {}).get("status")
    assert (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) == 0 and cache in (None, "miss"), (u, cache)
    return j["choices"][0]["message"]["content"], u["prompt_tokens"], dt

rows, lat, sel_hits, nullfp, pres, secs = [], {}, [], [], [], {}
for ci_, cid in enumerate(S["test"]):
    c = C[cid]; its = items(c); qs = [t for t, _ in its]
    t0 = time.monotonic()
    ws = windows(c, tok, TO); sc = np.stack([ane.window(w["ids"])[0] for w in ws])
    chosen, per_type = set(), {}
    for t in qs:
        k = TO.index(t); top = [int(j) for j in np.argsort(-sc[:, k])[:2]]
        sel = [] if sc[:, k].max() < tau[t] else top; per_type[t] = sel; chosen |= set(sel)
    ev = [c["context"][ws[j]["a"]:ws[j]["b"]] for j in sorted(chosen)]
    ane_s = time.monotonic() - t0
    for t in qs: sel_hits.append((cid, any(overlaps(c["spans"][t], ws[j]["a"], ws[j]["b"]) for j in per_type[t])))
    for k, t in enumerate(TO):
        p = bool(sc[:, k].max() >= tau[t]); g = bool(c["spans"][t]); pres.append((cid, t, p, g))
        if not g: nullfp.append((cid, p))
    if not qs: emit(event="no_value_questions", cid=cid, ane_seconds=ane_s); continue
    res = {}
    order = ("PIPE", "FULL") if ci_ % 2 == 0 else ("FULL", "PIPE")
    for arm in order:
        text = prompt(qs, nonce=f"[req {random.random():.12f}]", **(dict(evidence=ev) if arm == "PIPE" else dict(context=c["context"])))
        out, ptok, dt = ask(text); preds = parse_lines(out, len(qs))
        oks = [correct(t, g, PRED_PARSE[t](p)) for (t, g), p in zip(its, preds)]
        res[arm] = dict(seconds=dt + (ane_s if arm == "PIPE" else 0.0), llm_seconds=dt, prompt_tokens=ptok)
        rows += [dict(cid=cid, arm=arm, type=t, ok=o) for (t, _), o in zip(its, oks)]
        emit(event="req", cid=cid, arm=arm, types=qs, gold=[c["gold"][t] for t in qs], response=out, preds=preds, ok=oks, prompt_tokens=ptok,
             llm_seconds=dt, ane_seconds=ane_s if arm == "PIPE" else None, n_windows=len(ws), selected=per_type if arm == "PIPE" else None,
             prompt=text if arm == "PIPE" else text[:300])
    lat[cid] = res["PIPE"]["seconds"] - res["FULL"]["seconds"]; secs[cid] = res
ane.close(); md5_1 = sh(f"sudo -n md5 -q {MD}/weights/weight.bin")

cids = [c for c in S["test"] if items(C[c])]; rng = np.random.default_rng(0)
def by(arm): return {c: [r["ok"] for r in rows if r["arm"] == arm and r["cid"] == c] for c in cids}
P_, F_ = by("PIPE"), by("FULL"); n = lambda s: sum(len(P_[c]) for c in s)
d_obs = (sum(sum(P_[c]) for c in cids) - sum(sum(F_[c]) for c in cids)) / n(cids)
bs_d, bs_l, bs_h = [], [], []
H = {}; [H.setdefault(c, []).append(h) for c, h in sel_hits]
for _ in range(10000):
    s = rng.choice(cids, len(cids))
    bs_d.append((sum(sum(P_[c]) for c in s) - sum(sum(F_[c]) for c in s)) / n(s))
    bs_l.append(float(np.median([lat[c] for c in s]))); bs_h.append(sum(sum(H[c]) for c in s) / sum(len(H[c]) for c in s))
e2e = [float(np.percentile(bs_d, 2.5)), float(np.percentile(bs_d, 97.5))]; lci = [float(np.percentile(bs_l, 2.5)), float(np.percentile(bs_l, 97.5))]
tp = sum(p and g for _, _, p, g in pres); fp = sum(p and not g for _, _, p, g in pres); fn = sum(g and not p for _, _, p, g in pres)
per_type_f1 = {}
for t in TO:
    tp_ = sum(p and g for _, tt, p, g in pres if tt == t); pp = sum(p for _, tt, p, g in pres if tt == t); gg = sum(g for _, tt, p, g in pres if tt == t)
    per_type_f1[t] = dict(f1=2 * tp_ / max(1, pp + gg), n_pos=gg)
g_e2e, g_lat = e2e[0] >= -0.05, lci[1] < 0
emit(event="A3_RESULT", n_contracts=len(cids), n_questions=n(cids),
     acc_PIPE=float(np.mean([r["ok"] for r in rows if r["arm"] == "PIPE"])), acc_FULL=float(np.mean([r["ok"] for r in rows if r["arm"] == "FULL"])),
     e2e_diff=d_obs, e2e_ci=e2e, G_E2E=g_e2e, lat_median_diff_s=float(np.median(list(lat.values()))), lat_ci=lci, G_LAT=g_lat,
     median_PIPE_s=float(np.median([secs[c]["PIPE"]["seconds"] for c in secs])), median_FULL_s=float(np.median([secs[c]["FULL"]["seconds"] for c in secs])),
     median_PIPE_prompt_tokens=float(np.median([secs[c]["PIPE"]["prompt_tokens"] for c in secs])), median_FULL_prompt_tokens=float(np.median([secs[c]["FULL"]["prompt_tokens"] for c in secs])),
     sel_hit2=float(np.mean([h for _, h in sel_hits])), sel_ci=[float(np.percentile(bs_h, 2.5)), float(np.percentile(bs_h, 97.5))],
     null_false_positive_rate=float(np.mean([p for _, p in nullfp])), presence_micro_f1=2 * tp / max(1, 2 * tp + fp + fn), presence_per_type=per_type_f1,
     per_type_acc={t: {a: float(np.mean([r["ok"] for r in rows if r["arm"] == a and r["type"] == t])) for a in ("PIPE", "FULL")} for t in VALUE_TYPES},
     base_md5_unchanged=md5_1 == md5_0, verdict="PASS" if (g_e2e and g_lat) else "NOT PASS")
sent.terminate()
