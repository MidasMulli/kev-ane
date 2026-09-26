# PREREG DRAFT 2026-09-24 - Program C: several adapters swapped within one request, beside 27B decode

Status: DRAFT, UNSIGNED. Operator: "Go" (2026-09-24, after B). Order A -> B -> C per Astra.

## 1. Question (systems only)
On the resident Rev 5 base, a request that walks through THREE different adapters in sequence (CUA, W, D: stage 1, 2, 3), rebinding at
every stage change, while the 27B decodes. Does swapping cost the 27B anything beyond the same ANE work done with no swaps, and what does
a swap cost under load? No task-quality claim: the three adapters are unrelated tasks; this measures the MECHANISM a multi-stage
request would use (select -> check -> decide), not such a pipeline's usefulness.

## 2. Bar correction, stated before data
The brief's kill "swap under load > 50 ms median" is dropped: the recorded idle rebind cost for this 0.6B fp16 base is 71.7 ms
(`project_ane_mutable_weights` swap sweep), so a 50 ms bar could not be met by any outcome (Bar Must Be Reachable). Replaced by the
relative rules in section 5.

## 3. Arms (during a 512-token 27B decode, measured from the stream exactly as P-RATE/B1)
- G: 27B alone.
- S0 (no swap): ANE passes at a FIXED 20 passes/s (T=256, the P2/A kev_inputs input path via kevd), adapter CUA bound once.
- S1 (swap): the same 20 passes/s, but the adapter rotates CUA -> W -> D -> CUA every 8 passes (a "stage" = 8 passes, 0.4 s at 20/s),
  so about 2.5 binds per second, each timed by kevd.
- IDLE-S1: S1 with no 27B running (bind latency reference).
Fixed rate: 20 passes/s leaves room for the binds (29 ms x 20 = 0.58 s/s of ANE time plus 2.5 x about 72 ms = 0.18 s/s). Asserted:
achieved pass rate in S0 and S1 within 5% of each other and of 20.

## 4. Preconditions (asserted; failure = no run)
- Manipulation took: on one fixed window, the three adapters give three different outputs (pairwise max |diff| > 1e-2), and after the
  rotation CUA -> W -> D -> CUA the CUA output is BITWISE identical to its first output (swap is clean and reversible).
- Base weight.bin md5 unchanged before/after. GATE 0 GREEN; RED sentinel.

## 5. Decision rules (6 reps, order G then S0/S1 alternating, paired by rep; bootstrap 95% CI; margins fixed now)
- **C-GPU:** Delta = ret(S0) - ret(S1). Upper bound < 0.05 -> "swapping costs the 27B nothing at the 0.05 margin"; lower >= 0.05 ->
  "swapping costs the 27B"; else INCONCLUSIVE.
- **C-LAT:** ratio = median bind ms under load (S1) / median bind ms idle (IDLE-S1), per rep; CI of the mean ratio. Upper bound < 1.25 ->
  "binds are not materially slowed by 27B decode"; lower >= 1.25 -> "binds slow under load"; else INCONCLUSIVE. Absolute medians printed.
- Descriptive: per-request swap overhead for a 3-stage request = 2 binds / (2 binds + 3 stages of ANE time), idle and under load.
- **Kill (fail fast):** stop if the precondition fails, if any BIND fails, or if after 3 reps the rate assertion fails.
  Budget: 6 reps x 3 decodes of about 15 s + idle arms, well under 1 h of GPU.

## 6. Not claimed
Usefulness of any multi-stage chain; other bases, sizes or precisions; swap cost with a cold file cache (all adapter files are warm).

## Log
- 2026-09-24 drafted by CC.
- 2026-09-24 **Astra SIGNED C** ("I sign C. ...Dropping the unreachable 50 ms kill is appropriate..."). Operator: "Go".
- 2026-09-24 **C RESULT**: C-GPU +0.021 [0.001, 0.046] (no cost at 0.05; small measurable cost); C-LAT 1.10 [1.089, 1.112] (74.7 -> 81.9 ms). `RESULT_2026-09-24_C_multi_adapter_under_load.md`.
