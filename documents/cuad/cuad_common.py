"""Program A (Astra-signed 2026-09-24, PREREG_DRAFT_2026-09-24_A_cuad_contract_review.md): shared data, splits, questions, parsers.
Frozen with the splits: any change here after splits.json is written must be logged as a deviation."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import csv, json, os, random, re
HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 20260924
VALUE_TYPES = ["Governing Law", "Agreement Date", "Renewal Term", "Notice Period To Terminate Renewal"]
CSV_COL = {"Governing Law": "Governing Law-Answer", "Agreement Date": "Agreement Date-Answer",
           "Renewal Term": "Renewal Term-Answer", "Notice Period To Terminate Renewal": "Notice Period To Terminate Renewal- Answer"}
QUESTION = {
    "Governing Law": "Which jurisdiction's law governs this agreement? Answer with the state, province or country name only.",
    "Agreement Date": "What is the date of this agreement? Answer as M/D/YYYY; if only the year (or month and year) is stated, give only what is stated.",
    "Renewal Term": "How long is each renewal term of this agreement? Answer as a number and a unit, e.g. '1 year'.",
    "Notice Period To Terminate Renewal": "How much advance notice must a party give to prevent the agreement from renewing? Answer as a number and a unit, e.g. '90 days'.",
}
def key(name):
    name = name.strip().strip("'\"").strip()                                             # one CSV row carries stray quotes
    name = name.rsplit(".", 1)[0] if name.lower().endswith(".pdf") else name
    return re.sub(r"[&']", "_", name).strip().rstrip("-").strip()

def load():
    """-> list of contracts: {id, context, spans{type: [(start, text)]}, gold{value type: raw csv value}}; type_order = head mapping."""
    d = json.load(open(f"{HERE}/CUAD_v1/CUAD_v1.json"))["data"]
    rows = {key(r["Filename"]): r for r in csv.DictReader(open(f"{HERE}/CUAD_v1/master_clauses.csv", encoding="utf-8", errors="replace"))}
    out, type_order = [], None
    for c in d:
        p = c["paragraphs"][0]; types = [re.search(r'related to "(.+?)"', q["question"]).group(1) for q in p["qas"]]
        if type_order is None: type_order = types
        assert types == type_order, c["title"]
        r = rows[key(c["title"])]
        out.append(dict(id=key(c["title"]), context=p["context"],
                        spans={t: [(a["answer_start"], a["text"]) for a in q["answers"]] for t, q in zip(types, p["qas"])},
                        gold={t: r[CSV_COL[t]].strip() for t in VALUE_TYPES}))
    assert len(out) == 510 and len(type_order) == 41
    return out, type_order

# ---------------- parsers ----------------
WORDNUM = {w: str(i) for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}
US = set("alabama alaska arizona arkansas california colorado connecticut delaware florida georgia hawaii idaho illinois indiana iowa kansas "
         "kentucky louisiana maine maryland massachusetts michigan minnesota mississippi missouri montana nebraska nevada ohio oklahoma oregon "
         "pennsylvania tennessee texas utah vermont virginia washington wisconsin wyoming".split()) | {"new york", "new jersey", "new mexico",
         "new hampshire", "north carolina", "south carolina", "north dakota", "south dakota", "rhode island", "west virginia"}
ALIAS = {"prc": "china", "people's republic of china": "china", "peoples republic of china": "china", "federal republic of germany": "germany",
         "uk": "united kingdom", "u.k.": "united kingdom", "usa": "united states", "u.s.": "united states", "ny": "new york"}
def _jur(s):
    s = s.lower().strip().strip(".").replace("’", "'")
    s = re.sub(r"^(the )?(state|commonwealth|province|republic) of ", "", s); s = s.split(",")[0].strip()
    s = re.sub(r"^(the )?(state|commonwealth|province|republic) of ", "", s)
    return ALIAS.get(s, s)
def gold_jur(g):
    if not g or any(x in g for x in (";", "[", " in which")): return None
    parts = [p.strip().lower() for p in g.split(",")]
    if len(parts) == 2 and parts[0] in US and parts[1] in US: return None                     # two states: ambiguous
    return _jur(g)
def pred_jur(p): return _jur(p) if p else None

def _yr(y): y = int(y); return y + (2000 if y <= 30 else 1900) if y < 100 else y
def gold_date(g):
    m = re.fullmatch(r"(\d{1,2}|\[\])/(\d{1,2}|\[\])/(\d{2,4})", g.strip()) if g else None
    if not m: return None
    return tuple(None if x == "[]" else int(x) for x in m.groups()[:2]) + (_yr(m.group(3)),)
MONTHS = {m: i + 1 for i, m in enumerate("january february march april may june july august september october november december".split())}
def pred_date(p):
    if not p: return None
    s = p.lower()
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
    if m: return (int(m.group(1)), int(m.group(2)), _yr(m.group(3)))
    m = re.search(r"\b(\d{1,2})/(\d{4})\b", s)                                   # "11/2006" = month/year (A0 deviation 1)
    if m: return (int(m.group(1)), None, int(m.group(2)))
    y = re.search(r"\b(1[89]\d\d|20\d\d)\b", s); mo = next((v for k, v in MONTHS.items() if k in s), None)
    d = re.search(r"\b(\d{1,2})(st|nd|rd|th)?\b", re.sub(r"\b(1[89]\d\d|20\d\d)\b", "", s))
    if y: return (mo, int(d.group(1)) if (d and mo) else None, int(y.group(1)))
    return None
def date_ok(g, p):
    return p is not None and all(gv is None or gv == pv for gv, pv in zip(g, p))

DUR = re.compile(r"(\d+(?:\.\d+)?)\s*\)?\s*(day|week|month|year)s?")
def _dur_all(s):
    s = s.lower()
    for w, n in WORDNUM.items(): s = re.sub(rf"\b{w}\b", n, s)
    return [(float(a), u) for a, u in DUR.findall(s)]
def gold_dur(g):
    if not g or any(x in g for x in (";", "/", ",")): return None
    v = sorted(set(_dur_all(g)))
    return v[0] if len(v) == 1 else None
def pred_dur(p):
    v = _dur_all(p) if p else []
    return v[0] if v else None

GOLD_PARSE = {"Governing Law": gold_jur, "Agreement Date": gold_date, "Renewal Term": gold_dur, "Notice Period To Terminate Renewal": gold_dur}
PRED_PARSE = {"Governing Law": pred_jur, "Agreement Date": pred_date, "Renewal Term": pred_dur, "Notice Period To Terminate Renewal": pred_dur}
def correct(t, g, p):
    if t == "Agreement Date": return date_ok(g, p)
    return p is not None and p == g

def items(c):
    """The contract's gradeable value questions: csv value parses AND the json has >= 1 annotated span for that type."""
    out = []
    for t in VALUE_TYPES:
        g = GOLD_PARSE[t](c["gold"][t])
        if g is not None and c["spans"][t]: out.append((t, g))
    return out

def prompt(questions, context=None, evidence=None, nonce=""):
    qs = "\n".join(f"Q{i + 1}: {QUESTION[t]}" for i, t in enumerate(questions))
    fmt = "Answer each question on its own line as 'Q<n>: <answer>', nothing else. If the text does not state it, answer 'Q<n>: NONE'."
    if context is not None: body = f"Contract:\n{context}\n\n"
    elif evidence is not None: body = "Excerpts from a contract:\n" + "\n...\n".join(evidence) + "\n\n"
    else: body = "(No contract text is provided; answer from general knowledge if you can.)\n\n"
    return f"{nonce}\n{body}Questions:\n{qs}\n\n{fmt}"
def parse_lines(text, n):
    out = {}
    for line in text.splitlines():
        m = re.match(r"\s*\**Q(\d+)\**\s*[:.)-]\s*(.*)", line)
        if m and 1 <= int(m.group(1)) <= n and int(m.group(1)) not in out: out[int(m.group(1))] = m.group(2).strip().strip("*").strip()
    return [None if (out.get(i + 1) or "").upper().startswith("NONE") else out.get(i + 1) for i in range(n)]
