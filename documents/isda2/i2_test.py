"""I2 TEST (Astra-signed): 56 fresh genuine ISDA docs, 12 questions, adapter ISD2. Adapted from i1_test.py.
I1 TEST (Astra-signed). (1) G-SWAP: bind CUA -> fixed window hs; bind ISD -> hs; bind CUA -> hs: CUA runs bitwise identical, CUA != ISD,
base md5 unchanged. (2) 120 TEST ISDA docs: PIPE (ISD top-3 windows per field, no NULL gate -> 27B) vs FULL (27B reads all), cold,
alternating; per-field normalized comparison; disagreements go to blind 2+1 adjudication (i1_packets.py). Latency per doc measured."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, re, sys, random, time, hashlib, subprocess, urllib.request, numpy as np
sys.path.insert(0, ROOT + "/cuad"); os.chdir(ROOT + "/isda2")
from ane_run import Ane, export_and_pack, sh, MD, TRUST
from i2_common import NAMES, prompt, parse, norm as i2norm
P = json.load(open("isda2_corpus241.json")); SPLIT = json.load(open("i2_split.json"))
from transformers import AutoTokenizer
log = open("i2_test_raw.jsonl", "w")
def emit(**r): print(json.dumps(r)[:300], flush=True); log.write(json.dumps(r) + "\n"); log.flush()
g0 = sh(GATE0).splitlines()[-1]; assert g0.startswith("gate=GREEN"), g0
sent = subprocess.Popen([SENTINEL, str(os.getpid()), os.path.abspath("i2_test_red_sentinel.log")]); time.sleep(3); assert sent.poll() is None
tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base"); T_, STRIDE_ = 256, 224
def windows(text):
    enc = tok(text, return_offsets_mapping=True, add_special_tokens=False); ids, offs = enc["input_ids"], enc["offset_mapping"]; out = []
    for s0 in range(0, max(1, len(ids) - (T_ - STRIDE_)), STRIDE_):
        w = ids[s0:s0 + T_]; out.append(dict(ids=w, a=offs[s0][0], b=offs[s0 + len(w) - 1][1]))
        if s0 + T_ >= len(ids): break
    return out
head, amd5 = export_and_pack("i2_best.npz", "IS2"); md5_0 = sh(f"sudo -n md5 -q {MD}/weights/weight.bin")
ane = Ane("IS2", head)
# ---- G-SWAP ----
w0 = windows(P[SPLIT["test"][0]]["text"])[1]["ids"]
def hs_sha(tag):
    r = ane.cmd(f"BIND {TRUST}/{tag}.bin"); assert r.startswith("BOUND"), r; ane.window(w0); return hashlib.sha256(open(f"{ane.IN}/hs.f16", "rb").read()).hexdigest()[:16], float(r.split()[1])
s1 = hs_sha("CUA"); s2 = hs_sha("IS2"); s3 = hs_sha("CUA"); s4 = hs_sha("IS2")
g_swap = s1[0] == s3[0] and s1[0] != s2[0] and s2[0] == s4[0] and sh(f"sudo -n md5 -q {MD}/weights/weight.bin") == md5_0
emit(event="swap", cua=s1, isd=s2, cua_again=s3, isd_again=s4, G_SWAP=g_swap, adapter_md5=amd5)
def ask(text):
    body = {"model": LLM_MODEL, "stream": False, "temperature": 0, "reasoning_effort": "none", "max_tokens": 200, "messages": [{"role": "user", "content": text}]}
    req = urllib.request.Request(LLM_URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.monotonic(); j = json.load(urllib.request.urlopen(req, timeout=1800)); u = j["usage"]
    assert (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) == 0
    return j["choices"][0]["message"]["content"], u["prompt_tokens"], time.monotonic() - t0
ane.cmd(f"BIND {TRUST}/IS2.bin")
for n, i in enumerate(SPLIT["test"]):
    text = P[i]["text"]; t0 = time.monotonic(); ws = windows(text); sc = np.stack([ane.window(w["ids"])[0] for w in ws])
    chosen = sorted({int(j) for k in range(12) for j in np.argsort(-sc[:, k])[:3]}); ev = [text[ws[j]["a"]:ws[j]["b"]] for j in chosen]; ane_s = time.monotonic() - t0
    res = {}
    for arm in (("PIPE", "FULL") if n % 2 == 0 else ("FULL", "PIPE")):
        out, pt, dt = ask(prompt(**(dict(evidence_texts=ev) if arm == "PIPE" else dict(context=text)), nonce=f"[req {random.random():.12f}]"))
        res[arm] = dict(preds=parse(out), seconds=dt + (ane_s if arm == "PIPE" else 0), prompt_tokens=pt, response=out)
    agree = [i2norm(f, a) == i2norm(f, b) for f, a, b in zip(NAMES, res["PIPE"]["preds"], res["FULL"]["preds"])]
    emit(event="compare", cid=f"I{i}", idx=i, agree=agree, pipe=res["PIPE"]["preds"], full=res["FULL"]["preds"], lat_diff=res["PIPE"]["seconds"] - res["FULL"]["seconds"],
         pipe_s=res["PIPE"]["seconds"], full_s=res["FULL"]["seconds"], pipe_tok=res["PIPE"]["prompt_tokens"], full_tok=res["FULL"]["prompt_tokens"], ane_s=ane_s, windows=len(ws))
ane.close()
emit(event="I2_RUN_DONE", G_SWAP=g_swap, base_md5_unchanged=sh(f"sudo -n md5 -q {MD}/weights/weight.bin") == md5_0)
sent.terminate()
