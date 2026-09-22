"""Label-shuffle MUTATION suite (PREREG §5): permute each question's labels within the TRAIN partition, keep
everything else byte-identical. The held-out partition is untouched (scored against TRUE labels).
make_shuffled.py <suite> <out_suite>"""
import json, os, random, hashlib, shutil, sys
src,dst=sys.argv[1],sys.argv[2]; os.makedirs(dst,exist_ok=True); rng=random.Random(99)
man=json.load(open(f"{src}/manifest.json"))
for split in ("train","calibration","development","test"):
    rows=[json.loads(l) for l in open(f"{src}/{split}.jsonl")]
    if split=="train":
        for q in rows[0]["questions"]:
            labs=[r["questions"][q]["label"] for r in rows]; rng.shuffle(labs)
            for r,l in zip(rows,labs): r["questions"][q]["label"]=l
    p=f"{dst}/{split}.jsonl"; open(p,"w").write("".join(json.dumps(r)+"\n" for r in rows))
    man["files"][f"{split}.jsonl"]["sha256"]=hashlib.sha256(open(p,"rb").read()).hexdigest()
man["protocol"]["mutation"]="train labels permuted per question (seed 99); held-out untouched"
json.dump(man,open(f"{dst}/manifest.json","w"),indent=1); print(f"  {dst}: train labels shuffled")
