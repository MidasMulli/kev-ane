"""GATE 2 — the converted model on the Neural Engine vs the same reference.

fp16 on the engine, so the bar is looser than GATE 1 and declared before the run.
Expected on the reference record: ~9.3e-05.
"""
import sys, torch, coremltools as ct
from kev_ane.config import kev_dir
from kev_ane.readout import load_head, decide
from kev_ane.runtime import make_inputs, run_coreml
from kev_ane.merge import load_base
from kev_ane.trunk import Trunk
from gates.g0_encode_parity import REC

TOL = 1e-3          # declared BEFORE the run; fp16 rounding, not a fitted number


def main(pkg, kev_src):
    import warnings; warnings.filterwarnings("ignore")
    from gates.g1_numeric_cpu import reference
    ref, tok = reference(kev_src)
    emb = load_base(Trunk())                      # embeddings only; trunk unused here
    head, _ = load_head()
    feed, enc, T = make_inputs(tok, emb, REC["state"], REC["questions"])
    m = ct.models.MLModel(pkg, compute_units=ct.ComputeUnit.CPU_AND_NE)
    p, _ = decide(head, run_coreml(m, feed), enc)
    d = float((p - ref).abs().max())
    print("  reference:", [round(float(v), 6) for v in ref])
    print("  on ANE   :", [round(float(v), 6) for v in p])
    print(f"  max abs prob diff {d:.3e}   tolerance {TOL:.0e}   bucket T={T}")
    print("  argmax   : ours %d, ref %d" % (int(p.argmax()), int(ref.argmax())))
    ok = d < TOL and int(p.argmax()) == int(ref.argmax())
    print("\nGATE 2:", "PASS" if ok else "*** FAIL ***")
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default="kev06b_trunk.mlpackage")
    ap.add_argument("--kev-src", required=True)
    a = ap.parse_args()
    sys.exit(main(a.package, a.kev_src))
