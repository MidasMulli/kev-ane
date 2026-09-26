# RESULT 2026-09-25 - A4b: AX + table context, FRESH papers: **NOT PASS** (G-E2E). arXiv adapter line CLOSED (Astra's rule).

Prereg: `PREREG_DRAFT_2026-09-25_A4b_table_context.md` (Astra-signed v2). Raw `work/a4/a4b_test_raw.jsonl`; score `work/a4/a4b_score.json`.
74 fresh papers / 181 questions (never-walked pool tail, rule v4), AX weights unchanged, k = 8 (DEV coverage 0.982).

| gate | statistic | bar | result |
|---|---|---|---|
| Admission | acc(FULL) feasible = 0.890 (155 q, 64 papers) | >= 0.60 | admitted |
| **G-E2E** | acc(PIPE) - acc(FULL) = **-0.136 [-0.224, -0.053]** | lower >= -0.05 | **FAIL** |
| G-LAT | median per-paper -26.7 s [-29.7, -23.0]; PIPE 13.1 s vs FULL 39.2 s | upper < 0 | PASS |
| G-SWAP | CUA -> IS3 -> AX -> CUA bitwise, base md5 unchanged | all | PASS |

**What the change bought (paired, same papers):** PIPE - PIPE_A4 = **+0.094 [+0.022, +0.171]** (0.718 vs 0.624 over all 181).
By gold-table flag: OK tables PIPE 0.784 vs PIPE_A4 0.694 (111 q); TRUNCATED 0.614 vs 0.514 (70 q). PIPE - BM25 +0.039 [-0.064, +0.140].
Tokens PIPE 5,216 / BM25 6,775 / FULL 19,005. No excerpt dropped by the 16k cap.

## Where the remaining loss is (raw read)
(covered, correct) 128 · (covered, wrong) 32 · (not covered, wrong) 19 · (not covered, correct) 2.
- The wrong-cell class A4 diagnosed shrank: covered-but-wrong with FULL right 26 (A4, 202 q) -> 10 here (181 q); the other 22 covered-wrong
  are questions FULL also misses. The table-context diagnosis is supported (paired +0.094), not complete.
- **The dominant residual is COVERAGE:** gold row outside the excerpts 21/181 (11.6%). DEV (30 papers) said k = 8 gives 0.982; fresh
  TEST gave 0.884. A 30-paper DEV overstated coverage: the k rule was fit on too small a sample.
- PIPE NONE answers 16 (A4: 29).

## Status
arXiv adapter line CLOSED per Astra ("If the fresh retest does not materially recover PIPE accuracy, close the arXiv adapter line rather
than moving to self-swapping or a tool loop"). It recovered +0.094 of the -0.204 gap; the bar was the pre-registered G-E2E, which fails.
Findings banked: (1) row selection is necessary but not sufficient for tables; excerpts must carry their header (paired +0.094);
(2) small-DEV coverage estimates do not transfer (0.982 -> 0.884).

## Log
- 2026-09-25 filed by CC. No futility stop was pre-registered (operator rule added after launch: runs > 1 h need one).
