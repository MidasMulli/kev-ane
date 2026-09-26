# RESULT 2026-09-24: Program A / A2 (silicon parity). PASS

- adapter_CUA.bin (md5 ef2a095cd01f4b5c5cdab6a2fdeacc48, packed against the Rev 5 G0 base) bound into a private kevd on the resident base; head on host.
- All 1,406 DEV windows on the ANE vs the MLX A1 scores: per-(contract, type) top-1 window agreement **0.9939** over 1,640 pairs (gate
  >= 0.99, PASS). Value types 0.994 (160 pairs); pairs above tau 0.996 (739). Max |prob diff| per contract about 0.02.
- ANE predict 28.5 ms median, 28.97 ms p95 (kevd-measured, T=256). Base weight.bin md5 unchanged across bind and run.
- Raw `work/cuad/a2_raw.jsonl` (cbf132b998ae). First launch failed before any measurement (the packer needs head.pt in the run dir; added).
