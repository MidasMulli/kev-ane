"""A4b (Astra-signed v2) frozen pieces: table context with the overflow rule, k policy, prompt cap. Context is 27B-prompt text only."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import re
from a4_common import TAB, caption_of
CAP_TOK, HDR_TOK, PROMPT_CAP = 200, 300, 16000
def tables(text, tok):
    """[(start, end, context_text | None, flag)] per tabular env; flag in OK / TRUNCATED / NO_CONTEXT."""
    out = []
    for m in TAB.finditer(text):
        body = m.group(2); rows = []; p = 0
        for r in re.finditer(r"\\\\", body): rows.append((p, r.start())); p = r.end()
        rows.append((p, len(body)))
        hdr_end = None
        for i, (x, y) in enumerate(rows):
            if re.search(r"\\midrule|\\hline", body[y:rows[i + 1][0]] if i + 1 < len(rows) else "") and i < len(rows) - 1:
                if "\\midrule" in body[y:rows[i + 1][0]] or i >= 1: hdr_end = i; break
        cap = caption_of(text, m.start(), m.end())
        hrows = rows[:(hdr_end + 1 if hdr_end is not None else 1)]          # EXACTLY rule v4's effective header (column_header)
        hdr = " \\\\ ".join(body[x:y] for x, y in hrows)
        if not cap or not hdr.strip(): out.append((m.start(), m.end(), None, "NO_CONTEXT")); continue
        ci, hi = tok(cap, add_special_tokens=False)["input_ids"], tok(hdr, add_special_tokens=False)["input_ids"]
        flag = "TRUNCATED" if (len(ci) > CAP_TOK or len(hi) > HDR_TOK) else "OK"
        ctx = "[TABLE CONTEXT] " + tok.decode(ci[:CAP_TOK]) + "\n[TABLE HEADER] " + tok.decode(hi[:HDR_TOK])
        out.append((m.start(), m.end(), ctx, flag))
    return out
def policy(order, n, k):
    return sorted({j for i in order[:k] for j in (int(i) - 1, int(i), int(i) + 1) if 0 <= j < n})
def excerpts_with_context(text, ws, pick, rank, T, tok, context=True):
    """pick = window ids (document order); rank = {window: priority, lower = better}. Returns (excerpt strings, dropped windows).
    Context block before each table's first excerpt; whole prompt capped at PROMPT_CAP tokens by dropping lowest-priority windows."""
    keep = list(pick); dropped = []
    while True:
        out = []; seen = set()
        for j in keep:
            a, b = ws[j]["a"], ws[j]["b"]
            if context:
                for ti, (s, e, ctx, flag) in enumerate(T):
                    if s < b and e > a and ti not in seen:
                        seen.add(ti)
                        if ctx: out.append(ctx)
            out.append(text[a:b])
        n = sum(len(tok(x, add_special_tokens=False)["input_ids"]) for x in out)
        if n <= PROMPT_CAP or len(keep) <= 1: return out, dropped
        worst = max(keep, key=lambda j: rank[j]); keep.remove(worst); dropped.append(worst)
