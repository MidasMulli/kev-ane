# RESULT 2026-09-24: A'' (close the gap). PASS (registered), BORDERLINE and ADJUDICATION-SENSITIVE: non-inferior at 0.05 and 3.6x faster on 60 fresh contracts

Design `PREREG_DRAFT_2026-09-24_A2prime_close_the_gap.md` (Astra-signed v2). Policy P2 (top-3 windows per asked value type) picked on
USED data before the test set existed. Fresh set: 60 Pile-of-Law atticus contracts (public EDGAR), CUAD-disjoint (fuzzy max 0.026),
`work/cuad/fresh/fresh60.json` (30113583867e). All four value questions asked of every contract (240). Raw `work/cuad/a2p_raw.jsonl`
(3accf4b63962); scoring `a2p_result.json` (130186148002); sealed mapping 16821854b6e5, opened only after all verdicts were filed.

| | PIPE (ANE map, top-3 -> 27B) | FULL (27B reads the whole contract) |
|---|---|---|
| median seconds per contract | 7.40 | 26.93 |
| median 27B prompt tokens | 2,671 | 13,062 |
| answers agreeing with the other arm | 233 / 240 (0.971) | |

- **G-E2E PASS:** accuracy PIPE - FULL = -0.021 (1 PIPE-only-correct, 6 FULL-only-correct, of 240), contract-clustered CI
  [-0.046, 0.000]; bar lower >= -0.05. **Narrow: the lower bound clears the bar by 0.004.**
- **G-LAT PASS:** median per-contract -19.6 s, CI [-22.8, -17.3] (3.6x faster).
- Adjudication (fresh blinded sub-agents, CC adjudicated nothing): a1/a2 raw agreement 4/7 (0.571), **kappa 0.323 (low)**. The three
  splits (items 001, 002, 005, all Agreement Date) turned on rubric edge cases (a stock plan's "became effective" date; an "as of the
  Effective Date" opening); the third adjudicator decided all three for FULL by the rubric's literal wording.
- Sensitivity (descriptive, not a re-verdict): under adjudicator 1's reading of items 002 and 005 (effective dates count), those two go to
  PIPE and the difference is -0.004; the declared majority rule gives -0.021. The PASS holds under both readings.
- PIPE-only losses by type (final): Governing Law 1, Agreement Date 3, Renewal Term 1, Notice Period 1. PIPE-only win: Agreement Date 1.
- Scope: relative accuracy against a full read (no human gold), four value types, one frozen adapter, public commercial/employment/loan
  contracts of 8k-32k tokens. The adjudicators share a model family (disclosed limitation).

## Astra qualification (2026-09-24, verbatim)
"The frozen PASS can stand, but it should be qualified as borderline and adjudication-sensitive. The 0.004 margin is small relative to
the three arbitrated Agreement Date cases, and kappa=0.323 indicates limited inter-adjudicator agreement. Preserve the registered PASS,
while avoiding any claim of robust accuracy superiority or generalization beyond this 60-contract set and rubric."
