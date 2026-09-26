# RESULT 2026-09-25 - I3: ISDA, three weak fields shored, FRESH EDGAR TEST: **PASS**

Prereg: `PREREG_DRAFT_2026-09-25_I3_isda_shored.md` (Astra-signed). Parent: I2 NOT PASS by 0.004 (`RESULT_2026-09-25_I2_isda_masters.md`).
Raw: `work/isda3/i3_test_raw.jsonl`; score: `work/isda3/i3_score.json`; adjudication: `work/isda3/adjudication_i3/` (sealed sha 6c684c3140f3).

## Gates (all pass)
| gate | statistic | bar | result |
|---|---|---|---|
| G-E2E | acc(PIPE) - acc(FULL) = **-0.019 [-0.036, -0.004]** (document-clustered, 672 questions, 56 docs) | lower >= -0.05 | PASS |
| G-LAT | median per-doc (PIPE - FULL) = **-9.2 s [-11.7, -7.5]** | upper < 0 | PASS |
| G-SWAP | CUA <-> IS3 hidden states bitwise on return, CUA != IS3, base weight md5 unchanged | all | PASS |

- Agreement PIPE vs FULL before adjudication: 638/672 (0.949). 34 disagreements, blind 2+1: kappa(a1, a2) 0.909, 2 arbitrated.
- Of the 34: PIPE-only correct 6, FULL-only correct 19, both acceptable 9, both wrong 0.
- Median latency PIPE 11.4 s vs FULL 20.5 s (1.8x; ANE map 1.31 s); median prompt tokens 4,355 vs 9,648.
  The speed ratio is smaller than I2's 4.5x because the EDGAR TEST documents are shorter (median 9.6k tokens): the gain scales with length.

## Where the loss is (FULL-only minus PIPE-only, per question)
Form -2 (5 vs 3) · Party A -3 · Threshold Amount -2 · AET -2 · Cross Default -1 · Party B -2 · ATE -1 · date -1 · CSA 0 (1 vs 1) ·
Termination Currency +1 · Governing law 0 (7 both acceptable).
The three shored fields cost I2 8 / 7 / 7 FULL-only wins; here 5 / 1 / 2 (net -2 / 0 / -2). ⚠️ Different TEST documents (I2 = held-out
Pile-of-Law, I3 = fresh EDGAR), so this is not a paired comparison of the fixes; it is consistent with the diagnosis, not proof of it.

## What this establishes (and not)
- Established: on 56 genuine ISDA documents never seen in training, pulled fresh from SEC EDGAR, the ANE-selected excerpts let the 27B
  answer the 12 elections within the pre-registered 0.05 margin of reading the whole document, faster, with the adapter swapped in and
  out of the resident base bitwise.
- Not established: completeness of the fixes; transfer beyond EDGAR-filed ISDAs; the effect of the sidecar alone (not ablated).
- I2 stays filed as NOT PASS.

## Log
- 2026-09-25 filed by CC.
