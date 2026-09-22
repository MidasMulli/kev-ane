"""Rev 5 §4: FRESH eval-only suites for both domains from new-seed families. Every family -> development;
no training partition. Overlap check against the TRAINING families (roots / rosters / body sentences)."""
import json, glob, os, sys, hashlib, posixpath
fw=[json.loads(l) for p in sorted(glob.glob("fresh/families_w_*.jsonl")) for l in open(p)]
fd=[json.loads(l) for p in sorted(glob.glob("fresh/families_d_*.jsonl")) for l in open(p)]
tw=[json.loads(l) for l in open("../wscope/families.jsonl")]; td=[json.loads(l) for p in sorted(glob.glob("families_d*.jsonl")) if "discarded" not in p for l in open(p)]
roots_tr={f["root"] for f in tw}; ov=[f["root"] for f in fw if f["root"] in roots_tr]
ros_tr={a for f in td for a in f["authorized"]}; ovd=[a for f in fd for a in f["authorized"] if a in ros_tr]
sent_tr={s.strip().lower() for f in td for m in f["messages"] for s in m.split(".")}; ovs=sum(1 for f in fd for m in f["messages"] for s in m.split(".") if s.strip().lower() in sent_tr and len(s)>20)
print(f"  fresh W families {len(fw)} (root overlap with training: {len(ov)} {ov[:3]});  fresh D families {len(fd)} (roster overlap: {len(ovd)} {ovd[:3]}; body sentence overlap: {ovs})")
fw=[f for f in fw if f["root"] not in roots_tr]; fd=[f for f in fd if not any(a in ros_tr for a in f["authorized"])]
open("fresh/families_w.jsonl","w").write("".join(json.dumps(f)+"\n" for f in fw)); open("fresh/families_d.jsonl","w").write("".join(json.dumps(f)+"\n" for f in fd))
# reuse the two builders with all families forced to development
for script,src,out in (("build_w2.py","fresh/families_w.jsonl","fresh/suite_W"),("build_d.py","fresh/families_d.jsonl","fresh/suite_D")):
    s=open(script).read()
    s=s.replace('open("../wscope/families.jsonl")',f'open("{src}")').replace('sorted(glob.glob("families_d*.jsonl")) if "discarded" not in p','["'+src+'"]')
    s=s.replace('SPLIT={f["family"]:("train" if i<cut1 else "calibration" if i<cut2 else "development") for i,f in enumerate(fams)}','SPLIT={f["family"]:"development" for f in fams}')
    s=s.replace('"suite_W"','"'+out+'"').replace('"suite_D"','"'+out+'"').replace('f"suite_W/','f"'+out+'/').replace('f"suite_D/','f"'+out+'/').replace('write_scope2/{r','write_scope2f/{r').replace('disclosure/{r','disclosuref/{r')
    s=s.replace('"family"]=f"fam{i:04d}"','"family"]=f"ffam{i:04d}"').replace('"family"]=f"dfam{i:04d}"','"family"]=f"fdfam{i:04d}"')
    exec(compile(s,script,"exec"),{"__name__":"__main__"})
