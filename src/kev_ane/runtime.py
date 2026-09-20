"""Assemble model inputs for one record and run a decision, on CoreML or in torch."""
import numpy as np, torch
from .config import D
from .encode import encode, branch_mask, pick_bucket
from .trunk import rope_at


def make_inputs(tok, emb, state, questions, T=None):
    """-> (feed, enc, T). feed keys match the converted model: x, cos, sin, neg."""
    enc = encode(tok, state, questions)
    n = len(enc["ids"])
    T = T or pick_bucket(n)
    if T is None:
        raise ValueError(f"sequence {n} exceeds the largest bucket")
    pad = tok.pad_token_id or 0
    ids = enc["ids"] + [pad] * (T - n)
    pos = enc["pos"] + [0] * (T - n)
    cos, sin = rope_at(pos)
    neg = branch_mask(enc["seg"], T)
    x = torch.zeros(1, D, 1, T)
    x[0, :, 0, :] = emb[torch.as_tensor(ids)].T
    feed = {"x": x.numpy().astype(np.float32),
            "cos": cos.numpy().astype(np.float32),
            "sin": sin.numpy().astype(np.float32),
            "neg": neg.numpy().astype(np.float32)}
    return feed, enc, T


def run_torch(trunk, feed):
    with torch.no_grad():
        out = trunk(*[torch.as_tensor(feed[k]) for k in ("x", "cos", "sin", "neg")])
    return out[0, :, 0, :].T.float()          # [T, D]


def run_coreml(model, feed):
    out = model.predict(feed)["hs"]
    return torch.as_tensor(np.asarray(out))[0, :, 0, :].T.float()
