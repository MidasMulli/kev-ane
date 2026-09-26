"""A5 corpus (Astra-signed): papers from the fetched HF snapshot EXCLUDING every A4/A4b paper; keep iff \\begin{abstract} and 8k-32k Qwen
tokens; seeded draw 20260950 of 241 in walk order -> TRAIN 160 / DEV 25 / TEST 56 (split fixed before labelling)."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, itertools, random
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base")
excl = {c["arxiv"] for c in json.load(open("../a4/a4_corpus.json"))} | {c["arxiv"] for c in json.load(open("../a4/a4b_fresh.json"))} | \
       {c["arxiv"] for f in ("../a4/a4_corpus_v1_VOID.json", "../a4/a4_corpus_v3_VOID.json") for c in json.load(open(f))}
cand = []
for l in itertools.chain(open("../a4/a4_raw_hf.jsonl"), open("../a4/a4_raw_hf2.jsonl"), open("../a4/a4_raw_hf3.jsonl")):
    d = json.loads(l)
    if d["ok"] and d["arxiv"] not in excl and "\\begin{abstract}" in d["tex"]: cand.append(d)
rng = random.Random(20260950); rng.shuffle(cand); keep = []
for d in cand:
    n = len(tok(d["tex"], add_special_tokens=False)["input_ids"])
    if 8000 <= n <= 32000: keep.append(dict(arxiv=d["arxiv"], text=d["tex"], tokens=n, license=d.get("license")))
    if len(keep) == 241: break
assert len(keep) == 241 and not ({k["arxiv"] for k in keep} & excl)
json.dump(keep, open("a5_corpus.json", "w")); json.dump(dict(train=list(range(160)), dev=list(range(160, 185)), test=list(range(185, 241))), open("a5_split.json", "w"))
print(json.dumps(dict(candidates=len(cand), kept=len(keep), excluded=len(excl))))
