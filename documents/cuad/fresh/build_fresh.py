"""A'' fresh test set (Astra-signed): Pile of Law atticus_contracts validation shard 0. Drop any doc whose first 2,000 whitespace-normalized
chars match a CUAD contract's; keep docs whose first 3,000 chars contain 'agreement' and that are 8,000-32,000 Qwen tokens; seeded draw of 60."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import lzma, json, re, random, hashlib, sys
sys.path.insert(0, "..")
from cuad_common import load
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base")
norm = lambda s: re.sub(r"\s+", " ", s).strip()[:2000]
cuad = {norm(c["context"]) for c in load()[0]}
pool, dropped, scanned, lenfail, kwfail = [], 0, 0, 0, 0
with lzma.open("val0.jsonl.xz", "rt") as f:
    for line in f:
        d = json.loads(line); t = d["text"]; scanned += 1
        if norm(t) in cuad: dropped += 1; continue
        if "agreement" not in t[:3000].lower(): kwfail += 1; continue
        if not (20000 <= len(t) <= 200000): lenfail += 1; continue                 # char prefilter only; token rule applied next
        n = len(tok.encode(t))
        if 8000 <= n <= 32000: pool.append(dict(text=t, ntok=n, sha=hashlib.sha256(t.encode()).hexdigest()[:16]))
        else: lenfail += 1
pool = sorted({p["sha"]: p for p in pool}.values(), key=lambda p: p["sha"])          # dedupe identical texts, stable order
draw = random.Random(20260925).sample(pool, 60)
json.dump(dict(contracts=[dict(id=f"F{i:02d}_{p['sha']}", ntok=p["ntok"], text=p["text"]) for i, p in enumerate(draw)],
               stats=dict(scanned=scanned, cuad_dropped=dropped, keyword_fail=kwfail, length_fail=lenfail, pool=len(pool))), open("fresh60.json", "w"))
print(json.dumps(dict(scanned=scanned, cuad_dropped=dropped, keyword_fail=kwfail, length_fail=lenfail, pool=len(pool), drawn=60)))
