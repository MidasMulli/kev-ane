"""I3 train (Astra-signed): as I2 with the CORRECTED anchors (i3_common.evidence). I2 train (Astra-signed): 160 TRAIN genuine ISDA docs, labels = ANCHORED heading paragraphs (i2_common.evidence), 12-output head.
Adapted from i1_train.py. I1 train (Astra-signed; 150 TRAIN teacher-labelled docs). Adapted from a1_train.py: 4-output head (ISDA fields), labels = window overlaps the
teacher evidence span, DEV hit@3 over DEV docs whose field has a teacher span. KILL at 60 min if DEV hit@3 upper < 0.70 (diagnostic).
Original: Program A / A1 train (Astra-signed 2026-09-24). Qwen3-0.6B-Base + LoRA r16 q,k,v,o all 28 layers (Rev 5 slot schema) + host head:
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
import sys; sys.path.insert(0, "../cuad")
from cuad_windows import overlaps
sys.path.insert(0, ROOT + "/isda3"); sys.path.insert(0, ROOT + "/isda2"); from i3_common import NAMES as FIELDS, evidence as i2_evidence
STEPS, B = 3000, 16
log = open("i3_train_raw.jsonl", "w")
def emit(**r): print(json.dumps(r)[:400], flush=True); log.write(json.dumps(r) + "\n"); log.flush()
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()
g0 = sh(GATE0).splitlines()[-1]; assert g0.startswith("gate=GREEN"), g0
assert not sh("pgrep -f 'i3_test.py|i2_train.py|a4_train.py'"), "another GPU job is running"
avail = float(re.search(r"avail_ram=([\d.]+)GB", g0).group(1)); KILL_GB = min(16.0, avail - 12.4 - 3.0); assert KILL_GB > 4.0, KILL_GB
mx.set_cache_limit(0)
def _wd():
    while True:
        a = (mx.get_active_memory() + mx.get_cache_memory()) / 1e9
        if a > KILL_GB: log.write(json.dumps({"event": "WATCHDOG_KILL", "mlx_gb": a}) + "\n"); log.flush(); os._exit(4)
        time.sleep(0.05)
threading.Thread(target=_wd, daemon=True).start()
sent = subprocess.Popen([SENTINEL, str(os.getpid()), os.path.abspath("i3_red_sentinel.log")])
time.sleep(3); assert sent.poll() is None
U = json.load(open("../isda2/isda2_corpus241.json")); SPL = json.load(open("../isda2/i2_split.json"))
P = {i: U[i] for i in range(len(U))}
TCH = [dict(idx=i, split="train", evidence=i2_evidence(U[i]["text"])) for i in SPL["train"]] + [dict(idx=i, split="dev", evidence=i2_evidence(U[i]["text"])) for i in SPL["dev"]]
TO = FIELDS; tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base")
emit(event="launch", gate0=g0, kill_gb=KILL_GB, train_docs=len(SPL["train"]), dev_docs=len(SPL["dev"]))
T_, STRIDE_ = 256, 224
def windows(t):
    c = P[t["idx"]]; enc = tok(c["text"], return_offsets_mapping=True, add_special_tokens=False); ids, offs = enc["input_ids"], enc["offset_mapping"]; out = []
    for s0 in range(0, max(1, len(ids) - (T_ - STRIDE_)), STRIDE_):
        w = ids[s0:s0 + T_]; a_, b_ = offs[s0][0], offs[s0 + len(w) - 1][1]
        y = np.array([1.0 if (t["evidence"].get(f) and overlaps([(t["evidence"][f][0], "x" * (t["evidence"][f][1] - t["evidence"][f][0]))], a_, b_)) else 0.0 for f in FIELDS], np.float32)
        out.append(dict(ids=w, a=a_, b=b_, y=y))
        if s0 + T_ >= len(ids): break
    return out
W = {t["idx"]: windows(t) for t in TCH}
TRW = [w for t in TCH if t["split"] == "train" for w in W[t["idx"]]]; POS = [w for w in TRW if w["y"].any()]
Y = np.stack([w["y"] for w in TRW]); pw = np.clip((len(TRW) - Y.sum(0)) / np.maximum(Y.sum(0), 1), 1, 50).astype(np.float32)
DEVT = [t for t in TCH if t["split"] == "dev"]
emit(event="data", train_windows=len(TRW), pos_windows=len(POS), field_pos=dict(zip(FIELDS, Y.sum(0).astype(int).tolist())))
model, _ = lm_load("Qwen/Qwen3-0.6B-Base"); model.freeze()
linear_to_lora_layers(model, len(model.model.layers), {"rank": 16, "scale": 2.0, "dropout": 0.0,
                      "keys": ["self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj", "self_attn.o_proj"]})
D = model.args.hidden_size
class Head(nn.Module):
    def __init__(s): super().__init__(); s.l1 = nn.Linear(2 * D, 256); s.l2 = nn.Linear(256, 12)
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

def score(idx):
    ws = W[idx]; out = []
    for i in range(0, len(ws), 16):
        ids, n, _ = batch(ws[i:i + 16]); out.append(np.array(mx.sigmoid(net(ids, n)).astype(mx.float32)))
    return np.concatenate(out)
def dev_eval():
    per = {}
    for t in DEVT:
        sc = score(t["idx"]); hits = []
        for k, f in enumerate(FIELDS):
            if not t["evidence"].get(f): continue
            top = np.argsort(-sc[:, k])[:3]; e = t["evidence"][f]; hits.append(any(W[t["idx"]][j]["a"] < e[1] and W[t["idx"]][j]["b"] > e[0] for j in top))
        per[t["idx"]] = hits
    ids_ = [i for i in per if per[i]]; rng_ = np.random.default_rng(0)
    tot = sum(sum(per[i]) for i in ids_) / max(1, sum(len(per[i]) for i in ids_)); bs = []
    for _ in range(5000):
        s_ = rng_.choice(ids_, len(ids_)); bs.append(sum(sum(per[i]) for i in s_) / sum(len(per[i]) for i in s_))
    return tot, [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))], None
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
            best = (h, step); mx.savez("i3_best.npz", **dict(tree_flatten(net.trainable_parameters())))
            pass
        if due_kill or el >= 5400 or step == STEPS:
            if not kill_checked:
                kill_checked = True
                if ci[1] < 0.70: killed = True; emit(event="I3_KILL", step=step, hit2=h, ci=ci, note="diagnostic, not a capability verdict"); break
        if el >= 5400: emit(event="hard_stop_90min", step=step); break

emit(event="I3_TRAIN_DONE", best_step=best[1], dev_hit3=best[0], elapsed_s=time.time() - t0)
sent.terminate()
