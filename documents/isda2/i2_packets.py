"""A'' adjudication packets (Astra-signed design): one packet per PIPE/FULL disagreement. Answers shown as X/Y in per-item random order;
the arm mapping is written ONLY to adjudication/SEALED_mapping.json (CC does not open it until every verdict is filed). Contract texts
written to adjudication/texts/<cid>.txt. Prints counts only."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, random, hashlib

D = "adjudication_i2"; os.makedirs(f"{D}/texts", exist_ok=True); os.makedirs(f"{D}/packets", exist_ok=True)
from i2_common import Q
P = json.load(open("isda2_corpus241.json")); F = {f"I{i}": dict(text=p["text"]) for i, p in enumerate(P)}
FIELDS = {n: (q, None) for n, q, _ in Q}
R = [json.loads(l) for l in open("i2_test_raw.jsonl")]; cmp_ = [r for r in R if r["event"] == "compare"]
RUBRIC = """Rubric (fixed in advance; apply it exactly). The document is an ISDA Master Agreement and/or its Schedule.
1. Find and QUOTE the Schedule text (or the Master Agreement's opening) that answers the question.
2. The correct answer is what the document states for that election: Party A / Party B (legal names as defined); Agreement date (the
   'dated as of' date); Form (1992 or 2002 ISDA Master Agreement); Governing law; Termination Currency; Cross Default (which party it
   applies to); Threshold Amount (the first stated amount; any stated Threshold Amount is acceptable); Automatic Early Termination (which
   party it applies to); Additional Termination Events (whether any are specified); Credit Support Annex (whether one forms part of the
   agreement); Payment measure (Market Quotation / Loss / Close-out Amount as elected, or the form's default if the Schedule is silent
   is NOT assumed: answer only what is stated). If the document states none of it, NONE is correct.
3. Verdict, exactly one of: "X", "Y", "both_wrong", "both_acceptable" (same meaning, different wording, e.g. a defined short name and
   the full legal name of the same party)."""
rng = random.Random(20260931); sealed = {}; n = 0
for c in cmp_:
    open(f"{D}/texts/{c['cid']}.txt", "w").write(F[c["cid"]]["text"])
    for i, t in enumerate(FIELDS):
        if c["agree"][i]: continue
        pid = f"item{n:03d}"; n += 1
        p, f_ = c["pipe"][i] or "NONE", c["full"][i] or "NONE"
        if rng.random() < 0.5: X, Y, m = p, f_, {"X": "PIPE", "Y": "FULL"}
        else: X, Y, m = f_, p, {"X": "FULL", "Y": "PIPE"}
        sealed[pid] = dict(cid=c["cid"], type=t, **m)
        json.dump(dict(item=pid, contract_file=os.path.abspath(f"{D}/texts/{c['cid']}.txt"), question=FIELDS[t][0].split(" Answer")[0],
                       X=X, Y=Y, rubric=RUBRIC), open(f"{D}/packets/{pid}.json", "w"), indent=1)
json.dump(sealed, open(f"{D}/SEALED_mapping.json", "w"))
print(json.dumps(dict(packets=n, contracts_with_disagreement=len({v["cid"] for v in sealed.values()}),
                      sealed_sha=hashlib.sha256(open(f"{D}/SEALED_mapping.json", "rb").read()).hexdigest()[:12])))
