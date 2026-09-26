"""Program A / A1 train (Astra-signed 2026-09-24). Qwen3-0.6B-Base + LoRA r16 q,k,v,o all 28 layers (Rev 5 slot schema) + host head:
per window, 41 sigmoid scores from [last-token hidden ; mean-pooled hidden]. Windows T=256, stride 224, whole contract, NO question.
Label[type] = a gold span of that type overlaps the window's char range (original contract offsets). Head index = splits.json type_order.
Positive-weighted BCE; 50% of each batch drawn from windows with >= 1 positive label.
DEV every 500 steps: value-type hit@2 (positives only), contract-clustered bootstrap. KILL (diagnostic): at the first DEV eval at or after
60 min (or at the end of training if sooner), if the UPPER 95% bound < 0.70 -> stop and file. Hard stop 3,000 steps or 90 min.
Checkpoint kept = best DEV hit@2; tau per type = DEV presence-F1 argmax at that checkpoint (DEV only)."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, random, re, subprocess, threading, time, hashlib, numpy as np
import mlx.core as mx, mlx.nn as nn, mlx.optimizers as optim
from mlx.utils import tree_flatten
from mlx_lm import load as lm_load
from mlx_lm.tuner.utils import linear_to_lora_layers
from transformers import AutoTokenizer
from cuad_common import *
STEPS, B = 3000, 16
log = open("a1_raw.jsonl", "w")
def emit(**r): print(json.dumps(r)[:400], flush=True); log.write(json.dumps(r) + "\n"); log.flush()
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
g0 = sh(GATE0).splitlines()[-1]; assert g0.startswith("gate=GREEN"), g0
assert not sh("pgrep -f 'a0_admit.py|s2_extract.py|p1b_pointer.py|a3_final.py'"), "another GPU job is running"
avail = float(re.search(r"avail_ram=([\d.]+)GB", g0).group(1)); KILL_GB = min(16.0, avail - 12.4 - 3.0); assert KILL_GB > 4.0, KILL_GB
mx.set_cache_limit(0)
def _wd():
    while True:
        a = (mx.get_active_memory() + mx.get_cache_memory()) / 1e9
        if a > KILL_GB: log.write(json.dumps({"event": "WATCHDOG_KILL", "mlx_gb": a}) + "\n"); log.flush(); os._exit(4)
        time.sleep(0.05)
threading.Thread(target=_wd, daemon=True).start()
sent = subprocess.Popen([SENTINEL, str(os.getpid()), os.path.abspath("a1_red_sentinel.log")])
time.sleep(3); assert sent.poll() is None
S = json.load(open("splits.json")); assert hashlib.sha256(open("cuad_common.py", "rb").read()).hexdigest()[:12] == S["cuad_common_sha"]
TO = S["type_order"]; VI = [TO.index(t) for t in VALUE_TYPES]
emit(event="launch", gate0=g0, kill_gb=KILL_GB, splits_sha=hashlib.sha256(open("splits.json", "rb").read()).hexdigest()[:12])

tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base")
C = {c["id"]: c for c in load()[0]}
from cuad_windows import windows as _win, overlaps
def windows(c): return _win(c, tok, TO)
W = {cid: windows(C[cid]) for cid in S["train"] + S["dev"]}
TRW = [w for cid in S["train"] for w in W[cid]]; POS = [w for w in TRW if w["y"].any()]
Y = np.stack([w["y"] for w in TRW]); pw = np.clip((len(TRW) - Y.sum(0)) / np.maximum(Y.sum(0), 1), 1, 50).astype(np.float32)
emit(event="data", train_windows=len(TRW), pos_windows=len(POS), dev_windows=sum(len(W[c]) for c in S["dev"]),
     type_pos_counts=dict(zip(TO, Y.sum(0).astype(int).tolist())))

model, _ = lm_load("Qwen/Qwen3-0.6B-Base"); model.freeze()
linear_to_lora_layers(model, len(model.model.layers), {"rank": 16, "scale": 2.0, "dropout": 0.0,
                      "keys": ["self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj", "self_attn.o_proj"]})
D = model.args.hidden_size
class Head(nn.Module):
    def __init__(s): super().__init__(); s.l1 = nn.Linear(2 * D, 256); s.l2 = nn.Linear(256, 41)
    def __call__(s, hs, n):
        m = (mx.arange(hs.shape[1])[None, :] < n[:, None]).astype(hs.dtype)[..., None]
        feat = mx.concatenate([hs[mx.arange(hs.shape[0]), n - 1], (hs * m).sum(1) / n[:, None]], axis=-1)
        return s.l2(nn.gelu(s.l1(feat)))
class Net(nn.Module):
    def __init__(s): super().__init__(); s.base = model; s.head = Head()
    def __call__(s, ids, n): return s.head(s.base.model(ids), n)
net = Net(); PW = mx.array(pw)
def batch(ws):
    L = max(len(w["ids"]) for w in ws)
    return mx.array([w["ids"] + [0] * (L - len(w["ids"])) for w in ws]), mx.array([len(w["ids"]) for w in ws]), mx.array(np.stack([w["y"] for w in ws]))
def loss_fn(ids, n, y):
    z = net(ids, n); return (PW * y * nn.softplus(-z) + (1 - y) * nn.softplus(z)).mean()
opt = optim.Adam(learning_rate=1e-4); lossf = nn.value_and_grad(net, loss_fn)

def score(cid):
    ws = W[cid]; out = []
    for i in range(0, len(ws), 16):
        ids, n, _ = batch(ws[i:i + 16]); out.append(np.array(mx.sigmoid(net(ids, n)).astype(mx.float32)))
    return np.concatenate(out)                                                    # [n_windows, 41]
def dev_eval():
    per = {}; P = {}
    for cid in S["dev"]:
        sc = score(cid); P[cid] = sc; hits = []
        for t, _ in items(C[cid]):
            k = TO.index(t); top = np.argsort(-sc[:, k])[:2]
            hits.append(any(overlaps(C[cid]["spans"][t], W[cid][j]["a"], W[cid][j]["b"]) for j in top))
        per[cid] = hits
    cids = [c for c in S["dev"] if per[c]]; rng = np.random.default_rng(0)
    tot = sum(sum(per[c]) for c in cids) / sum(len(per[c]) for c in cids); bs = []
    for _ in range(5000):
        s = rng.choice(cids, len(cids)); bs.append(sum(sum(per[c]) for c in s) / sum(len(per[c]) for c in s))
    return tot, [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], P

rng = random.Random(1); t0 = time.time(); best = (-1, None); killed = False; kill_checked = False
for step in range(1, STEPS + 1):
    ws = [rng.choice(POS) for _ in range(B // 2)] + [rng.choice(TRW) for _ in range(B - B // 2)]
    L, g = lossf(*batch(ws)); opt.update(net, g); mx.eval(net.parameters(), opt.state)
    el = time.time() - t0
    if step % 100 == 0: emit(event="train", step=step, loss=float(L), elapsed_s=el, mlx_peak_gb=mx.get_peak_memory() / 1e9)
    due_kill = (not kill_checked) and el >= 3600
    if step % 500 == 0 or step == STEPS or due_kill or el >= 5400:
        h, ci, P = dev_eval(); emit(event="dev", step=step, elapsed_s=time.time() - t0, hit2=h, ci=ci)
        if h > best[0]:
            best = (h, step); mx.savez("a1_best.npz", **dict(tree_flatten(net.trainable_parameters())))
            np.savez("a1_best_devscores.npz", **{f"s{i}": P[c] for i, c in enumerate(S["dev"])})
        if due_kill or el >= 5400 or step == STEPS:
            if not kill_checked:
                kill_checked = True
                if ci[1] < 0.70: killed = True; emit(event="A1_KILL", step=step, hit2=h, ci=ci, note="diagnostic, not a capability verdict"); break
        if el >= 5400: emit(event="hard_stop_90min", step=step); break

# tau per type from the best checkpoint's DEV scores (presence F1 argmax); DEV only
if not killed:
    D_ = np.load("a1_best_devscores.npz"); tau = {}
    for k, t in enumerate(TO):
        mx_ = np.array([D_[f"s{i}"][:, k].max() for i in range(len(S["dev"]))]); pres = np.array([bool(C[c]["spans"][t]) for c in S["dev"]])
        cands = np.unique(np.concatenate([mx_, [1.01]])); f1 = []
        for th in cands:
            pr = mx_ >= th; tp = (pr & pres).sum(); f1.append(2 * tp / max(1, pr.sum() + pres.sum()))
        tau[t] = float(cands[int(np.argmax(f1))])
    json.dump(dict(tau=tau, best_step=best[1], dev_hit2=best[0], type_order=TO), open("a1_selection.json", "w"), indent=1)
    emit(event="A1_RESULT", best_step=best[1], dev_hit2=best[0], tau=tau, elapsed_s=time.time() - t0)
sent.terminate()
