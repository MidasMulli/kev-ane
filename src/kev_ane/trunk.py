"""Qwen3-0.6B in ANE conv-form: Conv2d-as-linear, (1,C,1,T), matmul attention.

Two deliberate differences from a generative port, both required by Kev:
  * cos / sin / neg are INPUTS, not baked buffers. Kev's branch positions restart after the
    state and its attention mask is block-causal over (state, question, options), so both are
    per-request data.
  * NO vocab head. Kev never generates text; the readout is a pointer head over hidden states.
"""
import torch, torch.nn as nn, torch.nn.functional as F, numpy as np
from .config import D, NL, NH, NKV, HD, IM, EPS, THETA


class RMSc(nn.Module):
    """RMSNorm over the channel dim of (1, C, 1, T)."""
    def __init__(s, C):
        super().__init__(); s.w = nn.Parameter(torch.ones(1, C, 1, 1))
    def forward(s, x):
        return x / torch.sqrt((x * x).mean(1, keepdim=True) + EPS) * s.w


class Block(nn.Module):
    def __init__(s):
        super().__init__()
        s.n1, s.n2 = RMSc(D), RMSc(D)
        s.q = nn.Conv2d(D, NH * HD, 1, bias=False)
        s.k = nn.Conv2d(D, NKV * HD, 1, bias=False)
        s.v = nn.Conv2d(D, NKV * HD, 1, bias=False)
        s.o = nn.Conv2d(NH * HD, D, 1, bias=False)
        s.qn = nn.Parameter(torch.ones(1, 1, HD, 1))      # Qwen3 per-head q/k norm
        s.kn = nn.Parameter(torch.ones(1, 1, HD, 1))
        s.gate = nn.Conv2d(D, IM, 1, bias=False)
        s.up   = nn.Conv2d(D, IM, 1, bias=False)
        s.down = nn.Conv2d(IM, D, 1, bias=False)

    def rmsh(s, x, w):
        return x / torch.sqrt((x * x).mean(2, keepdim=True) + EPS) * w

    def forward(s, x, cos, sin, neg):
        T = x.shape[3]; r = x; h = s.n1(x)
        q = s.q(h).view(1, NH, HD, T)
        k = s.k(h).view(1, NKV, HD, T)
        v = s.v(h).view(1, NKV, HD, T)
        q, k = s.rmsh(q, s.qn), s.rmsh(k, s.kn)
        def roth(z):
            z1, z2 = z[:, :, :HD // 2], z[:, :, HD // 2:]
            return torch.cat([-z2, z1], 2)
        q = q * cos + roth(q) * sin
        k = k * cos + roth(k) * sin
        k = k.repeat_interleave(NH // NKV, 1)             # GQA
        v = v.repeat_interleave(NH // NKV, 1)
        att = (q.transpose(-1, -2) @ k) / np.sqrt(HD) + neg
        att = att.softmax(-1)
        o = (v @ att.transpose(-1, -2)).reshape(1, NH * HD, 1, T)
        x = r + s.o(o); r = x; h = s.n2(x)
        return r + s.down(F.silu(s.gate(h)) * s.up(h))


class Trunk(nn.Module):
    """embed -> 28 blocks -> final norm. Returns hidden states, not logits."""
    def __init__(s):
        super().__init__()
        s.blocks = nn.ModuleList([Block() for _ in range(NL)])
        s.nf = RMSc(D)
    def forward(s, x, cos, sin, neg):
        for b in s.blocks:
            x = b(x, cos, sin, neg)
        return s.nf(x)


def rope_at(positions):
    """RoPE tables for ARBITRARY positions — Kev's branch positions are not a contiguous range."""
    inv = 1.0 / (THETA ** (torch.arange(0, HD, 2).float() / HD))
    p = torch.as_tensor(positions).float()
    e = torch.cat([torch.outer(p, inv)] * 2, -1)
    return (e.cos().T[None, None].contiguous(),
            e.sin().T[None, None].contiguous())
