"""GATE 1 — merged conv-form on CPU fp32 vs Kev's own PyTorch reference.

Expected on the reference record: max absolute probability difference ~1.6e-08.
"""
import sys, torch
from kev_ane.config import kev_dir
from kev_ane.merge import build
from kev_ane.readout import load_head, decide
from kev_ane.runtime import make_inputs, run_torch
from gates.g0_encode_parity import REC

TOL = 1e-6          # declared BEFORE the run; fp32-vs-fp32 should be ~1e-8


def reference(kev_src):
    sys.path.insert(0, kev_src)
    from kev.model import DecisionModel, load_tokenizer
    from peft import PeftModel
    kd = str(kev_dir())
    hd = torch.load(kd + "/head.pt", map_location="cpu", weights_only=False)
    tok = load_tokenizer(kd)
    m = DecisionModel(hd["base"], tok, "cpu", lora=hd["lora"], revision=hd.get("base_revision"),
                      head_dim=hd["head_dim"], option_isolation=hd["option_isolation"],
                      dtype=torch.float32)
    m.lm = PeftModel.from_pretrained(
        m.lm.base_model.model if hasattr(m.lm, "base_model") else m.lm, kd, is_trainable=False)
    m.head.load_state_dict(hd["head"]); m.eval()
    enc = m.encode(tok, {"state": REC["state"],
                         "questions": [{**q, "label": 0} for q in REC["questions"]]})
    with torch.no_grad():
        return m.probs(enc)[0], tok


def main(kev_src):
    import warnings; warnings.filterwarnings("ignore")
    ref, tok = reference(kev_src)
    trunk, emb, n = build(merged=True)
    assert n == 196, f"merged {n} deltas, expected 196"
    head, _ = load_head()
    feed, enc, T = make_inputs(tok, emb, REC["state"], REC["questions"])
    p, _ = decide(head, run_torch(trunk, feed), enc)
    d = float((p - ref).abs().max())
    print("  reference:", [round(float(v), 6) for v in ref])
    print("  ours     :", [round(float(v), 6) for v in p])
    print(f"  max abs prob diff {d:.3e}   tolerance {TOL:.0e}")
    print("  argmax   : ours %d, ref %d" % (int(p.argmax()), int(ref.argmax())))
    ok = d < TOL and int(p.argmax()) == int(ref.argmax())
    print("\nGATE 1:", "PASS" if ok else "*** FAIL ***")
    return 0 if ok else 1


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--kev-src", required=True)
    sys.exit(main(ap.parse_args().kev_src))
