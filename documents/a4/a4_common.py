"""A4 (Astra-signed v2) FROZEN anchoring rule. A PwC result (M, D, R, V) is ANCHORED iff exactly one LaTeX unit U contains V as a
word-boundary number token AND a model-name token AND a dataset-or-metric token. U = a tabular row (D/R tokens may come from the enclosing
table's caption + header rows) or a non-table sentence. >1 matching unit = AMBIGUOUS (dropped). Returns char spans in the document text."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import re
GENERIC = {"ours", "model", "base", "large", "small", "net"}
def toks(s, generic=()):
    return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(t) >= 3 and t not in generic}
def vnorm(v):
    v = (v or "").strip().replace("%", "").strip()
    return v if len(v) >= 3 and re.fullmatch(r"-?\d+(\.\d+)?", v) else None
def vre(v): return re.compile(r"(?<![\d.])" + re.escape(v) + r"(?![\d])")
def has(text_l, tokset): return any(re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", text_l) for t in tokset)
TAB = re.compile(r"\\begin\{(tabular\*?|tabularx|longtable|tabulary)\}(.*?)\\end\{\1\}", re.S)
TENV = re.compile(r"\\begin\{(table\*?|wraptable|sidewaystable)\}(.*?)\\end\{\1\}", re.S)
def caption_of(text, a, b):
    for m in TENV.finditer(text):
        if m.start() <= a and b <= m.end():
            c = re.search(r"\\caption\{", m.group(0)); return m.group(0)[c.start():c.start() + 600] if c else ""
    return ""
def units(text):
    """[(a, b, kind, context_for_DR)] : tabular rows (context = caption + header rows + row) and non-table sentences."""
    U = []; spans = []
    for m in TAB.finditer(text):
        body0 = m.start(2); body = m.group(2); spans.append((m.start(), m.end()))
        rows = []; p = 0
        for r in re.finditer(r"\\\\", body): rows.append((p, r.start())); p = r.end()
        rows.append((p, len(body)))
        hdr_end = None
        for i, (x, y) in enumerate(rows):
            if re.search(r"\\midrule|\\hline", body[y:rows[i + 1][0]] if i + 1 < len(rows) else "") and i < len(rows) - 1:
                if "\\midrule" in body[y:rows[i + 1][0]] or i >= 1: hdr_end = i; break
        hdr = " ".join(body[x:y] for x, y in rows[:(hdr_end + 1 if hdr_end is not None else 1)])
        cap = caption_of(text, m.start(), m.end())
        for x, y in rows:
            if body[x:y].strip(): U.append((body0 + x, body0 + y, "row", cap + " " + hdr + " " + body[x:y]))
    spans.sort(); p = 0; outside = []
    for a, b in spans: outside.append((p, a)); p = max(p, b)
    outside.append((p, len(text)))
    for a, b in outside:
        seg = text[a:b]; q = 0
        for s in re.finditer(r"(?<=[.!?])\s+|\n\s*\n", seg):
            if seg[q:s.start()].strip(): U.append((a + q, a + s.start(), "sent", seg[q:s.start()]))
            q = s.end()
        if seg[q:].strip(): U.append((a + q, b, "sent", seg[q:]))
    return U
def anchor(text, U, M, D, R, V):
    """-> ("ok", (a, b, kind)) | ("ambiguous", n) | ("none", reason)"""
    v = vnorm(V)
    if not v: return ("none", "value<3ch_or_nonnumeric")
    mt = toks(M, GENERIC); drt = toks(D) | toks(R)
    if not mt: return ("none", "no_model_token")
    rx = vre(v); hits = []
    for a, b, kind, ctx in U:
        u = text[a:b]
        if not rx.search(u): continue
        ul = u.lower()
        if has(ul, mt) and has(ctx.lower(), drt): hits.append((a, b, kind))
    if len(hits) == 1: return ("ok", hits[0])
    return ("ambiguous", len(hits)) if hits else ("none", "no_unit")

# ---------------- v2 rule (after anchor gate v1 FAILED 22/30): column binding + wider generic list ----------------
GENERIC2 = GENERIC | {"baseline", "method", "methods", "proposed", "our", "full", "with", "without", "joint", "the", "and", "version", "default", "final", "best"}
def cells(row):
    """split a tabular row on unescaped &, expanding \\multicolumn{n} to n slots -> list of (slot_start, slot_end, text)."""
    parts = re.split(r"(?<!\\)&", row); out = []; k = 0
    for p in parts:
        m = re.search(r"\\multicolumn\{(\d+)\}", p); n = int(m.group(1)) if m else 1
        out.append((k, k + n, p)); k += n
    return out
def column_header(body, rows, hdr_end, row_i, slot):
    """header text over that column slot (all header rows) + full-width section-label rows between header and row_i."""
    txt = []
    for x, y in rows[:(hdr_end + 1 if hdr_end is not None else 1)]:
        for a, b, t in cells(body[x:y]):
            if a <= slot < b: txt.append(t)
    for x, y in rows[(hdr_end + 1 if hdr_end is not None else 1):row_i]:
        cs = cells(body[x:y])
        if len(cs) == 1 and re.search(r"\\multicolumn", cs[0][2]): txt.append(cs[0][2])
    return " ".join(txt)
def units2(text):
    """as units(), but row units carry (value-cell-aware) structure: (a, b, 'row', caption, body, rows, hdr_end, i)."""
    U = []; spans = []
    for m in TAB.finditer(text):
        body0 = m.start(2); body = m.group(2); spans.append((m.start(), m.end()))
        rows = []; p = 0
        for r in re.finditer(r"\\\\", body): rows.append((p, r.start())); p = r.end()
        rows.append((p, len(body)))
        hdr_end = None
        for i, (x, y) in enumerate(rows):
            if re.search(r"\\midrule|\\hline", body[y:rows[i + 1][0]] if i + 1 < len(rows) else "") and i < len(rows) - 1:
                if "\\midrule" in body[y:rows[i + 1][0]] or i >= 1: hdr_end = i; break
        cap = caption_of(text, m.start(), m.end())
        for i, (x, y) in enumerate(rows):
            if body[x:y].strip(): U.append((body0 + x, body0 + y, "row", dict(cap=cap, body=body, rows=rows, hdr_end=hdr_end, i=i, x=x)))
    spans.sort(); p = 0; outside = []
    for a, b in spans: outside.append((p, a)); p = max(p, b)
    outside.append((p, len(text)))
    for a, b in outside:
        seg = text[a:b]; q = 0
        for s in re.finditer(r"(?<=[.!?])\s+|\n\s*\n", seg):
            if seg[q:s.start()].strip(): U.append((a + q, a + s.start(), "sent", None))
            q = s.end()
        if seg[q:].strip(): U.append((a + q, b, "sent", None))
    return U
def anchor2(text, U, M, D, R, V):
    """v2: row units need V in a cell whose COLUMN HEADER (+ section labels) has a D-or-R token, and the model token in the row's cells
    other than V's cell; sentences need V + model token + D token + R token. Generic list widened. >1 match = ambiguous."""
    v = vnorm(V)
    if not v: return ("none", "value<3ch_or_nonnumeric")
    mt = toks(M, GENERIC2); dt = toks(D); rt = toks(R); drt = dt | rt
    if not mt: return ("none", "no_model_token")
    rx = vre(v); hits = []
    for a, b, kind, st in U:
        u = text[a:b]
        if not rx.search(u): continue
        if kind == "sent":
            ul = u.lower()
            if has(ul, mt) and has(ul, dt) and has(ul, rt): hits.append((a, b, kind))
            continue
        row = st["body"][st["rows"][st["i"]][0]:st["rows"][st["i"]][1]]; cs = cells(row)
        for s0, s1, t in cs:
            if not rx.search(t): continue
            others = " ".join(tt for x0, x1, tt in cs if x0 != s0).lower()
            ch = column_header(st["body"], st["rows"], st["hdr_end"], st["i"], s0).lower()
            if has(others, mt) and has(ch, drt): hits.append((a, b, kind)); break
    if len(hits) == 1: return ("ok", hits[0])
    return ("ambiguous", len(hits)) if hits else ("none", "no_unit")

# ---------------- v3 rule (Astra ruling after gate v1 22/30): v2 + METRIC-LABEL agreement filter ----------------
def toks2(s): return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(t) >= 2}
def has_all(text_l, tokset): return bool(tokset) and all(re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", text_l) for t in tokset)
def anchor3(text, U, M, D, R, V):
    """v3: row units: V in a cell whose COLUMN HEADER + section-label rows contain EVERY metric token (len >= 2) of R, a dataset token of D
    appears in column header + section labels + caption, model token (GENERIC2 excluded) in another cell of the row. Sentence units: V +
    model token + a D token + EVERY R token. >1 match = ambiguous."""
    v = vnorm(V)
    if not v: return ("none", "value<3ch_or_nonnumeric")
    mt = toks(M, GENERIC2); dt = toks(D); rt = toks2(R)
    if not mt: return ("none", "no_model_token")
    if not rt or not dt: return ("none", "no_metric_or_dataset_token")
    rx = vre(v); hits = []
    for a, b, kind, st in U:
        u = text[a:b]
        if not rx.search(u): continue
        if kind == "sent":
            ul = u.lower()
            if has(ul, mt) and has(ul, dt) and has_all(ul, rt): hits.append((a, b, kind))
            continue
        row = st["body"][st["rows"][st["i"]][0]:st["rows"][st["i"]][1]]; cs = cells(row)
        for s0, s1, t in cs:
            if not rx.search(t): continue
            others = " ".join(tt for x0, x1, tt in cs if x0 != s0).lower()
            ch = column_header(st["body"], st["rows"], st["hdr_end"], st["i"], s0).lower()
            if has(others, mt) and has_all(ch, rt) and has(ch + " " + st["cap"].lower(), dt): hits.append((a, b, kind)); break
    if len(hits) == 1: return ("ok", hits[0])
    return ("ambiguous", len(hits)) if hits else ("none", "no_unit")

# ---------------- v4 candidate (after gate v3 failed 26/30, 25/30): ALL tokens, decimals kept, row units only ----------------
def toks4(s): return {t for t in re.split(r"[^a-z0-9.@]+", (s or "").lower().replace("%", "")) if len(t) >= 2 and t.strip(".") and t not in GENERIC2}
def has_all4(text_l, tokset): return bool(tokset) and all(re.search(r"(?<![a-z0-9.])" + re.escape(t.strip(".")) + r"(?![a-z0-9])", text_l) for t in tokset)
def anchor4(text, U, M, D, R, V):
    """v4: rows only. EVERY model token (len >= 2, generic excluded) in another cell of the row; EVERY metric token (decimals and @ kept)
    in the value's column header + section labels; EVERY dataset token in column header + section labels + caption. >1 match dropped."""
    v = vnorm(V)
    if not v: return ("none", "value<3ch_or_nonnumeric")
    mt, dt, rt = toks4(M), toks4(D), toks4(R)
    if not mt or not dt or not rt: return ("none", "empty_tokens")
    rx = vre(v); hits = []
    for a, b, kind, st in U:
        if kind != "row" or not rx.search(text[a:b]): continue
        row = st["body"][st["rows"][st["i"]][0]:st["rows"][st["i"]][1]]; cs = cells(row)
        for s0, s1, t in cs:
            if not rx.search(t): continue
            others = " ".join(tt for x0, x1, tt in cs if x0 != s0).lower()
            ch = column_header(st["body"], st["rows"], st["hdr_end"], st["i"], s0).lower()
            if has_all4(others, mt) and has_all4(ch, rt) and has_all4(ch + " " + st["cap"].lower(), dt): hits.append((a, b, kind)); break
    if len(hits) == 1: return ("ok", hits[0])
    return ("ambiguous", len(hits)) if hits else ("none", "no_unit")
