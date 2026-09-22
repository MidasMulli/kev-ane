#!/bin/bash
# PREREG G0 build gate on the SANCTIONED recipe (battery.sh): model in the aned cache, adapters in the trusted dir, sudo, units=3.
cd /Users/midas/Desktop/cowork/jev/work/w2d; ANED=/Library/Caches/com.apple.aned; TRUST=/var/db/AppleIntelligencePlatform/AppModelAssets/w2d
MD=$ANED/kev_inputs.mlmodelc; rm -f /tmp/w2d_bind.log g0_ts.log
sudo -n rm -rf "$MD"; sudo -n cp -R _out/kev_inputs.mlmodelc "$MD"; sudo -n mkdir -p $TRUST; sudo -n cp _out/adapter_g0.bin $TRUST/g0.bin
echo "  mutable consts in mil: $(grep -oE '[qkvo][AB]_[0-9]+_weight_to_fp16' $MD/model.mil | sort -u | wc -l | tr -d ' ')   BFMI: $(grep -c BlobFileMutabilityInfo $MD/model.mil)   base md5 before: $(sudo -n md5 -q $MD/weights/weight.bin)"
sudo -n log stream --level debug --style compact --predicate 'process == "aned" OR eventMessage CONTAINS "fvmlib" OR eventMessage CONTAINS "utable kernel section"' > /tmp/w2d_bind.log 2>/dev/null & LP=$!; sleep 3
echo "=== bogus adapter path (must -14) ==="; sudo -n ./kev4 $MD 3 "@model_path/weights/adapter.bin" $TRUST/DOES_NOT_EXIST.bin _in_g0 1 /tmp/bogus.f16 g0_ts.log | head -1
echo "=== bind real g0.bin, 8 records ==="; sudo -n ./kev4 $MD 3 "@model_path/weights/adapter.bin" $TRUST/g0.bin _in_g0 8 _in_g0/hs_g0.f16 g0_ts.log
sleep 3; sudo -n kill $LP 2>/dev/null; sleep 1
echo "  fvmlib overflow: $(grep -icE 'too many fvmlib' /tmp/w2d_bind.log)   Has mutable kernel section: $(grep -c 'Has mutable kernel section' /tmp/w2d_bind.log)   aned lines: $(wc -l < /tmp/w2d_bind.log | tr -d ' ')   base md5 after: $(sudo -n md5 -q $MD/weights/weight.bin)"
echo "=== placement (MLComputePlan, units 3) ==="; sudo -n ./computeplan $MD 3
echo "G0_GATE_DONE"
