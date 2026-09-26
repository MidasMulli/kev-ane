# PREREG 2026-09-24 - A''' harden: the A'' comparison at 200 fresh contracts, rubric tightened

Status: SIGNED (Astra, plan review 2026-09-24, with the universal-exclusion condition adopted; `PLAN_2026-09-24_after_A2prime.md`).
Operator: "go". Everything not stated here is IDENTICAL to `PREREG_DRAFT_2026-09-24_A2prime_close_the_gap.md` (frozen adapter CUA,
frozen policy P2 top-3, frozen question wording and parsers, PIPE vs FULL cold and alternating, blind 2+1 adjudication, gates).

## 1. Test set (drawn AFTER this file is written)
- Pool: the same Pile-of-Law atticus validation shard 0 filter (first 3,000 chars contain "agreement"; 8,000-32,000 Qwen tokens).
- **Universal exclusion (Astra's condition), recorded before the draw:** drop any document matching ANY of the 510 CUAD contracts (this
  covers TRAIN, DEV, ADMIT, A3 TEST, A-long and the envelope contracts) or ANY of the 60 A'' contracts, by exact text hash OR 6-word-shingle
  Jaccard > 0.3 on the first 1,500 words. Counts dropped are reported.
- Seeded draw (seed 20260927) of **200** contracts. Hash printed before any arm runs.

## 2. Rubric, tightened on the two A'' split cases (frozen now; applies to all four adjudicators equally)
- Agreement date, in this order: (a) a date the document states it is made, entered into, or dated as of; (b) otherwise its stated
  effective date, including a defined "Effective Date" that resolves to a calendar date anywhere in the document, and a plan's or
  instrument's "became/becomes effective" date; (c) otherwise the latest party signature date in the signature block; (d) otherwise NONE.
  A date given only as month and year (or year) is answered at that precision and matches only at that precision.
- Governing law, renewal term, non-renewal notice: unchanged from A''.
- "both_acceptable" = the two answers are the same jurisdiction, the same date at the precision stated, or the same duration
  (years = 12 months).

## 3. Gates and kill (bars unchanged)
- G-E2E: lower bound of PIPE - FULL >= -0.05 (contract-clustered). G-LAT: upper bound of median per-contract (PIPE - FULL) < 0.
- Kill: after 50 contracts, if PIPE-vs-FULL agreement < 0.80, stop and file.
- Reported: kappa between adjudicators 1 and 2 (A'' was 0.323), agreement, disagreement table, the sensitivity of the verdict to each
  arbitrated item.
- Budget: about 200 x (27 s FULL + 7 s PIPE), about 2 h of GPU.

## 4. Not claimed
As A''. A PASS here is the robustness check Astra asked for; a FAIL here supersedes A'''s borderline PASS in any summary.

## Log
- 2026-09-24 written by CC before the draw.
- 2026-09-24 **Set drawn**: `work/cuad/fresh/fresh200.json` (beaeb7b0294e); pool 28,542; universal exclusion removed 7 candidates while drawing (it fires); kept 200.
- 2026-09-24 **A''' RESULT: PASS (robust)** -0.011 [-0.021, -0.001]; kappa 1.0; latency -19.4 s. `RESULT_2026-09-24_A3prime_harden.md`.
