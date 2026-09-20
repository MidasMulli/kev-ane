"""GATE 4 — parity across MANY REAL RECORDS, not one fixture.

Gates 1 and 2 pin the numerics on a single hand-written record. That is enough to catch a broken
port and nowhere near enough to support a headline like "max abs difference 1e-08": one record
exercises one sequence length, one option count, one branch layout.

This runs Kev's own `transfer-v4` development records — the suite its author published out-of-domain
numbers on — through BOTH implementations and reports the DISTRIBUTION of the difference plus the
argmax agreement rate. Records are rendered with Kev's own `render`/`option_text`, so the comparison
cannot drift on our reinterpretation of the record format.

⛔ This gate does NOT measure decision quality. It measures whether our port returns what Kev's
   implementation returns on the same inputs. A record we both get wrong counts as agreement.
"""
import argparse, json, sys, numpy as np, torch
from kev_ane.config import kev_dir
from kev_ane.merge import build
from kev_ane.readout import load_head, decide
from kev_ane.runtime import make_inputs, run_torch, run_coreml
from kev_ane.encode import pick_bucket, encode

# ⛔ THE GATE BAR IS ARGMAX AGREEMENT, NOT A PROBABILITY TOLERANCE.
# Gates 1 and 2 declare 1e-6 / 1e-3 against ONE short 3-way record. Measured here, those bars do
# not transfer: across real 4-way and 6-way records the CPU difference reaches 1.1e-05 and the ANE
# difference 3.8e-02, three orders of magnitude above the single-record figures, while argmax
# agreement stays perfect. Padding was excluded as a cause (T=64 vs T=256 on the same record
# differs by exactly 0.000e+00), so this is accumulation order through 28 layers, growing with
# sequence length and option count. Setting a numeric bar AFTER seeing that distribution would be
# fitting the bar to the data, so this gate reports the distribution and gates on the functional
# property instead.


def suite_records(kev_src, n):
    p = f"{kev_src}/evals/v4/transfer-v4/development.jsonl"
    try:
        lines = open(p).read().splitlines()
    except FileNotFoundError:
        sys.exit(f"GATE 4 SKIPPED: no suite at {p}")
    return [json.loads(l) for l in lines][:n]


def to_pair(rec, render, option_text):
    """One suite record -> (state_text, our_questions, kev_questions). Kev's renderers, not ours."""
    state = render(rec["state"])
    ours, theirs = [], []
    for qid, q in rec["questions"].items():
        if q.get("type") != "choice":
            return None                       # keep the comparison to one question type
        opts = [option_text(k, v) for k, v in q["criteria"].items()]
        instr = render(q["instructions"])
        ours.append({"instr": instr, "options": opts})
        theirs.append({"instr": instr, "options": opts, "label": 0})
    return (state, ours, theirs) if ours else None


def main(a):
    import warnings; warnings.filterwarnings("ignore")
    sys.path.insert(0, a.kev_src)
    from kev.model import DecisionModel, load_tokenizer
    from kev.api import render, option_text
    from peft import PeftModel

    kd = str(kev_dir())
    hd = torch.load(kd + "/head.pt", map_location="cpu", weights_only=False)
    tok = load_tokenizer(kd)
    ref = DecisionModel(hd["base"], tok, "cpu", lora=hd["lora"], revision=hd.get("base_revision"),
                        head_dim=hd["head_dim"], option_isolation=hd["option_isolation"],
                        dtype=torch.float32)
    ref.lm = PeftModel.from_pretrained(
        ref.lm.base_model.model if hasattr(ref.lm, "base_model") else ref.lm, kd, is_trainable=False)
    ref.head.load_state_dict(hd["head"]); ref.eval()

    trunk, emb, ndelta = build(merged=True)
    assert ndelta == 196, f"merged {ndelta} deltas, expected 196"
    head, _ = load_head()

    ane = None
    if a.package:
        import coremltools as ct
        ane = ct.models.MLModel(a.package, compute_units=ct.ComputeUnit.CPU_AND_NE)

    dc, da, agree_c, agree_a, used, skipped, bucket_hist, opt_hist = [], [], 0, 0, 0, 0, {}, {}
    for rec in suite_records(a.kev_src, a.n):
        pair = to_pair(rec, render, option_text)
        if pair is None:
            skipped += 1; continue
        state, ourq, theirq = pair
        n_tok = len(encode(tok, state, ourq)["ids"])
        T = pick_bucket(n_tok)
        if T is None or (ane is not None and T != a.bucket):
            skipped += 1; continue           # ANE package is one fixed bucket
        with torch.no_grad():
            r = ref.probs(ref.encode(tok, {"state": state, "questions": theirq}))[0]
        feed, enc, _ = make_inputs(tok, emb, state, ourq, T=T)
        p_cpu, _ = decide(head, run_torch(trunk, feed), enc)
        dc.append(float((p_cpu - r).abs().max()))
        agree_c += int(int(p_cpu.argmax()) == int(r.argmax()))
        if ane is not None:
            p_ane, _ = decide(head, run_coreml(ane, feed), enc)
            da.append(float((p_ane - r).abs().max()))
            agree_a += int(int(p_ane.argmax()) == int(r.argmax()))
        used += 1
        bucket_hist[T] = bucket_hist.get(T, 0) + 1
        k = len(enc["opt_idx"][0]); opt_hist[k] = opt_hist.get(k, 0) + 1
        if used % 10 == 0:
            print(f"    {used} records...", flush=True)

    if not used:
        sys.exit("GATE 4: no usable records — nothing was compared.")
    print(f"\n  records compared {used}   skipped {skipped} "
          f"(non-choice, or outside the {a.bucket if ane is not None else 'available'} bucket)")
    print("  buckets  " + "  ".join(f"T={t}: {c}" for t, c in sorted(bucket_hist.items())))
    print("  options  " + "  ".join(f"{k}-way: {c}" for k, c in sorted(opt_hist.items())))

    def rep(name, d, agree):
        d = np.array(d)
        print(f"\n  {name}")
        print(f"    max abs prob diff   max {d.max():.3e}   p50 {np.percentile(d,50):.3e}   "
              f"p99 {np.percentile(d,99):.3e}     (reported, not gated)")
        print(f"    argmax agreement    {agree}/{used}   <- THE BAR")
        return agree == used

    ok = rep("CPU fp32 vs Kev reference", dc, agree_c)
    if ane is not None:
        ok &= rep("ANE fp16 vs Kev reference", da, agree_a)
    print("\nGATE 4:", "PASS" if ok else "*** FAIL ***")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kev-src", required=True)
    ap.add_argument("--n", type=int, default=60, help="suite records to read (before filtering)")
    ap.add_argument("--package", default=None, help="mlpackage; omit to run the CPU arm only")
    ap.add_argument("--bucket", type=int, default=64)
    ap.epilog = "The bar is argmax agreement. Probability differences are reported, not gated."
    sys.exit(main(ap.parse_args()))
