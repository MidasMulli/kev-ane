"""I3 fresh ISDA pull from SEC EDGAR (operator-authorized contact UA). Full-text search hits for Schedule/ISDA Master phrases -> fetch the
matched file from the Archives -> HTML to text -> FROZEN I2 classifier -> drop anything matching the 241 corpus (exact or 6-gram Jaccard
> 0.3) and within-pull duplicates. Rate-limited to ~3 requests/s. Writes edgar_pool.json."""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from _kevdoc import *  # repo paths + endpoints
import json, re, time, html, urllib.request, urllib.parse, hashlib, sys
assert SEC_USER_AGENT, "set SEC_USER_AGENT='name email' (SEC fair-access policy)"
UA = {"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "identity"}
def get(url):
    time.sleep(0.34); return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
def to_text(raw):
    t = raw.decode("utf-8", "replace")
    if "<html" in t[:2000].lower() or "<body" in t.lower()[:5000]:
        t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t); t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", t); t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t); t = re.sub(r"[ \t\xa0]+", " ", t); return re.sub(r"\n\s*\n+", "\n\n", t).strip()
def classify(text):
    head = text[:3000]
    if "Master Agreement" not in head and "MASTER AGREEMENT" not in head: return None
    low = text.lower()
    if re.search(r"schedule\s+to\s+the", head, re.I) and "part 1" in low and "termination provisions" in low: return "schedule"
    if "isda" in head.lower() and "interpretation" in low and "obligations" in low and "events of default and termination events" in low:
        return "master" if ("part 1" in low and "termination provisions" in low) else None   # I2 corpus rule: must contain Schedule content
    return None
def sh(t):
    w = re.findall(r"[a-z0-9]+", t.lower())[:1500]; return {" ".join(w[i:i + 6]) for i in range(len(w) - 5)}
C = json.load(open("../isda2/isda2_corpus241.json")); CS = [sh(c["text"]) for c in C]
out, seen, stats = [], set(), dict(hits=0, fetched=0, classified=0, dup_corpus=0, dup_pull=0, errors=0)
queries = ['"Schedule to the ISDA Master Agreement"', '"Schedule to the Master Agreement" "Termination Provisions"']
for q in queries:
    for frm in range(0, 1000, 100):
        try: d = json.loads(get("https://efts.sec.gov/LATEST/search-index?" + urllib.parse.urlencode({"q": q, "from": frm})))
        except Exception as e: stats["errors"] += 1; continue
        hits = d["hits"]["hits"]
        if not hits: break
        for h in hits:
            stats["hits"] += 1; adsh, fn = h["_id"].split(":"); cik = (h["_source"].get("ciks") or [""])[0].lstrip("0")
            key = adsh + fn
            if key in seen: continue
            seen.add(key)
            try: raw = get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh.replace('-', '')}/{fn}"); stats["fetched"] += 1
            except Exception: stats["errors"] += 1; continue
            t = to_text(raw); k = classify(t)
            if not k: continue
            stats["classified"] += 1; s = sh(t)
            if any(len(s & c) / max(1, len(s | c)) > 0.3 for c in CS): stats["dup_corpus"] += 1; continue
            if any(len(s & o["_sh"]) / max(1, len(s | o["_sh"])) > 0.3 for o in out): stats["dup_pull"] += 1; continue
            out.append(dict(sha=hashlib.sha256(t.encode()).hexdigest()[:16], kind=k, chars=len(t), adsh=adsh, file=fn, cik=cik, date=h["_source"].get("file_date"), text=t, _sh=s))
            if len(out) % 10 == 0: print(json.dumps(stats), len(out), flush=True)
        if len(out) >= 200: break
    if len(out) >= 200: break
json.dump([{k: v for k, v in o.items() if k != "_sh"} for o in out], open("edgar_pool.json", "w"))
print("DONE", json.dumps(stats), "kept", len(out), flush=True)
