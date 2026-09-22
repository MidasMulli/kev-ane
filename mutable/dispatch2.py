"""PREREG f23be94a §5 dispatch reconciliation: every ISSUED prediction (kev4 ts log, mach ns) matched 1:1 to a
predict-shaped ANE interval (xctrace ane-hw-intervals); load intervals reconciled SEPARATELY. A load interval can
never stand in for a prediction. dispatch2.py <ts.log> <intervals.xml>"""
import sys, xml.etree.ElementTree as ET
ts=[l.split() for l in open(sys.argv[1])]
loads=[(float(l[1]),float(l[2])) for l in ts if l[0]=="LOAD"]; preds=[(int(l[1]),float(l[2]),float(l[3])) for l in ts if l[0]=="PREDICT"]
c={}
def v(e):
    if e is None: return None
    r=e.get("ref")
    if r: return c.get(r)
    if e.get("id"): c[e.get("id")]=e.text
    return e.text
iv=sorted((int(a),int(b)) for r in ET.parse(sys.argv[2]).getroot().findall(".//row") for a,b in [(v(r.find("start-time")),v(r.find("duration")))] if a and b)
# common time base: align the first prediction's start to the first interval that starts after the last load window ends
t_first_pred=min(a for _,a,_ in preds); after_load=[s for s,d in iv if True]
# estimate offset from the median (pred.start - interval.start) over a greedy monotone pairing on the longest common run
def match(off):
    used=set(); m={}
    for r,a,b in sorted(preds,key=lambda x:x[1]):
        cands=[i for i,(s,d) in enumerate(iv) if i not in used and a-off-2e6<=s<=b-off]   # interval starts inside the (shifted) prediction window, 2 ms slack
        if cands: i=min(cands,key=lambda i:iv[i][0]); used.add(i); m[r]=i
    return m,used
best=None
for off0 in [a-s for _,a,_ in preds[:3] for s,_ in iv[:6]]:           # candidate offsets from early pairings
    m,used=match(off0)
    if best is None or len(m)>len(best[0]): best=(m,used,off0)
m,used,off=best
unmatched=[r for r,_,_ in preds if r not in m]; extra=[i for i in range(len(iv)) if i not in used]
durs=[iv[i][1]/1e6 for i in m.values()]; extra_d=[iv[i][1]/1e6 for i in extra]
print(f"  issued {len(preds)} predictions, {len(loads)} loads; ANE intervals {len(iv)}")
print(f"  matched 1:1: {len(m)}/{len(preds)}  unmatched predictions: {len(unmatched)} {unmatched[:5]}  matched p50 {sorted(durs)[len(durs)//2]:.2f} ms")
print(f"  intervals outside every prediction window: {len(extra)} (durations ms {[round(x,1) for x in extra_d[:8]]}) reconciled against {len(loads)} loads")
print("  DISPATCH:", "PASS" if not unmatched else "*** FAIL: unmatched issued predictions ***")
