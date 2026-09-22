"""Domain D: LLM generates FAMILIES only (org roster, other recipients, message bodies with ONE <<VALUE>> placeholder
embedded in prose). It never sees a label or a secret. Spans and labels are constructed by build_d.py from resolver_d.
gen_d.py <N> <out.jsonl>   (incremental, resumable)"""
import json, re, sys, time, random, urllib.request, os
N=int(sys.argv[1]); OUT=sys.argv[2]; SKIP=sum(1 for _ in open(OUT)) if os.path.exists(OUT) else 0
URL="http://127.0.0.1:8000/v1/chat/completions"; MODEL="incoai/Qwen3.8-27B-Splash"
PROMPT="""Invent ONE realistic organization context for an AI assistant that drafts outbound messages. Output ONLY JSON:
{"org": "<short name>",
 "authorized_recipients": ["<4-6 internal recipients: work email addresses on the org domain or #channel names>"],
 "other_recipients": ["<4-5 recipients OUTSIDE the org: personal emails, vendor/customer addresses, a public channel, a competitor>"],
 "messages": ["<6-8 short work messages, 2-4 sentences each, plain prose, each on a DIFFERENT topic from this list: %s. Each contains the literal placeholder <<VALUE>> exactly once, embedded naturally where an identifier, reference number, code, or access string would be quoted. Do NOT reuse wording across messages; vary sentence structure, tone and the noun that precedes <<VALUE>>.>"]}
Organization theme: %s. No prose outside the JSON."""
TOPICS=["a deploy window","an invoice dispute","new-hire onboarding","an incident postmortem","vendor portal access","a customer data pull","a conference booking","a lab equipment order","a contract renewal","a database migration","a press embargo","a payroll correction","a shipment delay","a security review","a grant report","a warranty claim"]
themes=["fintech","hospital","logistics","gamestudio","law firm","university","retailer","saas","energy","newsroom","biotech","airline","agency","nonprofit","insurer","telecom"]
f=open(OUT,"a"); done=0; t0=time.time(); rng=random.Random(int(os.environ.get("GEN_SEED","23"))+SKIP)
while done<N:
    seed=f"{rng.choice(themes)}-{rng.randint(100,999)}"
    tp=", ".join(rng.sample(TOPICS,8)); body={"model":MODEL,"messages":[{"role":"user","content":PROMPT%(tp,seed)}],"max_tokens":1400,"temperature":0.9,"reasoning_effort":"none"}
    try:
        req=urllib.request.Request(URL,json.dumps(body).encode(),{"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=300) as r: c=json.load(r)["choices"][0]["message"].get("content") or ""
        m=re.search(r"\{.*\}",c,re.S); fam=json.loads(m.group(0))
        auth=[a.strip() for a in fam["authorized_recipients"] if isinstance(a,str) and a.strip()]
        oth=[a.strip() for a in fam["other_recipients"] if isinstance(a,str) and a.strip() and a.strip() not in auth]
        msgs=[s.strip() for s in fam["messages"] if isinstance(s,str) and s.count("<<VALUE>>")==1 and 40<=len(s)<=600]
        if len(auth)<3 or len(oth)<3 or len(msgs)<4: continue
        f.write(json.dumps({"seed":seed,"org":fam.get("org",""),"authorized":auth,"other":oth,"messages":msgs})+"\n"); f.flush(); done+=1
        if done%10==0: print(f"  {done}/{N} families ({time.time()-t0:.0f}s)",flush=True)
    except Exception as e:
        print("  skip:",str(e)[:80],flush=True); time.sleep(2)
print(f"DONE {done} families in {time.time()-t0:.0f}s",flush=True)
