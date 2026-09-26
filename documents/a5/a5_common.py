"""A5 (Astra-signed): arXiv PAPER PROFILE. 12 fixed questions, FROZEN LaTeX anchors (no answer-string search), I3-form keyword sidecar,
prompt/parse/norm. Evidence spans are char offsets in the paper text (comment-stripped paper_text)."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import re
Q = [("Method name", "What is the name of the method or model this paper proposes? Answer with the name only."),
     ("Task", "What task or problem does the paper address? Answer with a short phrase."),
     ("Headline result", "What headline quantitative result does the abstract state? Give the number and what it measures."),
     ("Datasets", "Which datasets are used to evaluate the method? List up to 3."),
     ("Main metric", "Which evaluation metric is reported for the main results? Answer with the metric name."),
     ("Baselines", "Which baselines is the method compared against? List up to 3."),
     ("Code", "Is code released? Give the URL."),
     ("Hardware", "What hardware was used to train or run the experiments? Give the device type and count if stated."),
     ("Parameters", "How many parameters does the proposed model have? Answer with the number."),
     ("Training time", "How long does training take? Answer with the stated duration."),
     ("Optimizer", "Which optimizer is used for training? Answer with the optimizer name."),
     ("Limitations", "Does the paper discuss its limitations? Answer yes or no, and name one limitation if yes.")]
NAMES = [q[0] for q in Q]
SEC = re.compile(r"\\section\*?\{([^}]*)\}")
def sections(text):
    hs = [(m.start(), m.group(1)) for m in SEC.finditer(text)]; out = []
    for k, (s, t) in enumerate(hs): out.append((s, hs[k + 1][0] if k + 1 < len(hs) else len(text), t))
    return out
def sentences(text, a, b):
    seg = text[a:b]; q = 0
    for m in re.finditer(r"(?<=[.!?])\s+|\n\s*\n", seg):
        yield a + q, a + m.start(); q = m.end()
    yield a + q, b
def first_sentence(text, a, b, rx):
    for s, e in sentences(text, a, b):
        if re.search(rx, text[s:e], re.I | re.S): return (s, min(e, s + 900))
    return None
EXCL_SEC = r"related|background|prior work|previous work|literature|reference|bibliograph|acknowledg"
def body_spans(text):
    """Paper body: from the end of the abstract (else \\begin{document}) to the bibliography, minus related-work/background/acknowledgement
    sections. Frozen (anchor v2, after label spot check v1 FAILED 9/20)."""
    m = re.search(r"\\end\{abstract\}", text) or re.search(r"\\begin\{document\}", text); s0 = m.end() if m else 0
    b = re.search(r"\\begin\{thebibliography\}|\\bibliography\{|\\printbibliography", text[s0:]); s1 = s0 + b.start() if b else len(text)
    spans = []; cur = s0
    for s, e, t in sections(text):
        if e <= s0 or s >= s1: continue
        if re.search(EXCL_SEC, t, re.I):
            if s > cur: spans.append((cur, min(s, s1)))
            cur = max(cur, min(e, s1))
    if cur < s1: spans.append((cur, s1))
    return spans
def first_in(text, spans, rx):
    for a, b in spans:
        r = first_sentence(text, a, b, rx)
        if r: return r
    return None
def evidence(text):
    ev = {n: None for n in NAMES}
    m = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.S)
    ab = (m.start(1), m.end(1)) if (m and len(re.sub(r"\\input\{[^}]*\}", "", m.group(1)).strip()) > 200) else None
    body = body_spans(text)
    if ab:
        ev["Task"] = ab
        ev["Headline result"] = first_sentence(text, ab[0], ab[1], r"\d(\.\d+)?\s*(\\?%|x\b|times)|(improv|outperform|achiev|reduc|surpass)\w*[^.]{0,80}\d")
        ev["Method name"] = first_sentence(text, ab[0], ab[1], r"\b(we|this paper)\s+(propose|present|introduce|develop)\w*\s+(\\\w+\{)?[A-Z][A-Za-z0-9]*[A-Z0-9][A-Za-z0-9-]*|\b(called|named|dubbed|termed)\s+(\\\w+\{)?[A-Z]")
    if ev["Method name"] is None: ev["Method name"] = first_in(text, body[:1], r"\b(we|this paper)\s+(propose|present|introduce|develop)\w*[^.]{0,120}\b(called|named|dubbed|termed)\b")
    exp = [(s, e) for s, e, t in sections(text) if re.search(r"experiment|evaluation|results", t, re.I) and any(a <= s < b for a, b in body)]
    for s, e in exp:
        if ev["Datasets"] is None:
            for s_, e_ in sentences(text, s, e):
                u = text[s_:e_]
                if re.search(r"pre-?train", u, re.I): continue
                if re.search(r"(evaluat|experiment|test|conduct|report|benchmark)\w*[^.]{0,120}\b(on|using|with)\b[^.]{0,160}\\cite", u, re.I | re.S): ev["Datasets"] = (s_, min(e_, s_ + 900)); break
        if ev["Baselines"] is None:
            for s_, e_ in sentences(text, s, e):
                u = text[s_:e_]
                if re.search(r"baselines?|compare\w*\s+(with|to|against)", u, re.I) and len(re.findall(r"\\cite\w*\{([^}]*)\}", u)) + sum(x.count(",") for x in re.findall(r"\\cite\w*\{([^}]*)\}", u)) >= 2:
                    ev["Baselines"] = (s_, min(e_, s_ + 900)); break
        if ev["Main metric"] is None: ev["Main metric"] = first_sentence(text, s, e, r"(evaluat|report|measur|metric)\w*[^.]{0,120}(accuracy|\\bF1\\b|BLEU|ROUGE|mAP|\\bAP\\b|IoU|PSNR|SSIM|error|FID|top-?1|recall|precision|perplexity|AUC|MAE|RMSE|NDCG|\\bEM\\b)|(accuracy|\\bF1\\b|BLEU|ROUGE|mAP|\\bAP\\b|IoU|PSNR|SSIM|error|FID|top-?1|recall|precision|perplexity|AUC|MAE|RMSE|NDCG|\\bEM\\b)[^.]{0,80}(as|is) (the |our )?(evaluation |main |primary )?metric")
    bib = re.search(r"\\begin\{thebibliography\}|\\bibliography\{|\\printbibliography", text)
    ev["Code"] = first_sentence(text, 0, bib.start() if bib else len(text), r"\\(url|href)\{[^}]*(github|gitlab|huggingface|project)")   # title footnote / abstract allowed
    ev["Hardware"] = first_in(text, body, r"(train|experiment|conduct|run|use|implement|perform)\w*[^.]{0,150}\b(GPU|TPU|A100|V100|H100|RTX|NVIDIA)|\b(GPU|TPU|A100|V100|H100|RTX|NVIDIA)\w*[^.]{0,150}(train|experiment|conduct|run|use|implement|perform)")
    ev["Parameters"] = first_in(text, body, r"\d+(\.\d+)?\s*(M|B|million|billion)\s*(trainable\s+)?param(eter)?s")
    ev["Training time"] = first_in(text, body, r"train\w*.{0,80}?\d+(\.\d+)?\s*(hours|days|GPU[- ]hours)|\d+(\.\d+)?\s*(hours|days|GPU[- ]hours).{0,80}?train")
    ev["Optimizer"] = first_in(text, body, r"\b(Adam|AdamW|SGD|LAMB|Adafactor|optimizer)\b")
    h = None
    for a, b in body:
        h = re.search(r"\\(sub)*section\*?\{[^}]*limitation", text[a:b], re.I)
        if h: h = (a + h.start(), min(len(text), a + h.start() + 900)); break
    ev["Limitations"] = h or first_in(text, body, r"\b(a|one|the main|main|key) limitations? of (our|this|the proposed)|\bour (method|approach|model|work|framework) (has|have) (some |several )?limitations?|limitations? of our (method|approach|model|work)")
    return ev
SIDE = {"Code": r"\\(url|href)\{|github", "Hardware": r"\b(GPU|TPU|A100|V100|H100|RTX|NVIDIA)", "Parameters": r"param(eter)?s\b"}
def sidecar(text, windows):
    """Up to 2 windows per field (Code, Hardware, Parameters) containing its keyword, first occurrences in document order. Fixed before data."""
    out = set()
    for name, rx in SIDE.items():
        out |= set([i for i, w in enumerate(windows) if re.search(rx, text[w["a"]:w["b"]], re.I)][:2])
    return out
def prompt(context=None, evidence_texts=None, nonce=""):
    body = f"Paper (LaTeX source):\n{context}\n\n" if context is not None else "Excerpts from a paper's LaTeX source:\n" + "\n...\n".join(evidence_texts) + "\n\n"
    q = "\n".join(f"Q{i + 1}: {qq}" for i, (_, qq) in enumerate(Q))
    return f"{nonce}\n{body}Questions:\n{q}\n\nAnswer each question on its own line as 'Q<n>: <answer>', nothing else. If the paper does not state it, answer 'Q<n>: NONE'."
def parse(text):
    out = {}
    for line in text.splitlines():
        m = re.match(r"\s*\**Q(\d+)\**\s*[:.)-]\s*(.*)", line)
        if m and 1 <= int(m.group(1)) <= len(Q) and int(m.group(1)) not in out: out[int(m.group(1))] = m.group(2).strip().strip("*").strip()
    return [None if (out.get(i + 1) or "").upper().startswith("NONE") else out.get(i + 1) for i in range(len(Q))]
def norm(name, a):
    """Only for PIPE-vs-FULL agreement; every disagreement goes to blind adjudication."""
    if not a: return None
    s = re.sub(r"[\s`'\"*.,;:()\[\]{}\\-]+", " ", a.lower()).strip()
    if name == "Limitations": return "yes" if s.startswith("yes") else ("no" if s.startswith("no") else s)
    if name in ("Datasets", "Baselines"): return tuple(sorted(set(x.strip() for x in re.split(r"\s+and\s+|,|;", a.lower()) if x.strip())))
    return s
