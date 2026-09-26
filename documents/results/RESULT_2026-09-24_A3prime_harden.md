# RESULT 2026-09-24: A''' (harden). PASS, and ROBUST: non-inferior at 0.05 with the CI far inside the bar; adjudicators agree 23/23

Prereg `PREREG_2026-09-24_A3prime_harden.md` (signed). 200 fresh public contracts (fresh200.json beaeb7b0294e), disjoint from all 510 CUAD
and the 60 A'' contracts; frozen adapter CUA, frozen policy P2 (top-3), tightened rubric frozen before the draw. 800 questions.
Raw `work/cuad/a3p_raw.jsonl` (3ff0af94e66d); scoring `a3p_result.json` (dd840a63819b); sealed mapping 12f526d8a2b3 (opened after all verdicts).

| | PIPE (ANE top-3 -> 27B) | FULL (27B reads the whole contract) |
|---|---|---|
| median seconds per contract | 7.5 26.87 2659 13067 |  |
| median 27B prompt tokens |  |  |
| agreement between arms | 777 / 800 (0.971) | |

- **G-E2E PASS:** PIPE - FULL = **-0.011, CI [-0.021, -0.001]** (bar: lower >= -0.05; clears by 0.029). The upper bound is below 0: a SMALL
  REAL deficit of about 1 point remains; non-inferior at the declared margin, not equal.
- **G-LAT PASS:** median per-contract -19.4 s, CI [-21.2, -17.4].
- Adjudication: 23 disagreements; adjudicators 1 and 2 agreed on **23/23 (kappa 1.0)**, no arbitration (A'' was 4/7, kappa 0.323: the
  tightened rubric removed the ambiguity). PIPE-only correct 5, FULL-only correct 14, both wrong 4.
- Remaining PIPE-only losses: Agreement Date 8 (dates again), Governing Law 3, Renewal Term 2, Notice Period 1.
- Protocol deviations (logged, judged non-material): three adjudicator batch agents ran `ls` on their OWN adjudicator's output folder
  after writing (filenames only, no contents opened); one batch agent could not rule out overwriting its own files. No agent read the
  other adjudicator's folder or the sealed mapping.
- This supersedes A'''s borderline reading: on 200 more fresh contracts, with near-perfect adjudicator agreement, the ANE map + 27B is
  within about 1 point of a full read while taking a quarter of the time and about a fifth of the tokens.
