#!/bin/zsh
# Download the remaining Pile-of-Law atticus shards and scan each for genuine ISDA Master Agreements / Schedules.
cd "${0:A:h}"
for f in train.atticus_contracts.0 train.atticus_contracts.1 train.atticus_contracts.2 train.atticus_contracts.3 train.atticus_contracts.4 validation.atticus_contracts.1; do
  [ -f $f.jsonl.xz ] || curl -sL -o $f.jsonl.xz "https://huggingface.co/datasets/pile-of-law/pile-of-law/resolve/main/data/$f.jsonl.xz"
  echo "$(date +%H:%M) downloaded $f $(ls -la $f.jsonl.xz | awk '{print $5}')" >> scan.log
done
ln -sf ../cuad/fresh/val0.jsonl.xz validation.atticus_contracts.0.jsonl.xz
nice -n 10 {sys.executable} scan_master.py >> scan.log 2>&1
