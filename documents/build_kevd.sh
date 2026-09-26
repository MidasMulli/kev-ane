#!/bin/zsh
# Build + ad-hoc sign the resident ANE daemon from ../mutable/ui/kevd.mm. The four private aned entitlements are only
# honored on an unlocked research machine (SIP off, amfi_get_out_of_my_way=1); see ../mutable/README.md.
set -e
HERE=${0:A:h}; SRC=$HERE/../mutable/ui/kevd.mm; OUT=${1:-$HERE/../mutable/ui/kevd}
xcrun clang++ -std=c++17 -O2 -arch arm64 -fobjc-arc "$SRC" -o "$OUT" -framework Foundation -framework CoreML
codesign -f -s - --entitlements "$HERE/kevd.entitlements" "$OUT"
echo "built + signed: $OUT"
