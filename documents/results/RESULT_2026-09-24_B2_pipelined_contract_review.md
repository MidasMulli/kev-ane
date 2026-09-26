# RESULT 2026-09-24: Program B2 (pipelined ANE map + 27B). PASS: pipelining raises throughput +46%

Design `PREREG_DRAFT_2026-09-24_B2_pipelined_contract_review.md` (signed CC + Astra). 24 contracts (first 24 of A3 TEST with value
questions; reuse stated, no accuracy claim), adapter CUA, T=256, top-2 windows per asked value type, cold 27B requests. 5 reps, order
alternating. Raw `work/cuad/b2_raw.jsonl` (5c5b4443a4bb).

| rep | SEQ wall s | PIPE wall s | gain | 27B per-request PIPE/SEQ (median) | response mismatches |
|---|---|---|---|---|---|
| 0 | 89.9 | 63.1 | +0.424 | 1.006 | 0/24 |
| 1 | 89.4 | 62.6 | +0.428 | 1.000 | 0/24 |
| 2 | 88.9 | 60.0 | +0.481 | 0.988 | 0/24 |
| 3 | 89.4 | 60.7 | +0.474 | 0.997 | 0/24 |
| 4 | 88.3 | 58.6 | +0.506 | 0.998 | 0/24 |

- **Gain = wall(SEQ)/wall(PIPE) - 1: +0.462, CI [0.436, 0.489] -> "pipelining RAISES throughput"** (bar: lower >= 0.05).
- Ceiling for this workload (from SEQ timings, (ANE + 27B) / max - 1): +0.513. PIPE reaches about 90% of it: the ANE stage (about 30 s of
  ANE time per 24 contracts) is almost fully hidden behind the 27B (about 59 s).
- 27B per-request time beside the running ANE map: median ratio 0.998 (no measurable slowdown on these prefill-heavy requests; T=256 is
  the low-weight-traffic setting from B1b). GPU power rises from about 35 W (SEQ) to 43-53 W (PIPE) because the GPU is idle less.
- All responses identical between modes (0 mismatches in 120 pairs). Base md5 unchanged.
- Not claimed: accuracy (A3 stands); other workloads, request mixes or batch sizes.
