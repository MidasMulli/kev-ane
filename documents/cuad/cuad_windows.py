"""Program A: the ONE window builder shared by A1 (train), A2 (parity) and A3 (final). T=256, stride 224, char ranges at original offsets.
Label[k] = a gold span of type_order[k] overlaps the window's char range (the location-based hit definition, frozen)."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import numpy as np
T, STRIDE = 256, 224
def overlaps(spans, a, b): return any(st < b and st + len(tx) > a for st, tx in spans)
def windows(c, tok, TO):
    enc = tok(c["context"], return_offsets_mapping=True, add_special_tokens=False); ids, offs = enc["input_ids"], enc["offset_mapping"]
    out = []
    for s in range(0, max(1, len(ids) - (T - STRIDE)), STRIDE):
        w = ids[s:s + T]; a, b = offs[s][0], offs[s + len(w) - 1][1]
        out.append(dict(ids=w, a=a, b=b, y=np.array([1.0 if overlaps(c["spans"][t], a, b) else 0.0 for t in TO], np.float32)))
        if s + T >= len(ids): break
    return out
