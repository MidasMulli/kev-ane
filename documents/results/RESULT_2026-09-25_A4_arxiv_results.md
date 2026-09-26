# RESULT 2026-09-25 - A4: arXiv adapter AX (third domain on the resident base): **NOT PASS** (G-E2E)

Prereg: `PREREG_DRAFT_2026-09-25_A4_arxiv_results.md` (Astra-signed v2 + three logged rulings; anchor rule v4 gate PASS 29/30, 30/30).
Raw `work/a4/a4_test_raw.jsonl`; score `work/a4/a4_score.json`; train `work/a4/a4_train_raw.jsonl` (best DEV hit@6 0.850 at step 500).
Corpus: `secemp9/arxiv-complete` paper_text, 390 papers (280/30/80), gold = Papers with Code values anchored by rule v4.

| gate | statistic | bar | result |
|---|---|---|---|
| Admission | acc(FULL) on feasible questions = 0.910 (167 q, 67 papers <= 32k tokens) | >= 0.60 | admitted |
| **G-E2E** | acc(PIPE) - acc(FULL) = **-0.204 [-0.298, -0.118]** (paper-clustered) | lower >= -0.05 | **FAIL** |
| G-LAT | median per-paper (PIPE - FULL) = -32.7 s [-35.5, -29.9]; PIPE 10.0 s vs FULL 42.9 s (4.3x) | upper < 0 | PASS |
| G-SWAP | CUA -> IS3 -> AX -> CUA: CUA bitwise on return, three distinct, base md5 unchanged | all | PASS |

Reported: all 202 questions: PIPE 0.703, BM25 0.609, NONE 0.000. PIPE - BM25 = +0.094 [-0.020, +0.210] (not separated).
Coverage (gold row inside the sent windows): PIPE 0.886, BM25 0.525. Median prompt tokens PIPE 3,382 / BM25 4,665 / FULL 20,433.

## Where the loss is (raw read, not a re-verdict)
Retrieval is not the main loss: (covered, correct) 136 · (covered, wrong) 43 · (not covered, wrong) 17 · (not covered, correct) 6.
Of the 43 covered-but-wrong, FULL was right on 26; PIPE's answers are real numbers from the SAME table, wrong cell: the neighbouring
metric column (PillarNet mAP 66.0 answered 71.4 = its NDS), another split/table (Lite-HRNet test-dev 66.9 answered 67.6), or NONE (29 NONE
answers overall). **Candidate diagnosis (NOT verified):** 256-token excerpts separate a table row from its column header / caption, so
the reader cannot bind the value to its column or table: the evidence-identity problem the anchor gate had, reappearing at answer time.
Selection target (the row) was necessary but not sufficient; the unit the reader needs is row + header + caption.

## What this establishes (and not)
- Established: a third 9.2 MB adapter on the same resident base swaps bitwise with two others; on fresh papers it cuts reading 6x and
  latency 4.3x and puts the gold row in the excerpt 89% of the time (BM25 53%). The end-to-end answer is 0.20 worse than a full read.
- Not established: that a header/caption-aware policy closes the gap (a new design, not a re-run).
- A4 closes as NOT PASS. The anchoring gates (v1 22/30, v3 26/25/30, v4 29/30 30/30) are in the prereg log.

## Log
- 2026-09-25 filed by CC.
