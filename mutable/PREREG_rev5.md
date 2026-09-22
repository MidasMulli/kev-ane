# PREREG Revision 5 (prospective): one resident mutable base, two domain adapters — CONDITIONAL fidelity claim with prospective coverage, and participation witnesses that satisfy the bounds on both states

Status: **CC author. ASTRA COUNTERSIGNED befe024c (design signature). NOTHING RUNS UNTIL THE OPERATOR AUTHORIZES.**
Supersedes Rev 4 (0d2a96c7, unsigned: acceptance did not establish the claim, and the participation
witness lost its guarantee). Supersedes §5 deployment acceptance of f23be94a ONLY; everything else in
f23be94a is unchanged and re-evaluated on fresh families. Rev 3 records are INSPECTED; used below only to
show reachability, never scored. Adapters W, D and the G0 base are not retrained or rebuilt.

## 0. The claim, narrowed explicitly (conditional fidelity)
On fresh held-out families, for each adapter with its own head, the deployed adapter:
- (i) is within the fp16 substrate bound of its torch reference at EVERY decide position (unconditional);
- (ii) reproduces EVERY reference decision the reference makes with |logit margin| >= 2;
- (iii) reproduces EVERY reference probability within 1e-3 where |logit margin| >= 8;
and those conditions COVER the task: per (domain, question), at least **99%** of held-out (record,question)
have margin >= 2 and at least **95%** have margin >= 8. Records outside coverage are reported with ids and
gaps. **Not claimed:** fidelity of any kind on records the reference decides with margin < 2; probability
fidelity below margin 8. PASS means exactly (i)-(iii) with the coverage bars met.

## 1. Acceptance rules, own combinations (W with H_W on suite_W, D with H_D on suite_D)
- **C1 substrate (every record):** relative hidden-state error at each decide position `<= 5e-2`. The value
  is the measured fp16 error on this build (p99 2.4e-02, max 3.9e-02 over 2464 positions, flat across
  margins) with margin; a violation is INVESTIGATED, not attributed. Any record over = FAIL.
- **C2 decision:** argmax equal on every record with margin >= 2. Any flip = FAIL.
- **C3 probability:** `|dp| <= 1e-3` on every record with margin >= 8. Any miss = FAIL.
- **Coverage (prospective):** margin >= 2 on >= 99% and margin >= 8 on >= 95% of (record,question), per
  (domain, question). Below either = the claim is NOT ESTABLISHED for that cell.
- Every report prints its complement: counts per margin band, worst gap per band.

## 2. Participation, with witnesses that satisfy the bounds on BOTH states (Astra)
A witness is a record on which the two adapter states are guaranteed distinguishable by a bound that
holds unconditionally on both. Two witness classes are required, a third reported:
- **P1 substrate witness:** at least one record where `rel ||hs_W - hs_D|| / ||hs_ref|| > 0.15` (3x C1) at a
  decide position, with BOTH deployed hs within C1 of their own references. C1 is unconditional, so
  identical deployed streams cannot pass.
- **P2 decision witness (fixed head):** with H_W held (then H_D), at least one record where the two torch
  reference states have OPPOSITE argmax, each with margin >= 2, and BOTH deployed states reproduce their
  reference decision (C2 applies to each state on that record).
- **P3 probability witness (reported; required only where it exists in torch):** records where the two
  reference states differ by > 2e-3 and BOTH have margin >= 8: both deployed states within 1e-3.
Zero P1 or zero P2 witnesses = PARTICIPATION NOT ESTABLISHED. Cross combinations are scored under
C1 (every record), C2 and C3 (in their margin bands), with coverage REPORTED, not required (they are
witnesses, not claims).

## 3. Reachability, from the INSPECTED Rev 3 run (headroom only; not scored under this revision)
Own coverage: W margin >= 2 on 99.96%, >= 8 on 99.92%; D 100% / 99.96% (bars 99% / 95%).
P1: hs separation W vs D on the same inputs 0.65-1.02 at all 2464 positions (threshold 0.15).
P2: H_W 41 witnesses, H_D 1333. P3: H_W 0 (would be reported as none), H_D 643.

## 4. Fresh evaluation set, and everything else
New families for both domains, new seeds, eval-only suites, >= 300 pairs per question, integrity gates
first, torch-tier §3 bars re-scored on them. Retention bitwise, dispatch 1:1, placement, bogus -14, rails
with adjacent idle, packed-vs-separate parity under C1-C3, wrong-domain as statistic: unchanged.
Mutation results from the Rev 3 run carry (trained on the frozen suites, not the eval set).

## Signatures
- CC: authored 2026-09-21 after Rev 4's rejection.
- **Astra: COUNTERSIGNED, body hash befe024c** (sha256 befe024c7c8ab26cb32e95bd98d52c2b885f258a53ac3073e3014f2ac08842c7; this block appended after signing). Verbatim: *"Yes. Countersigned as a design: Revision 5."* Design signature, not execution authorization. Rev 4 (0d2a96c7) rejected: acceptance did not establish the claim; participation witness lost its guarantee.
- Operator: run NOT authorized.
