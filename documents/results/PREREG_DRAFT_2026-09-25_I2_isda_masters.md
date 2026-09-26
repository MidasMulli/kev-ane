# PREREG DRAFT 2026-09-25 - I2: genuine ISDA Master Agreements / Schedules, 12 elections, anchored labels

Status: DRAFT, UNSIGNED. Operator (2026-09-25): "if we're training on ISDAs, it should be real ISDA master agreements, not documents that
mention ISDAs"; question count set to 12 as the fail-fast sense check. Supersedes nothing: I1 stays filed as NOT PASS.

## 0. Why I1 fell short (diagnosed from its raw, filed with it)
(1) Corpus: many I1 documents only MENTIONED ISDA (loan agreements, mortgages). (2) Labels: 95 of 120 Calculation Agent training labels
pointed at the wrong place (CC's rule took the first "Dealer" within 300 chars after any "calculation agent" mention). Both are fixed here.

## 1. Corpus (measured)
All 7 Pile-of-Law atticus shards (~650k public EDGAR contracts) scanned with a structural classifier: 346 unique genuine ISDA documents,
**241 containing a Schedule** ("Part 1 Termination Provisions"): 153 Masters with Schedule attached + 88 standalone Schedules.
**Classifier FROZEN (as run):** keep a document only if its first 3,000 chars contain "Master Agreement" AND either (MASTER) "ISDA" in
the first 3,000 chars plus the printed form's sections "Interpretation", "Obligations" and "Events of Default and Termination Events",
or (SCHEDULE) "Schedule to the" in the first 3,000 chars plus "Part 1" and "Termination Provisions"; exact-duplicate texts removed.
**Validation gate (Astra, before accepting the corpus):** 30 documents drawn with seed 20260930 from the 241 are judged BLIND by fresh
sub-agents (reading each document) as "an ISDA Master Agreement, or a Schedule to an ISDA Master Agreement" yes/no, with the deciding
quote. Accept the corpus iff >= 28/30 are yes (Clopper-Pearson lower 95% bound printed). Otherwise the classifier is tightened and the gate
re-run on a NEW sample before any labelling.
Seeded split (seed 20260927) before any labelling, only after the gate passes: TRAIN 160 / DEV 25 / TEST 56.

## 2. Questions (12, fixed now; answers are copied values or fixed choices)
Party A · Party B · Agreement date · Form (1992 | 2002) · Governing law · Termination Currency · Cross Default applies to (A | B | both |
neither) · Threshold Amount (first stated; any stated amount acceptable) · Automatic Early Termination applies to (A | B | both | neither) ·
Additional Termination Events specified (yes | no) · Credit Support Annex part of the agreement (yes | no) · Early-termination payment
measure (Market Quotation | Loss | Close-out Amount). NONE allowed where the document states none.

## 3. Labels (TRAIN/DEV only; teacher labels, disclosed) - ANCHORED, the I1 fix
The 27B reads the SCHEDULE portion (from the "Schedule" heading to the end; the printed form carries no elections) and answers the 12.
Evidence location = the paragraph under the election's own heading (e.g. "Termination Currency", "Governing Law", "Cross Default",
"Threshold Amount", "Automatic Early Termination", "Additional Termination Event", "Credit Support", "Payments on Early Termination"),
found by heading regex; for Party A/B and the agreement date, the Schedule's opening paragraph. No answer-string search. A 20-document
spot check of label locations is printed before training (gate: >= 18/20 land on the right paragraph, else labelling is fixed first).

## 4. Adapter and test
ISD2 = the CUA architecture, 12-output head, same slot schema; guards as always; kill (diagnostic) at 60 min if DEV hit@3 upper < 0.70.
TEST (56 fresh docs, 672 questions): PIPE (union of ISD2 top-3 windows per question -> 27B, all 12 questions in one request) vs FULL (27B
reads the whole document), cold, alternating; disagreements adjudicated blind by two fresh sub-agents (rubric = the question definitions
above), third arbitrates, kappa reported, mapping sealed.
- **G-E2E:** PIPE - FULL lower 95% bound >= -0.05 (document-clustered). **G-LAT:** median per-document (PIPE - FULL) upper bound < 0.
- **G-SWAP:** CUA <-> ISD2 bitwise round trip (as I1). PASS = all three. Per-question accuracy reported; Close-out Amount (2002-only,
  thin) reported separately.

## 5. Demo (engineering, not a claim)
A "drop in an ISDA" tab: paste or upload a document; detect ISDA; swap to ISD2; ANE map; 27B answers the 12 with the quoted clause for each.

## Log
- 2026-09-25 drafted by CC.
- 2026-09-25 Astra NOT SIGNED v1 (defect: corpus eligibility, 'has a Schedule' does not establish an ISDA Master Agreement). Revised: classifier frozen as run + blind 30-doc validation gate (>= 28/30) before accepting the corpus.
- 2026-09-25 **Astra SIGNED I2** (revised): "The frozen classifier plus blind 30-document validation gate addresses the corpus-eligibility defect. The design is signed as scoped." Operator: real ISDA masters, 12 questions.
- 2026-09-25 **Corpus VALIDATION GATE PASS**: 30/30 judged genuine ISDA Master Agreement or Schedule (blind, 3 fresh sub-agents), Clopper-Pearson lower 0.884. Corpus `work/isda2/isda2_corpus241.json` (fa2735e68bf1); split frozen `work/isda2/i2_split.json` (TRAIN 160 / DEV 25 / TEST 56). Heading anchors found in the Schedule (of 241): missing Threshold Amount 79, Payment measure 55, Cross Default 17, Termination Currency 9, ATE 4 (no positive label where absent).
- 2026-09-25 **Label spot-check PASS**: 19/20 anchored labels on the operative paragraph (fresh sub-agent; the miss: an Additional Termination Event cross-reference). **Declared change:** the 27B teacher run is SKIPPED: the selector trains only on anchored locations, which do not use teacher answers (saves ~2 h; training and TEST unchanged).
- 2026-09-25 **I2 RESULT: NOT PASS by 0.004** (E2E -0.037 [-0.054, -0.022]); LAT PASS 4.5x; SWAP PASS; kappa 0.95. `RESULT_2026-09-25_I2_isda_masters.md`.
