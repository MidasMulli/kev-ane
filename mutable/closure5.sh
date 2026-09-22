#!/bin/bash
# Rev 5 closure: dispatch 1:1 and rails with adjacent idle ON THE FRESH INPUTS (Astra: carried observations do not close the signed protocol).
set -u; cd /Users/midas/Desktop/cowork/jev/work/w2d; PY=/Users/midas/.mlx-env/bin/python3; F=fresh
ANED=/Library/Caches/com.apple.aned; TRUST=/var/db/AppleIntelligencePlatform/AppModelAssets/w2d; MD=$ANED/kev_inputs.mlmodelc; K="@model_path/weights/adapter.bin"
echo "=== dispatch: xctrace over 300 issued predictions under W on fresh W inputs, 1:1 reconciliation ==="
rm -rf /tmp/w2d5.trace ts_dispatch5.log; sudo -n xcrun xctrace record --instrument "Neural Engine" --output /tmp/w2d5.trace --launch -- $PWD/kev4 $MD 3 $K $TRUST/W.bin $PWD/$F/_in_W 300 /tmp/disp5.f16 $PWD/ts_dispatch5.log >/dev/null 2>&1
sudo -n xcrun xctrace export --input /tmp/w2d5.trace --xpath '/trace-toc/run[@number="1"]/data/table[@schema="ane-hw-intervals"]' --output /tmp/w2d5.xml >/dev/null 2>&1
$PY dispatch2.py ts_dispatch5.log /tmp/w2d5.xml
echo "=== rails: ADJACENT idle (6 x 300 ms) then loaded under W on fresh inputs (12 x 300 ms), then under D ==="
for arm in idle W D; do
  if [ $arm != idle ]; then IN=$([ $arm = W ] && echo $F/_in_W || echo $F/_in_D); N=$([ $arm = W ] && echo 600 || echo 600); sudo -n ./kev4 $MD 3 $K $TRUST/$arm.bin $IN $N /tmp/rails5.f16 ts_rails5.log > /tmp/rails5_$arm.log 2>&1 & RP=$!; sleep 1.5; fi
  sudo -n powermetrics -i 300 -n $([ $arm = idle ] && echo 6 || echo 12) -s cpu_power,gpu_power,ane_power 2>/dev/null | grep -E "^(CPU|GPU|ANE) Power" | $PY -c "
import sys,re,collections; d=collections.defaultdict(list)
for l in sys.stdin:
    m=re.match(r'(\w+) Power:\s*(\d+)',l); d[m.group(1)].append(int(m.group(2))) if m else None
for k in ('CPU','GPU','ANE'): print(f'  $arm {k} mean {sum(d[k])/len(d[k]):7.0f} mW  (n={len(d[k])})' if d[k] else f'  $arm {k}: INSTRUMENT SILENT')"
  [ $arm != idle ] && wait $RP && tail -1 /tmp/rails5_$arm.log | sed "s/^/  workload $arm: /"
done
echo "=== CLOSURE5 DONE ==="
