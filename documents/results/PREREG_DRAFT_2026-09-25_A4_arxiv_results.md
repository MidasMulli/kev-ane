# PREREG DRAFT 2026-09-25 - A4: an arXiv adapter (third domain on the resident base): reported results from papers

Status: DRAFT, UNSIGNED. Operator: "Can we build an arXiv adapter?" ... "Go".

## 1. Claim
A third swappable adapter (AX) on the same resident ANE base maps an arXiv paper's LaTeX once; the 27B, given only the selected windows,
answers "what does model M achieve on dataset D for metric R in this paper?" no worse than reading the whole paper (margin 0.05), faster,
and against an INDEPENDENT gold (Papers with Code reported results), not a model's own reading.

## 2. Data (measured)
- Gold: Papers with Code archive (pwc-archive/evaluation-tables, CC BY-SA 4.0): 260,526 reported results linked to 16,596 arXiv papers.
- Documents: arXiv LaTeX source (e-print), .tex files concatenated (main file with \input expanded where possible, else all .tex in
  order), comments stripped; kept if 8k-40k Qwen tokens. Fetched politely (<= 1 request / 3 s).
- Papers with >= 3 reported results are sampled (seed 20260935), 450 targeted; split by PAPER before any training: TRAIN 320 / DEV 40 /
  TEST 90.
- **Evidence identity (Astra v1 defect), FROZEN anchoring rule:** a PwC result (model M, dataset D, metric R, value V) is ANCHORED in a
  paper iff there is a LaTeX unit U that contains V as a word-boundary number token AND a token of M (model name lowercased, split on
  non-alphanumerics, tokens >= 3 chars, ignoring generic tokens {ours, model, base, large, small, net}), where U is either (a) a table row
  (text between two `\\` inside a tabular environment) whose enclosing table (caption + header rows + the row) also contains a token of D
  or R, or (b) a sentence (outside tables) containing V, a token of M and a token of D or R. If more than one U matches, the result is
  AMBIGUOUS and dropped. Only anchored, unambiguous results are usable (labels AND test gold); papers with < 2 usable results dropped
  before the draw.
- **Blind anchor validation gate, before any training:** 30 anchored results drawn with seed 20260936 are judged BLIND by fresh
  sub-agents shown the unit U with its table caption/header (or sentence) and asked "Does this report <R> of <M> on <D> as <V>? yes/no,
  deciding quote". Accept iff >= 27/30 yes (Clopper-Pearson lower printed); otherwise the rule is tightened and re-gated on a NEW sample.
## 3. Adapter AX (CUA architecture; one head)
Per window (T=256, stride 224), one output RESULT = the window overlaps the anchor unit U of one of the paper's usable results. Selection policy fixed now: top-6 RESULT windows + each one's immediate neighbours (table headers/captions often sit one
window away), deduped, document order. Selection does NOT see the question (one ANE read serves every question about the paper).
Guards as always; kill (diagnostic) at 60 min if DEV hit@6 upper < 0.70.

## 4. TEST (90 fresh papers, 3 questions each, seeded: 270)
Question: "In this paper, what <metric> does <model> achieve on <dataset>? Answer with the number only." Gold = PwC value; correct iff
numerically equal (relative 1e-3) or string-equal after stripping "%" and formatting.
Arms: PIPE (AX policy -> 27B) · FULL (whole LaTeX if <= 32k tokens; else declared infeasible row) · BM25 (question as query, same window
budget as PIPE: top-6 + neighbours) · NONE. 27B cold, reasoning off, T=0.
- **Admission (the gold must be learnable):** FULL accuracy on feasible questions >= 0.60, else A4 is VOID (PwC gold too noisy for this task).
- **G-E2E:** acc(PIPE) - acc(FULL) lower 95% >= -0.05 (paper-clustered). **G-LAT:** median per-paper latency upper < 0.
- **G-SWAP:** CUA -> IS3 -> AX -> CUA on the base: hidden states bitwise identical on return; three distinct adapters.
- Reported: PIPE vs BM25 (S rule); hit@6+neighbours; tokens.

## 5. Not claimed
Papers without LaTeX source; figures; claims beyond reported results; PwC gold errors are not corrected (the admission gate bounds them).

## Log
- 2026-09-25 drafted by CC.
- 2026-09-25 Astra NOT SIGNED v1 (defect: evidence identity; a value string in the LaTeX does not prove it belongs to the queried model/dataset/metric). Revised: frozen row/sentence anchoring rule (value + model token + dataset/metric token, ambiguous dropped) + blind 30-result validation gate (>= 27/30) before training.
- 2026-09-25 **Astra SIGNED A4 v2**: "The frozen anchoring rule and blind pre-training validation gate address the evidence-identity defect. A4 v2 is signed as scoped."
- 2026-09-25 **Implementation declared before any data is scored:** (1) sources via `https://arxiv.org/src/<id>` with curl (Python urllib gets HTTP 406 from arXiv); sources > 40 MB skipped (logged `too_big`), a small non-random exclusion; (2) the 450 = first 450 qualifying papers in the seeded fetch order, positions 0-319 TRAIN / 320-359 DEV / 360-449 TEST; (3) TEST questions = min(3, anchored) per paper (seed 20260938), so the count may be < 270; (4) one 27B request per paper per arm with all its questions listed (as I2); BM25 picks top-6 + neighbours PER QUESTION, unioned per paper. Dry run on the first 25 fetched papers: 32 anchored / 11 ambiguous / 144 no unit (spot-read: misses are genuine absence or another model's row, e.g. 0.155 on ReMoDiffuse's row, rejected for Free-T2M).
- 2026-09-25 **Declared source change, before any corpus is built:** operator pointed to `secemp9/arxiv-complete` (HF, snapshot 2026-09-05). Documents now come from its `paper_text` config (one assembled TeX per paper: main file with \input/\include expanded, else path-order concatenation, .bbl appended) instead of live arxiv.org/src, SAME seeded candidate order, same comment strip; the 40 MB cap no longer applies. Read per Parquet row group via footer stats (`work/a4/a4_fetch_hf.py`). The arxiv.org fetch (72 papers) is abandoned, not mixed in.
- 2026-09-25 **Anchor gate v1 FAILED 22/30** (bar 27; 3 blind judges, `work/a4/gate/`). Classes: value in wrong column of the right row (3), generic model token 'baseline' (1), PwC metric label disagrees with the paper (3-4: CoLA 'Accuracy' vs MCC, 'AP@0.15' vs 'mAP', 'inter-ocular' vs 'inter-pupil'). CC proposed an identity-only bar; **Astra NOT SIGNED** ("changes the acceptance question after seeing failures ... metric mismatch changes the task's gold"): keep BOTH identity and metric-label agreement at 27/30 on a new sample, drop metric-mismatched records before corpus construction. **Rule v3 frozen** (`a4_common.anchor3`): value in a CELL whose column header + section-label rows contain EVERY metric token (len >= 2), a dataset token in column header/sections/caption, model token (generic list widened: baseline, method, proposed, ...) in another cell of the row; sentences need value + model + dataset token + every metric token; >1 match dropped. Dry run on the failed 30: keeps 3, all judged yes. Yield on 800 fetched papers: 58 with >= 2 anchored (7.3%); candidate fetch extended to the first 8,000 in the same seeded order. Re-gate: NEW 30 (seed 20260939), judge asked identity AND metric-label agreement, >= 27/30 both.
- 2026-09-25 **Anchor gate v3 FAILED: identity 26/30, metric 25/30** (bar 27 each; NEW sample seed 20260939, 3 blind judges, `work/a4/gate_v3/`). Identity misses: partial model-name match to a sibling variant (TResNet-L vs -XL; AR-CNAPS vs CNAPS+FETI), dataset subset unstated (MASS SS2), backbone unstated. Metric misses: numeric qualifier lost by tokenization (mAP@0.5 vs 0.25), macro vs micro F1 (sentence unit), task label as column header, scaled unit MSE(10^3). v3 corpus VOID for training.
- 2026-09-25 **Astra ruled A (final try):** "Run v4 once. The table-row-only rule and scaled 280/30/80 split are acceptable if frozen before sampling, with the same independent 30-item gate requiring both identity and metric agreement at 27/30. If either fails, close A4 permanently." **FROZEN before sampling:** rule `a4_common.anchor4` (sha below); candidates = the ENTIRE seeded pool (12,743); corpus = first 390 qualifying papers in seeded order, TRAIN 0-279 / DEV 280-309 / TEST 310-389; TEST questions min(3, anchored) seed 20260938; gate NEW 30 seed 20260940.
  anchor rule file sha: 63d88d7f1a4b
- 2026-09-25 **Anchor gate v4 (final) PASS: identity 29/30, metric 30/30** (bar 27 each; NEW sample seed 20260940, 3 blind judges, `work/a4/gate_v4/`; the miss: plain "BiAttention (MRU)" anchored to its "Ensemble (x9)" row). Corpus v4 `work/a4/a4_corpus.json`: 390 papers (walked 10,454 of 12,743 candidates), 1,618 anchored table-row results, 202 TEST questions. Training launched.
- 2026-09-25 **A4 RESULT: NOT PASS** (E2E -0.204 [-0.298, -0.118]; LAT PASS 4.3x; SWAP PASS 3 adapters; coverage 0.886). `RESULT_2026-09-25_A4_arxiv_results.md`.
