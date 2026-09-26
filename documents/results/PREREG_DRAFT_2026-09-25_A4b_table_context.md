# PREREG DRAFT 2026-09-25 - A4b: AX with table context, on FRESH papers

Status: DRAFT, UNSIGNED. Parent: A4 NOT PASS (`RESULT_2026-09-25_A4_arxiv_results.md`), E2E -0.204. Astra (after A4): "Run the frozen
table-context expansion first ... retest AX on genuinely new papers ... If the fresh retest does not materially recover PIPE accuracy,
close the arXiv adapter line rather than moving to self-swapping or a tool loop."

## 0. Headroom (Bar Must Be Reachable)
A4: gold row inside PIPE excerpts 0.886; FULL 0.910. Even if table context fixed every covered-but-wrong answer, the ~11% uncovered rows
stay discordant, and the paper-clustered lower bound would sit below -0.05 (A4 half-width ~0.09 at 67 papers). So context alone cannot
clear the bar; selection COVERAGE must rise too. Both changes are fixed here, before any data.

## 1. Frozen changes (adapter AX = `work/a4/a4_best.npz` UNCHANGED, no retraining)
1. **Window budget k:** top-k RESULT windows + immediate neighbours, k = the smallest of {6, 8, 10, 12, 16} whose DEV coverage (30 DEV
   papers, anchored rows inside the selected windows) >= 0.95; if none reaches it, k = 16. Computed on DEV only, before TEST is touched.
2. **Table context:** for every selected window overlapping a tabular environment, send that table's caption (enclosing table env) and its
   header rows (rule-v4 `hdr_end`), once per table, as a "[TABLE CONTEXT]" block immediately before that table's first excerpt, document
   order. Deterministic. **The ANE graph and its 256-token windows are UNCHANGED:** context is host-side text added to the 27B prompt,
   never an ANE input. The same expansion is applied to the BM25 arm (same k), so the comparison stays fair.

3. **Overflow rule (Astra v1 defect):** per table, caption <= 200 Qwen tokens and header rows <= 300 Qwen tokens; longer ones are cut at the
   token limit and the table is flagged TRUNCATED. Header rows = rule-v4 `hdr_end`; a table with no detectable header (hdr_end None) or
   caption is flagged NO_CONTEXT and sent as in A4. A question whose gold row sits in a TRUNCATED or NO_CONTEXT table is SCORED AS IS
   (never excluded; a truncation failure is a failure) and reported separately. Whole PIPE prompt capped at 16,000 tokens: excerpts beyond
   the cap are dropped from the lowest-scoring window up, logged. Flags are computed before any 27B call.

## 2. TEST: fresh papers
The 74 papers that qualify under the FROZEN rule v4 in the part of the seeded pool the A4 corpus never walked (positions 10,455-12,743 of
the seed-20260935 order; counted before this draft, no model run on them). Questions min(3, anchored) per paper, seed 20260941.
Arms (order rotated): PIPE (k + context) · PIPE-A4 (A4 policy: top-6 + neighbours, no context; the PAIRED control that shows what the
changes bought) · FULL (<= 32k tokens) · BM25 (k + context) · NONE. 27B cold, reasoning off, T=0. Scoring = A4 scorer (PwC gold, rel 1e-3).

## 3. Gates (unchanged from A4)
Admission acc(FULL) >= 0.60 · **G-E2E** acc(PIPE) - acc(FULL) lower 95% >= -0.05 (paper-clustered) · G-LAT upper < 0 · G-SWAP (CUA -> IS3
-> AX -> CUA). Reported: PIPE - PIPE-A4 (paired, CI), coverage at k, tokens, per-failure class read of the raw.
**Closure rule (Astra):** G-E2E FAIL closes the arXiv adapter line; no further policy variants.

## 4. Not claimed
That the fix transfers to questions other than reported results; anything about self-swap or a tool loop.

## Log
- 2026-09-25 drafted by CC.
- 2026-09-25 Astra NOT SIGNED v1 (defect: no fixed token-budget/truncation rule). Revised: overflow rule 1.3; clarified that context is 27B-prompt text, the ANE 256-token graph is untouched; truncated tables scored as is, reported separately.
- 2026-09-25 **Astra SIGNED A4b v2**: "The deterministic truncation, NO_CONTEXT handling, prompt cap, and mandatory reporting make overflow an observed failure mode rather than an exclusion or hidden tuning decision."
- 2026-09-25 **Prep, before any 27B call:** fresh TEST = 74 papers / 181 questions (none in the A4 corpus, asserted). DEV coverage k=6 0.912, k=8 0.982, 10 0.982, 12 0.982, 16 1.000 -> **k = 8**. **Implementation fix found by smoke test (Verify Manipulation Took):** rule v4's `hdr_end` detector never fires (it looks for \midrule between rows, but the separator text sits at the start of the next row), so v4's EFFECTIVE header has always been the table's first row (`column_header` falls back to rows[:1]); the first A4b builder used the raw `hdr_end` and flagged all 181 gold tables NO_CONTEXT (manipulation would have been null). Builder now uses exactly v4's effective header. Gold-table flags: OK 111, TRUNCATED 70, NO_CONTEXT 0. Rule v4 itself unchanged.
- 2026-09-25 **A4b RESULT: NOT PASS** (E2E -0.136 [-0.224, -0.053]; paired gain over A4 policy +0.094 [+0.022, +0.171]; LAT PASS; SWAP PASS). arXiv adapter line CLOSED. `RESULT_2026-09-25_A4b_table_context.md`.
