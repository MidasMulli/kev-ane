"""I2 shared (Astra-signed): the 12 questions, Schedule-portion extraction, ANCHORED evidence (heading paragraph, never answer-string
search), prompt/parse, normalization for the PIPE-vs-FULL comparison."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import re, json
Q = [("Party A", "Who is Party A? Answer with the legal name only.", None),
     ("Party B", "Who is Party B? Answer with the legal name only.", None),
     ("Agreement date", "What is the date of the Master Agreement (the 'dated as of' date)? Answer as M/D/YYYY.", None),
     ("Form", "Is this the 1992 or the 2002 ISDA Master Agreement? Answer 1992 or 2002.", None),
     ("Governing law", "Which law governs the agreement? Answer with the jurisdiction name only.", r"governing\s+law"),
     ("Termination Currency", "What is the Termination Currency? Answer with the currency.", r"termination\s+currency"),
     ("Cross Default", "To which party does Cross Default apply? Answer Party A, Party B, both, or neither.", r"cross[\s\-]+default"),
     ("Threshold Amount", "What is the Threshold Amount? Answer with the amount and currency (the first stated).", r"threshold\s+amount"),
     ("Automatic Early Termination", "To which party does Automatic Early Termination apply? Answer Party A, Party B, both, or neither.", r"automatic\s+early\s+termination"),
     ("Additional Termination Events", "Are any Additional Termination Events specified? Answer yes or no.", r"additional\s+termination\s+event"),
     ("Credit Support Annex", "Is a Credit Support Annex part of this agreement? Answer yes or no.", r"credit\s+support\s+(annex|document)"),
     ("Payment measure", "Which payment measure applies on early termination: Market Quotation, Loss, or Close-out Amount?", r"payments\s+on\s+early\s+termination")]
NAMES = [q[0] for q in Q]
def schedule_start(text):
    m = re.search(r"schedule\s*(\n|\s)*to\s+the", text, re.I)
    return m.start() if m else 0
def evidence(text):
    """Char span per question: the paragraph under the election's own heading inside the Schedule; Party A/B, date and Form use the
    Schedule's opening paragraph. Returns {name: (a, b) | None}."""
    s0 = schedule_start(text); sched = text[s0:]; ev = {}
    open_end = s0 + min(len(sched), 900)
    for name, _, rx in Q:
        if rx is None: ev[name] = (s0, open_end); continue
        m = re.search(rx, sched, re.I)
        ev[name] = (s0 + m.start(), min(len(text), s0 + m.start() + 700)) if m else None
    return ev
def prompt(context=None, evidence_texts=None, nonce=""):
    body = f"Document:\n{context}\n\n" if context is not None else "Excerpts from a document:\n" + "\n...\n".join(evidence_texts) + "\n\n"
    q = "\n".join(f"Q{i + 1}: {qq}" for i, (_, qq, _) in enumerate(Q))
    return f"{nonce}\n{body}Questions:\n{q}\n\nAnswer each question on its own line as 'Q<n>: <answer>', nothing else. If the document does not state it, answer 'Q<n>: NONE'."
def parse(text):
    out = {}
    for line in text.splitlines():
        m = re.match(r"\s*\**Q(\d+)\**\s*[:.)-]\s*(.*)", line)
        if m and 1 <= int(m.group(1)) <= len(Q) and int(m.group(1)) not in out: out[int(m.group(1))] = m.group(2).strip().strip("*").strip()
    return [None if (out.get(i + 1) or "").upper().startswith("NONE") else out.get(i + 1) for i in range(len(Q))]
def norm(name, a):
    if not a: return None
    s = a.strip().lower().rstrip(".")
    if name in ("Party A", "Party B"):
        s = re.sub(r"[.,()\"]", " ", s); s = re.sub(r"\b(inc|llc|ltd|limited|plc|n a|na|ag|sa|lp|l p|corporation|corp|company|co|the|bank)\b", " ", s); return " ".join(s.split())
    if name == "Agreement date":
        m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s); return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else s
    if name == "Form": return "2002" if "2002" in s else ("1992" if "1992" in s else s)
    if name in ("Cross Default", "Automatic Early Termination"):
        if "both" in s: return "both"
        if "neither" in s or s in ("no", "not applicable", "none"): return "neither"
        a_, b_ = "party a" in s, "party b" in s; return "both" if a_ and b_ else ("A" if a_ else ("B" if b_ else s))
    if name in ("Additional Termination Events", "Credit Support Annex"): return "yes" if s.startswith("yes") else ("no" if s.startswith("no") else s)
    if name == "Payment measure":
        for k in ("market quotation", "loss", "close-out amount"):
            if k in s: return k
        return s
    if name == "Threshold Amount":
        num = re.findall(r"\d[\d,]*(?:\.\d+)?", s); mult = 1e6 if "million" in s else 1; return round(float(num[0].replace(",", "")) * mult) if num else s
    return s
