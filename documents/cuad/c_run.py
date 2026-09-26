"""Program C (Astra-signed 2026-09-24): three adapters rotated within one request beside 27B decode. Systems only.
S0: 20 passes/s, CUA bound once. S1: 20 passes/s, rotate CUA -> W -> D every 8 passes (kevd-timed binds). G: 27B alone. IDLE-S1: S1 alone.
C-GPU: ret(S0) - ret(S1): upper < 0.05 no cost; lower >= 0.05 costs. C-LAT: bind ms load/idle ratio: upper < 1.25 not slowed; lower >= 1.25
slowed. Preconditions: distinct outputs per adapter; CUA output bitwise identical after the rotation; rates within 5%; base md5 unchanged."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, random, subprocess, threading, time, urllib.request, numpy as np, torch, sys
from transformers import AutoTokenizer
from cuad_common import *
from cuad_windows import windows
sys.path.insert(0, SRC)
from kev_ane.trunk import rope_at
from kev_ane.merge import load_base
from kev_ane.trunk import Trunk
from kev_ane.encode import branch_mask
from ane_run import sh, MD, W2D, TRUST
log = open("c_raw.jsonl", "w")
def emit(**r): print(json.dumps(r)[:300], flush=True); log.write(json.dumps(r) + "\n"); log.flush()
g0 = sh(GATE0).splitlines()[-1]; assert g0.startswith("gate=GREEN"), g0
sent = subprocess.Popen([SENTINEL, str(os.getpid()), os.path.abspath("c_red_sentinel.log")])
time.sleep(3); assert sent.poll() is None
md5_0 = sh(f"sudo -n md5 -q {MD}/weights/weight.bin")
S = json.load(open("splits.json")); TO = S["type_order"]; C = {c["id"]: c for c in load()[0]}
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base"); emb = load_base(Trunk().eval())
w = windows(C[S["test"][0]], tok, TO)[3]; T, D = 256, 1024                         # one fixed full-length window
IN = f"/tmp/c_kevd_in_{os.getpid()}"; os.makedirs(IN, exist_ok=True); os.chmod(IN, 0o777)
ids = w["ids"]; n = len(ids); assert n == T
cos, sin = rope_at(list(range(n))); neg = branch_mask([0] * n, T); x = torch.zeros(1, D, 1, T); x[0, :, 0, :] = emb[torch.as_tensor(ids)].T
for k, t in (("x", x), ("cos", cos), ("sin", sin), ("neg", neg)): np.ascontiguousarray(t.numpy()).astype(np.float16).tofile(f"{IN}/{k}.f16")
p = subprocess.Popen(["sudo", "-n", KEVD, MD], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
assert p.stdout.readline().strip() == "READY"
lock = threading.Lock()
def cmd(s):
    with lock: p.stdin.write(s + "\n"); p.stdin.flush(); return p.stdout.readline().strip()
def bind(a): r = cmd(f"BIND {TRUST}/{a}.bin"); assert r.startswith("BOUND"), r; return float(r.split()[1])
def predict(out=None):
    r = cmd(f"PREDICT {IN} {out or IN + '/hs.f16'}"); assert r.startswith("PRED"), r; return float(r.split()[1])
def hs():
    predict(); return np.fromfile(f"{IN}/hs.f16", dtype=np.float16).copy()
ROT = ["CUA", "W", "D"]

# ---- preconditions ----
outs = {}
for a in ROT: bind(a); outs[a] = hs()
bind("CUA"); back = hs()
dist = {f"{a}-{b}": float(np.abs(outs[a].astype(np.float32) - outs[b].astype(np.float32)).max()) for a, b in (("CUA", "W"), ("CUA", "D"), ("W", "D"))}
emit(event="precondition", distinct=dist, cua_roundtrip_bitwise=bool(np.array_equal(back, outs["CUA"])))
assert all(v > 1e-2 for v in dist.values()), dist; assert np.array_equal(back, outs["CUA"]), "round trip not bitwise"

def ane_loop(swap, stop, out):
    rate, stage = 20.0, 8; t0 = time.monotonic(); k = 0; cur = 0
    while not stop.is_set():
        if swap and k > 0 and k % stage == 0:
            cur = (cur + 1) % 3; b0 = time.monotonic(); ms = bind(ROT[cur]); out["binds"].append((b0, time.monotonic(), ms))
        tgt = t0 + k / rate; now = time.monotonic()
        if tgt > now: time.sleep(tgt - now)
        a = time.monotonic(); predict(); out["passes"].append((a, time.monotonic())); k += 1
def gpu_decode(tag):
    body = {"model": LLM_MODEL, "stream": True, "stream_options": {"include_usage": True}, "temperature": 0, "reasoning_effort": "none", "max_tokens": 512,
            "messages": [{"role": "user", "content": f"[run {tag} {random.random():.12f}] Write a detailed, multi-paragraph technical explanation of how a hash map handles collisions, resizing and iteration order."}]}
    req = urllib.request.Request(LLM_URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    stamps = []; usage = None
    with urllib.request.urlopen(req, timeout=900) as resp:
        for raw in resp:
            line = raw.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]": continue
            j = json.loads(line[5:]); now = time.monotonic()
            if j.get("usage"): usage = j["usage"]
            ch = j.get("choices") or []
            if ch and ch[0].get("delta", {}).get("content"): stamps.append(now)
    assert usage and len(stamps) == usage["completion_tokens"], (len(stamps), usage)
    assert (usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0) == 0, usage
    return stamps[0], stamps[-1], (len(stamps) - 1) / (stamps[-1] - stamps[0])
def arm(name, rep, swap=None, gpu=True, idle_s=15.0):
    bind("CUA")
    if swap is None: t0, t1, tps = gpu_decode(f"{name}{rep}"); return dict(arm=name, rep=rep, gpu_tps=tps)
    stop, out = threading.Event(), {"passes": [], "binds": []}; th = threading.Thread(target=ane_loop, args=(swap, stop, out)); th.start(); time.sleep(1.0)
    if gpu: t0, t1, tps = gpu_decode(f"{name}{rep}")
    else: t0 = time.monotonic(); time.sleep(idle_s); t1 = time.monotonic(); tps = None
    stop.set(); th.join()
    ins = [q for q in out["passes"] if q[0] >= t0 and q[1] <= t1]; bi = [b[2] for b in out["binds"] if b[0] >= t0 and b[1] <= t1]
    return dict(arm=name, rep=rep, gpu_tps=tps, pass_rate=len(ins) / (t1 - t0), n_binds=len(bi), bind_ms_median=float(np.median(bi)) if bi else None, bind_ms=bi)

rows = []
for rep in range(6):
    g = arm("G", rep); rows.append(g); emit(event="arm", **g)
    for name, sw in ((("S0", False), ("S1", True)) if rep % 2 == 0 else (("S1", True), ("S0", False))):
        r = arm(name, rep, sw); r["retention"] = r["gpu_tps"] / g["gpu_tps"]; rows.append(r); emit(event="arm", **{k: v for k, v in r.items() if k != "bind_ms"})
    r = arm("IDLE_S1", rep, True, gpu=False); rows.append(r); emit(event="arm", **{k: v for k, v in r.items() if k != "bind_ms"})
    for a in ("S0", "S1"):
        pr = next(x["pass_rate"] for x in rows if x["rep"] == rep and x["arm"] == a)
        assert abs(pr / 20 - 1) <= 0.05, f"rate {a} rep {rep}: {pr}"
p.stdin.close(); p.wait(timeout=30)
def v(a, k): return np.array([next(x[k] for x in rows if x["rep"] == r and x["arm"] == a) for r in range(6)])
def ci(d):
    rng = np.random.default_rng(0); bs = np.sort([rng.choice(d, len(d)).mean() for _ in range(10000)]); return [float(bs[250]), float(bs[9750])]
dg = v("S0", "retention") - v("S1", "retention"); ratio = v("S1", "bind_ms_median") / v("IDLE_S1", "bind_ms_median"); cg, cl = ci(dg), ci(ratio)
gpu_v = "swapping costs the 27B NOTHING at 0.05" if cg[1] < 0.05 else ("swapping COSTS the 27B" if cg[0] >= 0.05 else "INCONCLUSIVE")
lat_v = "binds NOT materially slowed under load" if cl[1] < 1.25 else ("binds SLOW under load" if cl[0] >= 1.25 else "INCONCLUSIVE")
ane_ms = 29.0; bl, bi_ = float(np.median(v("S1", "bind_ms_median"))), float(np.median(v("IDLE_S1", "bind_ms_median")))
emit(event="C_RESULT", ret_S0=float(v("S0", "retention").mean()), ret_S1=float(v("S1", "retention").mean()), C_GPU=[float(dg.mean()), cg], C_GPU_verdict=gpu_v,
     bind_ms_load_median=bl, bind_ms_idle_median=bi_, C_LAT_ratio=[float(ratio.mean()), cl], C_LAT_verdict=lat_v,
     overhead_3stage_idle=2 * bi_ / (2 * bi_ + 3 * 8 * ane_ms), overhead_3stage_load=2 * bl / (2 * bl + 3 * 8 * ane_ms),
     pass_rates={a: float(v(a, "pass_rate").mean()) for a in ("S0", "S1")}, base_md5_unchanged=sh(f"sudo -n md5 -q {MD}/weights/weight.bin") == md5_0)
sent.terminate()
