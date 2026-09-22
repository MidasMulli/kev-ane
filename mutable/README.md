# Mutable adapters: one resident Kev base, swappable policies

> **This is a research characterization, not a stock-Mac feature.** Binding an adapter at runtime uses
> Apple's e5rt mutable-weight path, and that path is reserved by **two separate disabled boundaries**,
> for two distinct reasons (Paper 4 §1.7):
>
> 1. **Library validation (AMFI) off**, via `amfi_get_out_of_my_way=1`, so the harness can be ad-hoc
>    signed with the **four private entitlements** the bind requires:
>    `com.apple.aned.private.adapterWeight.allow`, `com.apple.aned.private.allow`,
>    `com.apple.aned.private.mappingMutableWeightsBuffer.allow`, `com.apple.private.IOKit-user-access`.
>    Removing any one of the four makes the mutable plan build return `-14` deterministically. This
>    barrier sits at **harness build time**.
> 2. **SIP off**, so the base and the adapter can be staged under the AppleIntelligence trusted path
>    (`/private/var/db/AppleIntelligencePlatform/AppModelAssets/`), which the runtime trusts by
>    **container prefix, not content signature**; writing there is impossible with SIP enabled. This
>    barrier sits at **deploy time**.
>
> The two are separable: entitlements are why a freshly built harness cannot bind on a stock machine;
> the trusted path is why the artifact cannot be placed where the runtime would accept it. Nothing in
> this directory runs on a stock Mac. What does not need the unlocked box: the suites, the
> pre-registration, the torch-tier results, and the training itself.

Kev-0.6B is a **Jev-class decision model**: typed questions go in as inputs, one forward pass answers all of them,
the answer is read off the hidden states by a pointer head. No decode. This directory makes that base **mutable on
the Apple Neural Engine**: the base is compiled once and stays resident; a policy is a 9.2 MB LoRA adapter (q,k,v,o,
r=16, 224 factor tensors) bound by URL through the e5rt mutable-weight path, exactly the mechanism of
[`ane-mutable-adapters`](https://github.com/MidasMulli/ane-mutable-adapters). The schema tensors (`cos`, `sin`,
block-causal `neg`) are graph **inputs**, so questions stay inputs on the mutable base too.

Two purpose-trained adapters ship here, on different domains, each answering two questions per pass:

| adapter | domain | questions |
|---|---|---|
| `adapters/W.bin` + `head_W.pt` | write-scope (tool-call phase) | outside the authorized write scope? deletes or overwrites? |
| `adapters/D.bin` + `head_D.pt` | disclosure (send phase) | recipient outside the authorized set? body carries a declared-pattern credential span? |

Labels come from deterministic resolvers (`resolver.py`, `resolver_d.py`); the adapters are advisory classifiers
that must express those policies faithfully. The LLM only generated scenario families; it never labelled anything.

## Results (Apple M5 Pro, macOS 27.0, PREREG_rev5.md, countersigned; RESULT_rev5.md)

Fresh scenario families, new seeds, never seen in training. Torch tier: W scope 6/1020 missed, 0/1020 unnecessary,
1014/1020 flip pairs; W destructive 0, 0, 1020/1020; D recipient and D secret 0, 0, 320/320 each.

On the ANE, one compiled base, adapters swapped by URL:

| | |
|---|---|
| swap (bind) | 65-80 ms, base `weight.bin` md5 unchanged after every bind |
| pass | 29.5 ms at T=256, two questions |
| substrate | rel hidden-state error <= 5e-2 at every decide position (max 4.98e-02) |
| decisions | every reference decision at margin >= 2 reproduced; every probability within 1e-3 at margin >= 8; coverage 0.9995-1.0 |
| participation | streams differ > 0.15 with both within bound on 4080/4080 positions; 76 and 639 opposite-decision witnesses reproduced |
| retention | W -> D -> W bitwise on 2040 records |
| dispatch | 300 issued predictions matched 1:1 to 300 ANE intervals |
| energy | ANE 0 -> 7,050 mW with adjacent idle; ~191 mJ/decision on the ANE rail, ~243 mJ whole-system incl. host work |
| placement | runtime trace: 1 ANE procedure, mutable section 0x8c0000 = adapter bytes minus headers, one ANE request per pass, no fallbacks |

**Claim boundary.** Conditional fidelity, as written in PREREG_rev5.md §0: nothing is claimed for records the
reference decides within 2 logits of the boundary; fp16 cannot hold a probability there, which is why the first
criterion (RESULT_rev3_FAIL.md) failed on one record and was re-derived prospectively. The D evaluation rests on 8
families (62 of 70 generated were dropped by a no-shared-roster-id rule). Not claimed: broad competence, or that two
adapters beat one. Energy at T=256 is about 4x the fused T=107 figure in the top-level README: same silicon, longer
window.

## What is here

- `deploy_inputs.py` builds the mutable base (`g0`) and packs a trained adapter against it (`pack`).
- `kev4.mm` (4-input entitled harness, timestamps per load/predict), `computeplan.mm`, `ui/kevd.mm` (resident daemon).
- `prep4.py` (records -> x/cos/sin/neg), `hs_ref.py` (torch hidden-state references), `analyze_rev5.py` (acceptance),
  `dispatch2.py` (1:1 dispatch reconciliation), `score2.py` (torch-tier bars with Wilson LCB), `integrity2.py`.
- Data pipeline: `gen_scenarios.py` / `gen_d.py` (families from a local LLM), `build_w2.py` / `build_d.py` /
  `build_fresh.py` (suites, flip pairs, family split), `make_shuffled.py` (label-shuffle mutation).
- Drivers, in the order they ran: `g0_gate.sh`, `battery2.sh`, `rev5.sh`, `closure5.sh`.
- `ui/`: the live swap UI (`server.py` + `index.html`), telemetry from `powermetrics`, `capture_demo.py` (the video).
- `suites/`: frozen training suites and the fresh eval suites, with manifests. `kev_swap_demo.mp4`: the live capture.

## Reproducing

1. The base and the bind recipe are the sanctioned e5rt path from `ane-mutable-adapters`, and carry its
   requirements in full: **SIP off**, `amfi_get_out_of_my_way=1`, the four `aned` entitlements on the
   harness (self-signed, honored only under SIP off), the compiled model copied into
   `/Library/Caches/com.apple.aned`, adapters in `/var/db/AppleIntelligencePlatform/AppModelAssets/…`, run under
   `sudo`, compute units CPU+NE. From an ordinary directory the mutable plan build fails with the generic `-14`.
2. `python deploy_inputs.py g0 _out 256` builds and repoints the base (224 consts -> `adapter.bin`, `BlobFileMutabilityInfo`).
3. `python deploy_inputs.py pack _out 256 W <kev_run_dir>` packs a Kev-trained attn adapter (`kev.train --lora_targets attn`).
4. `g0_gate.sh`, then `battery2.sh` / `rev5.sh` for the full acceptance; `ui/README.md` for the live UI.

Training uses Kev's trainer (`kev.train`, [jaredpalmer/kev](https://github.com/jaredpalmer/kev)); the hidden-state
side uses this repo's `kev_ane` package.

**Paths.** These scripts ran on one machine and still carry its absolute paths (`/Users/midas/...`, listed by
`grep -l /Users/midas *`). They are published as they ran, not rewritten; adjust the few path constants at the top of
each file. Every number above was produced by exactly these files.

**Placement evidence.** `MLComputePlan` is a plan, not placement. The evidence used here is the runtime log across a
cold bind (`log stream` with the `espresso`/`ANE`/`aned`/`ANECompilerService` predicate): `numProcedures=1`, the
mutable kernel section size equal to the adapter bytes minus section headers, `ResetStream(): No ops in stream`, and
one `addWeightsBuffer ... procId` request per prediction.
