"""Merge adj_h1 + adj_h2 into adj_all for the final A5 score (items prefixed h1_/h2_; sealed maps merged; copies, originals untouched)."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, os, shutil, glob
D = "adj_all"; shutil.rmtree(D, ignore_errors=True)
for sub in ("packets", "a1", "a2", "a3"): os.makedirs(f"{D}/{sub}")
M = {}
for h in ("h1", "h2"):
    S = json.load(open(f"adj_{h}/SEALED_mapping.json"))
    for k, v in S.items(): M[f"{h}_{k}"] = v
    for sub in ("packets", "a1", "a2", "a3"):
        for f in glob.glob(f"adj_{h}/{sub}/*.json"):
            d = json.load(open(f)); d["item"] = f"{h}_{d['item']}"
            json.dump(d, open(f"{D}/{sub}/{h}_{os.path.basename(f)}", "w"), indent=1)
json.dump(M, open(f"{D}/SEALED_mapping.json", "w"))
print(dict(packets=len(glob.glob(f"{D}/packets/*.json")), a1=len(glob.glob(f"{D}/a1/*.json")), a2=len(glob.glob(f"{D}/a2/*.json")), a3=len(glob.glob(f"{D}/a3/*.json")), sealed=len(M)))
