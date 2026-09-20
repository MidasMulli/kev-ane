"""Record encoding and the block-causal branch mask.

Both come from Kev (jaredpalmer/kev, Apache-2.0) and are reimplemented here against its
published contract so this package has no import-time dependency on the training repo.
A record is one shared STATE plus typed questions, each with its own allowed answers.
"""
import re, torch
from .config import BUCKETS

SPECIAL = ["<|fim_prefix|>", "<|fim_middle|>", "<|box_start|>", "<|box_end|>", "<|fim_suffix|>"]
MAX_STATE = 384
OPT_NONE, OPT_DECIDE = -1, -2
_SPECIAL_RE = re.compile(r"<\|([A-Za-z0-9_]+)\|>")


def user_tokens(tok, text):
    """Caller text can never emit a delimiter: option boundaries stay unforgeable."""
    return tok(_SPECIAL_RE.sub(r"<¦\1¦>", text), add_special_tokens=False).input_ids


def encode(tok, state, questions, max_state=MAX_STATE):
    """[<state> ...] then per question [<q> instr <opt> o </opt>... <decide>]."""
    st = user_tokens(tok, state)
    S = [tok.convert_tokens_to_ids(SPECIAL[0])] + st[: max_state - 1]
    ids, seg, pos, opt = list(S), [0] * len(S), list(range(len(S))), [OPT_NONE] * len(S)
    q_id, o_id, c_id, d_id = (tok.convert_tokens_to_ids(t) for t in SPECIAL[1:])
    decide_idx, opt_idx = [], []
    for k, q in enumerate(questions, start=1):
        instr = [q_id] + user_tokens(tok, q["instr"])
        spans = [[o_id] + user_tokens(tok, o) + [c_id] for o in q["options"]]
        br = instr + [t for sp in spans for t in sp] + [d_id]
        base, p0 = len(ids), len(S)
        ids += br
        seg += [k] * len(br)
        pos += list(range(p0, p0 + len(br)))           # branch positions restart after the state
        opt += ([OPT_NONE] * len(instr)
                + [j for j, sp in enumerate(spans) for _ in sp] + [OPT_DECIDE])
        ends, cursor = [], len(instr)
        for sp in spans:
            cursor += len(sp); ends.append(cursor - 1)
        decide_idx.append(base + len(br) - 1)
        opt_idx.append([base + e for e in ends])
    return {"ids": ids, "seg": seg, "pos": pos, "opt": opt,
            "decide_idx": decide_idx, "opt_idx": opt_idx}


def branch_mask(seg, length, dtype=torch.float32, clamp=-1e4):
    """attend(i,j) iff j<=i and (seg[j]==0 or seg[j]==seg[i]). Additive [1,1,L,L].

    The state is shared; question branches never see each other. Right-padded keys are masked
    for every query, and the diagonal is kept so no row is fully masked.
    ⛔ clamp: torch.finfo(float32).min overflows fp16 on the CoreML path. -1e4 is already
    saturating under softmax and is fp16-safe.
    """
    L = max(len(seg), length)
    s = torch.full((1, L), -1, dtype=torch.long)
    s[0, : len(seg)] = torch.as_tensor(seg)
    causal = torch.tril(torch.ones(L, L, dtype=torch.bool))
    same = (s[:, None, :] == s[:, :, None]) | (s[:, None, :] == 0)
    allow = causal[None] & same & (s != -1)[:, None, :]
    allow = allow | torch.eye(L, dtype=torch.bool)[None]
    m = torch.zeros(1, L, L, dtype=dtype).masked_fill(~allow, torch.finfo(dtype).min)
    return m.clamp(min=clamp)[:, None]


def pick_bucket(n):
    for T in BUCKETS:
        if n <= T:
            return T
    return None
