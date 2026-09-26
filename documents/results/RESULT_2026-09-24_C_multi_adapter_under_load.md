# RESULT 2026-09-24: Program C (three adapters swapped within one request, beside 27B decode). Both rules favourable

Design `PREREG_DRAFT_2026-09-24_C_multi_adapter_under_load.md` (signed CC + Astra). Systems only; no task-quality claim. Resident Rev 5
base, adapters CUA / W / D rotated every 8 passes at a fixed 20 passes/s (T=256), 6 reps. Raw `work/cuad/c_raw.jsonl` (1b02c2f28367).

- Preconditions PASS: the three adapters give distinct outputs on one window (max |diff| CUA-W 80.4, CUA-D 77.3, W-D 17.7); after
  CUA -> W -> D -> CUA the CUA output is bitwise identical to its first output. Pass rates S0 19.97, S1 19.95 (target 20). Base md5 unchanged.
- **C-GPU:** ret(S0) - ret(S1) = +0.021, CI [0.001, 0.046] -> **"swapping costs the 27B nothing at the 0.05 margin"** (upper < 0.05).
  The lower bound is above 0: a small cost of about 2 points of decode retention is measurable, below the declared margin.
  (27B retention: S0 0.979, S1 0.958, with about 2.4 binds/s.)
- **C-LAT:** bind ms under load / idle = 1.10, CI [1.089, 1.112] -> **"binds not materially slowed under load"** (upper < 1.25).
  Medians: 74.7 ms idle, 81.9 ms beside 27B decode (about +10%). Consistent with the recorded 71.7 ms sweep value.
- Descriptive: for a 3-stage request (2 binds, 3 stages of 8 passes), swap overhead is 17.7% of ANE time idle and 19.1% under load.
  Swap cost is per adapter CHANGE; stages longer than 8 passes shrink it proportionally.
- Not claimed: usefulness of any multi-stage chain; other bases or precisions; cold file cache.
