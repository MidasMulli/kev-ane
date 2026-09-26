# PREREG DRAFT 2026-09-24 - Program B2: pipelining the ANE contract map with the 27B

Status: DRAFT, UNSIGNED. Order per Astra: B1b, then B2 "with the mechanism and kill thresholds fixed". Mechanism fixed from B1b: the
GPU cost tracks ANE weight re-reads per second, so the ANE side runs at T=256 (the lowest weight traffic per token available).

## 1. Question
In the Program A pipeline (ANE map of a contract -> 27B answers from the top-2 windows per asked value type), does running the ANE map of
contract i+1 WHILE the 27B serves contract i raise end-to-end throughput over running the two stages back to back? This is a systems
measurement: answers are checked for equality between modes, accuracy is not re-claimed (A3 stands).

## 2. Workload (frozen)
- The first 24 contracts of the A3 TEST list with >= 1 value question (already used; no accuracy claim, so reuse is admissible here; stated).
- Selection policy: top-2 windows per asked value type (the A' diagnostic policy, no NULL gate), adapter CUA, same prompt, cold requests
  (nonce), reasoning_effort none, temperature 0, max_tokens 200.
- SEQ: for each contract, ANE map then 27B request, then the next contract.
- PIPE: an ANE thread maps contracts in order into a queue; the main thread sends each 27B request as soon as its evidence is ready.
  The ANE may run ahead by any amount (no cap).

## 3. Measurement
Wall time for all 24 contracts, per mode; 5 reps, order alternating (SEQ first on even reps). Per request: ANE stage time, 27B time,
prompt tokens; per mode: CPU/GPU/ANE watts (powermetrics).
- Correctness check (asserted per rep): every 27B response text identical between SEQ and PIPE for the same contract (temperature 0).
  A mismatch is logged and counted; more than 2 of 24 in a rep voids that rep.

## 4. Decision rule (paired by rep, bootstrap over 5 reps, 95% CI; margin fixed now)
Gain = wall(SEQ) / wall(PIPE) - 1.
- lower bound >= 0.05 -> "pipelining raises throughput";
- upper bound < 0.05 -> "no practical gain at the 5% margin";
- otherwise INCONCLUSIVE with the interval.
- Descriptive: the ceiling for this workload, (sum of ANE + sum of 27B) / max(sum of ANE, sum of 27B) - 1, from the SEQ timings, and
  the 27B per-request slowdown in PIPE vs SEQ (the contention cost, now on a prefill-heavy request, which P-CC did not measure).
- Kill (fail fast): after 2 reps, if both reps show PIPE slower than SEQ, stop and file. Budget: 5 reps x 2 modes x 24 contracts x
  about 3.5 s, about 14 min of GPU.

## 5. Not claimed
Accuracy (A3 stands); other workloads, request mixes, batch sizes; the mechanism behind any 27B slowdown beyond B1b's.

## Log
- 2026-09-24 drafted by CC.
- 2026-09-24 **Astra SIGNED B2** ("I sign B2. ...Reuse of A3 contracts is acceptable because B2 makes no accuracy or generalization claim.").
- 2026-09-24 **B2 PASS**: gain +0.462 [0.436, 0.489], ceiling +0.513, 27B per-request ratio 0.998, 0 mismatches. `RESULT_2026-09-24_B2_pipelined_contract_review.md`.
