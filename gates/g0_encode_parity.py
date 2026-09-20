"""GATE 0 — our reimplemented encoder must agree with Kev's own, token for token.

Everything downstream is meaningless if the encoding differs, so this runs first. It needs
Kev's source (a dev-only dependency): pip install 'kev-ane[parity]' or clone jaredpalmer/kev.
"""
import sys, torch
from kev_ane.config import kev_dir
from kev_ane.encode import encode, branch_mask

REC = dict(
    state="pytest cannot collect tests: ModuleNotFoundError: No module named yaml",
    questions=[{"instr": "Which investigation best fits this failure?",
                "options": ["Inspect missing dependencies and the Python environment.",
                            "Inspect an assertion that compared the wrong values.",
                            "Inspect a remote request that timed out."]}])


def main(kev_src=None):
    if kev_src:
        sys.path.insert(0, kev_src)
    try:
        from kev.model import encode as kev_encode, branch_mask_batch, load_tokenizer
    except ImportError:
        sys.exit("GATE 0 SKIPPED: needs jaredpalmer/kev on the path (--kev-src PATH)")
    tok = load_tokenizer(str(kev_dir()))
    theirs = kev_encode(tok, {"state": REC["state"],
                              "questions": [{**q, "label": 0} for q in REC["questions"]]},
                        option_isolation=False)
    ours = encode(tok, REC["state"], REC["questions"])
    ok = True
    for k in ("ids", "seg", "pos", "opt", "decide_idx", "opt_idx"):
        same = theirs[k] == ours[k]
        ok &= same
        print(f"  {k:12s} {'MATCH' if same else 'DIFFER'}")
    T = 64
    mt = branch_mask_batch([theirs["seg"]], torch.device("cpu"),
                           dtype=torch.float32, length=T).clamp(min=-1e4)
    mo = branch_mask(ours["seg"], T)
    md = float((mt - mo).abs().max())
    print(f"  {'branch_mask':12s} max abs diff {md:.3e}")
    ok &= md == 0.0
    print("\nGATE 0:", "PASS" if ok else "*** FAIL ***")
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--kev-src")
    sys.exit(main(ap.parse_args().kev_src))
