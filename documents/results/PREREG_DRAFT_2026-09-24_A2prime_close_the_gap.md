# PREREG DRAFT 2026-09-24 - A'' "close the gap": evidence-selection policy for value questions, tested on fresh contracts

Status: DRAFT, UNSIGNED. Operator: "Close the gap" (2026-09-24). Written to Astra's A' conditions: a new development rule, fresh test
contracts disjoint from everything used, prospectively fixed handling of asked value types.

## 0. Diagnosis (from the raw of A3 and A-long, both already-used sets)
PIPE-only losses left after the no-NULL fix (A-long) and the A3 date losses, read one by one:
- Agreement Date, gold in a window NOT sent: window 27 when {0, 28} were sent; window 3 when {0, 1}; window 2 when {0, 91}.
  Dates sit in the first few windows or next to the signature block; top-2 by ANE score misses them.
- Agreement Date, gold window sent but misread: 1 ("June , 2010" answered "2010").
- Three more A3 date items were wrong in BOTH arms (the gold date is a signature-page date; both read the preamble date): no gap.
The gap is mostly SELECTION, not reading. A2 established the ANE ranking is the lever (A' diagnostic: top-2 no-NULL hit 0.965).

## 1. Development rule (declared now; run on USED data only: A3 TEST 95 + A-long 31 contracts; ANE only, no 27B)
Candidate policies for every asked value question (the same policy for all four types):
P1 top-2 (current) · P2 top-3 · P3 top-4 · P4 top-2 plus each selected window's neighbours (+-1) · P5 top-2 plus windows 0-2 ·
P6 top-3 plus windows 0-1.
Score per policy: location hit (gold span inside the evidence) over all value questions, and median evidence tokens per contract.
**Pick:** the highest hit; ties within 0.005 go to fewer median tokens; any policy whose median evidence exceeds 3,000 tokens is excluded.
The pick and its dev numbers are filed BEFORE the test set is built or read.

## 2. Fresh test set (built after the pick; frozen and hashed before any arm runs)
- Source: Pile of Law `atticus_contracts` (public EDGAR contracts, CC BY-NC-SA 4.0), validation shard 0 (downloaded, 1.07 GB).
- Disjoint from CUAD: any document whose first 2,000 characters (whitespace-normalized) match a CUAD contract's is dropped; the count
  dropped is reported.
- Filter (declared): the first 3,000 characters contain "agreement" (case-insensitive); 8,000-32,000 Qwen tokens. Seeded draw
  (seed 20260925) of **60 contracts**. All four value questions are asked of every contract; NONE is a valid answer.

## 3. Arms and measure
PIPE (frozen adapter CUA, frozen policy from section 1) vs FULL (27B reads the whole contract). Cold, alternating order, as A3.
- There is no human gold. Answers are compared per question after normalization (the A-long parsers: jurisdiction, date fields,
  duration with years = 12 months; NONE vs NONE is agreement).
- **Only disagreements are adjudicated, blind, by TWO independent adjudicators plus arbitration (revised after Astra's review):**
  - Adjudicators are fresh sub-agents with no session context (CC adjudicates NOTHING). Each gets only: the question, the two answers
    as "X" and "Y" in a per-item random order (arm mapping in a sealed file CC does not open until all verdicts are filed), the full
    contract text, and the rubric below. Adjudicators 1 and 2 run separately and never see each other's verdicts.
  - **Rubric (fixed now):** (1) Quote the contract sentence that answers the question. (2) The correct answer is what that sentence
    states: Governing law = the jurisdiction named in the governing-law clause; Agreement date = the date the agreement states it is
    made, entered into, or dated as of (opening paragraph first; a signature-block date only if the opening gives none); Renewal term =
    the length of each renewal period; Non-renewal notice = the advance notice required to prevent renewal. If the contract states none,
    NONE is correct. (3) Verdict: X correct / Y correct / both wrong / both acceptable (same meaning, different wording).
  - **Arbitration:** where adjudicators 1 and 2 differ, a third fresh adjudicator (same inputs, same rubric) decides by majority of
    three; if all three differ, the item counts AGAINST PIPE (conservative). Inter-rater agreement (raw and Cohen's kappa) between 1 and 2
    is reported. The operator may spot-check any verdict before unsealing.
  - Limitation named: all adjudicators are the same model family (Claude); independence is by context and blinding, not by model.
- Accuracy difference PIPE - FULL = (PIPE-only-correct - FULL-only-correct) / all questions (ties and both-wrong add 0).

## 4. Gates (contract-clustered bootstrap, 95% CI; bars as A3, not moved)
- **G-E2E:** lower bound of (PIPE - FULL) >= -0.05.  **G-LAT:** upper bound of median per-contract (PIPE - FULL) seconds < 0.
- PASS = both. Reported: agreement rate, disagreement count by type, adjudication table, evidence tokens.
- Kill (fail fast): after 20 contracts, if PIPE-vs-FULL agreement < 0.80, stop and file (adjudication then covers what ran).
- Budget: FULL at about 2 s per 1k tokens, 60 contracts x about 20k tokens, about 40 min of GPU plus PIPE.

## 5. Not claimed
Anything beyond these four value types; the presence map; ISDA or other families; human-gold accuracy (the measure is relative, by blind
adjudication of disagreements).

## Log
- 2026-09-24 drafted by CC.
- 2026-09-24 Astra NOT SIGNED v1: single-adjudicator defect. Revised: two independent blinded sub-agent adjudicators, fixed rubric, third-adjudicator arbitration (ties against PIPE), kappa reported; CC adjudicates nothing.
- 2026-09-24 **Astra SIGNED A''** (v2): "I sign A''. The adjudication defect is fixed... The same-model-family limitation is appropriately disclosed." Operator: "Close the gap".
- 2026-09-24 **DEV PICK filed before the test set exists: P2 (top-3)**. Dev hit (263 used value questions): P1 0.954 / P2 0.981 / P3 0.985 / P4 0.962 / P5 0.966 / P6 0.981; median evidence tokens 1,024 / 1,455 / 1,894 / 2,048 / 1,513 / 1,649. P3 highest; P2 within 0.005 with fewer tokens -> P2 by the declared rule. `work/cuad/a2p_policy.json` (9377b06d7fc7), raw a2p_dev_raw.jsonl (4eaa48a05a86). Base md5 unchanged.
- 2026-09-24 **Fresh set built**: `work/cuad/fresh/fresh60.json` (30113583867e); shard scanned 118,642 docs, exact-prefix CUAD matches 0,
  keyword fail 21,744, length fail 68,282, pool 28,542, drawn 60 (median 12,746 tokens). The exact-prefix check found 0, so a fuzzy
  check was added before any arm ran: 6-word-shingle Jaccard vs all 510 CUAD contracts, max 0.026; the check scores a reformatted CUAD
  contract 1.0 against itself (it can fire).
- 2026-09-24 A redraw excluding 2 ISDA-referencing documents was started for Rule 9 and ABANDONED on the operator's ruling (verbatim):
  "isda is fine, it's publicaly available information". The original draw (30113583867e) stands unchanged; no arm had run.
- 2026-09-24 **A'' RESULT: PASS** (-0.021 [-0.046, 0.000]; latency -19.6 s [-22.8, -17.3]); kappa 0.323 disclosed. `RESULT_2026-09-24_A2prime_close_the_gap.md`.
