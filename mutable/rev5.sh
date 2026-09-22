#!/bin/bash
# PREREG Rev 5 (befe024c) run: fresh eval-only suites -> integrity -> torch refs -> ANE passes on the ONE base -> hs refs -> acceptance.
set -u; cd /Users/midas/Desktop/cowork/jev/work/w2d; PY=/Users/midas/.mlx-env/bin/python3; F=fresh; T=256
ANED=/Library/Caches/com.apple.aned; TRUST=/var/db/AppleIntelligencePlatform/AppModelAssets/w2d; MD=$ANED/kev_inputs.mlmodelc; K="@model_path/weights/adapter.bin"
echo "=== 1. fresh suites + integrity gates ==="; $PY build_fresh.py
$PY integrity2.py $F/suite_W scope authorized_write_scope destructive; $PY integrity2.py $F/suite_W destructive kind scope
$PY integrity2.py $F/suite_D recipient authorized_recipients secret; $PY integrity2.py $F/suite_D secret body recipient
echo "=== 2. torch tier on fresh: bars + references (packed own, fixed-head cross) ==="
$PY score2.py runs/W $F/suite_W --tag fresh; $PY score2.py runs/D $F/suite_D --tag fresh
$PY score2.py runs/D $F/suite_W --head runs/W --tag fresh_fixedhead_HW | grep -E "^\s+\["; $PY score2.py runs/W $F/suite_D --head runs/D --tag fresh_fixedhead_HD | grep -E "^\s+\["
echo "=== 3. inputs ==="
$PY prep4.py $F/suite_W/development.jsonl $F/_in_W $T; $PY prep4.py $F/suite_D/development.jsonl $F/_in_D $T
$PY prep4.py $F/suite_W/development.jsonl $F/_in_W_scope $T --only scope; $PY prep4.py $F/suite_W/development.jsonl $F/_in_W_destr $T --only destructive
$PY prep4.py $F/suite_D/development.jsonl $F/_in_D_recip $T --only recipient; $PY prep4.py $F/suite_D/development.jsonl $F/_in_D_secret $T --only secret
NW=$($PY -c "import json;print(json.load(open('$F/_in_W/meta.json'))['n'])"); ND=$($PY -c "import json;print(json.load(open('$F/_in_D/meta.json'))['n'])")
echo "=== 4. hs references (torch KevIn, 4 combinations) in the background ==="
( $PY hs_ref.py runs/W $F/_in_W $F/ref_W_on_W.npz; $PY hs_ref.py runs/D $F/_in_W $F/ref_D_on_W.npz ) > $F/hsref_a.log 2>&1 &
( $PY hs_ref.py runs/D $F/_in_D $F/ref_D_on_D.npz; $PY hs_ref.py runs/W $F/_in_D $F/ref_W_on_D.npz ) > $F/hsref_b.log 2>&1 &
echo "=== 5. ANE passes on the ONE base ==="; rm -f ts_rev5.log
sudo -n log stream --level debug --style compact --predicate 'process == "aned" OR eventMessage CONTAINS "fvmlib" OR eventMessage CONTAINS "utable kernel section"' > /tmp/w2d_rev5.log 2>/dev/null & LP=$!; sleep 3
run(){ sudo -n ./kev4 $MD 3 $K $TRUST/$1.bin $2 $3 hs_$4.f16 ts_rev5.log | tail -1 | sed "s/^/  $4: /"; }
run W $F/_in_W $NW fW_on_W; run D $F/_in_D $ND fD_on_D; run W $F/_in_W $NW fW_on_W_again; run W $F/_in_D $ND fW_on_D; run D $F/_in_W $NW fD_on_W
run W $F/_in_W_scope $NW fW_scope; run W $F/_in_W_destr $NW fW_destr; run D $F/_in_D_recip $ND fD_recip; run D $F/_in_D_secret $ND fD_secret
sleep 3; sudo -n kill $LP 2>/dev/null; sleep 1
echo "  fvmlib overflow: $(grep -icE 'too many fvmlib' /tmp/w2d_rev5.log)   Has mutable kernel section: $(grep -c 'Has mutable kernel section' /tmp/w2d_rev5.log)   base md5: $(sudo -n md5 -q $MD/weights/weight.bin)"
echo "  RETENTION W->D->W bitwise (fresh W inputs): $(cmp -s hs_fW_on_W.f16 hs_fW_on_W_again.f16 && echo True || echo FALSE)"
wait; echo "  hs refs: $(grep -c 'HS_REF DONE' $F/hsref_a.log $F/hsref_b.log | tr '\n' ' ')"
echo "=== 6. acceptance ==="; $PY analyze_rev5.py
echo "=== REV5 DONE ==="
