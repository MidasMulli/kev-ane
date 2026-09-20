"""Fixed-count decision workload. Prints its OWN predict count for the took-check."""
import os, sys, time, numpy as np, coremltools as ct, warnings
warnings.filterwarnings("ignore")
from transformers import AutoTokenizer
from kev_ane.config import kev_dir
from kev_ane.merge import load_base
from kev_ane.trunk import Trunk
from kev_ane.runtime import make_inputs
from gates.g0_encode_parity import REC

n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
pkg = sys.argv[2] if len(sys.argv) > 2 else "kev06b_trunk.mlpackage"
tok = AutoTokenizer.from_pretrained(str(kev_dir()))
feed, enc, T = make_inputs(tok, load_base(Trunk()), REC["state"], REC["questions"])
m = ct.models.MLModel(pkg, compute_units=ct.ComputeUnit.CPU_AND_NE)
out = m.predict(feed)                       # warm-up; counts as one in-process predict
t0 = time.perf_counter()
for _ in range(n):
    out = m.predict(feed)
el = max(time.perf_counter() - t0, 1e-9)
open(os.environ.get("KEV_ANE_COUNT_FILE", "predicts.txt"), "w").write(str(n + 1))
print(f"WORKLOAD predicts={n + 1} loop={n} elapsed={el:.3f}s rate={n/el:.1f}/s "
      f"absmax={np.abs(np.asarray(out['hs'])).max():.4g}")
