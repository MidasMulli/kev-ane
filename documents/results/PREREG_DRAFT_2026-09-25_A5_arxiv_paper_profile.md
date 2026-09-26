# PREREG DRAFT 2026-09-25 - A5: arXiv PAPER PROFILE adapter AX2 (I3 recipe on papers)

Status: DRAFT, UNSIGNED. **Operator reopened the arXiv line (2026-09-25): "we need a working arxiv adapter, something orthogonal to
contracts."** A4 / A4b stay filed as NOT PASS; this is a different task, not a re-run of their policy.
Why this shape: A4/A4b failed on single-CELL identity (wrong column, missed results table) with PwC gold that is ~8% ambiguous as worded.
I3 (ISDA) PASSED with: fixed question set, anchored heading labels, top-3 per question + keyword sidecar, PIPE vs FULL, blind 2+1.
A5 applies the I3 recipe to papers.

## 1. Corpus
Papers from the already-fetched HF snapshot (`work/a4/a4_raw_hf*.jsonl`, `secemp9/arxiv-complete` paper_text), EXCLUDING every A4 / A4b
paper (asserted). Kept iff LaTeX has `\begin{abstract}` and 8,000-32,000 Qwen tokens (FULL always feasible). Seeded draw (20260950):
TRAIN 160 / DEV 25 / TEST 56, split before labelling. TEST papers are never used in training or label design.

## 2. The 12 questions (fixed now)
1 Method name (the method/model the paper proposes) · 2 Task addressed · 3 Headline quantitative result stated in the abstract (number +
what it measures) · 4 Evaluation datasets (up to 3) · 5 Main evaluation metric · 6 Baselines compared (up to 3) · 7 Code released (URL
or NONE) · 8 Training hardware (device type and count if stated) · 9 Parameter count of the proposed model · 10 Training time ·
11 Optimizer · 12 Limitations discussed (yes/no + one if yes). NONE is correct where the paper does not state it.

## 3. Anchored labels (TRAIN/DEV only; no teacher answers)
Per field, the evidence span = first match of a FROZEN LaTeX pattern (no answer-string search): 1-3 the abstract environment;
4 first sentence containing "dataset" inside an Experiment*/Evaluation/Results section; 5 first table caption inside those sections;
6 first sentence with "baseline" or "compare(d) (with|to|against)"; 7 sentence with `\url{`/`\href{` containing github|gitlab|huggingface|
project; 8 sentence with GPU|TPU|A100|V100|H100|RTX|NVIDIA; 9 sentence matching a number + (M|B|million|billion) + param(eter)s;
10 sentence with train* within 80 chars of a number + (hours|days|GPU-hours); 11 sentence with
Adam|AdamW|SGD|LAMB|Adafactor|optimizer; 12 a Limitation* section heading, else first sentence containing "limitation".
No match -> no positive label. **Label spot check (gate): 20 anchored labels, fresh blind sub-agent, >= 18/20 on the right span**, else
anchors fixed and re-checked on a NEW 20 before training.

## 4. Adapter AX2 and policy
CUA architecture, 12-output head, same slot schema, LoRA r16 q,k,v,o, Qwen3-0.6B base. Policy (fixed): union of top-3 windows per
question + keyword sidecar (up to 2 windows each, first occurrences) for fields 7, 8, 9 (the I3 sidecar form). All 12 questions in one
27B request.

## 5. TEST, gates, adjudication (I3 unchanged)
56 fresh papers x 12 = 672 questions. PIPE vs FULL, cold, alternating, reasoning off, T=0. Disagreements -> blind 2+1 sub-agents with a
fixed rubric ("the correct answer is what the paper states; for list fields any stated item is acceptable; NONE is correct only if the
paper does not state it"), mapping sealed, kappa reported.
- **G-E2E:** PIPE - FULL lower 95% >= -0.05 (paper-clustered). **G-LAT:** median per-paper upper < 0.
- **G-SWAP:** CUA -> IS3 -> AX2 -> CUA bitwise on return, three distinct, base md5 unchanged. PASS = all three.

## 6. Fail-fast (operator rule 2026-09-25: runs > 1 h need a built-in stop)
- Training (est. 45 min, I3 took 44): DEV hit@3 upper < 0.70 at the first eval >= 60 min -> stop (diagnostic).
- TEST (est. 56 x ~65 s = ~61 min + adjudication): at paper 28, pause; packets for papers 1-28 adjudicated blind (same protocol);
  **if the paper-clustered PIPE - FULL UPPER 95% bound < -0.05, stop: NOT PASS** (cannot pass). Otherwise continue; final verdict on all 56
  (the interim look can only stop for futility, never declare a pass).

## 7. Not claimed
Transfer beyond ML-style arXiv papers; question sets other than these 12; anything about A4's results-table task.

## Log
- 2026-09-25 drafted by CC.
- 2026-09-25 **Astra SIGNED A5**: "Yes, I sign A5. The fixed anchored-label spot check, fresh paper split, bounded token length, explicit sidecar scope, blind adjudication, and futility stop make this a valid orthogonal paper-profile test rather than an A4 rerun. Keep any pass limited to the specified 12 questions and paper snapshot."
- 2026-09-25 Editorial, before any data: anchor 10 text had a drafting stray ("epochs? no:"); frozen form is number + (hours|days|GPU-hours), as signed in substance.
- 2026-09-25 **Label spot check v1 FAILED 9/20** (bibliography/related-work matches, baselines from background text, wrong table caption for metric, method name absent from abstract, abstract without a number, unresolved \input abstract). **Anchors v2 (frozen before re-check):** searches limited to the paper body (after abstract, before bibliography, minus related-work/background/acknowledgement sections; Code may also match title footnote/abstract); Baselines only in experiment sections; Main metric only a caption naming a metric; Method name only a "we propose/called/named" sentence; Headline result only an abstract sentence with a number; placeholder abstracts dropped. Re-check on a NEW 20 (seed 20260952).
- 2026-09-25 **Label spot check v2 FAILED 12/20** (Main metric 0/4 via captions, Datasets 0/2, Method name, Limitations). **Anchors v3:** Main metric = experiment-section sentence stating what is evaluated/reported and naming a metric; Datasets = experiment-section sentence citing a dataset/benchmark; Method name = "we propose/present/introduce" + a capitalized name, or "called/named/dubbed/termed" + capitalized; Limitations = Limitations heading or a sentence about the paper's OWN limitation. Re-check on a NEW 20 (seed 20260953).
- 2026-09-25 **Label spot check v3: 16/20, FAILED** (misses: Datasets x2 = dataset description / pretraining set; Main metric x1 = regex bug, `EM` lacked a leading boundary; Baselines x1 = figure caption naming none). **Anchors v4:** Datasets = experiment-section sentence with an evaluation verb + on/using/with + - 2026-09-25 **Label spot check v4: 17/20, FAILED** (Baselines x2: a simplicity comparison, accuracy numbers without a list; Hardware x1: general hardware requirements). **Anchors v5:** Baselines = experiment-section comparison/baseline sentence citing >= 2 methods; Hardware = device named with a train/run/conduct/use/implement/perform verb. Re-check on a NEW 20 (seed 20260955).
- 2026-09-25 **Label spot check v5 PASS 19/20** (seed 20260955; miss: a Baselines span citing references without naming methods). TRAIN+DEV anchored labels per field: Task 180, Optimizer 108, Main metric 99, Datasets 94, Method name 87, Hardware 86, Code 77, Baselines 56, Headline result 55, Training time 24, Limitations 18, Parameters 17 (of 185). Anchor code = `work/a5/a5_common.py` sha c7ccfc195fe4. Training launched.
- 2026-09-25 **Interim (futility) look, papers 1-28:** PIPE - FULL = -0.006 [-0.021, +0.009] (336 q, 58 disagreements, blind 2+1, kappa 0.941, 1 arbitrated) -> **no futility stop; continue** (the interim cannot declare a pass). LAT -27.2 s. G-SWAP PASS (CUA/IS3/AX2 bitwise). Incident: the two adjudicators shared a helper-script filename in the scratchpad (a generic stdin-to-file writer, no verdict content); audited: 0 byte-identical verdicts, 0 identical quote+reason pairs; independence intact.
- 2026-09-25 **A5 RESULT: PASS** (E2E -0.010 [-0.027, +0.004]; LAT 2.4x; SWAP PASS; kappa 0.875). `RESULT_2026-09-25_A5_arxiv_paper_profile.md`.
