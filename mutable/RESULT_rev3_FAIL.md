# RESULT 2026-09-21: PREREG one_base_two_domains (Rev 3, f23be94a) — W-deployment FAIL; two-domain deployment claim NOT ESTABLISHED

Ruling (Astra, verbatim): *"File W-deployment FAIL and the overall two-domain deployment claim as not
established under f23be94a. W breaches the every-record fidelity rule, and both fixed-head cross-
combinations fail their reference-fidelity gates. Margin-conditional reporting is useful diagnosis, not an
alternative route to PASS. The successful build, placement, retention and passing fidelity cells remain
reportable as separate results. They do not discharge the failed gates."*

## Separate results that stand (each measured, instrument named)
- **G0, the new blueprint row:** kev-form base (x,cos,sin,neg as graph INPUTS, block-causal mask per
  request) with 224 mutable q/k/v/o factors on ONE compiled base, T=256. Sanctioned recipe: bind OK,
  `Has mutable kernel section` 3 (11 across the battery's 9 binds), fvmlib overflow 0, bogus path -14,
  MLComputePlan NE=2302 CPU=0 GPU=0, base weight.bin md5 unchanged across every bind. Load 100 ms,
  predict 29.5 ms at T=256 (kev4.mm; T^2 attention vs 9 ms at T=80).
- **Torch tier, every bar clear** (held-out, family split, majority 0.500): W scope 0/616 missed,
  2/616 unnecessary, 614/616 pairs (LCB 0.988); W destructive 0, 0, 616/616; D recipient 0, 0, 668/668;
  D secret (declared-pattern membership) 0, 0, 668/668. Integrity predictors exactly 0 on the masked
  question, the other question unchanged. Mutation (shuffled labels): W at chance loss; D pending.
- **Silicon, passing cells:** D fidelity PASS, max|dp| 1.5e-04 and argmax equal on all 2672 held-out
  (record,question); retention W->D->W bitwise on 1232 records; packed-vs-separate parity W[scope]
  bitwise 0.00, all four within rule; dispatch 300 issued matched 1:1 to 300 ANE intervals, p50 28.77 ms,
  1 extra interval reconciled against 1 load, PASS; fixed-head participation established in torch
  (separation > 2e-3 on 2464 / 1657 pairs) and D own-trunk deployed vs reference PASS.
- **Wrong-domain readout (statistic):** all four combinations 0.500-0.502 vs majority 0.500.

## Failed gates (the rule: max|dp| <= 1e-3 AND argmax equal on EVERY record)
- W fidelity: 2462/2464 within 1.6e-06, argmax 2464/2464, ONE record (fam0103/op7/in/orig) |dp| 0.19,
  its twin 0.084. **FAIL.**
- Fixed-head cross combinations: H_W on D-trunk max|dp| 2.45e-02, 5 argmax flips; H_D on W-trunk
  1.79e-02, 0 flips. **FAIL.**

## Diagnosis (hypothesis, per Astra; not a route to PASS)
max|dp| by torch |logit margin| bin is monotone in every combination: >=8 -> <=1.7e-04; [4,8) -> <=6.6e-03;
<4 -> up to 0.19. Consistent with sigmoid sensitivity to an fp16 hidden-state error. The hidden-state error
itself is being measured directly (hs_error.py) to establish or refute the uniform-perturbation mechanism
before any Revision 4 criterion is proposed. These records are inspected; Revision 4 cannot relabel them.

## Not claimed
Two-domain deployment on one base; any fidelity claim on low-margin records; W deployment.

## Addendum: mechanism measured (hs_error.py, after the ruling; changes no verdict)
Relative hidden-state error of deployed W vs torch KevIn at all 2464 decide positions: p50 1.06e-02,
p99 2.38e-02, max 3.89e-02 (a saturated record). By torch-margin bin the p50 is 1.5e-02, 1.7e-02,
1.02e-02, 1.09e-02: flat. The two failing records (1.7e-02, 1.4e-02) are inside the population. The
artifact is uniformly fp16-accurate; the probability gap is sigmoid slope at small margin.

## Addendum: mutation and rails (landed after the ruling; no verdict changes)
Shuffled-label mutation, held-out vs true labels: W scope 47.4/56.8%, pairs 10.9%; W destructive
55.4/44.6%, pairs 0; D recipient constant "no" (missed 100%, pairs 0); D secret missed 90.7%, pairs
8.4%. All at or below majority 0.500. Rails, quiet box, adjacent idle: ANE 0 -> 7060 mW under W
(predict 28.71 ms, 600 records); CPU 1066 -> 2669 mW; GPU 2662 -> 4092 mW (Splash resident; the
+1.4 W GPU rise under an ANE workload is unexplained and reported as observed).
