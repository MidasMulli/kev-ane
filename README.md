# kev-ane

**Kev-0.6B, a Jev-class decision model, running on the Apple Neural Engine.**

One document (the *state*), a set of typed questions with allowed answers, and a probability
distribution per question out — in **one forward pass, with no token generation**.

All numbers below were measured on an M5 Pro (macOS 27.0, build 26A5421a) and are reproducible
with the gates in this repo. Nothing here is a claim about Jev's internals.

| | |
|---|---|
| latency, T=64 | **7.16 ms** p50, p99 7.62 (encode 0.35 · ANE 6.72 · pointer head 0.09) |
| latency, T=256 | **27.64 ms** p50, p99 28.61 (encode 0.75 · ANE 26.72 · pointer head 0.09) |
| throughput, T=64 | **150.5 decisions/s** sustained (3 reps, 1000 predicts each: 150.5 / 150.4 / 150.5) |
| agreement with Kev's reference, **155 real records** | **155/155 argmax**, both the CPU fp32 and the ANE fp16 arm |
| probability difference over those 155 | CPU fp32 max **1.23e-05** (p50 2.1e-06) · ANE fp16 max **3.80e-02** (p50 4.4e-03) |
| probability difference, single reference record | CPU fp32 **9.08e-09** · ANE fp16 **9.25e-05** |

Every figure above was reproduced from a clean clone in a temp directory, not from the tree it
was developed in.

⛔ **Read the two agreement rows together.** The single-record figures are the best case — one
short 3-way record. Across 155 real 4-way and 6-way records from Kev's own `transfer-v4`
development suite the difference is three orders of magnitude larger, while the decision itself
never changes. Padding is excluded as the cause: the same record at T=64 and T=256 differs by
exactly 0.000e+00, so this is accumulation order through 28 layers, growing with sequence length
and option count. `gates/g4_suite_parity.py` gates on argmax agreement and reports the
probability spread rather than judging it against a bar set on one record.

## Placement is measured, not asserted

A port that "runs on the ANE" is easy to claim and easy to get wrong. Three supporting
observations, all reproducible here. Individually each is weaker than it looks — the first shows
only that the tested CPU path fails, the second only that the engine participated — but nothing
explains all three except the work running on the Neural Engine:

1. **Output divergence.** `CPU_ONLY` returns **all zeros** for this graph — that CoreML backend
   does not compute it. A correct result is obtainable only when the Neural Engine is allowed.
   ⛔ This is *not* a speed comparison, and not evidence about CPUs in general: there is simply no
   working CPU output to compare against.
2. **Dispatch intervals.** Apple's xctrace *Neural Engine* instrument counts **303 intervals =
   2 load + 301 predict** against 301 in-process predicts, and at n=1000, **1003 = 2 + 1001**
   against 1001 — the took-check that instrument requires. Steady state: 150.8/s, 95.9% duty,
   p50 6.35 ms.
   `tools/ane_dispatch.py`. Two details that decide whether the number means anything:
   * The **two load dispatches** (a multi-second compile and a ~26 ms first-touch) precede the
     first predict. Including them in the span understates the rate by ~3x; the tool reports them
     separately and computes the rate over steady state only.
   * The **took-check is mechanized, not advisory.** The workload writes its own predict count to
     a file, because xctrace captures the launched process's stdout and a printed count never
     reaches you. Defeating the ref/id resolution — the naive-reader bug the tool warns about —
     was measured to yield **277 against 301**, an 8% undercount with an unchanged p50 and a
     wholly plausible 139.7/s. Without the check that reads as a measurement.
3. **Power.** `powermetrics` reads **0 mW idle → ~7100 mW under load** on the ANE rail.
   ⛔ `-s ane_power` **alone emits no ANE section at all**; the `ANE Power` line only appears when
   `cpu_power` is requested alongside it. Ask for `-s cpu_power,ane_power` or you get silence and
   will read it as zero.

## Quick start

```sh
pip install -e '.[parity]'          # parity extra is needed by every gate that cites Kev
kev-ane-convert --buckets 64 256    # downloads base + adapter, merges, converts
python gates/g3_placement.py        # the proof that needs no reference implementation
```
Gates 0, 1, 2 and 4 all compare against Kev's own code, so they need it on the path:
```sh
git clone --depth 1 https://github.com/jaredpalmer/kev /tmp/kev
python gates/g0_encode_parity.py --kev-src /tmp/kev   # encoder must match token-for-token
python gates/g1_numeric_cpu.py   --kev-src /tmp/kev   # merged conv-form vs reference
python gates/g2_numeric_ane.py   --kev-src /tmp/kev   # on the engine
python gates/g4_suite_parity.py  --kev-src /tmp/kev --n 400 --package kev06b_trunk.mlpackage
```
Gate 4 is the one to run if you only run one: 155 real records rather than a single fixture.

## What the port actually does

* **Conv-form trunk** — Qwen3-0.6B as Conv2d-as-linear over `(1, C, 1, T)`, matmul attention,
  GQA, per-head q/k norm, SwiGLU. `src/kev_ane/trunk.py`.
* **`cos`, `sin` and the attention mask are INPUTS, not baked constants.** This is the part that
  matters. Kev's branch positions restart after the state, and its mask is **block-causal** over
  (state, question, options) — rebuilt per request from the `seg`/`opt` arrays. A port that bakes
  positions and a plain causal mask cannot express a second schema.
* **No vocab head.** Kev never generates; the readout is a pointer head over hidden states, run
  on the CPU in ~0.09 ms.
* **196 LoRA deltas merged** — 28 layers × 7 projections, `W += (α/r)·B@A`.
* **Fixed shape buckets, 64 and 256.** The engine prefers static shapes; Kev solves the same
  problem on MPS with `KEV_SHAPE_BUCKET`.

## Two things this repo does not claim

**Decision quality.** This repo does not measure it, and nothing here should be read as evidence
about it. What the gates establish is *agreement*: on the same inputs, our port returns what Kev's
implementation returns, including on records both get wrong. Agreement is not accuracy.

For accuracy, use the author's own published figures rather than anything derived here. Kev-0.6B
scores **0.801 dev / 0.808 locked test** in-distribution (1,200 items) and **0.620 dev / 0.642
locked test** out-of-domain (764 items, `transfer-v4`), on frozen checksummed suites with the
locked test read once. Those are the numbers to cite, with that checkpoint and suite revision
named. See Kev's README and model cards.

**That the ANE is faster.** No speed advantage is established here, in either direction. The
CoreML CPU arm returns zeros, so it cannot serve as a baseline, and we did not build another one.
The motivating property is not speed but placement: these decisions run on silicon that is
otherwise idle while a GPU-resident LLM generates.

## Relationship to ane-mutable-adapters

[`MidasMulli/ane-mutable-adapters`](https://github.com/MidasMulli/ane-mutable-adapters) hot-swaps
a LoRA adapter over a frozen resident base on the ANE. **This repo is the other half, and they do
not compose today:**

| | mutable adapter slots | live schema |
|---|---|---|
| `ane-mutable-adapters` | ✅ 56 parallel-delta slots, mutable bind | ⛔ positions and mask baked as buffers |
| `kev-ane` | ⛔ LoRA merged, no slots | ✅ positions and mask are inputs |

⛔ **These are two different capabilities, and it is easy to run them together.** Changing the
*schema* needs no weight change at all — in this repo schemas are request inputs, so a different
question set, option count or branch layout is already just a different `cos`/`sin`/`neg`. What
does not exist in either repo is the **combination**: swapping the adapter live, on a resident
base, while schemas stay request-dependent. That is the missing piece, not schema switching.

## Credit

Kev is **[@jaredpalmer](https://github.com/jaredpalmer/kev)**'s independent, Jev-inspired
implementation (Apache-2.0). It is not official open-source Jev.

The Jev decision paradigm is **TypeSafe / Diogo Almeida**'s, and Jev itself is closed. The precise
boundary: **no proprietary Jev code or weights are used here.** This port derives from Kev, which
in turn follows an architecture **Archer Hume** reconstructed from external probing in
[*Jev's Architecture Unmasked*](https://archerhume.com/posts/jevs-architecture-unmasked) — an
inference about Jev's internals, not confirmed knowledge of them, and we treat it as such.

We ported Kev to the Neural Engine and measured it. See `NOTICE`.
