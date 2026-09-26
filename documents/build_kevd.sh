#!/bin/zsh
# Build + ad-hoc sign the resident ANE daemon from ../mutable/ui/kevd.mm. The four private aned entitlements are only
# honored on an unlocked research machine (SIP off, amfi_get_out_of_my_way=1); see ../mutable/README.md.
set -e
HERE=${0:A:h}; UI=$HERE/../mutable/ui
for NAME in kevd kevd_multi; do   # kevd: rebind per swap (published results); kevd_multi: one pre-bound instance per adapter (the demo)
  xcrun clang++ -std=c++17 -O2 -arch arm64 -fobjc-arc "$UI/$NAME.mm" -o "$UI/$NAME" -framework Foundation -framework CoreML
  codesign -f -s - --entitlements "$HERE/kevd.entitlements" "$UI/$NAME"
  echo "built + signed: $UI/$NAME"
done
