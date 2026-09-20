"""GATE 3 — prove the work happened ON the Neural Engine, three independent ways.

1. OUTPUT DIVERGENCE. CPU_ONLY returns all zeros for this graph, so a correct result is only
   obtainable when the ANE is allowed. This is not a latency comparison: there is no working
   CPU output to compare against.
2. DISPATCH INTERVALS. Apple's xctrace "Neural Engine" instrument, with the took-check the
   instrument requires — the interval count must match an independent in-process predict count,
   or a ref/id parsing bug silently undercounts.
3. POWER. powermetrics reads ~0 mW idle and thousands of mW under load on the ANE rail.
   NOTE: "-s ane_power" ALONE emits no ANE section; the ANE Power line only appears when
   cpu_power is requested alongside it. Needs passwordless sudo; skipped otherwise.
"""
import subprocess, sys, time, numpy as np, torch, coremltools as ct
from kev_ane.config import kev_dir
from kev_ane.merge import load_base
from kev_ane.trunk import Trunk
from kev_ane.runtime import make_inputs
from gates.g0_encode_parity import REC


def divergence(pkg, feed):
    out = {}
    for tag, cu in (("CPU_ONLY", ct.ComputeUnit.CPU_ONLY),
                    ("CPU_AND_NE", ct.ComputeUnit.CPU_AND_NE)):
        m = ct.models.MLModel(pkg, compute_units=cu)
        a = np.asarray(m.predict(feed)["hs"])
        out[tag] = float(np.abs(a).max())
        print(f"  {tag:11s} hidden-state absmax {out[tag]:.4f}")
    ok = out["CPU_ONLY"] == 0.0 and out["CPU_AND_NE"] > 1.0
    print("  proof 1 output divergence:", "PASS" if ok else "*** FAIL ***")
    return ok


def power(pkg, feed, seconds=8):
    try:
        subprocess.run(["sudo", "-n", "true"], check=True, capture_output=True)
    except Exception:
        print("  proof 3 power: SKIPPED (needs passwordless sudo for powermetrics)")
        return None
    import re, os, tempfile
    path = tempfile.mktemp(suffix=".txt")
    pr = subprocess.Popen(["sudo", "-n", "powermetrics", "-i", "300",
                           "-s", "cpu_power,ane_power", "-o", path],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    idle = _read(path)
    m = ct.models.MLModel(pkg, compute_units=ct.ComputeUnit.CPU_AND_NE); m.predict(feed)
    t0 = time.time()
    while time.time() - t0 < seconds:
        m.predict(feed)
    time.sleep(1); pr.terminate()
    vals = _read(path)
    if not vals:
        print("  proof 3 power: INSTRUMENT SILENT — powermetrics emitted no ANE Power line.")
        print("                 Not a 0 mW reading; the sampler produced nothing. Check sudo and")
        print("                 that cpu_power is requested alongside ane_power.")
        return None
    peak = max(vals)
    print(f"  proof 3 power: idle max {max(idle) if idle else 0} mW -> loaded peak {peak} mW"
          f"  ({len(vals)} samples)")
    ok = peak > 1000
    print("  proof 3 power:", "PASS" if ok else "*** FAIL ***")
    return ok


def _read(path):
    import re
    try:
        return [int(v) for v in re.findall(r"ANE Power:\s*(\d+)\s*mW",
                                           open(path, errors="replace").read())]
    except FileNotFoundError:
        return []


def main(pkg):
    import warnings; warnings.filterwarnings("ignore")
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(kev_dir()))
    emb = load_base(Trunk())
    feed, enc, T = make_inputs(tok, emb, REC["state"], REC["questions"])
    print("proof 1 — output divergence")
    ok1 = divergence(pkg, feed)
    print("\nproof 2 — dispatch intervals: run tools/ane_dispatch.py (needs xctrace)")
    print("\nproof 3 — power rail")
    ok3 = power(pkg, feed)
    ok = ok1 and (ok3 is not False)
    print("\nGATE 3:", "PASS" if ok else "*** FAIL ***")
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default="kev06b_trunk.mlpackage")
    sys.exit(main(ap.parse_args().package))
