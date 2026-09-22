"""battery2 step 4: fidelity per adapter (packed, every held-out record) vs torch; packed-vs-separate parity;
fixed-head control with references (H_W on W-trunk and on D-trunk, torch refs from score2 --head);
wrong-domain readout as statistic vs majority ONLY. Tolerance 1e-3 + argmax equal (PREREG f23be94a §5)."""
import json, sys, numpy as np, torch
from analyze2 import probs, head, fid, TOL
W,D="runs/W","runs/D"; HW,HD_=head(f"{W}/head.pt"),head(f"{D}/head.pt")
tp=lambda p:{json.loads(l)["id"]:json.loads(l) for l in open(p)}
def align(ane,ref): return ane,[ref[r["id"]] for r in ane]
print("--- fidelity, packed, every held-out record ---")
Won=probs("hs_W_on_W.f16","_in_W/meta.json",HW); fid(*align(Won,tp(f"{W}/heldout_preds.jsonl")),"W adapter, suite_W")
Don=probs("hs_D_on_D.f16","_in_D/meta.json",HD_); fid(*align(Don,tp(f"{D}/heldout_preds.jsonl")),"D adapter, suite_D")
print("--- packed-vs-separate parity (ANE vs ANE, per question) ---")
for name,hs,meta,h,q in (("W",'hs_W_scope_only.f16','_in_W_scope/meta.json',HW,'scope'),("W",'hs_W_destr_only.f16','_in_W_destr/meta.json',HW,'destructive'),
                         ("D",'hs_D_recip_only.f16','_in_D_recip/meta.json',HD_,'recipient'),("D",'hs_D_secret_only.f16','_in_D_secret/meta.json',HD_,'secret')):
    sep=probs(hs,meta,h); packed=Won if name=="W" else Don
    fid([{"p":{q:r["p"][q]}} for r in packed],[{"p":{q:r["p"][q]}} for r in sep],f"parity {name}[{q}] packed vs separate")
print("--- fixed-head control (reference-anchored, separation > 2e-3 established in torch first) ---")
for hname,H,inp,onA,onB,refA,refB in (("H_W",HW,"_in_W","hs_W_on_W.f16","hs_D_on_W.f16",f"{W}/heldout_preds.jsonl",f"{D}/fixedhead_HW_preds.jsonl"),
                                       ("H_D",HD_,"_in_D","hs_D_on_D.f16","hs_W_on_D.f16",f"{D}/heldout_preds.jsonl",f"{W}/fixedhead_HD_preds.jsonl")):
    ra,rb=tp(refA),tp(refB); sep=sum(1 for k in ra for q in ra[k]["p"] if abs(ra[k]["p"][q]-rb[k]["p"][q])>2e-3)
    print(f"  {hname}: torch reference separation > 2e-3 on {sep} (record,question) pairs -> {'established' if sep>0 else '*** PARTICIPATION NOT ESTABLISHED ***'}")
    a=probs(onA,f"{inp}/meta.json",H); b=probs(onB,f"{inp}/meta.json",H)
    fid(*align(a,ra),f"  {hname} own-trunk deployed vs ref"); fid(*align(b,rb),f"  {hname} other-trunk deployed vs ref")
    moved=sum(1 for x,y in zip(a,b) for q in x["p"] if abs(x["p"][q]-y["p"][q])>TOL); print(f"  {hname}: deployed states differ > tol on {moved} (record,question) pairs [statistic]")
print("--- wrong-domain readout (statistic only, no bar) ---")
for lab,hs,meta,h in (("W adapter+H_W on suite_D","hs_W_on_D.f16","_in_D/meta.json",HW),("D adapter+H_D on suite_W","hs_D_on_W.f16","_in_W/meta.json",HD_)):
    r=probs(hs,meta,h)
    for q in r[0]["p"]:
        acc=sum((x["p"][q]>=0.5)==bool(x["labels"][q]) for x in r)/len(r)
        pos=sum(bool(x["labels"][q]) for x in r)/len(r); print(f"  {lab} [{q}]: agreement with label {acc:.3f}  majority {max(pos,1-pos):.3f}")
print("ANALYZE_BATTERY2 DONE")
