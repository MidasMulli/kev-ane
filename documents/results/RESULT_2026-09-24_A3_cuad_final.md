# RESULT 2026-09-24: Program A / A3 (frozen TEST). NOT PASS: latency gate PASS, accuracy gate FAIL

Design: `PREREG_DRAFT_2026-09-24_A_cuad_contract_review.md` (signed CC + Astra). 95 TEST contracts with value questions (1 of 96 has
none), 202 questions, one run, no re-tuning. Raw `work/cuad/a3_raw.jsonl` (2c73383d83a0). Adapter CUA (A1 step 500), tau from DEV.

| | PIPE (ANE map -> 27B reads selected windows) | FULL (27B reads whole contract) |
|---|---|---|
| accuracy | 0.936 | 0.975 |
| median end-to-end latency per contract | 3.51 s (ANE stage included) | 12.45 s |
| median 27B prompt tokens | 1,127 | 6,321 |

- **G-E2E FAIL:** PIPE - FULL = -0.040, contract-clustered 95% CI [-0.075, -0.005]; the bar needed the lower bound >= -0.05.
- **G-LAT PASS:** median per-contract (PIPE - FULL) = -9.12 s, CI [-11.98, -6.33]; 3.5x faster at the median.
- G-SEL (reported, gates nothing): hit@2 0.911, CI [0.871, 0.949]. DEV had been 1.00 (83/83): DEV did not predict TEST.
- Per type (PIPE / FULL): Governing Law 1.00 / 1.00; Agreement Date 0.944 / 0.944; **Renewal Term 0.762 / 1.00; Notice Period 0.833 / 1.00**.
- Descriptive presence map (41 types, TEST): micro-F1 0.685; NULL false-positive rate on absent types 0.258. Value types: GL 0.968,
  AD 0.968, RT 0.627, NP 0.476.
- Base md5 unchanged.

## Where the accuracy went (every PIPE/FULL disagreement read from the raw: 12 total, PIPE lost 10, won 2)
- **7 of 10 losses are tau NULLs**: the ANE's top score for Renewal Term / Notice Period fell below the DEV-set threshold (0.972 / 0.990),
  so NO window was sent and the 27B answered NONE. These tau values were flagged as a risk when A1 was filed; DEV had only 10 and 5
  positives for these types, so the thresholds were fit to almost nothing.
- 1 scoring-rule loss: PIPE "12 months" vs gold "1 year" (declared exact-unit rule; FULL happened to say "1 year").
- 2 selection/reading losses on Agreement Date (a wrong window picked; one NONE with windows sent). PIPE won 2 Agreement Date items FULL
  got wrong.
- Governing Law: 74/74 both arms. (CORRECTED 2026-09-24: first filed as 76/76, which was the presence-positive count, not the question count.)

## What this does and does not show
- Shows: on real public contracts, one ANE read (about 29 ms per 256-token window) plus a 27B reading about 1.1k tokens is 3.5x faster than
  the 27B reading the whole contract, at 0.936 vs 0.975 accuracy; the loss is concentrated in two rare types and mostly in one mechanism
  (the NULL threshold), not in window ranking.
- Does NOT show non-inferiority at the 0.05 margin. No bar moved (SR 27). Removing the NULL rule or refitting tau is a NEW design,
  not a reanalysis; the ANE scores for the NULLed items were not logged, so whether their top-2 windows held the answer is UNMEASURED.
