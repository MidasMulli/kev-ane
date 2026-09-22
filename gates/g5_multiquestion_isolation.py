"""GATE 5 — many questions in ONE pass, and branch isolation.

WHY THIS EXISTS. Gates 1, 2 and 4 all read QUESTION 0 ONLY. Kev's entire premise is that one
document is encoded once and many typed questions are answered together, each in its own branch
under a block-causal mask. Question 0 is precisely the case that still passes when every sibling
branch is broken, so those gates were narrower than the claim they were being used to support.

TWO CHECKS, and the second is not implied by the first:

 1. MULTI-QUESTION PARITY — every question's probabilities against Kev's own reference, from a
    single packed pass.
 2. ISOLATION, packed vs separate — each question asked ALONE must give the same answer it gives
    packed. Check 1 CANNOT establish this. If our port and Kev's both let a question see a
    sibling in the same way, they agree with each other and are both wrong. Kev states the property
    as "a question cannot see a sibling question; packed and separate requests agree to 3.7e-6"
    (their max over their full suite; this gate runs one record, so it is far narrower coverage —
    the same property, not a better result).

MUTATION-TESTED, and the result is the reason this gate exists. Replacing the block-causal mask
with a plain causal one (siblings visible) gives:

    q0  CPU 3.099e-06  argmax MATCH   isolation 0.000e+00     <- UNCHANGED
    q1  CPU 2.472e-01  argmax DIFFER  isolation 2.472e-01
    q2  CPU 4.278e-01  argmax DIFFER  isolation 4.278e-01

QUESTION 0 IS BLIND TO THE BUG. It is the first branch, so under a plain causal mask it has no
preceding sibling to leak from and its numbers do not move at all. A port with a COMPLETELY BROKEN
branch mask passes gates 1, 2 and 4. That is not a hypothetical — it is measured above.

Fixture is Kev's own README example: one support ticket, three typed questions, all three shapes
(choice, noul-as-two-options, score-as-ordered-levels).
"""
import argparse, sys, torch
from kev_ane.config import kev_dir, BUCKETS
from kev_ane.merge import build
from kev_ane.readout import load_head, decide
from kev_ane.runtime import make_inputs, run_torch, run_coreml

TOL_CPU_PARITY, TOL_ANE_PARITY = 1e-4, 1e-2      # declared before the run
TOL_CPU_ISO, TOL_ANE_ISO = 1e-4, 1e-2

TICKET = ("Shoes arrived two weeks late and in the wrong size. "
          "Also I see two charges on my card.")
DEPT = {"returns": "Exchanges, refunds, wrong or damaged items",
        "shipping": "Delivery status, delays, lost packages",
        "billing": "Charges, invoices, payment problems"}
LEVELS = ["Calm", "Frustrated", "Very angry"]


def questions(option_text):
    return [{"instr": "Which team should handle this?",
             "options": [option_text(k, v) for k, v in DEPT.items()]},
            {"instr": "Does this need urgent human attention?",
             "options": [option_text("no", None), option_text("yes", None)]},
            {"instr": "How frustrated is the customer?", "options": LEVELS}]


def pkg_for(T, pattern):
    return pattern.format(T="" if T == 64 else f"_{T}")


def main(a):
    import warnings; warnings.filterwarnings("ignore")
    sys.path.insert(0, a.kev_src)
    try:
        from kev.model import DecisionModel, load_tokenizer
        from kev.api import option_text
        from peft import PeftModel
    except ImportError:
        sys.exit("GATE 5 SKIPPED: needs jaredpalmer/kev on the path (--kev-src PATH)")

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
    qs = questions(option_text)

    models = {}
    def ane(feed, T):
        if not a.package:
            return None
        import coremltools as ct
        if T not in models:
            models[T] = ct.models.MLModel(pkg_for(T, a.package),
                                          compute_units=ct.ComputeUnit.CPU_AND_NE)
        return run_coreml(models[T], feed)

    with torch.no_grad():
        R = ref.probs(ref.encode(tok, {"state": TICKET,
                                       "questions": [{**q, "label": 0} for q in qs]}))
    fp, ep, Tp = make_inputs(tok, emb, TICKET, qs)
    packed_cpu, packed_ane = run_torch(trunk, fp), ane(fp, Tp)

    print(f"CHECK 1 — {len(qs)} questions, ONE packed pass, T={Tp}, vs Kev's reference")
    pc_max = pa_max = 0.0; argmax_ok = True
    for i in range(len(qs)):
        r = R[i]
        pc = decide(head, packed_cpu, ep, q=i)[0]
        dc = float((pc - r).abs().max()); pc_max = max(pc_max, dc)
        line = f"  q{i} ({len(qs[i]['options'])} opts)  CPU {dc:.3e}"
        argmax_ok &= int(pc.argmax()) == int(r.argmax())
        if packed_ane is not None:
            pa = decide(head, packed_ane, ep, q=i)[0]
            da = float((pa - r).abs().max()); pa_max = max(pa_max, da)
            line += f"   ANE {da:.3e}"
            argmax_ok &= int(pa.argmax()) == int(r.argmax())
        print(line + f"   argmax {'MATCH' if argmax_ok else 'DIFFER'}")
    ok1 = pc_max < TOL_CPU_PARITY and argmax_ok and (
        packed_ane is None or pa_max < TOL_ANE_PARITY)
    print(f"  max CPU {pc_max:.3e} (tol {TOL_CPU_PARITY:.0e})"
          + (f"   max ANE {pa_max:.3e} (tol {TOL_ANE_PARITY:.0e})" if packed_ane is not None else "")
          + f"  -> {'PASS' if ok1 else '*** FAIL ***'}")

    print("\nCHECK 2 — isolation: each question asked ALONE must equal its packed answer")
    ic_max = ia_max = 0.0; iso_argmax = True
    for i, q in enumerate(qs):
        fs, es, Ts = make_inputs(tok, emb, TICKET, [q])
        sc = decide(head, run_torch(trunk, fs), es, q=0)[0]
        pc = decide(head, packed_cpu, ep, q=i)[0]
        dc = float((pc - sc).abs().max()); ic_max = max(ic_max, dc)
        line = f"  q{i}  separate T={Ts:3d}  CPU {dc:.3e}"
        if packed_ane is not None:
            sa = decide(head, ane(fs, Ts), es, q=0)[0]
            pa = decide(head, packed_ane, ep, q=i)[0]
            da = float((pa - sa).abs().max()); ia_max = max(ia_max, da)
            line += f"   ANE {da:.3e}"
            iso_argmax &= int(pa.argmax()) == int(sa.argmax())
        print(line)
    ok2 = ic_max < TOL_CPU_ISO and iso_argmax and (packed_ane is None or ia_max < TOL_ANE_ISO)
    print(f"  max CPU {ic_max:.3e} (tol {TOL_CPU_ISO:.0e})"
          + (f"   max ANE {ia_max:.3e} (tol {TOL_ANE_ISO:.0e})" if packed_ane is not None else "")
          + f"  -> {'PASS' if ok2 else '*** FAIL ***'}")
    if Tp != 64:
        print(f"  note: the separate runs used a smaller bucket than the packed run (T={Tp}), so a"
              f"\n        CPU agreement this tight also re-confirms that padding is inert.")

    print("\nGATE 5:", "PASS" if ok1 and ok2 else "*** FAIL ***")
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kev-src", required=True)
    ap.add_argument("--package", default="kev06b_trunk{T}.mlpackage",
                    help="naming pattern; omit to run the CPU arm only")
    ap.add_argument("--cpu-only", action="store_true")
    a = ap.parse_args()
    if a.cpu_only:
        a.package = None
    sys.exit(main(a))
