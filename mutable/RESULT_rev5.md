# RESULT 2026-09-21: PREREG Rev 5 (befe024c) — COMPLETE / PASS (Astra: "closes as COMPLETE / PASS on the documented evidence")

One resident kev-form base on the ANE (G0, unchanged), adapters W and D unchanged, evaluated on families
generated with new seeds after the ruling. Fresh W: 70 families, 0 root overlap with training, 2040 records,
1020 pairs per question. Fresh D: 70 generated, 62 DROPPED by the no-shared-roster-id rule (generic channel
names such as `#dev-ops` recur across organizations), 8 kept, 640 records, 320 pairs per question (bar 300;
THIN, stated). Integrity gates: 0 violations, all four questions.

## Torch tier (§3 bars, fresh)
W scope missed 6/1020 (0.59%), unnecessary 0/1020, pairs 1014/1020 (LCB 0.987). W destructive 0, 0, 1020/1020.
D recipient 0, 0, 320/320. D secret 0, 0, 320/320. Majority 0.500 everywhere.

## Silicon (9 passes, one base): predict 29.4-29.5 ms; `Has mutable kernel section` 9; fvmlib overflow 0; base md5 unchanged; RETENTION W->D->W bitwise on 2040 fresh records.
- **C1 substrate (every position):** W on W p50 1.05e-02 **max 4.98e-02** (bound 5e-2: met by 0.02e-02 on one
  position, flagged); D on D max 2.28e-02; D on W (cross) 1.26e-02; W on D (cross) 4.08e-02. 0 over. PASS.
- **C2/C3 + coverage, own:** W coverage margin>=2 1.0000, >=8 0.9995; 0 flips, 0 misses, 0 below-2. D coverage
  1.0000 / 1.0000; 0 / 0 / 0. Worst |dp| in the >=8 band: W 2.1e-05, D 3.6e-06. **PASS, both cells.**
- **Cross combinations (witness material):** 0 flips, 0 misses in their bands; coverage reported (H_W on
  D-trunk 0.025 / 0; H_D on W-trunk 0.997 / 0.426).
- **Participation:** P1 4080/4080 positions (streams differ > 0.15, both within C1). P2 H_W 76/76 reproduced,
  H_D 639/639. P3 H_W none exist (reported), H_D 278/278 within 1e-3. **Established.**
- **Parity packed vs separate:** 0 argmax mismatches, max|dp| <= 2.1e-07 (W scope and D recipient bitwise 0).
- **Wrong-domain (statistic):** 0.500-0.510 vs majority 0.500.
- **Dispatch, fresh run (closure5.sh):** 300 issued predictions matched 1:1 to 300 ANE intervals, p50 28.18 ms, 1 extra
  interval reconciled against 1 load. PASS.
- **Rails, fresh run, ADJACENT idle (6 x 300 ms) then loaded (12 x 300 ms), 600 records each:** ANE 0 -> 7050 mW (W)
  and 7063 mW (D); CPU 2133 -> 2368 / 2839 mW; GPU 349 -> 315 / 325 mW (flat: the +1.4 W GPU rise seen in the Rev 3 rails
  was other GPU activity at the time, not this workload).
- Astra on the numerical result (before closure): *"Neither the 4.98e-02 value nor the eight-family D set blocks the
  conditional numerical PASS... Report the 62 exclusions prominently; this is not evidence of broad domain coverage."*

## Claim that stands if banked (conditional, as written in Rev 5 §0)
One resident base, two 9.2 MB domain adapters each answering two typed questions per pass, swapped by URL
with bitwise retention; on fresh families the deployed adapters are within the fp16 substrate bound of their
references everywhere, reproduce every reference decision at margin >= 2 and every probability within 1e-3 at
margin >= 8, with coverage 0.9995-1.0 (bars 0.99/0.95). Not claimed: low-margin fidelity; competence beyond
these two bounded policies; that two adapters beat one.

## Addendum: placement by op-level runtime trace (operator: "MLComputePlan doesn't guarantee ANE placement")
`log stream` with the recorded 07-28 predicate (espresso / ANE / aned / ANECompilerService) across a COLD load
of a renamed copy of the base with adapter W, then 5 and 20 predictions (kev4, fresh W inputs):
- aned: `numInputs=4 : numOutputs=1 : numProcedures=1` — ONE ANE procedure for the whole model.
- kernel: `initMutableKernelSections: ... size: 0x8c0000` = 9,175,040 = W.bin 9,189,440 - 225 x 64-byte headers,
  EXACT (CQ258 positive control). ANECompilerService mapped W.bin (9,189,440 B) from the trusted dir.
- e5rt: `ResetStream() : No ops in stream` (the non-ANE stream is empty); cold compile 8.9 s; warm = cache hit.
- per prediction: 20 issued -> 20 `addWeightsBuffer: Cluster mutable index: 0 for request with procId: 0`,
  one request per pass with the mutable buffer attached.
- 0 fallback / unsupported lines; the only "cpu" line is CoreML registering BNNSGraph as an available backend.
The CPU rail rise during a burst (+1.5 W) is host work around a single-procedure ANE pass. MLComputePlan is
withdrawn as placement evidence for these artifacts; the trace above is the Rule 22 evidence.
