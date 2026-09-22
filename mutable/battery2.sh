#!/bin/bash
# PREREG f23be94a §5 deployment battery on ONE resident base (G0 artifact) with adapters W and D.
# Usage: battery2.sh   (after runs/W, runs/D exist and both suites are frozen). Unattended.
set -u; cd /Users/midas/Desktop/cowork/jev/work/w2d; PY=/Users/midas/.mlx-env/bin/python3
ANED=/Library/Caches/com.apple.aned; TRUST=/var/db/AppleIntelligencePlatform/AppModelAssets/w2d; MD=$ANED/kev_inputs.mlmodelc; T=256; K="@model_path/weights/adapter.bin"
echo "=== 0. pack W and D against the G0 base (offsets must equal the base's repoint) ==="
$PY deploy_inputs.py pack _out $T W runs/W && $PY deploy_inputs.py pack _out $T D runs/D || { echo PACK_FAIL; exit 1; }
sudo -n cp _out/adapter_W.bin $TRUST/W.bin; sudo -n cp _out/adapter_D.bin $TRUST/D.bin; echo "  base md5 before: $(sudo -n md5 -q $MD/weights/weight.bin)"
echo "=== 1. inputs: every held-out record, packed and per-question ==="
$PY prep4.py suite_W/development.jsonl _in_W $T && $PY prep4.py suite_D/development.jsonl _in_D $T
$PY prep4.py suite_W/development.jsonl _in_W_scope $T --only scope && $PY prep4.py suite_W/development.jsonl _in_W_destr $T --only destructive
$PY prep4.py suite_D/development.jsonl _in_D_recip $T --only recipient && $PY prep4.py suite_D/development.jsonl _in_D_secret $T --only secret
NW=$($PY -c "import json;print(json.load(open('_in_W/meta.json'))['n'])"); ND=$($PY -c "import json;print(json.load(open('_in_D/meta.json'))['n'])")
rm -f ts_battery.log; sudo -n log stream --level debug --style compact --predicate 'process == "aned" OR eventMessage CONTAINS "fvmlib" OR eventMessage CONTAINS "utable kernel section"' > /tmp/w2d_bat.log 2>/dev/null & LP=$!; sleep 3
echo "=== 2. bogus path must -14 ==="; sudo -n ./kev4 $MD 3 $K $TRUST/DOES_NOT_EXIST.bin _in_W 1 /tmp/bogus.f16 ts_battery.log | head -1
echo "=== 3. passes on the ONE base: W(W) D(D) W(W) again; wrong-domain W(D) D(W); per-question separate ==="
run(){ sudo -n ./kev4 $MD 3 $K $TRUST/$1.bin $2 $3 hs_$4.f16 ts_battery.log | tail -1 | sed "s/^/  $4: /"; }
run W _in_W $NW W_on_W;   run D _in_D $ND D_on_D;   run W _in_W $NW W_on_W_again
run W _in_D $ND W_on_D;   run D _in_W $NW D_on_W
run W _in_W_scope $NW W_scope_only; run W _in_W_destr $NW W_destr_only; run D _in_D_recip $ND D_recip_only; run D _in_D_secret $ND D_secret_only
sleep 3; sudo -n kill $LP 2>/dev/null; sleep 1
echo "  fvmlib overflow: $(grep -icE 'too many fvmlib' /tmp/w2d_bat.log)   Has mutable kernel section: $(grep -c 'Has mutable kernel section' /tmp/w2d_bat.log)   base md5 after: $(sudo -n md5 -q $MD/weights/weight.bin)"
echo "  RETENTION W->D->W bitwise: $(cmp -s hs_W_on_W.f16 hs_W_on_W_again.f16 && echo True || echo FALSE)"
echo "=== 4. analysis (fidelity, fixed-head, wrong-domain, packed-vs-separate) ==="; $PY analyze_battery2.py
echo "=== 5. dispatch: xctrace over 300 issued predictions under W, 1:1 reconciliation ==="
rm -rf /tmp/w2d.trace ts_dispatch.log; sudo -n xcrun xctrace record --instrument "Neural Engine" --output /tmp/w2d.trace --launch -- $PWD/kev4 $MD 3 $K $TRUST/W.bin _in_W 300 /tmp/disp.f16 $PWD/ts_dispatch.log >/dev/null 2>&1
sudo -n xcrun xctrace export --input /tmp/w2d.trace --xpath '/trace-toc/run[@number="1"]/data/table[@schema="ane-hw-intervals"]' --output /tmp/w2d.xml >/dev/null 2>&1
$PY dispatch2.py ts_dispatch.log /tmp/w2d.xml
echo "=== 6. rails with ADJACENT idle: idle 6 samples, then loaded under W ==="
sudo -n powermetrics -i 300 -n 6 -s cpu_power,gpu_power,ane_power 2>/dev/null | grep -E "^(CPU|GPU|ANE) Power" | sed 's/^/  idle  /' | sort | uniq -c | head -3
sudo -n ./kev4 $MD 3 $K $TRUST/W.bin _in_W 300 /tmp/disp.f16 ts_rails.log > /tmp/rails_run.log 2>&1 & RP=$!; sleep 1
sudo -n powermetrics -i 300 -n 12 -s cpu_power,gpu_power,ane_power 2>/dev/null | grep -E "^(CPU|GPU|ANE) Power" | $PY -c "
import sys,re,collections; d=collections.defaultdict(list)
for l in sys.stdin:
    m=re.match(r'(\w+) Power:\s*(\d+)',l); d[m.group(1)].append(int(m.group(2))) if m else None
for k in ('CPU','GPU','ANE'): print(f'  {k} loaded mean {sum(d[k])/len(d[k]):7.0f} mW' if d[k] else f'  {k}: INSTRUMENT SILENT')"
wait $RP; echo "=== BATTERY2 DONE ==="
