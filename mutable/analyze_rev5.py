"""PREREG Rev 5 (befe024c) acceptance on the FRESH suites. C1 substrate (every record), C2 decisions at margin>=2,
C3 probabilities at margin>=8, prospective coverage 99%/95%; participation P1 (hs-level), P2 (decision-level), P3 (reported);
parity, wrong-domain, retention. All references from files written before this runs."""
import json, numpy as np, torch
from analyze2 import probs, head
D=1024; C1=5e-2; TOL=1e-3
def L(p): p=min(max(p,1e-12),1-1e-12); return np.log(p/(1-p))
def deployed_hs(hs_path,meta):
    M=json.load(open(meta)); n=M["n"]; hs=np.memmap(hs_path,dtype=np.float16,mode="r").reshape(n,D,-1)
    return {f"{rec['id']}|{q}":np.asarray(hs[i,:,d],dtype=np.float32) for i,rec in enumerate(M["records"]) for q,d in zip(rec["qkeys"],rec["decide"])}
def ref_hs(npz): z=np.load(npz); return dict(zip(z["ids"].tolist(),z["ref"]))
def tp(p): return {json.loads(l)["id"]:json.loads(l) for l in open(p)}
def c1(dep,ref,label):
    e={k:float(np.linalg.norm(dep[k]-ref[k])/np.linalg.norm(ref[k])) for k in ref}; v=[k for k in e if e[k]>C1]
    print(f"  C1 {label}: n={len(e)} rel hs err p50 {np.median(list(e.values())):.2e} max {max(e.values()):.2e}  over {C1:g}: {len(v)} -> {'PASS' if not v else '*** FAIL (investigate) ***'}"); return e,v
def c23(ane,ref,label,coverage_required):
    rows=[(k,q,ane_p,ref[k]["p"][q]) for k,r in ane.items() for q,ane_p in r["p"].items()]
    m=np.array([abs(L(rp)) for _,_,_,rp in rows]); flips=[(k,q) for (k,q,ap,rp),mm in zip(rows,m) if mm>=2 and (ap>=0.5)!=(rp>=0.5)]
    miss=[(k,q,abs(ap-rp)) for (k,q,ap,rp),mm in zip(rows,m) if mm>=8 and abs(ap-rp)>TOL]
    cov2,cov8=float((m>=2).mean()),float((m>=8).mean()); low=[(k,q,round(abs(ap-rp),4)) for (k,q,ap,rp),mm in zip(rows,m) if mm<2]
    bands=[((m>=a)&(m<b)) for a,b in ((0,2),(2,8),(8,1e9))]; worst=[max([abs(ap-rp) for (k,q,ap,rp),s in zip(rows,bb) if s],default=0) for bb in bands]
    okc = (cov2>=0.99 and cov8>=0.95) if coverage_required else True
    print(f"  {label}: n={len(rows)}  coverage margin>=2 {cov2:.4f} (bar .99) >=8 {cov8:.4f} (bar .95)  bands n={[int(b.sum()) for b in bands]} worst|dp|={[f'{w:.1e}' for w in worst]}")
    print(f"    C2 flips at margin>=2: {len(flips)} {flips[:3]}   C3 misses at margin>=8: {len(miss)} {miss[:3]}   below-2 reported: {len(low)} {low[:4]}")
    print(f"    -> {'PASS' if not flips and not miss and okc else ('NOT ESTABLISHED (coverage)' if not flips and not miss else '*** FAIL ***')}")
    return rows
def wrong(hs,meta,h,label):
    r=probs(hs,meta,h)
    for q in r[0]["p"]:
        acc=np.mean([(x["p"][q]>=0.5)==bool(x["labels"][q]) for x in r]); pos=np.mean([bool(x["labels"][q]) for x in r]); print(f"  {label} [{q}]: agreement {acc:.3f} majority {max(pos,1-pos):.3f}")
HW,HD_=head("runs/W/head.pt"),head("runs/D/head.pt"); F="fresh"
print("=== C1 substrate, all four combinations ===")
eWW,vWW=c1(deployed_hs("hs_fW_on_W.f16",f"{F}/_in_W/meta.json"),ref_hs(f"{F}/ref_W_on_W.npz"),"W adapter on suite_W")
eDD,vDD=c1(deployed_hs("hs_fD_on_D.f16",f"{F}/_in_D/meta.json"),ref_hs(f"{F}/ref_D_on_D.npz"),"D adapter on suite_D")
eDW,vDW=c1(deployed_hs("hs_fD_on_W.f16",f"{F}/_in_W/meta.json"),ref_hs(f"{F}/ref_D_on_W.npz"),"D adapter on suite_W (cross)")
eWD,vWD=c1(deployed_hs("hs_fW_on_D.f16",f"{F}/_in_D/meta.json"),ref_hs(f"{F}/ref_W_on_D.npz"),"W adapter on suite_D (cross)")
print("=== C2/C3 + coverage, own combinations (the claim) ===")
aWW=probs("hs_fW_on_W.f16",f"{F}/_in_W/meta.json",HW); aDD=probs("hs_fD_on_D.f16",f"{F}/_in_D/meta.json",HD_)
byid=lambda a:{r["id"]:r for r in a}
c23(byid(aWW),tp("runs/W/fresh_preds.jsonl"),"W own (H_W)",True); c23(byid(aDD),tp("runs/D/fresh_preds.jsonl"),"D own (H_D)",True)
print("=== C2/C3 cross combinations (witness material; coverage reported) ===")
aDW=probs("hs_fD_on_W.f16",f"{F}/_in_W/meta.json",HW); aWD=probs("hs_fW_on_D.f16",f"{F}/_in_D/meta.json",HD_)
c23(byid(aDW),tp("runs/D/fresh_fixedhead_HW_preds.jsonl"),"H_W on D-trunk",False); c23(byid(aWD),tp("runs/W/fresh_fixedhead_HD_preds.jsonl"),"H_D on W-trunk",False)
print("=== participation ===")
rW=ref_hs(f"{F}/ref_W_on_W.npz"); dW=deployed_hs("hs_fW_on_W.f16",f"{F}/_in_W/meta.json"); dD=deployed_hs("hs_fD_on_W.f16",f"{F}/_in_W/meta.json")
p1=[k for k in rW if np.linalg.norm(dW[k]-dD[k])/np.linalg.norm(rW[k])>3*C1 and eWW[k]<=C1 and eDW[k]<=C1]
print(f"  P1 substrate witnesses (W vs D streams differ > {3*C1:g}, both within C1): {len(p1)}/{len(rW)} -> {'established' if p1 else '*** NOT ESTABLISHED ***'}")
for hname,own,cross,aown,across in (("H_W","runs/W/fresh_preds.jsonl","runs/D/fresh_fixedhead_HW_preds.jsonl",byid(aWW),byid(aDW)),("H_D","runs/D/fresh_preds.jsonl","runs/W/fresh_fixedhead_HD_preds.jsonl",byid(aDD),byid(aWD))):
    o,c=tp(own),tp(cross); p2=p2ok=p3=p3ok=0
    for k in o:
        for q in o[k]["p"]:
            lo,lc=L(o[k]["p"][q]),L(c[k]["p"][q])
            if (lo>0)!=(lc>0) and abs(lo)>=2 and abs(lc)>=2:
                p2+=1; p2ok+= ((aown[k]["p"][q]>=0.5)==(lo>0)) and ((across[k]["p"][q]>=0.5)==(lc>0))
            if abs(o[k]["p"][q]-c[k]["p"][q])>2e-3 and abs(lo)>=8 and abs(lc)>=8:
                p3+=1; p3ok+= abs(aown[k]["p"][q]-o[k]["p"][q])<=TOL and abs(across[k]["p"][q]-c[k]["p"][q])<=TOL
    print(f"  P2 decision witnesses {hname}: {p2} in torch, {p2ok} reproduced on both states -> {'established' if p2 and p2ok==p2 else '*** NOT ESTABLISHED ***' if p2==0 else '*** FAIL ***'}")
    print(f"  P3 probability witnesses {hname}: {p3} in torch, {p3ok} within 1e-3 on both states (reported{'; none exist' if p3==0 else ''})")
print("=== parity packed vs separate (own, C2/C3 form) ===")
for lab,hs,meta,h,q,packed in (("W scope","hs_fW_scope.f16",f"{F}/_in_W_scope/meta.json",HW,"scope",aWW),("W destr","hs_fW_destr.f16",f"{F}/_in_W_destr/meta.json",HW,"destructive",aWW),("D recip","hs_fD_recip.f16",f"{F}/_in_D_recip/meta.json",HD_,"recipient",aDD),("D secret","hs_fD_secret.f16",f"{F}/_in_D_secret/meta.json",HD_,"secret",aDD)):
    sep=byid(probs(hs,meta,h)); rows=[(k,r["p"][q],sep[k]["p"][q]) for k,r in byid(packed).items()]
    fl=sum((a>=0.5)!=(b>=0.5) for _,a,b in rows); mx=max(abs(a-b) for _,a,b in rows); print(f"  {lab}: argmax mismatches {fl}  max|dp| {mx:.2e}")
print("=== wrong-domain (statistic) ==="); wrong("hs_fW_on_D.f16",f"{F}/_in_D/meta.json",HW,"W+H_W on suite_D"); wrong("hs_fD_on_W.f16",f"{F}/_in_W/meta.json",HD_,"D+H_D on suite_W")
print("ANALYZE_REV5 DONE")
