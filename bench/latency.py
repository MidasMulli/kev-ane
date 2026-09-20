"""Single-decision latency, decomposed. Throughput is not latency."""
import sys, time, warnings, numpy as np, coremltools as ct
warnings.filterwarnings("ignore")
from transformers import AutoTokenizer
from kev_ane.config import kev_dir, BUCKETS
from kev_ane.merge import load_base
from kev_ane.trunk import Trunk
from kev_ane.readout import load_head, decide
from kev_ane.runtime import make_inputs, run_coreml
from gates.g0_encode_parity import REC

WARMUP, N = 10, 60
tok = AutoTokenizer.from_pretrained(str(kev_dir()))
emb = load_base(Trunk())
head, _ = load_head()
for T in BUCKETS:
    pkg = "kev06b_trunk.mlpackage" if T == 64 else f"kev06b_trunk_{T}.mlpackage"
    try:
        m = ct.models.MLModel(pkg, compute_units=ct.ComputeUnit.CPU_AND_NE)
    except Exception as e:
        print(f"T={T}: skipped ({pkg} not built)"); continue
    enc_t, ane_t, head_t, tot = [], [], [], []
    for i in range(WARMUP + N):
        t0 = time.perf_counter()
        feed, enc, _ = make_inputs(tok, emb, REC["state"], REC["questions"], T=T)
        t1 = time.perf_counter()
        hs = run_coreml(m, feed)
        t2 = time.perf_counter()
        decide(head, hs, enc)
        t3 = time.perf_counter()
        if i >= WARMUP:
            enc_t.append((t1-t0)*1e3); ane_t.append((t2-t1)*1e3)
            head_t.append((t3-t2)*1e3); tot.append((t3-t0)*1e3)
    q = lambda v, p: float(np.percentile(v, p))
    print(f"T={T}  (n={len(tot)}, {WARMUP} warmup discarded)")
    for nm, v in (("encode (python)", enc_t), ("ANE predict", ane_t),
                  ("head+softmax", head_t), ("TOTAL", tot)):
        print(f"   {nm:16s} p50 {q(v,50):6.2f} ms   p90 {q(v,90):6.2f}   p99 {q(v,99):6.2f}")
    print()
