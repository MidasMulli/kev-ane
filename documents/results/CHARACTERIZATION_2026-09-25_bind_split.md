# CHARACTERIZATION 2026-09-25 - where the ~70-90 ms of a kevd BIND goes (not a claim-bearing experiment)

Instrument: `work/bindprof/bind_profile.py`, a fresh kevd on the resident Qwen3-0.6B kev-form base (fp16), ANE otherwise idle (asserted),
GATE 0 GREEN, one process, one session, n = 20 per arm (10 for first-predict). Raw + summary: `work/bindprof/bind_profile.json`.
kevd BIND = `[MLModel modelWithContentsOfURL:configuration:]` with `setE5rtMutableMILWeightURLs:` (warm e5rt cache hit; the base is not
recompiled; the adapter fills the program's mutable weight sections; card: project_ane_mutable_weights).

| arm | median | p10-p90 |
|---|---|---|
| BIND none (instantiate, no adapter) | **61.6 ms** | 61.0-64.8 |
| BIND CUA, same adapter repeated | 65.5 ms | 64.7-67.9 |
| BIND alternating CUA / IS3 | 66.2 ms | 64.9-69.1 |
| first PREDICT after a BIND | 33.5 ms | 32.9-34.6 |
| steady PREDICT | 28.5 ms | 28.4-28.8 |
| read the 9.2 MB adapter file (page cache) | 0.25 ms | 0.24-0.32 |

## Split (arithmetic on the medians)
- Instantiating the cached model: ~61.6 ms, about 87% of the effective swap.
- The adapter itself (mutable-section fill): 66.2 - 61.6 = **~4.6 ms**.
- Deferred to the first PREDICT: 33.5 - 28.5 = **~5.0 ms**.
- Effective swap cost ~71 ms; matches the recorded 0.6B fp16 sweep (71.7 ms). Data movement is negligible (0.25 ms read).
- kevd does not skip a same-adapter BIND: repeat (65.5) ~= alternating (66.2). A skip-if-already-bound check saves the whole cost for
  consecutive same-domain documents (the recorded tool path already does this: 0.0 ms repeat).
- Demo-run binds read 88-98 ms today vs 65 ms here; the difference was not isolated (system load at the time is the untested candidate).

## What it opens (engineering, untested)
The adapter is ~5 ms of a ~71 ms swap; ~62 ms is per-instance setup. Holding one pre-bound MLModel instance per adapter would make a
switch a pointer change, if instances share the resident base. Memory per instance is the unknown to measure first.

## Log
- 2026-09-25 filed by CC. The runtime log-trace split (e5rt cache hit / initMutableKernelSections) was not needed for this answer and not run.
