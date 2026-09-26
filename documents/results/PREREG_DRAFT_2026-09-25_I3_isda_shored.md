# PREREG DRAFT 2026-09-25 - I3: ISDA with the three weak fields shored up, on FRESH EDGAR documents

Status: DRAFT, UNSIGNED. Operator: "Can you shore up the weak points?" and authorized his email as the SEC EDGAR User-Agent contact.
Parent: I2 NOT PASS by 0.004 (`RESULT_2026-09-25_I2_isda_masters.md`); I2 stays filed.

## 1. Changes from I2 (all fixed now; everything else identical: 12 questions, rubric, CUA architecture, gates, 2+1 blind adjudication)
1. **Label anchors (the I2 diagnosis):** Form -> the document's first page (Master title / copyright line) AND the Schedule header;
   Threshold Amount -> the "Threshold Amount" heading, else the Cross Default paragraph; Credit Support Annex -> headings "Credit Support
   Annex", "Credit Support Document" or "Credit Support Provider". Retrain on I2's TRAIN 160 (DEV 25 for the checkpoint), same schedule.
   Spot check of 20 new-anchor labels before training (>= 18/20), as I2.
2. **Keyword sidecar at inference (automated verification):** for Form, Threshold Amount and Credit Support Annex only, add up to 2 windows
   each that contain "1992"/"2002", "threshold", "credit support" (first occurrences in document order) to the ANE top-3. Deterministic;
   fixed before data.
3. **Fresh TEST from SEC EDGAR:** full-text search for Schedule/ISDA Master phrases, documents fetched from the Archives, the FROZEN I2
   classifier applied, anything matching the 241-doc corpus (exact or 6-gram Jaccard > 0.3) or another pulled doc dropped. A 30-doc blind
   validation gate as I2 (>= 28/30 genuine) on the pulled pool; then a seeded draw of 56 TEST docs. No pulled doc is used in training.

## 2. Gates (unchanged from I2)
G-E2E: PIPE - FULL lower 95% >= -0.05 (document-clustered, blind adjudication). G-LAT: upper < 0. G-SWAP: CUA <-> IS3 bitwise.
Reported per question, and the three shored fields separately vs I2.

## 3. Not claimed
That the fixes are complete; that the result transfers to non-EDGAR ISDAs.

## Log
- 2026-09-25 drafted by CC.
- 2026-09-25 **Astra SIGNED I3** ("The corrected anchors, frozen keyword sidecar, fresh EDGAR search, deduplication, and blind validation gate address I2's weaknesses. The design is signed as scoped.").
- 2026-09-25 **Label spot check v1 FAILED 12/20** (Form 5/7: fallback to first page when no year stated; Threshold 5/7: Cross Default paragraphs saying Not Applicable; CSA 2/6: first match was a passing mention). Anchors revised: Form ONLY on an explicit year pattern (else no label); Threshold via Cross Default ONLY if the paragraph states an amount or percentage; CSA only on a line-start heading/election form ('Credit Support Document/Provider/Annex' followed by ':' '.' 'means' or 'Details of any Credit Support Document'). Re-check on a NEW 20-item sample (seed 13), gate unchanged.
- 2026-09-25 **Label spot check v2 FAILED 12/20**: CSA 6/6, Threshold 6/7, Form 0/7 = CC's offset BUG (a first-page match was shifted by the Schedule offset). Fixed; v3 re-check on a NEW sample (seed 14).
- 2026-09-25 **Label spot check v3 PASS 19/20** (Form 7/7, CSA 6/6, Threshold 6/7; miss = a Threshold defined by reference to a Fee Letter). TRAIN labels: Form 89/160, Threshold 105/160, CSA 123/160 (precision over coverage). I3 training launched.
- 2026-09-25 **EDGAR validation gate PASS 30/30** (2 blind judges; borderline notes: a blank FORM OF Schedule and a Schedule attached to a confirmation, both counted genuine per the rule). Pool `work/isda3/edgar_pool.json`: 92 fresh docs.
- 2026-09-25 **I3 RESULT: PASS** (E2E -0.019 [-0.036, -0.004]; LAT -9.2 s; SWAP PASS; kappa 0.909). `RESULT_2026-09-25_I3_isda_shored.md`.
