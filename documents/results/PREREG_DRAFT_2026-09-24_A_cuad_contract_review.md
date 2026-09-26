# PREREG DRAFT 2026-09-24 - Program A: ANE contract map -> 27B value answers (CUAD)

Status: SIGNED CC + Astra 2026-09-24 (design sha 5f5b57451265). Operator go: standing approval for Astra-signed designs in this arc + "Go with cuad for now". Operator chose CUAD (2026-09-24, "Go with cuad for now"); ISDA NOT used (Rule 9). Direction agreed by
Astra (order A -> B -> C; kills as paired CI-bound rules; A's 1 h kill diagnostic-only), `BRIEF_2026-09-24_kev_arc_synthesis_for_astra.md`.

## 0. Data (measured 2026-09-24)
- CUAD v1 (Zenodo 4595826, CC BY 4.0), zip sha256 88b694d99007..., `work/cuad/`. 510 contracts, 41 clause types, 20,910 (contract, type)
  pairs, 6,702 positive. Qwen3 tokens: p10 1,457 / p50 6,852 / p90 26,079 / max 82,345; 34 contracts > 32,768.
- **Finding that shapes the design:** for the 35 Yes/No types, `master_clauses.csv` Yes/No equals "an annotated span exists" in 99.99% of
  rows. On those, the answer IS the selection; a 27B adds nothing. The information-sharing test therefore uses the VALUE types, whose answer
  must be READ out of the clause: Governing Law (434 non-empty; e.g. "New York"), Agreement Date (465; "4/7/17", "[]/[]/2013"),
  Renewal Term (163; "successive 1 year"), Notice Period To Terminate Renewal (101; "90 days").
  Excluded: Expiration Date (often derived from several clauses), Effective Date (overlaps Agreement Date), Parties/Document Name (free text).

## 1. Claim (what a PASS entails, SR 53)
On held-out real contracts, one read of the contract by the resident ANE base with a swapped CUAD adapter produces a 41-type clause map.
Given only the ANE-selected windows, the 27B answers the value questions **no worse than when it reads the whole contract (margin 0.05)**
and **with lower median end-to-end latency**. NOT claimed: novelty of retrieve-then-read (RECOMP, LongLLMLingua, the CUAD paper own that);
anything about ISDA or other contract families; causes of the latency gain beyond "fewer 27B prompt tokens".

## 2. Splits (frozen and hashed BEFORE any training)
Eligible = contracts <= 32,768 Qwen3 tokens (476). Seeded shuffle (seed 20260924): TEST 96, DEV 40, ADMIT 60, TRAIN the rest (280).
Written as `work/cuad/splits.json`, sha printed in the launch record. TEST is never read until the final run.

## 3. Stages, gates and kills
**A0 Admission (27B only, < 1 h GPU).** ADMIT contracts; every value type with a gold answer in that contract is asked. One request per contract, all of its value
questions together, fixed answer formats in the prompt. Arms: FULL (whole contract), GOLD (the annotated spans of each asked type), NONE
(questions only). Cold per request (nonce, cache miss asserted), `reasoning_effort` "none", temperature 0.
ADMIT iff GOLD accuracy >= 0.50 AND paired GOLD - NONE lower 95% bound >= 0.15. Also printed: FULL accuracy, and per-type rows.
Fail -> the 27B is not an admissible reader on this task; A stops with a filed result.

**A1 Train (MLX GPU; kill checked early).** Qwen3-0.6B-Base, LoRA r16 on q,k,v,o all 28 layers (Rev 5 slot schema, binds with no
remap) + a host-side head: for each window, 41 sigmoid scores from [last-token hidden ; mean-pooled hidden]. Windows T=256 tokens, stride
224 (32 overlap), whole contract, no question in the input (one read serves all 41 types; the P-RATE rule favours T=256). Label = the type's
gold span overlaps the window. Positive-weighted BCE. Selection per type: top-2 windows by score; NULL if the max is below tau, tau set on
DEV only.
- Guards as P1b: GATE 0 GREEN launch, in-process watchdog, RED sentinel, kill line from gate0 avail.
- **KILL (diagnostic, not a capability verdict):** DEV evaluated every 500 steps. If, at 60 min of wall-clock training, DEV value-type hit@2
  (gold span overlaps a selected window, positives only) has a paired-bootstrap UPPER 95% bound < 0.70 -> stop and file. Hard stop at 3,000
  steps or 90 min, whichever first.

**A2 Silicon parity (ANE, < 1 h).** Pack, bind with kevd; base md5 unchanged before and after. DEV windows through ANE vs MLX:
per-type top-1 window agreement >= 0.99; predict latency printed (median, p95).

**A3 Final (TEST, frozen; one run, no re-tuning).** Per contract, one request per arm with all of its value questions:
PIPE = the question list + the ANE-selected windows (top-2 per value type, deduped, in document order); FULL = the whole contract.
Latency per contract, measured, not modelled: PIPE = ANE wall time for all windows of the contract (bind excluded, resident) + 27B request
time; FULL = 27B request time. Both cold.
- **G-E2E:** accuracy(PIPE) - accuracy(FULL), paired by question, contract-clustered bootstrap: lower 95% bound >= -0.05.
- **G-LAT:** median of per-contract (PIPE - FULL) seconds, contract bootstrap: upper 95% bound < 0.
- **G-SEL (reported with its bound, gates nothing alone):** TEST value-type hit@2 with CI; NULL false-positive rate on absent types.
- PASS = G-E2E AND G-LAT. Anything else is reported as measured with its bounds; no bar moves after data (SR 27).
- **Descriptive only:** ANE presence decisions for all 41 types on TEST (per-type F1 with CI, vs CUAD Yes/No). No bar: the 27B is not
  run on presence (4,000 FULL calls is out of scope), so this measures the map, not the handoff.

## 4. Scoring (parsers frozen with the splits; gold rows the parser cannot read are EXCLUDED and counted, never guessed)
Governing Law: US state or country name, case/"State of" normalized, exact. Agreement Date: m/d/y compared on the fields present in gold
("[]/[]/2013" = year only). Renewal Term and Notice Period: (number, unit) with unit in days/months/years, "successive" ignored, exact.
Answer extraction from the 27B: one line per question id; a missing line is WRONG.
Raw per question (prompt, response, parsed, gold) written live to jsonl in every stage; hashes in the result.

## 5. Known risks, named before data
- CUAD contracts are public EDGAR filings; the 27B may know some. NONE arm measures it; GOLD - NONE is the admission margin.
- Value-type positives on TEST: gold rates 0.85/0.91/0.32/0.20 (from all 510) x 96 contracts, roughly 220 questions; small types (Notice Period) get wide CIs and are
  reported per type, never headlined alone.
- NQ's failure mode (confident wrong picks from distractor sections) may recur; in-domain training on a CLOSED 41-type vocabulary is the
  difference being tested, and the 1 h kill catches it early.
- Head runs on host, like P2; the ANE provides hidden states. Said in every result.

## 6. Order and GPU budget
A0 (< 1 h) -> A1 (kill at 60 min, cap 90) -> A2 (< 1 h) -> A3 (< 1 h). Each stage starts only after the previous stage's filed result.

## Log
- 2026-09-24 drafted by CC.
- 2026-09-24 **Astra SIGNED** (verbatim): "I sign the design. The scope is appropriately narrowed to four value types, with the 35 presence
  types retained only descriptively. The staged gates are coherent... The no-question ANE pass is admissible because the four heads represent
  fixed contract field types; the prereg must retain the frozen type-to-head mapping and location-based definition of a hit."
  Condition adopted: head index i = the i-th CUAD category in `CUAD_v1.json` question order (frozen in splits.json as `type_order`);
  hit = gold span char range [start, start+len) intersects the selected window's char range, at original contract offsets.
- 2026-09-24 **Splits frozen**: `work/cuad/splits.json` (ids unchanged since first write; TEST 96/202 questions, DEV 40/83, ADMIT 60/127,
  TRAIN 280/630). Gold values the parser cannot read: GL 17, AD 11, RT 16, NP 4 (excluded, counted). Parser mutation tests 14/14.
- 2026-09-24 **A0 attempt 1 VOID (no result), CORRECTED**: first logged as "died silently"; that was WRONG. My liveness check
  (`pgrep -f "python3 a0_admit"`) cannot match the process, whose name is `.../Python a0_admit.py`, so it reported dead a run that was
  alive. Attempt 1 (PID 3536, 07:02:52, OLD parser) ran concurrently with attempt 2 (PID 6106, 07:06:36) for about 90 s, then CC killed
  3536 and its sentinel by PID. Attempt 1 raw kept as `a0_raw_attempt1.jsonl` (void). Attempt 2's first requests overlapped attempt 1 on
  Splash: A0 gates accuracy only, so its timings are not used.
- 2026-09-24 **DEVIATION 1 (before any A0 result)**: the prediction date parser dropped the month in "11/2006" (a correct month/year answer
  graded wrong). Fixed; mutation tests 6/6; `cuad_common.py` sha df4579a78cb3 -> 4367e946110d; splits.json sha now 7c0f095e56a3 (only the
  recorded code sha changed). Found by reading the raw. **Noted, NOT changed:** CUAD CSV gold can disagree with the annotated span (PAXMEDICA
  "5/25/08" vs the span "May 25th, 2018"); gold stays as declared, affects all arms equally, reported in the result.
- 2026-09-24 **A0 ADMITTED**: GOLD 0.976, FULL 0.969, NONE 0.000, GOLD-NONE CI [0.938, 1.000]. `RESULT_2026-09-24_A0_cuad_admission.md`. A1 launched.
- 2026-09-24 **A1 done**: DEV hit@2 1.00 (83/83) at step 500; DEVIATION 2 (stopped early, checkpoint provably fixed). `RESULT_2026-09-24_A1_cuad_train.md`. A2 launched.
- 2026-09-24 **A2 PASS**: agreement 0.9939 (1,640 pairs), 28.5 ms/window, base md5 unchanged. `RESULT_2026-09-24_A2_cuad_ane_parity.md`. A3 launched.
- 2026-09-24 **A3 NOT PASS**: G-LAT PASS (-9.12 s, CI [-11.98, -6.33]; 3.51 vs 12.45 s), G-E2E FAIL (-0.040, CI [-0.075, -0.005]).
  7 of 10 PIPE losses are tau NULLs on Renewal Term / Notice Period. `RESULT_2026-09-24_A3_cuad_final.md`. Program A closes as filed.
- 2026-09-24 **Astra ruling (verbatim)**: "A3 closes Program A as a latency win without non-inferior end-to-end accuracy. The NULL calibration
  diagnosis is useful, but removing that gate or always sending top-2 changes the policy and cannot be applied retrospectively to the frozen
  TEST. Move to B. An A' is defensible only as a separately signed follow-up with a new development rule, fresh test contracts, and a
  prospectively fixed handling of asked value types; the existing A3 result remains the failed preregistered outcome." **Program A CLOSED.**
