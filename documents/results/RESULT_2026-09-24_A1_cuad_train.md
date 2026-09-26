# RESULT 2026-09-24: Program A / A1 (ANE contract-map adapter, MLX training). DEV hit@2 1.00, no kill

- Data: 11,338 TRAIN windows (4,199 with >= 1 positive label), 1,406 DEV windows; T=256, stride 224, no question in the input.
- DEV value-type hit@2 at step 500: **1.00 (83/83), CI [1.00, 1.00]** (contract-clustered; CI degenerate at ceiling).
  Per type: Governing Law 32/32, Agreement Date 36/36, Renewal Term 10/10, Notice Period 5/5.
- Surprise checks (all before continuing): trivial baselines on the same DEV questions: first-2 windows 0.41 (Agreement Date 0.94, all
  others 0.00); random-2 at most 0.19. Independent recomputation from the saved DEV scores: 1.00. Location check: 91.6% of gold spans lie
  FULLY inside a chosen window, the minimum is 76%.
- KILL rule: DEV upper bound 1.00 >= 0.70, not fired. Peak MLX 10.2 GB (kill line 16.0).
- **DEVIATION 2 (execution only; outputs identical by construction):** the declared checkpoint rule keeps the best DEV hit@2 and replaces
  it only on a strictly higher value. At 1.00 after step 500 it could never be replaced, so the remaining steps could not change the kept
  checkpoint. CC stopped the run at about step 650 and computed tau with the SAME code block from a1_train.py on the saved step-500 DEV
  scores. Checkpoint `a1_best.npz` md5 54181a9b1c5f.
- Caveat named: DEV is small (40 contracts, 83 questions) and at ceiling, so it cannot tell checkpoints apart; A3 TEST (96 contracts, 202
  questions) is the measurement. tau (DEV presence-F1 argmax): Governing Law 0.539, Agreement Date 0.233, Renewal Term 0.972, Notice Period
  0.990; the high Renewal/Notice thresholds can NULL true positives on TEST, which counts as wrong there (declared).
