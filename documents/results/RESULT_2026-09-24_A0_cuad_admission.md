# RESULT 2026-09-24: Program A / A0 (CUAD receiver admission). ADMITTED

Design: `PREREG_DRAFT_2026-09-24_A_cuad_contract_review.md` (signed CC + Astra). 27B only; 60 ADMIT contracts, 127 value questions, one
cold request per contract per arm, reasoning_effort none, temperature 0. Splits sha 7c0f095e56a3; cuad_common 4367e946110d.

| arm | accuracy | n |
|---|---|---|
| FULL (whole contract) | 0.969 | 127 |
| GOLD (annotated spans only) | 0.976 | 127 |
| NONE (questions only) | 0.000 | 127 |

- ADMIT rule: GOLD >= 0.50 (0.976) AND GOLD - NONE lower 95% bound >= 0.15 (CI [0.938, 1.000], contract-clustered) -> **ADMITTED**.
- FULL - GOLD CI [-0.025, 0.000]: the 27B reading the whole contract is near ceiling. Consequence for A3: PIPE must lose less than 0.05
  against a baseline of about 0.97, so ANE selection has to be very accurate (the bar was set before this was known; it is not moved).
- Per type (FULL / GOLD / n): Governing Law 1.00 / 1.00 / 47; Agreement Date 0.96 / 0.98 / 53; Renewal Term 0.94 / 0.94 / 17;
  Notice Period 0.90 / 0.90 / 10.
- NONE = 0.000: the 27B answers NONE without text on every question; no memorized-contract leakage seen.
- Raw `work/cuad/a0_raw.jsonl` (c4c2e5f83a02). Known emission defect (scoring unaffected): one ADMIT contract has no gradeable question; its three
  requests carry the whole running list in the `ok` field (`rows[-0:]`); the verdict is computed from `rows`, which is correct. A3 skips
  such contracts. Attempt 1 void (see the prereg log).
