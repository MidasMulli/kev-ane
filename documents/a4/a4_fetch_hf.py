"""A4 fetch, source = secemp9/arxiv-complete `paper_text` (snapshot 2026-09-05; one assembled TeX per paper: main file with \\input/\\include
expanded, else path-order concatenation, .bbl appended). Replaces live arxiv.org/src (1 req/3 s). SAME seeded candidate order (20260935)
as a4_fetch.py; comments stripped with the same strip_comments. Reads only the Parquet row group holding each paper (footer stats).
Writes a4_raw_hf.jsonl in seeded order {arxiv, ok, why, tex, license, resolution}."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, random, re, sys, time
from concurrent.futures import ThreadPoolExecutor
import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem
N = int(sys.argv[1]) if len(sys.argv) > 1 else 2500
START = int(sys.argv[2]) if len(sys.argv) > 2 else 0
OUT = sys.argv[3] if len(sys.argv) > 3 else "a4_raw_hf.jsonl"
R = pq.read_table("pwc_results_arxiv.parquet").to_pylist(); cnt = {}
for r in R: cnt[r["arxiv"]] = cnt.get(r["arxiv"], 0) + 1
ids = sorted(a for a, c in cnt.items() if c >= 3); random.Random(20260935).shuffle(ids); ids = ids[START:N]
IDX = json.load(open("arxc_paper_text_index.json")); fs = HfFileSystem()
def strip_comments(s): return re.sub(r"(?<!\\)%.*", "", s)
groups = {}
for a in ids:
    h = [x for x in IDX if x[0] <= a <= x[1]]
    groups.setdefault((h[0][2], h[0][3]) if h else None, []).append(a)
def load(k):
    if k is None: return {}
    for attempt in range(3):
        try:
            tb = pq.ParquetFile(fs.open(k[0])).read_row_group(k[1], columns=["paper_id", "text", "license", "resolution"]); break
        except Exception:
            if attempt == 2: raise
            time.sleep(5)
    want = set(groups[k]); out = {}
    for pid, t, lic, res in zip(*(tb.column(c).to_pylist() for c in ("paper_id", "text", "license", "resolution"))):
        if pid in want: out[pid] = (t, lic, res)
    return out
got = {}; t0 = time.time()
with ThreadPoolExecutor(8) as ex:
    for n, d in enumerate(ex.map(load, list(groups))):
        got.update(d)
        if n % 100 == 0: print(n, len(groups), round(time.time() - t0), flush=True)
with open(OUT, "w") as f:
    for a in ids:
        if a in got and got[a][0] and "\\begin{document}" in got[a][0]:
            f.write(json.dumps(dict(arxiv=a, ok=True, why=None, tex=strip_comments(got[a][0]), license=got[a][1], resolution=got[a][2])) + "\n")
        else: f.write(json.dumps(dict(arxiv=a, ok=False, why="not_in_paper_text" if a not in got else "no_document", tex=None)) + "\n")
print("FETCH_DONE", len(ids), sum(1 for a in ids if a in got), round(time.time() - t0))
