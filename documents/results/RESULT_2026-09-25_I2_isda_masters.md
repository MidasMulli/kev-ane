# RESULT 2026-09-25: I2 (genuine ISDA Master Agreements/Schedules, 12 elections). NOT PASS by 0.004 on the accuracy bound; SWAP, LATENCY PASS

Prereg `PREREG_DRAFT_2026-09-25_I2_isda_masters.md` (Astra-signed; corpus gate 30/30; label spot check 19/20). Adapter IS2 (anchored labels,
160 TRAIN docs), best DEV hit@3 0.989 (I1 was 0.815). TEST 56 fresh genuine ISDA docs, 672 questions. Raw `work/isda2/i2_test_raw.jsonl`
(c3dbbafe5633); scoring `i2_result.json` (d856325d532f); sealed mapping 547be09d30ff opened after all verdicts.

| | PIPE (ANE map -> 27B) | FULL (27B reads the whole ISDA) |
|---|---|---|
| median seconds per document | 13.6 | 61.8 |
| median 27B prompt tokens | 4,287 | 28,031 |
| agreement between arms | 611 / 672 (0.909) | |

- **G-E2E FAIL (narrow):** PIPE - FULL = **-0.037**, CI **[-0.054, -0.022]**; bar lower >= -0.05, missed by 0.004. PIPE-only correct 5,
  FULL-only correct 29, one three-way split counted against PIPE (rule).
- **G-LAT PASS:** -47.8 s per document, CI [-52.9, -29.8] (4.5x faster). **G-SWAP PASS:** CUA <-> IS2 bitwise round trip, ~73 ms binds.
- Adjudication: 61 disagreements; adjudicators 59/61 agreement (kappa 0.95); 2 arbitrated.
- Where the loss is (FULL-only wins): Form 1992/2002: 8; Credit Support Annex: 7; Threshold Amount: 7; Cross Default: 3; date 2; Party A 1;
  Termination Currency 1. Governing law's 23 disagreements were all wording ("New York" vs "State of New York": both acceptable). Termination
  Currency, AET, ATEs, payment measure: near-perfect.
- Diagnosis (named, not a re-verdict): the Form answer usually lives on the Master Agreement's FIRST page (the printed form's title /
  copyright line), but the label anchor pointed Form to the Schedule's opening, so the selector rarely sent that page (a label-design
  defect of CC's). Threshold Amount is often stated inside the Cross Default paragraph, and 79/241 Schedules have no "Threshold Amount"
  heading at all, so those got no label. Credit Support: the Schedule often speaks of a "Credit Support Document" rather than an Annex.
