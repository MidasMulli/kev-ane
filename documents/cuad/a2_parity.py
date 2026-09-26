"""Program A / A2 silicon parity (Astra-signed). Export the A1 best checkpoint, pack against the Rev 5 G0 base, bind in a private kevd,
run every DEV window on the ANE (head on host). GATE: per-(contract, type) top-1 window agreement with the MLX A1 scores >= 0.99 over all
40 x 41 pairs. Printed: base md5 before/after bind, predict latency median/p95, and (descriptive) agreement on value types and on pairs
whose MLX max clears tau."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, time, hashlib, subprocess, numpy as np
from transformers import AutoTokenizer
from cuad_common import *
from cuad_windows import windows
from ane_run import export_and_pack, Ane, sh, MD
log = open("a2_raw.jsonl", "w")
def emit(**r): print(json.dumps(r)[:400], flush=True); log.write(json.dumps(r) + "\n"); log.flush()
g0 = sh(GATE0).splitlines()[-1]; assert g0.startswith("gate=GREEN"), g0
S = json.load(open("splits.json")); assert hashlib.sha256(open("cuad_common.py", "rb").read()).hexdigest()[:12] == S["cuad_common_sha"]
TO = S["type_order"]; SEL = json.load(open("a1_selection.json"))
md5_0 = sh(f"sudo -n md5 -q {MD}/weights/weight.bin")
head, amd5 = export_and_pack(); ane = Ane("CUA", head)
emit(event="bound", reply=ane.bind, adapter_md5=amd5, base_md5=md5_0, base_md5_after_bind=sh(f"sudo -n md5 -q {MD}/weights/weight.bin"))
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base"); C = {c["id"]: c for c in load()[0]}
MLX = np.load("a1_best_devscores.npz"); agree = []; agree_v = []; agree_t = []; lat = []
for i, cid in enumerate(S["dev"]):
    ws = windows(C[cid], tok, TO); m = MLX[f"s{i}"]; assert len(ws) == len(m), (cid, len(ws), len(m))
    a = []
    for w in ws: p, ms = ane.window(w["ids"]); a.append(p); lat.append(ms)
    a = np.stack(a)
    for k, t in enumerate(TO):
        ok = int(np.argmax(a[:, k]) == np.argmax(m[:, k])); agree.append(ok)
        if t in VALUE_TYPES: agree_v.append(ok)
        if m[:, k].max() >= SEL["tau"][t]: agree_t.append(ok)
    emit(event="contract", cid=cid, windows=len(ws), agree=float(np.mean(agree[-41:])), max_abs_prob_diff=float(np.abs(a - m).max()))
ane.close(); md5_1 = sh(f"sudo -n md5 -q {MD}/weights/weight.bin")
emit(event="A2_RESULT", pairs=len(agree), agreement=float(np.mean(agree)), gate_pass=float(np.mean(agree)) >= 0.99,
     agreement_value_types=float(np.mean(agree_v)), agreement_above_tau=float(np.mean(agree_t)) if agree_t else None, n_above_tau=len(agree_t),
     predict_ms_median=float(np.median(lat)), predict_ms_p95=float(np.percentile(lat, 95)), n_windows=len(lat), base_md5_unchanged=md5_1 == md5_0)
