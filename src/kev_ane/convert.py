"""Trace the merged trunk and convert to a fixed-shape CoreML mlprogram, fp16.

Shape is fixed per bucket because the Neural Engine prefers static shapes. Kev solves the same
problem on MPS with KEV_SHAPE_BUCKET; this is the CoreML equivalent.
"""
import torch, coremltools as ct
from .config import D, HD, BUCKETS
from .merge import build


def convert(T: int, out_path: str):
    trunk, _, n = build(merged=True)
    if n != 196:
        raise RuntimeError(f"merged {n} deltas, expected 196 (28 layers x 7 projections)")
    ex = (torch.zeros(1, D, 1, T), torch.zeros(1, 1, HD, T),
          torch.zeros(1, 1, HD, T), torch.zeros(1, 1, T, T))
    with torch.no_grad():
        ts = torch.jit.trace(trunk, ex)
    m = ct.convert(
        ts,
        inputs=[ct.TensorType(name=n_, shape=t.shape) for n_, t in
                zip(("x", "cos", "sin", "neg"), ex)],
        outputs=[ct.TensorType(name="hs")],
        convert_to="mlprogram",
        compute_precision=ct.precision.FLOAT16,
        minimum_deployment_target=ct.target.macOS15,
    )
    m.save(out_path)
    return out_path


def main():
    import argparse
    ap = argparse.ArgumentParser(description="convert the merged Kev trunk to CoreML")
    ap.add_argument("--buckets", type=int, nargs="+", default=list(BUCKETS))
    ap.add_argument("--out", default="kev06b_trunk{T}.mlpackage")
    a = ap.parse_args()
    for T in a.buckets:
        p = a.out.format(T="" if T == 64 else f"_{T}")
        print("converting T=%d -> %s" % (T, p), flush=True)
        convert(T, p)


if __name__ == "__main__":
    main()
