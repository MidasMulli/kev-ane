"""Program A: ANE side. Export a1_best.npz -> PEFT run dir -> pack against the Rev 5 G0 base -> bind in a private kevd; score windows
(hidden states from the ANE, the A1 head on host, float32 numpy). Same input path as P2/PLD2 (x, cos, sin, neg; T=256; right pad)."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, subprocess, sys, time, numpy as np, torch
sys.path.insert(0, SRC)
from kev_ane.trunk import Trunk, rope_at
from kev_ane.merge import load_base
from kev_ane.encode import branch_mask
W2D = MUTABLE; MD = BASE_MLMODELC
TRUST = TRUST_DIR; T, D = 256, 1024
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()

def export_and_pack(npz="a1_best.npz", tag="CUA"):
    import mlx.core as mx
    from safetensors.torch import save_file
    w = mx.load(npz); run = os.path.abspath(f"run_{tag}"); os.makedirs(run, exist_ok=True); out = {}
    for L in range(28):
        for p in ("q", "k", "v", "o"):
            a = np.array(w[f"base.model.layers.{L}.self_attn.{p}_proj.lora_a"].astype(mx.float32)); b = np.array(w[f"base.model.layers.{L}.self_attn.{p}_proj.lora_b"].astype(mx.float32))
            out[f"base_model.model.layers.{L}.self_attn.{p}_proj.lora_A.weight"] = torch.tensor(a.T.copy())
            out[f"base_model.model.layers.{L}.self_attn.{p}_proj.lora_B.weight"] = torch.tensor(b.T.copy())
    save_file(out, f"{run}/adapter_model.safetensors")
    json.dump({"r": 16, "lora_alpha": 32, "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"]}, open(f"{run}/adapter_config.json", "w"))
    head = {k.replace("head.", ""): np.array(w[k].astype(mx.float32)) for k in w if k.startswith("head.")}
    np.savez(f"{run}/head.npz", **head)
    torch.save({k: torch.tensor(v) for k, v in head.items()}, f"{run}/head.pt")          # deploy_inputs.py pack reads head.pt
    pk = subprocess.run(f"cd {W2D} && {sys.executable} deploy_inputs.py pack _out 256 {tag} {run}", shell=True, capture_output=True, text=True)
    assert f"PACKED {tag}" in pk.stdout, pk.stdout[-500:] + pk.stderr[-500:]
    subprocess.run(["sudo", "-n", "cp", f"{W2D}/_out/adapter_{tag}.bin", f"{TRUST}/{tag}.bin"], check=True)
    return head, sh(f"md5 -q {W2D}/_out/adapter_{tag}.bin")

class Ane:
    def __init__(s, tag, head):
        s.emb = load_base(Trunk().eval()); s.h = head; s.IN = f"/tmp/cuad_kevd_in_{os.getpid()}"; os.makedirs(s.IN, exist_ok=True); os.chmod(s.IN, 0o777)
        s.p = subprocess.Popen(["sudo", "-n", KEVD, MD], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        assert s.p.stdout.readline().strip() == "READY"
        s.bind = s.cmd(f"BIND {TRUST}/{tag}.bin"); assert s.bind.startswith("BOUND"), s.bind
    def cmd(s, x): s.p.stdin.write(x + "\n"); s.p.stdin.flush(); return s.p.stdout.readline().strip()
    def window(s, ids):
        n = len(ids); full = ids + [0] * (T - n)
        cos, sin = rope_at(list(range(n)) + [0] * (T - n)); neg = branch_mask([0] * n, T)
        x = torch.zeros(1, D, 1, T); x[0, :, 0, :] = s.emb[torch.as_tensor(full)].T
        for k, t in (("x", x), ("cos", cos), ("sin", sin), ("neg", neg)): np.ascontiguousarray(t.numpy()).astype(np.float16).tofile(f"{s.IN}/{k}.f16")
        r = s.cmd(f"PREDICT {s.IN} {s.IN}/hs.f16"); assert r.startswith("PRED"), r
        hs = np.fromfile(f"{s.IN}/hs.f16", dtype=np.float16).reshape(D, -1).astype(np.float32).T[:n]
        feat = np.concatenate([hs[n - 1], hs.mean(0)])
        u = torch.nn.functional.gelu(torch.from_numpy(feat @ s.h["l1.weight"].T + s.h["l1.bias"])).numpy()   # exact erf GELU = mlx nn.gelu
        z = u @ s.h["l2.weight"].T + s.h["l2.bias"]
        return 1 / (1 + np.exp(-z)), float(r.split()[1])
    def close(s): s.p.stdin.close(); s.p.wait(timeout=30)
