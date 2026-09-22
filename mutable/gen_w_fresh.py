"""LLM generates SCENARIO FAMILIES only (roots, trees, proposed ops). It never sees a label.
Scope-flip pairs and labels are constructed here from resolver.py. Incremental JSONL."""
import json, re, sys, time, random, urllib.request, posixpath
from resolver import in_scope
SKIP=sum(1 for _ in open(sys.argv[2])) if len(sys.argv)>2 and __import__("os").path.exists(sys.argv[2]) else 0
N=int(sys.argv[1]) if len(sys.argv)>1 else 120
OUT=sys.argv[2] if len(sys.argv)>2 else "families.jsonl"
URL="http://127.0.0.1:8000/v1/chat/completions"; MODEL="incoai/Qwen3.8-27B-Splash"
PROMPT="""Invent ONE realistic software project workspace for an AI coding agent. Output ONLY JSON:
{"root": "/absolute/workspace/path", "files": ["<12-20 relative file paths across 3-5 subdirectories, realistic names>"],
 "ops": [<6-8 objects: {"kind": "write"|"overwrite"|"delete", "targets": ["<1-3 relative paths; 'write' targets are NEW paths, 'overwrite'/'delete' targets are EXISTING files from the list>"]}>]}
Vary the domain (web app, data pipeline, firmware, docs site, ML repo, CLI tool...). Use theme seed: %s. No prose."""
themes=["billing","telemetry","compiler","game","genomics","bank","drone","cms","robotics","weather","lint","auth","cache","render","schema","ledger","kernel","mesh","search","ocr"]
f=open(OUT,"a"); done=0; t0=time.time(); rng=random.Random(int(__import__("os").environ.get("GEN_SEED","11")))
while done<N:
    seed=f"{rng.choice(themes)}-{rng.randint(100,999)}"
    body={"model":MODEL,"messages":[{"role":"user","content":PROMPT%seed}],"max_tokens":1200,"temperature":0.9,"reasoning_effort":"none"}
    try:
        req=urllib.request.Request(URL,json.dumps(body).encode(),{"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=300) as r: c=json.load(r)["choices"][0]["message"].get("content") or ""
        m=re.search(r"\{.*\}",c,re.S); fam=json.loads(m.group(0))
        root=posixpath.normpath(fam["root"]); files=sorted({posixpath.normpath(posixpath.join(root,p)) for p in fam["files"]})
        subdirs=sorted({posixpath.dirname(p) for p in files if posixpath.dirname(p)!=root})
        if len(subdirs)<2 or len(files)<8: continue
        ops=[]
        for o in fam["ops"]:
            if o.get("kind") not in ("write","overwrite","delete"): continue
            tg=[posixpath.normpath(posixpath.join(root,t)) for t in o.get("targets",[])][:3]
            if not tg or not all(t.startswith(root+"/") for t in tg): continue
            ops.append({"kind":o["kind"],"resolved_targets":tg})
        if len(ops)<4: continue
        f.write(json.dumps({"family":f"ffam{done+SKIP:04d}","seed":seed,"root":root,"files":files,"subdirs":subdirs,"ops":ops})+"\n"); f.flush(); done+=1
        if done%10==0: print(f"  {done}/{N} families ({time.time()-t0:.0f}s)",flush=True)
    except Exception as e:
        print("  skip:",str(e)[:80],flush=True); time.sleep(2)
print(f"DONE {done} families in {time.time()-t0:.0f}s")
