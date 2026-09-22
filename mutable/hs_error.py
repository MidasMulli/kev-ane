"""Mechanism test for the fidelity failures: hidden-state error of the DEPLOYED W adapter vs torch KevIn (same
four inputs) at the decide positions, for every held-out W record, printed against the torch logit margin.
If the hs error is flat across margins, the probability gap is sigmoid sensitivity; if it concentrates on the
failing records, something else is wrong with those records."""
import json, sys, numpy as np, torch
sys.argv=["x","g0","_out","256"]; exec(open("deploy_inputs.py").read().split("if MODE==")[0])
FA,FB=factors_from_run("runs/W"); m=KevIn().eval(); rload(m.base)
with torch.no_grad():
    for a in PROJ:
        for L in range(NL): getattr(m,f"{a}A")[L].weight.copy_(FA[a][L][:,:,None,None]); getattr(m,f"{a}B")[L].weight.copy_(FB[a][L][:,:,None,None])
M=json.load(open("_in_W/meta.json")); n=M["n"]
ld=lambda k,shape: np.memmap(f"_in_W/{k}.f16",dtype=np.float16,mode="r").reshape(n,*shape)
X,C,S,N=ld("x",(1,D,1,T)),ld("cos",(1,1,HD,T)),ld("sin",(1,1,HD,T)),ld("neg",(1,1,T,T))
hs=np.memmap("hs_W_on_W.f16",dtype=np.float16,mode="r").reshape(n,1,D,1,T)
tp={json.loads(l)["id"]:json.loads(l) for l in open("runs/W/heldout_preds.jsonl")}
def L(p): p=min(max(p,1e-12),1-1e-12); return abs(np.log(p/(1-p)))
out=[]
for i,rec in enumerate(M["records"]):
    with torch.no_grad(): ref=m(*[torch.tensor(np.asarray(a[i],dtype=np.float32)) for a in (X,C,S,N)]).numpy()[0,:,0,:]
    for q,d in enumerate(rec["decide"]):
        r,a=ref[:,d],np.asarray(hs[i,0,:,0,d],dtype=np.float32); rel=float(np.linalg.norm(r-a)/np.linalg.norm(r))
        out.append({"id":rec["id"],"q":rec["qkeys"][q],"rel_hs_err":rel,"margin":L(tp[rec["id"]]["p"][rec["qkeys"][q]])})
    if i%200==0: print(f"  {i}/{n}",flush=True); json.dump(out,open("hs_error.json","w"))
json.dump(out,open("hs_error.json","w"))
e=np.array([o["rel_hs_err"] for o in out]); mg=np.array([o["margin"] for o in out])
print(f"rel hs error at decide, all {len(e)}: p50 {np.median(e):.2e} p99 {np.percentile(e,99):.2e} max {e.max():.2e}")
for a,b in ((0,2),(2,4),(4,8),(8,16),(16,1e9)):
    s=(mg>=a)&(mg<b); print(f"  margin [{a},{b}): n={s.sum()}  rel hs err p50 {np.median(e[s]):.2e}  max {e[s].max():.2e}" if s.any() else f"  margin [{a},{b}): -")
bad=[o for o in out if o["id"].startswith("write_scope2/fam0103/op7")]; print("  failing records:",[(o["id"].split("/")[-2:],o["q"],round(o["rel_hs_err"],4)) for o in bad])
print("HS_ERROR DONE")
