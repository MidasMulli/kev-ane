"""A'' adjudication packets (Astra-signed design): one packet per PIPE/FULL disagreement. Answers shown as X/Y in per-item random order;
the arm mapping is written ONLY to adjudication/SEALED_mapping.json (CC does not open it until every verdict is filed). Contract texts
written to adjudication/texts/<cid>.txt. Prints counts only."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, random, hashlib
from cuad_common import QUESTION, VALUE_TYPES
D = "adjudication3"; os.makedirs(f"{D}/texts", exist_ok=True); os.makedirs(f"{D}/packets", exist_ok=True)
F = {f["id"]: f for f in json.load(open("fresh/fresh200.json"))["contracts"]}
R = [json.loads(l) for l in open("a3p_raw.jsonl")]; cmp_ = [r for r in R if r["event"] == "compare"]
RUBRIC = """Rubric (fixed in advance; apply it exactly):
1. Find and QUOTE the sentence(s) in the document that answer the question.
2. The correct answer is:
   - Governing law = the jurisdiction named in the governing-law clause.
   - Agreement date, in this order: (a) a date the document states it is made, entered into, or dated as of; (b) otherwise its stated
     effective date, including a defined "Effective Date" that resolves to a calendar date anywhere in the document, and a plan's or
     instrument's "became/becomes effective" date; (c) otherwise the latest party signature date in the signature block; (d) otherwise
     NONE. A date given only as month and year (or year) is answered at that precision and matches only at that precision.
   - Renewal term = the length of each renewal period.
   - Non-renewal notice = the advance notice a party must give to prevent the agreement from renewing.
   If the document states none of it, NONE is the correct answer.
3. Verdict, exactly one of: "X" (only X correct), "Y" (only Y correct), "both_wrong", "both_acceptable" (same jurisdiction, the same
   date at the precision stated, or the same duration with years = 12 months)."""
rng = random.Random(20260928); sealed = {}; n = 0
for c in cmp_:
    open(f"{D}/texts/{c['cid']}.txt", "w").write(F[c["cid"]]["text"])
    for i, t in enumerate(VALUE_TYPES):
        if c["agree"][i]: continue
        pid = f"item{n:03d}"; n += 1
        p, f_ = c["pipe"][i] or "NONE", c["full"][i] or "NONE"
        if rng.random() < 0.5: X, Y, m = p, f_, {"X": "PIPE", "Y": "FULL"}
        else: X, Y, m = f_, p, {"X": "FULL", "Y": "PIPE"}
        sealed[pid] = dict(cid=c["cid"], type=t, **m)
        json.dump(dict(item=pid, contract_file=os.path.abspath(f"{D}/texts/{c['cid']}.txt"), question=QUESTION[t].split(" Answer")[0],
                       X=X, Y=Y, rubric=RUBRIC), open(f"{D}/packets/{pid}.json", "w"), indent=1)
json.dump(sealed, open(f"{D}/SEALED_mapping.json", "w"))
print(json.dumps(dict(packets=n, contracts_with_disagreement=len({v["cid"] for v in sealed.values()}),
                      sealed_sha=hashlib.sha256(open(f"{D}/SEALED_mapping.json", "rb").read()).hexdigest()[:12])))
