"""PREREG f23be94a §5 integrity gate, per question: within every held-out pair, labels OPPOSITE on this
question, EQUAL on the other, and rendered state BYTE-IDENTICAL once the masked field is removed.
integrity2.py <suite> <qkey> <masked_field> <other_qkey>   pair key = id with the flip-variant segment removed."""
import json, sys
from collections import defaultdict
sys.path.insert(0,"/Users/midas/Desktop/cowork/jev/work/kevsrc"); from kev.api import render
suite,qk,field,oq=sys.argv[1:5]
rows=[json.loads(l) for l in open(f"{suite}/development.jsonl")]
SEG={"scope":0,"destructive":1,"recipient":0,"secret":1}[qk]          # which variant segment this question flips
pairs=defaultdict(list)
for r in rows:
    v=r["_meta"]["variant"].split("/"); hold=tuple(x for i,x in enumerate(v) if i!=SEG)
    pairs[(r["_meta"]["group_id"],r["_meta"]["id"].split("/")[2],hold)].append(r)
bad=[]; n=0
def strip(st):
    st=json.loads(json.dumps(st))
    if field in st: st.pop(field)
    else: st["proposed_message"].pop(field) if field in st.get("proposed_message",{}) else st["proposed_operation"].pop(field)
    return render(st)
for k,pr in pairs.items():
    if len(pr)!=2: bad.append((k,"pair size",len(pr))); continue
    n+=1; a,b=pr
    if a["questions"][qk]["label"]==b["questions"][qk]["label"]: bad.append((k,"labels NOT opposite"))
    if a["questions"][oq]["label"]!=b["questions"][oq]["label"]: bad.append((k,"other question label CHANGED"))
    if strip(a["state"])!=strip(b["state"]): bad.append((k,"masked inputs DIFFER"))
print(f"  {suite} {qk}: held-out pairs {n}  violations {len(bad)}  -> {'PASS' if not bad and n>=300 else '*** FAIL ***' if bad else f'*** only {n} pairs ***'}")
for v in bad[:4]: print("   ",v)
