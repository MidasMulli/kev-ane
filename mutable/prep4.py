"""Records -> four fp16 input streams at fixed T for kev4 (x, cos, sin, neg), using kev-ane's own
make_inputs (encode + branch_mask + rope_at) and Kev's render/option_text, so the ANE sees exactly
what the trainer saw. prep4.py <suite.jsonl> <outdir> <T> [n] [--mask FIELD] [--only QKEY] [--noq]"""
import json, os, sys, numpy as np, torch
sys.path.insert(0,"/Users/midas/Desktop/cowork/jev/kev-ane/src"); sys.path.insert(0,"/Users/midas/Desktop/cowork/jev/work/kevsrc")
from kev_ane.runtime import make_inputs
from kev_ane.trunk import Trunk
from kev_ane.merge import load_base
from kev.api import render, option_text
from transformers import AutoTokenizer
src,out,T=sys.argv[1],sys.argv[2],int(sys.argv[3]); n=int(sys.argv[4]) if len(sys.argv)>4 and sys.argv[4].isdigit() else None
mask=sys.argv[sys.argv.index("--mask")+1] if "--mask" in sys.argv else None
only=sys.argv[sys.argv.index("--only")+1] if "--only" in sys.argv else None
os.makedirs(out,exist_ok=True); tok=AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B-Base")
emb=load_base(Trunk().eval())
rows=[json.loads(l) for l in open(src)][:n]
fx,fc,fs,fn=(open(f"{out}/{k}.f16","wb") for k in ("x","cos","sin","neg")); meta=[]
for r in rows:
    st=dict(r["state"]);
    if mask: st.pop(mask,None)
    qs=[]
    for key,q in r["questions"].items():
        if only and key!=only: continue
        c=q.get("criteria") or {}
        qs.append({"instr":render(q["instructions"]),"options":[option_text("no",c.get("false")),option_text("yes",c.get("true"))],"label":int(bool(q["label"]))})
    feed,enc,T_=make_inputs(tok,emb,render(st),qs,T=T); assert T_==T, (T_,T)
    for f,k in ((fx,"x"),(fc,"cos"),(fs,"sin"),(fn,"neg")): f.write(np.ascontiguousarray(feed[k]).astype(np.float16).tobytes())
    meta.append({"id":r["_meta"]["id"],"decide":enc["decide_idx"],"opt":enc["opt_idx"],"labels":[q["label"] for q in qs],"qkeys":[k for k in r["questions"] if not only or k==only]})
json.dump({"T":T,"n":len(rows),"mask":mask,"only":only,"records":meta},open(f"{out}/meta.json","w"))
print(f"PREP4 {out}: {len(rows)} records T={T} mask={mask} only={only}")
