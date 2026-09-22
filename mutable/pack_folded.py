"""pack() for FOLDED deltas. The recipe's pack routes inputs by `shape[1]==D else x[:,:R]`,
which only admits factored factors (1024 or rank-16). Folded deltas take 1024/2048/3072, so the
dummy input is sized to the widest and each conv slices its own in-channels. Offset extraction is
the recipe's, unchanged."""
import os, re, shutil, subprocess, numpy as np, torch, torch.nn as nn, warnings
warnings.filterwarnings("ignore")
import coremltools as ct

def pack_folded(fs, tag, out, T):
    WIN = max(f.shape[1] for f in fs)
    class P(nn.Module):
        def __init__(s):
            super().__init__()
            s.c = nn.ModuleList([nn.Conv2d(f.shape[1], f.shape[0], 1, bias=False) for f in fs])
            s.w = [int(f.shape[1]) for f in fs]      # PYTHON ints, frozen at build time:
        def forward(s, x):                            # reading .weight.shape inside forward makes
            acc = 0.0                                 # the trace emit an int cast coremltools
            for i, cc in enumerate(s.c):              # cannot convert
                acc = acc + cc(x[:, :s.w[i]]).sum()
            return acc
    P_ = P().eval()
    with torch.no_grad():
        for i, f in enumerate(fs): P_.c[i].weight.copy_(f[:, :, None, None])
    ml = ct.convert(torch.jit.trace(P_, torch.rand(1, WIN, 1, T)),
                    inputs=[ct.TensorType(name="x", shape=(1, WIN, 1, T), dtype=np.float16)],
                    convert_to="mlprogram", compute_precision=ct.precision.FLOAT16,
                    minimum_deployment_target=ct.target.macOS15)
    pk = os.path.join(out, f"_pkf_{tag}.mlpackage"); shutil.rmtree(pk, ignore_errors=True); ml.save(pk)
    o = os.path.join(out, f"_pkf_{tag}"); shutil.rmtree(o, ignore_errors=True)
    subprocess.run(f"xcrun coremlcompiler compile '{pk}' '{o}'", shell=True, capture_output=True)
    mdir = subprocess.run(f"ls -d '{o}'/*.mlmodelc", shell=True, capture_output=True, text=True).stdout.strip()
    mil = open(os.path.join(mdir, "model.mil")).read(); offs = {}
    for cn in re.findall(r'c_\d+_weight_to_fp16', mil):
        i = mil.find(cn + " = const"); e = mil.find(";", i)
        offs[int(re.search(r'c_(\d+)_', cn).group(1))] = int(re.search(r'weight\.bin"\), offset = uint64\((\d+)\)', mil[i:e]).group(1))
    assert len(offs) == len(fs), f"{len(offs)} consts for {len(fs)} factors"
    return open(os.path.join(mdir, "weights", "weight.bin"), "rb").read(), [offs[i] for i in range(len(fs))]
