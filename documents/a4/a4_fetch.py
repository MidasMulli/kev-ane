"""A4 (Astra-signed v2) fetch: papers with >= 3 PwC results, seeded order (20260935), arXiv e-print LaTeX, <= 1 request / 3 s.
Writes a4_raw.jsonl {arxiv, ok, why, tex}. Resumable. Filtering (tokens, anchoring) is a4_corpus.py; nothing here sees gold."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import io, json, os, random, re, tarfile, gzip, time, urllib.request, sys
import pyarrow.parquet as pq
N = int(sys.argv[1]) if len(sys.argv) > 1 else 900
R = pq.read_table("pwc_results_arxiv.parquet").to_pylist()
cnt = {}
for r in R: cnt[r["arxiv"]] = cnt.get(r["arxiv"], 0) + 1
ids = sorted(a for a, c in cnt.items() if c >= 3); random.Random(20260935).shuffle(ids)
UA = {"User-Agent": "jev-research (arXiv source fetch, 1 req/3s)", "Accept": "*/*"}
def strip_comments(s): return re.sub(r"(?<!\\)%.*", "", s)
def flatten(files):
    tex = {k: v for k, v in files.items() if k.endswith(".tex")}
    if not tex: return None
    mains = [k for k, v in tex.items() if "\\documentclass" in v and "\\begin{document}" in v]
    if not mains: return "\n".join(strip_comments(tex[k]) for k in sorted(tex))
    def expand(name, depth=0):
        s = strip_comments(tex.get(name, ""))
        if depth > 6: return s
        def rep(m):
            f = m.group(2).strip(); c = [f, f + ".tex"] + [k for k in tex if k.endswith("/" + f) or k.endswith("/" + f + ".tex")]
            for k in c:
                if k in tex: return expand(k, depth + 1)
            return ""
        return re.sub(r"\\(input|include)\{([^}]+)\}", rep, s)
    return expand(max(mains, key=lambda k: len(tex[k])))
def fetch(a):
    import subprocess
    for attempt in (0, 1):
        p = subprocess.run(["curl", "-sL", "--max-time", "180", "--max-filesize", "40000000", "-A", UA["User-Agent"], "-w", "%{http_code}", "-o", "/tmp/a4_src.bin", f"https://arxiv.org/src/{a}"], capture_output=True, text=True)
        if p.returncode == 63: return "TOO_BIG"
        if p.returncode == 0 and p.stdout.strip() == "200": break
        if attempt: raise RuntimeError(f"curl rc={p.returncode} http={p.stdout.strip()}")
        time.sleep(3)
    b = open("/tmp/a4_src.bin", "rb").read()
    try:
        t = tarfile.open(fileobj=io.BytesIO(b)); files = {}
        for m in t.getmembers():
            if m.isfile() and m.name.endswith(".tex") and m.size < 5_000_000: files[os.path.normpath(m.name)] = t.extractfile(m).read().decode("utf-8", "replace")
        return flatten(files)
    except tarfile.ReadError:
        try: s = gzip.decompress(b).decode("utf-8", "replace")
        except OSError: return None
        return strip_comments(s) if "\\begin{document}" in s else None
done = {json.loads(l)["arxiv"] for l in open("a4_raw.jsonl")} if os.path.exists("a4_raw.jsonl") else set()
out = open("a4_raw.jsonl", "a")
for a in ids[:N]:
    if a in done: continue
    t0 = time.monotonic()
    try:
        tex = fetch(a)
        rec = dict(arxiv=a, ok=False, why="too_big", tex=None) if tex == "TOO_BIG" else dict(arxiv=a, ok=bool(tex), why=None if tex else "no_latex", tex=tex)
    except Exception as e: rec = dict(arxiv=a, ok=False, why=repr(e)[:200], tex=None)
    out.write(json.dumps(rec) + "\n"); out.flush()
    time.sleep(max(0, 3.0 - (time.monotonic() - t0)))
print("FETCH_DONE")
