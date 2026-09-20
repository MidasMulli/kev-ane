"""Kev's pointer head, on CPU. Two linears and a scaled dot product — microseconds."""
import numpy as np, torch, torch.nn as nn
from .config import D, kev_dir


class PointerHead(nn.Module):
    def __init__(s, d=D, dp=256):
        super().__init__()
        s.q, s.k = nn.Linear(d, dp), nn.Linear(d, dp)
        s.scale = 1.0 / np.sqrt(dp)
    def forward(s, h_decide, h_opts):        # [d], [K,d] -> [K]
        return (s.k(h_opts) @ s.q(h_decide)) * s.scale


def load_head(kev=None):
    kev = kev or kev_dir()
    hd = torch.load(kev / "head.pt", map_location="cpu", weights_only=False)
    h = PointerHead(D, hd["head_dim"])
    h.load_state_dict(hd["head"]); h.eval()
    return h, hd


def decide(head, hs, enc, q=0):
    """Option probabilities for question q from hidden states [T, D]."""
    with torch.no_grad():
        logits = head(hs[enc["decide_idx"][q]],
                      hs[torch.as_tensor(enc["opt_idx"][q])])
        return torch.softmax(logits, -1), logits
