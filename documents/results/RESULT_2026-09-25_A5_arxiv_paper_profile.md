# RESULT 2026-09-25 - A5: arXiv PAPER PROFILE adapter AX2: **PASS**

Prereg: `PREREG_DRAFT_2026-09-25_A5_arxiv_paper_profile.md` (Astra-signed; label gate passed at v5 19/20; futility look passed).
Raw `work/a5/a5_test_raw.jsonl`; score `work/a5/a5_score.json`; adjudication `work/a5/adj_h1`, `adj_h2`, merged `adj_all` (sealed 37b7e18901b2 / dc5c69cd07e8).
Scope (Astra): the pass holds for these 12 questions on papers from this snapshot, nothing wider.

| gate | statistic | bar | result |
|---|---|---|---|
| G-E2E | PIPE - FULL = **-0.010 [-0.027, +0.004]** (paper-clustered, 672 questions, 56 fresh papers) | lower >= -0.05 | PASS |
| G-LAT | median per-paper (PIPE - FULL) = **-25.4 s [-30.1, -21.3]**; PIPE 17.1 s vs FULL 41.6 s (2.4x) | upper < 0 | PASS |
| G-SWAP | CUA -> IS3 -> AX2 -> CUA bitwise on return, three distinct, base md5 unchanged, both halves | all | PASS |

- Agreement before adjudication 569/672 (0.847). 103 disagreements, blind 2+1: kappa(a1, a2) 0.875, 5 arbitrated.
  PIPE-only correct 7, FULL-only correct 14, both acceptable 80, both wrong 2.
- Median prompt tokens PIPE 6,375 vs FULL 18,816 (about one third).
- Interim futility look at 28 papers: -0.006 [-0.021, +0.009], continued (logged before the second half ran).

## Per question (FULL-only minus PIPE-only)
Parameters -3 · Limitations -2 · Code -2 · Baselines -2 · Optimizer -1 · Training time 0 (2 vs 2) · Method name 0 · Headline result +2 ·
Hardware +1 · Task, Main metric, Datasets: 0 (all disagreements both acceptable or both wrong).
The residual loss sits in the sparsely labelled fields (Parameters 17 anchored labels, Limitations 18, Code 77): consistent with label
coverage, not tested.

## Notes
- Training (see operator note on the record): best DEV at step 1,000 of 3,000, held-out flat from there; selection used the held-out
  checkpoint, so the verdict stands; the coarse 500-step eval grid is a known defect (TRAINING_BLUEPRINT G1/G2/G4), fixed from the next adapter.
- Adjudicator incident (half 1): a shared helper-script filename in the scratchpad; audited, no verdict content shared, independence intact.
- Label gate took five rounds (9, 12, 16, 17, 19 of 20), each on a new sample, logged in the prereg.

## Log
- 2026-09-25 filed by CC.
