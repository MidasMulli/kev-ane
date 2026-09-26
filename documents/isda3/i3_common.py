"""I3 (Astra-signed): I2's questions/prompt/parse/norm unchanged; CORRECTED anchors for Form, Threshold Amount, Credit Support Annex;
the fixed keyword sidecar used at inference."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import re, sys
sys.path.insert(0, ROOT + "/isda2")
from i2_common import Q, NAMES, prompt, parse, norm, schedule_start, evidence as i2_evidence
def evidence(text):
    ev = i2_evidence(text); s0 = schedule_start(text); sched = text[s0:]
    # Form: ONLY an explicit year (title "1992/2002 ... Master Agreement", "ISDA 2002", or a copyright line with the year); else no label
    ev["Form"] = None
    m = re.search(r"(1992|2002)\s+(isda\s+)?master\s+agreement|isda\s*(®)?\s*(1992|2002)|copyright[^\n]{0,60}\b(1992|2002)\b", text[:8000], re.I)
    if m: ev["Form"] = (m.start(), min(len(text), m.start() + 500))                                  # offsets in FULL-text coordinates
    else:
        m = re.search(r"(1992|2002)\s+(isda\s+)?master\s+agreement", sched[:3000], re.I)
        if m: ev["Form"] = (s0 + m.start(), min(len(text), s0 + m.start() + 500))
    # Threshold Amount: its heading; else the Cross Default paragraph ONLY if it states an amount or a percentage
    if ev["Threshold Amount"] is None:
        m = re.search(r"cross[\s\-]+default", sched, re.I)
        if m:
            para = sched[m.start():m.start() + 900]
            if re.search(r"(\$|usd|eur|gbp|u\.s\.\s*dollars?)\s*[\d,]{3,}|[\d,]{4,}\s*(dollars|usd)|\d+(\.\d+)?\s*%|percent", para, re.I):
                ev["Threshold Amount"] = (s0 + m.start(), min(len(text), s0 + m.start() + 900))
    # Credit Support Annex: a line-start heading / election, never a passing mention
    m = re.search(r"(^|\n)[ \t]*(\(?[a-z0-9ivx]{1,4}[.)]\)?[ \t]*)?(details\s+of\s+any\s+credit\s+support\s+document|credit\s+support\s+(document|provider|annex)s?[ \t]*(\.|:|means|shall\s+mean|in\s+relation))", sched, re.I)
    ev["Credit Support Annex"] = (s0 + m.start(3), min(len(text), s0 + m.start(3) + 700)) if m else None
    return ev
SIDE = {"Form": r"\b(1992|2002)\b", "Threshold Amount": r"threshold", "Credit Support Annex": r"credit\s+support"}
def sidecar(text, windows):
    """Up to 2 windows per weak field containing its keyword (first occurrences in document order). Fixed before data."""
    out = set()
    for name, rx in SIDE.items():
        hits = [i for i, w in enumerate(windows) if re.search(rx, text[w["a"]:w["b"]], re.I)][:2]; out |= set(hits)
    return out
