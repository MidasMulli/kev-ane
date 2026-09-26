"""A4 TEST (Astra-signed v2): 90 fresh TEST papers, up to 3 anchored questions each (a4_test_questions.json).
(1) G-SWAP: bind CUA -> IS3 -> AX -> CUA on one fixed window: CUA bitwise identical on return, three distinct hidden states, base md5 unchanged.
(2) Per paper: AX map once (question-blind), policy = top-6 RESULT windows + immediate neighbours, deduped, document order.
Arms (order rotated per paper): PIPE (AX excerpts), FULL (whole LaTeX if <= 32k doc tokens, else infeasible), BM25 (question words as
query over the same windows, top-6 + neighbours per question), NONE (questions only). One request per paper per arm, all its questions listed. 27B cold, reasoning off, T=0.
BM25 is run per question (it needs the question), so a BM25 request carries the union of its questions' picks, same per-question budget."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, re, sys, math, random, time, hashlib, subprocess, urllib.request, numpy as np
sys.path.insert(0, ROOT + "/cuad"); os.chdir(ROOT + "/a4"); sys.path.insert(0, ROOT + "/a4")
from ane_run import Ane, export_and_pack, sh, MD, TRUST
from a4_common import toks
C = json.load(open("a4_corpus.json")); S = json.load(open("a4_split.json")); QS = json.load(open("a4_test_questions.json"))
from transformers import AutoTokenizer
log = open("a4_test_raw.jsonl", "w")
def emit(**r): print(json.dumps(r)[:300], flush=True); log.write(json.dumps(r) + "\n"); log.flush()
g0 = sh(GATE0).splitlines()[-1]; assert g0.startswith("gate=GREEN"), g0
sent = subprocess.Popen([SENTINEL, str(os.getpid()), os.path.abspath("a4_test_red_sentinel.log")]); time.sleep(3); assert sent.poll() is None
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base"); T_, STRIDE_ = 256, 224
def windows(text):
    enc = tok(text, return_offsets_mapping=True, add_special_tokens=False); ids, offs = enc["input_ids"], enc["offset_mapping"]; out = []
    for s0 in range(0, max(1, len(ids) - (T_ - STRIDE_)), STRIDE_):
        w = ids[s0:s0 + T_]; out.append(dict(ids=w, a=offs[s0][0], b=offs[s0 + len(w) - 1][1]))
        if s0 + T_ >= len(ids): break
    return out
def policy(order, n):
    top = [int(j) for j in order[:6]]; return sorted({k for j in top for k in (j - 1, j, j + 1) if 0 <= k < n})
def bm25_order(ws_text, q, k1=1.5, b=0.75):
    docs = [re.findall(r"[a-z0-9]+", t.lower()) for t in ws_text]; N = len(docs); avg = sum(map(len, docs)) / N
    df = {}
    for d in docs:
        for w in set(d): df[w] = df.get(w, 0) + 1
    qt = re.findall(r"[a-z0-9]+", q.lower()); sc = []
    for d in docs:
        tf = {}
        for w in d: tf[w] = tf.get(w, 0) + 1
        sc.append(sum(math.log(1 + (N - df.get(w, 0) + 0.5) / (df.get(w, 0) + 0.5)) * tf.get(w, 0) * (k1 + 1) / (tf.get(w, 0) + k1 * (1 - b + b * len(d) / avg)) for w in qt))
    return np.argsort(-np.array(sc), kind="stable")
def qtext(q): return f"In this paper, what {q['metric']} does {q['model']} achieve on {q['dataset']}? Answer with the number only."
def prompt(qs, context=None, excerpts=None, nonce=""):
    body = (f"Paper (LaTeX source):\n{context}\n\n" if context is not None else ("Excerpts from a paper's LaTeX source:\n" + "\n...\n".join(excerpts) + "\n\n" if excerpts is not None else ""))
    ql = "\n".join(f"Q{i + 1}: {qtext(q)}" for i, q in enumerate(qs))
    return f"{nonce}\n{body}Questions:\n{ql}\n\nAnswer each question on its own line as 'Q<n>: <answer>', nothing else. If the text does not state it, answer 'Q<n>: NONE'."
def parse(text, n):
    out = {}
    for line in text.splitlines():
        m = re.match(r"\s*\**Q(\d+)\**\s*[:.)-]\s*(.*)", line)
        if m and 1 <= int(m.group(1)) <= n and int(m.group(1)) not in out: out[int(m.group(1))] = m.group(2).strip()
    return [out.get(i + 1) for i in range(n)]
def correct(ans, gold):
    if not ans: return False
    g = gold.replace("%", "").strip(); m = re.search(r"-?\d+(?:\.\d+)?", ans.replace(",", ""))
    if not m: return False
    a = m.group(0)
    if a == g: return True
    try: return abs(float(a) - float(g)) <= 1e-3 * max(abs(float(g)), 1e-9)
    except ValueError: return False
def ask(text):
    body = {"model": LLM_MODEL, "stream": False, "temperature": 0, "reasoning_effort": "none", "max_tokens": 120, "messages": [{"role": "user", "content": text}]}
    req = urllib.request.Request(LLM_URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.monotonic(); j = json.load(urllib.request.urlopen(req, timeout=1800)); u = j["usage"]
    assert (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) == 0
    return j["choices"][0]["message"]["content"], u["prompt_tokens"], time.monotonic() - t0
head, amd5 = export_and_pack("a4_best.npz", "AX"); md5_0 = sh(f"sudo -n md5 -q {MD}/weights/weight.bin")
ane = Ane("AX", head)
w0 = windows(C[S["test"][0]]["text"])[1]["ids"]
def hs_sha(tag):
    r = ane.cmd(f"BIND {TRUST}/{tag}.bin"); assert r.startswith("BOUND"), r; ane.window(w0); return hashlib.sha256(open(f"{ane.IN}/hs.f16", "rb").read()).hexdigest()[:16], float(r.split()[1])
s1 = hs_sha("CUA"); s2 = hs_sha("IS3"); s3 = hs_sha("AX"); s4 = hs_sha("CUA")
g_swap = s1[0] == s4[0] and len({s1[0], s2[0], s3[0]}) == 3 and sh(f"sudo -n md5 -q {MD}/weights/weight.bin") == md5_0
emit(event="swap", cua=s1, is3=s2, ax=s3, cua_again=s4, G_SWAP=g_swap, adapter_md5=amd5)
ane.cmd(f"BIND {TRUST}/AX.bin")
byd = {}
for q in QS: byd.setdefault(q["doc"], []).append(q)
ARMS = ["PIPE", "FULL", "BM25", "NONE"]
for n, i in enumerate(S["test"]):
    qs = byd[i]; text = C[i]["text"]; ntok = C[i]["tokens"]
    t0 = time.monotonic(); ws = windows(text); sc = np.stack([ane.window(w["ids"])[0] for w in ws])[:, 0]
    pick = policy(np.argsort(-sc, kind="stable"), len(ws)); ane_s = time.monotonic() - t0
    wt = [text[w["a"]:w["b"]] for w in ws]
    bpick = sorted({k for q in qs for k in policy(bm25_order(wt, qtext(q)), len(ws))})
    spans = [C[i]["results"][q["ridx"]]["span"] for q in qs]
    cover = lambda P_: [any(ws[j]["a"] < e[1] and ws[j]["b"] > e[0] for j in P_) for e in spans]
    res = {}; order = ARMS[n % 4:] + ARMS[:n % 4]
    for arm in order:
        if arm == "FULL" and ntok > 32000: res[arm] = None; continue
        kw = dict(PIPE=dict(excerpts=[wt[j] for j in pick]), FULL=dict(context=text), BM25=dict(excerpts=[wt[j] for j in bpick]), NONE={})[arm]
        out, pt, dt = ask(prompt(qs, nonce=f"[req {random.random():.12f}]", **kw)); preds = parse(out, len(qs))
        res[arm] = dict(preds=preds, ok=[correct(p, q["value"]) for p, q in zip(preds, qs)], seconds=dt + (ane_s if arm == "PIPE" else 0), prompt_tokens=pt, raw=out)
    emit(event="paper", doc=i, arxiv=C[i]["arxiv"], doc_tokens=ntok, windows=len(ws), pipe_windows=len(pick), bm25_windows=len(bpick), ane_s=ane_s,
         gold=[q["value"] for q in qs], questions=[qtext(q) for q in qs], pipe_cover=cover(pick), bm25_cover=cover(bpick), arms=res)
ane.close()
emit(event="A4_RUN_DONE", G_SWAP=g_swap, base_md5_unchanged=sh(f"sudo -n md5 -q {MD}/weights/weight.bin") == md5_0)
sent.terminate()
