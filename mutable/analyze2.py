"""ANE-side analysis for PREREG f23be94a §5. Applies Kev pointer heads host-side to hs dumps.
analyze2.py <passes.json>  where passes.json lists {name, hs, meta, head, torch_preds(optional), role}."""
import json, sys, numpy as np, torch
sys.path.insert(0,"/Users/midas/Desktop/cowork/jev/kev-ane/src"); from kev_ane.readout import PointerHead
from kev_ane.config import D
TOL=1e-3
def head(path):
    hd=torch.load(path,map_location="cpu",weights_only=False); h=PointerHead(D,hd["head_dim"]); h.load_state_dict(hd["head"]); h.eval(); return h
def probs(hs_path, meta, h):
    M=json.load(open(meta)); n,T=M["n"],M["T"]; hs=np.fromfile(hs_path,dtype=np.float16).reshape(n,D,-1).astype(np.float32); out=[]
    for i,rec in enumerate(M["records"]):
        H=torch.tensor(hs[i]).T; ps=[]
        for q,(d,o) in enumerate(zip(rec["decide"],rec["opt"])):
            with torch.no_grad(): ps.append(float(torch.softmax(h(H[d],H[torch.as_tensor(o)]),-1)[1]))
        out.append({"id":rec["id"],"p":dict(zip(rec["qkeys"],ps)),"labels":dict(zip(rec["qkeys"],rec["labels"]))})
    return out
def fid(a,b,label):
    dp=[]; am=0; n=0
    for x,y in zip(a,b):
        for k in x["p"]:
            if k in y["p"]: dp.append(abs(x["p"][k]-y["p"][k])); am+=(x["p"][k]>=0.5)!=(y["p"][k]>=0.5); n+=1
    worst=max(dp); print(f"  {label}: n={n} max|dp| {worst:.2e}  argmax mismatches {am}  -> {'PASS' if worst<=TOL and am==0 else '*** FAIL ***'}"); return worst,am
if __name__=="__main__":
    P=json.load(open(sys.argv[1])); R={}
    for p in P:
        R[p["name"]]=probs(p["hs"],p["meta"],head(p["head"]))
        if p.get("torch_preds"):
            tp={json.loads(l)["id"]:json.loads(l) for l in open(p["torch_preds"])}
            fid(R[p["name"]],[tp[r["id"]] for r in R[p["name"]]],f"FIDELITY {p['name']} vs torch")
        for r in R[p["name"]][:0]: pass
    json.dump(R,open("ane_probs.json","w"))
    print("ANALYZE2 DONE", list(R))
