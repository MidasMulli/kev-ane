# RESULT 2026-09-24: A-long (plan step 1; 31 untouched long CUAD contracts). NOT PASS on accuracy by the frozen bound; 10.4x faster

Plan `PLAN_2026-09-24_next_sequence.md` (step 1 signed by Astra). 31 gated contracts (33k-82k tokens; the 3 envelope contracts excluded
before the run), 61 value questions. Frozen adapter CUA, top-2 windows per asked type, no NULL gate, years = 12 months in both arms.
Raw `work/cuad/along_raw.jsonl` (549f41229cf4). Base md5 unchanged. Envelope: all GATE 0 GREEN up to 83,040 27B tokens.

| | PIPE (ANE map -> 27B on ~1.2k tokens) | FULL (27B reads the whole contract) |
|---|---|---|
| accuracy | 0.967 (59/61) | 1.000 (61/61) |
| median seconds per contract | 8.65 | 90.07 |
| median 27B prompt tokens | 1,172 | 39,731 |

- **G-E2E FAIL:** PIPE - FULL = -0.033, contract-clustered CI [-0.085, 0.000]; the bar needed the lower bound >= -0.05.
- **G-LAT PASS:** median per-contract (PIPE - FULL) = -80.9 s, CI [-105.0, -74.1]: **10.4x faster** at the median.
- Per type (PIPE / FULL): Governing Law 1.00 / 1.00 (29); Agreement Date 0.917 / 1.00 (24); Renewal Term 1.00 / 1.00 (6);
  Notice Period 1.00 / 1.00 (2). Selection hit@2 0.918, CI [0.850, 0.982].
- **Both misses are Agreement Date:** gold "06/[]/2010", PIPE answered "2010" (month missing), FULL "June, 2010"; gold "5/5/98",
  PIPE "6/1/1998" (a different date from a selected window), FULL "5/5/1998".
- Power, stated plainly: with 61 questions and FULL at 1.000, two PIPE misses already put the lower bound at -0.085; the gate needed
  about one miss or fewer. The plan named the low power before the run; the bar is not moved.
- Reading (not a claim beyond the data): on unseen long contracts the ANE->27B pipeline answered 59 of 61 value questions right while the
  27B read about 3% of the tokens and returned in a tenth of the time; the fix for A3's NULL losses held here (Renewal/Notice 8/8), and the
  two losses are date-reading on dates, not NULLs.
