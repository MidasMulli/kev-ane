"""Load Qwen3-0.6B-Base into the conv-form trunk and merge Kev's LoRA into the weights.

Kev-0.6B is LoRA r=16, alpha=32 over ALL SEVEN projections across 28 layers = 196 deltas
(392 tensors: an A and a B per delta). We MERGE them: the published port is not mutable.
"""
import json, torch
from safetensors.torch import load_file
from .config import D, NL, HD, base_snapshot, kev_dir
from .trunk import Trunk

HF_TO_CONV = {
    "self_attn.q_proj": "q", "self_attn.k_proj": "k",
    "self_attn.v_proj": "v", "self_attn.o_proj": "o",
    "mlp.gate_proj": "gate", "mlp.up_proj": "up", "mlp.down_proj": "down",
}


def load_base(trunk: Trunk):
    """Populate the trunk from Qwen3-0.6B-Base.

    The base has TIED embeddings, so `lm_head.weight` is absent — which is fine here because
    this port deletes the vocab head. Returns the embedding matrix for the caller.
    """
    W = load_file(base_snapshot() / "model.safetensors")
    g = lambda k: W[k].float()
    cw = lambda conv, wt: conv.weight.data.copy_(wt[:, :, None, None])
    for L, b in enumerate(trunk.blocks):
        p = f"model.layers.{L}."
        b.n1.w.data = g(p + "input_layernorm.weight").view(1, D, 1, 1)
        b.n2.w.data = g(p + "post_attention_layernorm.weight").view(1, D, 1, 1)
        for hf, attr in HF_TO_CONV.items():
            cw(getattr(b, attr), g(p + hf + ".weight"))
        b.qn.data = g(p + "self_attn.q_norm.weight").view(1, 1, HD, 1)
        b.kn.data = g(p + "self_attn.k_norm.weight").view(1, 1, HD, 1)
    trunk.nf.w.data = g("model.norm.weight").view(1, D, 1, 1)
    return g("model.embed_tokens.weight")


def merge_lora(trunk: Trunk, kev=None) -> int:
    """W += (alpha/r) * B @ A for every delta. Returns the count; expect 196."""
    kev = kev or kev_dir()
    lora = load_file(kev / "adapter_model.safetensors")
    cfg = json.load(open(kev / "adapter_config.json"))
    scale = cfg["lora_alpha"] / cfg["r"]
    n = 0
    for L in range(NL):
        for hf, attr in HF_TO_CONV.items():
            A = lora.get(f"base_model.model.layers.{L}.{hf}.lora_A.weight")
            B = lora.get(f"base_model.model.layers.{L}.{hf}.lora_B.weight")
            if A is None or B is None:
                continue
            delta = scale * (B.float() @ A.float())
            getattr(trunk.blocks[L], attr).weight.data += delta[:, :, None, None]
            n += 1
    return n


def build(merged: bool = True):
    """Returns (trunk, embeddings, n_merged). merged=False gives the base for a control arm."""
    t = Trunk().eval()
    emb = load_base(t)
    n = merge_lora(t) if merged else 0
    return t, emb, n
