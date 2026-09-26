"""Contract Review live demo (plan step 2, Astra-signed order). PRIVATE, research config. LAN-visible on port 8733 at operator request
(2026-09-24); runs are REFUSED while any experiment script is running (so the demo cannot perturb a measurement).
Drives the MEASURED stack live: resident Rev 5 base in kevd with adapter CUA -> 41-type contract map on the ANE (T=256 windows) ->
top-2 windows per asked value type -> Splash 27B answers from ~1k tokens. Also: pipeline mode (ANE maps the next contract while the
27B answers, B2) and an adapter swap check (C). No new claims: every number is live-measured or cited to a RESULT file.
Run: {sys.executable} demo_server.py   then open http://127.0.0.1:8733"""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, queue, random, subprocess, sys, threading, time, urllib.request, hashlib
import numpy as np
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
HERE = os.path.dirname(os.path.abspath(__file__)); CUAD = ROOT + "/cuad"; os.chdir(CUAD); sys.path.insert(0, CUAD)
from transformers import AutoTokenizer
from cuad_common import load, items, prompt, parse_lines, correct, PRED_PARSE, VALUE_TYPES
from cuad_windows import windows, overlaps
from ane_run import Ane, sh, MD, TRUST

S = json.load(open("splits.json")); TO = S["type_order"]
try: C = {c["id"]: c for c in load()[0]}
except FileNotFoundError: C = {}   # CUAD_v1 not downloaded: the contract list is empty, drop-in still works
LONG = [c for c in json.load(open("along_set.json"))["gated"] if c in C]
POOL = [c for c in S["test"] + LONG if c in C and items(C[c])]
FRESH = json.load(open("fresh/fresh60.json"))["contracts"] if os.path.exists("fresh/fresh60.json") else []; A2P = {r["cid"]: r for r in (json.loads(l) for l in open("a2p_raw.jsonl")) if r["event"] == "compare"}
for f in FRESH:
    C[f["id"]] = dict(id=f["id"], context=f["text"], spans={t: [] for t in TO}, gold={t: "" for t in VALUE_TYPES}); S["ntok"][f["id"]] = f["ntok"]
POOL = POOL + [f["id"] for f in FRESH]
K = 3   # frozen A'' policy P2 (top-3 windows per asked value type)
def asked(cid): return [(t, None) for t in VALUE_TYPES] if cid.startswith("F") and cid in A2P else items(C[cid])
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base")
head = dict(np.load("run_CUA/head.npz")); TAU = json.load(open("a1_selection.json"))["tau"]
BASE_MD5 = sh(f"sudo -n md5 -q {MD}/weights/weight.bin")
import ane_run as _AR
class AneMulti(Ane):
    """One PRE-BOUND instance per adapter (kevd_multi): each adapter is LOADed once at startup on the one resident base; a swap is
    USE, a pointer switch. Nothing is discarded or rebuilt after startup (CHARACTERIZATION_2026-09-26_swap_battery.md)."""
    KEVD_MULTI = KEVD_MULTI   # from _kevdoc
    def __init__(s, tag, head, tags):
        s.emb = _AR.load_base(_AR.Trunk().eval()); s.h = head; s.IN = f"/tmp/cuad_kevd_in_{os.getpid()}"; os.makedirs(s.IN, exist_ok=True); os.chmod(s.IN, 0o777)
        s.p = subprocess.Popen(["sudo", "-n", s.KEVD_MULTI, MD], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        assert s.p.stdout.readline().strip() == "READY"
        s.loads = {}
        for t in tags:
            r = s.cmd(f"LOAD {t} {TRUST}/{t}.bin"); assert r.startswith("LOADED"), r; s.loads[t] = float(r.split()[1])
        s.bind = s.switch(tag)
    def switch(s, tag):
        r = s.cmd(f"USE {tag}"); assert r.startswith("USED"), r; return f"SWITCHED {r.split()[1]}"
ane = AneMulti("CUA", head, ["CUA", "IS3", "AX2", "W", "D"]); ALOCK = threading.Lock(); CURRENT = ["CUA"]
print("demo: pre-bound instances loaded once", ane.loads, flush=True)
print("demo: kevd bound", ane.bind, "base md5", BASE_MD5[:12], flush=True)
CITED = {
    "A3 (96 contracts, median 6.9k tokens)": {"PIPE_s": 3.51, "FULL_s": 12.45, "PIPE_acc": 0.936, "FULL_acc": 0.975, "file": "RESULT_2026-09-24_A3_cuad_final.md", "verdict": "NOT PASS (accuracy); latency PASS"},
    "A-long (31 unseen contracts, 33k-82k tokens)": {"PIPE_s": 8.65, "FULL_s": 90.07, "PIPE_acc": 0.967, "FULL_acc": 1.0, "file": "RESULT_2026-09-24_Along_cuad_long_contracts.md", "verdict": "NOT PASS (accuracy); latency PASS, 10.4x"},
    "A'' (60 FRESH public contracts, top-3)": {"PIPE_s": 7.40, "FULL_s": 26.93, "PIPE_acc": "-0.021 vs full [-0.046, 0]", "FULL_acc": "ref", "file": "RESULT_2026-09-24_A2prime_close_the_gap.md", "verdict": "PASS (borderline, adjudication-sensitive; kappa 0.323)"},
    "B2 pipelining": {"gain": "+46% [44, 49]", "file": "RESULT_2026-09-24_B2_pipelined_contract_review.md"},
    "B1b": {"finding": "GPU cost tracks ANE weight re-reads (+0.247)", "file": "RESULT_2026-09-24_B1b_dispatch_vs_weights.md"},
    "C swaps": {"finding": "3-adapter rotation under decode: +0.021 [0.001, 0.046] retention cost; bind 74.7 -> 81.9 ms", "file": "RESULT_2026-09-24_C_multi_adapter_under_load.md"},
}
SHORT = {"Governing Law": "Governing law", "Agreement Date": "Agreement date", "Renewal Term": "Renewal term", "Notice Period To Terminate Renewal": "Non-renewal notice"}

def ensure_cua():
    if CURRENT[0] != "CUA":
        r = ane.switch("CUA"); CURRENT[0] = "CUA"; return r
    return None

def ane_map(cid, emit, tag):
    c = C[cid]; its = asked(cid); qs = [t for t, _ in its]
    t0 = time.monotonic(); ws = windows(c, tok, TO)
    emit(dict(ev="map_start", cid=cid, tag=tag, n_windows=len(ws), n_chars=len(c["context"]), tokenize_s=time.monotonic() - t0,
              questions=[SHORT[t] for t in qs]))
    sc = []
    with ALOCK:
        ensure_cua()
        for i, w in enumerate(ws):
            p, ms = ane.window(w["ids"]); sc.append(p)
            emit(dict(ev="window", cid=cid, tag=tag, i=i, ms=ms, a=w["a"], b=w["b"], s=[round(float(x), 3) for x in p]))
    sc = np.stack(sc); sel = {}; chosen = set()
    for t in qs:
        top = [int(j) for j in np.argsort(-sc[:, TO.index(t)])[:K]]; sel[t] = top; chosen |= set(top)
    ev = [c["context"][ws[j]["a"]:ws[j]["b"]] for j in sorted(chosen)]
    hit = {SHORT[t]: any(overlaps(c["spans"][t], ws[j]["a"], ws[j]["b"]) for j in sel[t]) for t in qs}
    present = {TO[k]: bool(sc[:, k].max() >= TAU[TO[k]]) for k in range(41)}
    emit(dict(ev="map_done", cid=cid, tag=tag, ane_s=time.monotonic() - t0, selected={SHORT[t]: v for t, v in sel.items()}, hit=hit,
              present_count=sum(present.values()), evidence_chars=sum(len(e) for e in ev),
              evidence=[dict(i=j, text=c['context'][ws[j]['a']:ws[j]['b']]) for j in sorted(chosen)]))
    return its, ev, time.monotonic() - t0

def ask(cid, its, ev, emit, tag):
    qs = [t for t, _ in its]; text = prompt(qs, evidence=ev, nonce=f"[demo {random.random():.12f}]")
    body = {"model": LLM_MODEL, "stream": True, "stream_options": {"include_usage": True}, "temperature": 0,
            "reasoning_effort": "none", "max_tokens": 200, "messages": [{"role": "user", "content": text}]}
    req = urllib.request.Request(LLM_URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.monotonic(); out = ""; usage = None; first = None
    emit(dict(ev="llm_start", cid=cid, tag=tag))
    with urllib.request.urlopen(req, timeout=900) as resp:
        for raw in resp:
            line = raw.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]": continue
            j = json.loads(line[5:])
            if j.get("usage"): usage = j["usage"]
            ch = j.get("choices") or []
            d = ch[0].get("delta", {}).get("content") if ch else None
            if d:
                if first is None: first = time.monotonic() - t0
                out += d; emit(dict(ev="llm_token", cid=cid, tag=tag, t=d))
    preds = parse_lines(out, len(qs)); c = C[cid]
    ans = [dict(q=SHORT[t], pred=p, gold=(c["gold"][t] or "no gold (fresh contract)"), ok=(None if g is None else bool(correct(t, g, PRED_PARSE[t](p))))) for (t, g), p in zip(its, preds)]
    llm_s = time.monotonic() - t0
    emit(dict(ev="llm_done", cid=cid, tag=tag, llm_s=llm_s, first_token_s=first, prompt_tokens=(usage or {}).get("prompt_tokens"), answers=ans))
    return llm_s

def run_one(cid, emit):
    its, ev, a = ane_map(cid, emit, "solo"); l = ask(cid, its, ev, emit, "solo")
    emit(dict(ev="done", cid=cid, total_s=a + l, ane_s=a, llm_s=l, full_tokens=S["ntok"].get(cid)))

def run_pipeline(cids, emit):
    q = queue.Queue(); t0 = time.monotonic()
    def producer():
        for cid in cids: its, ev, a = ane_map(cid, emit, "pipe"); q.put((cid, its, ev))
    th = threading.Thread(target=producer); th.start()
    for _ in cids:
        cid, its, ev = q.get(); ask(cid, its, ev, emit, "pipe")
    th.join(); emit(dict(ev="pipe_done", wall_s=time.monotonic() - t0))

def swap_check(emit):
    w = windows(C[POOL[0]], tok, TO)[2]
    with ALOCK:
        res = []
        for a in ("CUA", "W", "D", "CUA"):
            r = ane.switch(a); CURRENT[0] = a; ms = float(r.split()[1])
            ane.window(w["ids"]); h = hashlib.sha256(open(f"{ane.IN}/hs.f16", "rb").read()).hexdigest()[:12]
            res.append(dict(adapter=a, bind_ms=ms, hs_sha=h)); emit(dict(ev="swap", **res[-1]))
        ensure_cua()
    emit(dict(ev="swap_done", roundtrip_identical=res[0]["hs_sha"] == res[-1]["hs_sha"], distinct=len({r["hs_sha"] for r in res[:3]}) == 3,
              base_md5_unchanged=sh(f"sudo -n md5 -q {MD}/weights/weight.bin") == BASE_MD5))

EXPERIMENTS = "a3p_run.py|a2p_run.py|along_run.py|a3_final.py|b2_run.py|c_run.py|b1_run.py|b1b_run.py|a0_admit.py|a1_train.py|i2_train.py|i2_test.py|i1_test.py|vf_train.py|vf_eval.py|t1_train.py|t1_eval.py|gk_eval.py|g1b_eval.py|i3_train.py|i3_test.py|a4_train.py|a4_test.py|a4b_prep.py|a4b_test.py|a5_train.py|a5_test.py"
def experiment_running():
    return subprocess.run(["pgrep", "-f", EXPERIMENTS], capture_output=True).returncode == 0

import re as _re, base64, tempfile
sys.path.insert(0, ROOT + "/isda2"); sys.path.insert(0, ROOT + "/isda3")
from i3_common import sidecar as isda_sidecar
from i2_common import Q as ISDA_Q, prompt as isda_prompt, parse as isda_parse
from cuad_common import QUESTION as C_QUESTION
sys.path.insert(0, ROOT + "/a5")
from a5_common import Q as AX_Q, prompt as ax_prompt, parse as ax_parse, sidecar as ax_sidecar
def is_arxiv(text):
    return "\\begin{abstract}" in text or "\\documentclass" in text[:5000]
def is_isda(text):
    head = text[:3000]
    if "Master Agreement" not in head and "MASTER AGREEMENT" not in head: return False
    low = text.lower()
    return bool((_re.search(r"schedule\s+to\s+the", head, _re.I) and "part 1" in low and "termination provisions" in low) or
                ("isda" in head.lower() and "interpretation" in low and "obligations" in low and "events of default and termination events" in low))
_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
def _answer_patterns(ans):
    """Search patterns for an answer's verbatim text; [] when the answer is a choice with nothing to quote."""
    a = (ans or "").strip()
    if not a or a.lower().strip(". ") in ("yes", "no", "neither", "both", "none", "party a", "party b", "1992", "2002"): return []
    m = _re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", a)
    if m:
        mo, d, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if 1 <= mo <= 12: return [rf"{_MONTHS[mo - 1]}\s+{d},?\s+{y}", rf"{d}(st|nd|rd|th)?\s+(day\s+of\s+)?{_MONTHS[mo - 1]},?\s+{y}"]
    nums = _re.findall(r"\d[\d,]*(?:\.\d+)?", a)
    if nums:
        big = max(nums, key=len).replace(",", "")
        if len(big) >= 3: return [r"(?<![\d,.])" + ",?".join(_re.escape(ch) for ch in big) + r"(?![\d])"]
    first = _re.split(r",|;|\band\b", a)[0].strip(" .\"'")
    if len(first) < 3: return []
    return [r"\s+".join(_re.escape(w) for w in first.split())]
def cite_window(ans, chosen, qscores, text, ws):
    """Cite the highest-scoring SENT window that contains the answer's text; else the top-scored window, flagged."""
    order = sorted(chosen, key=lambda j: -qscores[j])
    pats = _answer_patterns(ans)
    for j in order:
        w = text[ws[j]["a"]:ws[j]["b"]]
        if pats and any(_re.search(p, w, _re.I) for p in pats): return j, True, "contains the answer"
    top = int(max(range(len(qscores)), key=lambda j: qscores[j]))
    if not (ans or "").strip(): return top, False, "top-scored window · no answer given (NONE)"
    return top, False, ("top-scored window · the answer is a choice, nothing to quote" if not pats else "top-scored window · answer text not found in the sent windows")
def gen_windows(text):
    enc = tok(text, return_offsets_mapping=True, add_special_tokens=False); ids, offs = enc["input_ids"], enc["offset_mapping"]; out = []
    for s0 in range(0, max(1, len(ids) - 32), 224):
        w = ids[s0:s0 + 256]; out.append(dict(ids=w, a=offs[s0][0], b=offs[s0 + len(w) - 1][1]))
        if s0 + 256 >= len(ids): break
    return out, len(ids)
def analyze(text, emit):
    t0 = time.monotonic(); isda = is_isda(text); arxiv = (not isda) and is_arxiv(text) and os.path.exists(f"{TRUST}/AX2.bin")
    tag = "IS3" if isda else ("AX2" if arxiv else "CUA")
    kind = "isda" if isda else ("arxiv" if arxiv else "contract")
    qs = [(n, q) for n, q, _ in ISDA_Q] if isda else ([(n, q) for n, q in AX_Q] if arxiv else [(t, C_QUESTION[t]) for t in VALUE_TYPES])
    head_path = {"AX2": ROOT + "/a5/run_AX2/head.npz", "IS3": ROOT + "/isda3/run_IS3/head.npz", "CUA": "run_CUA/head.npz"}[tag]
    h = dict(np.load(head_path)); ws, ntok = gen_windows(text)
    emit(dict(ev="doc", isda=isda, kind=kind, adapter=tag, tokens=ntok, windows=len(ws), questions=[n for n, _ in qs]))
    with ALOCK:
        if CURRENT[0] != tag:   # swap only when the document needs a different adapter than the one already bound
            r = ane.switch(tag); CURRENT[0] = tag; emit(dict(ev="bind", adapter=tag, reply=r, swapped=True))
        else:
            emit(dict(ev="bind", adapter=tag, reply="ALREADY", swapped=False))
        saved = ane.h; ane.h = h; sc = []
        try:
            for i, w in enumerate(ws):
                p, ms = ane.window(w["ids"]); sc.append(p)
                if True: emit(dict(ev="progress", i=i + 1, n=len(ws), ms=ms, score=round(float(max(p)), 3)))
        finally: ane.h = saved
    # no restore to CUA here: the next document binds only if it needs a different adapter (contract-list paths call ensure_cua themselves)
    sc = np.stack(sc); k_of = {n: (k if (isda or arxiv) else TO.index(n)) for k, (n, _) in enumerate(qs)}
    top = {n: [int(j) for j in np.argsort(-sc[:, k_of[n]])[:3]] for n, _ in qs}; chosen = sorted({j for v in top.values() for j in v} | (set(isda_sidecar(text, ws)) if tag == "IS3" else (set(ax_sidecar(text, ws)) if tag == "AX2" else set())))
    ev = [text[ws[j]["a"]:ws[j]["b"]] for j in chosen]; ane_s = time.monotonic() - t0
    emit(dict(ev="mapped", ane_s=ane_s, evidence_windows=len(chosen), chosen=chosen, n=len(ws)))
    if isda: body = isda_prompt(evidence_texts=ev, nonce=f"[demo {random.random():.12f}]")
    elif arxiv: body = ax_prompt(evidence_texts=ev, nonce=f"[demo {random.random():.12f}]")
    else: body = prompt([n for n, _ in qs], evidence=ev, nonce=f"[demo {random.random():.12f}]")
    req = urllib.request.Request(LLM_URL, json.dumps({"model": LLM_MODEL, "stream": False, "temperature": 0,
          "reasoning_effort": "none", "max_tokens": 400, "messages": [{"role": "user", "content": body}]}).encode(), {"Content-Type": "application/json"})
    t1 = time.monotonic(); j = json.load(urllib.request.urlopen(req, timeout=900)); out = j["choices"][0]["message"]["content"]
    preds = isda_parse(out) if isda else (ax_parse(out) if arxiv else parse_lines(out, len(qs)))
    ans = []
    for (n, q), p in zip(qs, preds):
        cj, grounded, why = cite_window(p, chosen, sc[:, k_of[n]], text, ws)
        ans.append(dict(q=n, question=q, answer=p, cite=text[ws[cj]["a"]:ws[cj]["b"]], grounded=grounded, cite_note=why))
    emit(dict(ev="answers", answers=ans, llm_s=time.monotonic() - t1, prompt_tokens=j["usage"]["prompt_tokens"], total_s=time.monotonic() - t0, full_tokens=ntok))

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, o):
        b = json.dumps(o).encode(); self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/analyze": self.send_response(404); self.end_headers(); return
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or b"{}")
        text = body.get("text", "")
        if body.get("pdf_b64"):
            with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
                f.write(base64.b64decode(body["pdf_b64"])); f.flush()
                text = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True).stdout
        self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-cache"); self.end_headers()
        lk = threading.Lock()
        def emit(o):
            with lk: self.wfile.write(f"data: {json.dumps(o)}\n\n".encode()); self.wfile.flush()
        try:
            if experiment_running(): emit(dict(ev="error", msg="An experiment is running on this box; runs are paused so the demo cannot disturb it. Try again when it finishes."))
            elif len(text) < 500: emit(dict(ev="error", msg="Document text too short (paste the full agreement, or upload a .txt/.pdf)."))
            else: analyze(text, emit)
        except (BrokenPipeError, ConnectionResetError): pass
        except Exception as e:
            try: emit(dict(ev="error", msg=repr(e)[:300]))
            except Exception: pass
    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query)
        if u.path == "/":
            b = open(os.path.join(HERE, "index.html"), "rb").read(); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b); return
        if u.path == "/contracts":
            return self._json(dict(contracts=[dict(id=c, tokens=S["ntok"][c], long=c in LONG, fresh=c in A2P, questions=len(asked(c))) for c in POOL],
                                   type_order=TO, tau=[TAU[t] for t in TO], cited=CITED, base_md5=BASE_MD5[:12]))
        if u.path == "/text":
            c = q["cid"][0]; return self._json(dict(text=C[c]["context"]))
        if u.path == "/status": return self._json(dict(experiment_running=experiment_running()))
        if u.path in ("/run", "/pipeline", "/swap") and experiment_running():
            self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.end_headers()
            self.wfile.write(f"data: {json.dumps(dict(ev='error', msg='An experiment is running on this box; runs are paused so the demo cannot disturb it. Browsing still works. Try again when it finishes.'))}\n\n".encode()); return
        if u.path in ("/run", "/pipeline", "/swap"):
            self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-cache"); self.end_headers()
            lk = threading.Lock()
            def emit(o):
                with lk: self.wfile.write(f"data: {json.dumps(o)}\n\n".encode()); self.wfile.flush()
            try:
                if u.path == "/run": run_one(q["cid"][0], emit)
                elif u.path == "/pipeline": run_pipeline(q["cids"][0].split("|"), emit)
                else: swap_check(emit)
            except (BrokenPipeError, ConnectionResetError): pass
            except Exception as e:
                try: emit(dict(ev="error", msg=repr(e)[:300]))
                except Exception: pass
            return
        self.send_response(404); self.end_headers()

ThreadingHTTPServer((os.environ.get("KEV_DEMO_HOST", "127.0.0.1"), int(os.environ.get("KEV_DEMO_PORT", 8733))), H).serve_forever()
