"""I2 TEACHER labels (Astra-signed): the 27B reads the SCHEDULE portion of each TRAIN/DEV document (the printed form carries no elections)
and answers the 12 questions (cold, T=0). Evidence is NOT taken from the answers: it is the anchored heading paragraph (i2_common.evidence).
Resumable; writes i2_teacher.jsonl."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, random, time, subprocess, urllib.request
from i2_common import prompt, parse, schedule_start, NAMES
U = json.load(open("isda2_corpus241.json")); S = json.load(open("i2_split.json"))
def ask(text):
    body = {"model": LLM_MODEL, "stream": False, "temperature": 0, "reasoning_effort": "none", "max_tokens": 400, "messages": [{"role": "user", "content": text}]}
    req = urllib.request.Request(LLM_URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.monotonic(); j = json.load(urllib.request.urlopen(req, timeout=1800)); return j["choices"][0]["message"]["content"], j["usage"]["prompt_tokens"], time.monotonic() - t0
if __name__ == "__main__":
    g0 = subprocess.run(GATE0, shell=True, capture_output=True, text=True).stdout.strip().splitlines()[-1]; assert g0.startswith("gate=GREEN"), g0
    done = {json.loads(l)["idx"] for l in open("i2_teacher.jsonl")} if os.path.exists("i2_teacher.jsonl") else set()
    out = open("i2_teacher.jsonl", "a")
    for split in ("dev", "train"):
        for i in S[split]:
            if i in done: continue
            t = U[i]["text"]; sched = t[schedule_start(t):]
            a, pt, dt = ask(prompt(context=sched, nonce=f"[teach {random.random():.12f}]"))
            out.write(json.dumps(dict(idx=i, split=split, answers=dict(zip(NAMES, parse(a))), prompt_tokens=pt, seconds=dt, raw=a)) + "\n"); out.flush()
    print("TEACHER_DONE")
