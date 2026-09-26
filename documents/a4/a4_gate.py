"""A4 anchor gate v4 (final) (Astra ruling): NEW 30 anchored results (seed 20260940) under rule v3. Each packet shows the caption, the value's COLUMN
header (+ section-label rows) and the row (or the sentence). Judges answer TWO things per item: IDENTITY (the value is that model's, on that
dataset) and METRIC (the metric named is what the paper reports in that cell). Accept iff >= 27/30 on BOTH."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, random, os
from a4_common import units2, cells, column_header, vre, vnorm
C = json.load(open("a4_corpus.json")); os.makedirs("gate_v4", exist_ok=True)
allr = [(i, k) for i, c in enumerate(C) for k in range(len(c["results"]))]
pick = random.Random(20260940).sample(allr, 30); out = []
for n, (i, k) in enumerate(pick):
    c = C[i]; r = c["results"][k]; a, b = r["span"]; row = c["text"][a:b]
    if r["kind"] == "row":
        st = next(x for x in units2(c["text"]) if x[0] == a and x[1] == b)[3]; rx = vre(vnorm(r["value"]))
        slot = next(s0 for s0, s1, t in cells(row) if rx.search(t))
        shown = "CAPTION: " + st["cap"][:900] + "\nCOLUMN HEADER OF THE VALUE'S COLUMN (+ section labels): " + column_header(st["body"], st["rows"], st["hdr_end"], st["i"], slot) + \
                "\nTABLE HEADER ROWS: " + " \\\\ ".join(st["body"][x:y] for x, y in st["rows"][:(st["hdr_end"] + 1 if st["hdr_end"] is not None else 1)])[:1200] + "\nTHE ROW: " + row
    else: shown = "SENTENCE: " + row
    out.append(dict(item=n, arxiv=c["arxiv"], kind=r["kind"], model=r["model"], dataset=r["dataset"], metric=r["metric"], value=r["value"], shown=shown))
json.dump(out, open("gate_v4/a4_gate_items.json", "w"), indent=1)
for part in range(3):
    with open(f"gate_v4/packet_{part}.md", "w") as f:
        f.write("For each item: LaTeX from a research paper: the table caption, the header of the column the value sits in, the table header rows, and ONE row (or one sentence).\n"
                "Answer TWO questions per item, strictly:\n(1) IDENTITY: is the given VALUE this MODEL's result on this DATASET (right row, right column)?\n"
                "(2) METRIC: is the given METRIC what the paper reports in that cell (allow trivial formatting variants such as 'Top-1' vs 'Top1', but not a different measure, variant or normalization)?\n"
                "Allow obvious naming variants for the model (a macro or abbreviation). Answer per item: `item N: identity yes|no, metric yes|no | deciding quote (<=20 words)`.\n\n")
        for x in out[part * 10:(part + 1) * 10]:
            f.write(f"## item {x['item']}\nMODEL: {x['model']}\nDATASET: {x['dataset']}\nMETRIC: {x['metric']}\nVALUE: {x['value']}\nEXCERPT:\n```\n{x['shown']}\n```\n\n")
print("gate v4 packets written", len(out))
