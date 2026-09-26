"""A''' test set (PREREG_2026-09-24_A3prime_harden.md): same shard and filter as A''; universal exclusion vs all 510 CUAD + the 60 A''
contracts (exact hash or 6-gram Jaccard > 0.3 on the first 1,500 words); seeded draw (20260927) of 200."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import lzma, json, re, random, hashlib, sys
sys.path.insert(0, "..")
from cuad_common import load
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base")
def sh(t):
    w = re.findall(r"[a-z0-9]+", t.lower())[:1500]; return {" ".join(w[i:i+6]) for i in range(len(w) - 5)}
EX = [c["context"] for c in load()[0]] + [f["text"] for f in json.load(open("fresh60.json"))["contracts"]]
EXH = {hashlib.sha256(t.encode()).hexdigest() for t in EX}; EXS = [sh(t) for t in EX]
pool, scanned = [], 0
with lzma.open("val0.jsonl.xz", "rt") as f:
    for line in f:
        d = json.loads(line); t = d["text"]; scanned += 1
        if "agreement" not in t[:3000].lower() or not (20000 <= len(t) <= 200000): continue
        n = len(tok.encode(t))
        if 8000 <= n <= 32000: pool.append(dict(text=t, ntok=n, sha=hashlib.sha256(t.encode()).hexdigest()))
pool = sorted({p["sha"]: p for p in pool}.values(), key=lambda p: p["sha"])
rng = random.Random(20260927); order = rng.sample(pool, len(pool)); keep, dropped = [], 0
for p in order:                                   # walk the seeded order; exclusion checked per candidate until 200 are kept
    if p["sha"] in EXH: dropped += 1; continue
    s = sh(p["text"])
    if any(len(s & e) / max(1, len(s | e)) > 0.3 for e in EXS): dropped += 1; continue
    keep.append(p)
    if len(keep) == 200: break
json.dump(dict(contracts=[dict(id=f"H{i:03d}_{p['sha'][:16]}", ntok=p["ntok"], text=p["text"]) for i, p in enumerate(keep)],
               stats=dict(scanned=scanned, pool=len(pool), excluded_while_drawing=dropped)), open("fresh200.json", "w"))
print(json.dumps(dict(scanned=scanned, pool=len(pool), excluded_while_drawing=dropped, kept=len(keep))))
