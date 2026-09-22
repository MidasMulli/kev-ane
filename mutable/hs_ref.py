"""Rev 5 C1 reference: torch KevIn with <run>'s factors at the SAME four inputs as the ANE pass; writes the reference
hs at every decide position (D floats each) so C1 and P1 are computed from files. hs_ref.py <run> <indir> <out.npz>"""
import json, sys, numpy as np, torch
run,ind,out=sys.argv[1],sys.argv[2],sys.argv[3]
sys.argv=["x","g0","_out","256"]; exec(open("deploy_inputs.py").read().split("if MODE==")[0])
FA,FB=factors_from_run(run); m=KevIn().eval(); rload(m.base)
with torch.no_grad():
    for a in PROJ:
        for L in range(NL): getattr(m,f"{a}A")[L].weight.copy_(FA[a][L][:,:,None,None]); getattr(m,f"{a}B")[L].weight.copy_(FB[a][L][:,:,None,None])
M=json.load(open(f"{ind}/meta.json")); n=M["n"]
ld=lambda k,shape: np.memmap(f"{ind}/{k}.f16",dtype=np.float16,mode="r").reshape(n,*shape)
X,C,S,N=ld("x",(1,D,1,T)),ld("cos",(1,1,HD,T)),ld("sin",(1,1,HD,T)),ld("neg",(1,1,T,T))
refs=[]; ids=[]
for i,rec in enumerate(M["records"]):
    with torch.no_grad(): r=m(*[torch.tensor(np.asarray(a[i],dtype=np.float32)) for a in (X,C,S,N)]).numpy()[0,:,0,:]
    for q,d in enumerate(rec["decide"]): refs.append(r[:,d]); ids.append(f"{rec['id']}|{rec['qkeys'][q]}")
    if i%200==0: print(f"  {run} on {ind}: {i}/{n}",flush=True)
np.savez(out,ref=np.array(refs,dtype=np.float32),ids=np.array(ids)); print(f"HS_REF DONE {out} {len(ids)} positions",flush=True)
