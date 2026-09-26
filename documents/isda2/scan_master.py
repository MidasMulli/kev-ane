"""Find GENUINE ISDA Master Agreements and Schedules (not documents that merely mention ISDA). Classifier (declared, heuristic):
MASTER  = the printed form: 'ISDA' + 'Master Agreement' in the first 3,000 chars AND the form's section structure
          ('Interpretation' + 'Obligations' + 'Events of Default and Termination Events' within the text);
SCHEDULE= 'Schedule to the' (or 'SCHEDULE') + 'Master Agreement' in the first 3,000 chars AND 'Part 1' + 'Termination Provisions'.
Writes isda2_pool.json with kind, length, source shard."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import lzma, json, re, hashlib, glob
out, seen, stats = [], set(), {}
for path in sorted(glob.glob("*.jsonl.xz")):
    n = m = s = 0
    with lzma.open(path, "rt") as f:
        for line in f:
            t = json.loads(line)["text"]; n += 1; head = t[:3000]
            if "Master Agreement" not in head and "MASTER AGREEMENT" not in head: continue
            low = t.lower(); kind = None
            if re.search(r"schedule\s+to\s+the", head, re.I) and "part 1" in low and "termination provisions" in low: kind = "schedule"
            elif "isda" in head.lower() and "interpretation" in low and "obligations" in low and "events of default and termination events" in low: kind = "master"
            if not kind: continue
            h = hashlib.sha256(t.encode()).hexdigest()[:16]
            if h in seen: continue
            seen.add(h); out.append(dict(sha=h, kind=kind, chars=len(t), shard=path, text=t)); m += kind == "master"; s += kind == "schedule"
    stats[path] = dict(docs=n, master=m, schedule=s); print(path, stats[path], flush=True)
json.dump(out, open("isda2_pool.json", "w"))
import collections; print("TOTAL", len(out), collections.Counter(x["kind"] for x in out))
