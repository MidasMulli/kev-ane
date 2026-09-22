"""PREREG one_base_two_domains (f23be94a) §4/§5 G0: ONE kev-form base (x,cos,sin,neg as graph INPUTS,
block-causal mask supplied per request) with 224 mutable q,k,v,o LoRA factors. Adapters are repacked
into adapter_<tag>.bin against the SAME compiled base; the base never rebuilds per adapter.
  deploy_inputs.py g0 <out_dir> <T>                          # build gate: random BLOBFILE-sized factors
  deploy_inputs.py pack <out_dir> <T> <tag> <kev_run_dir>    # pack a trained adapter (+ its head) for that base
Derived from work/wscope/deploy_attn.py (baked schema) + kev-ane convert.py (input list).
"""
import json, os, re, shutil, subprocess, sys, numpy as np, torch, torch.nn as nn, warnings
warnings.filterwarnings("ignore"); import coremltools as ct
for p in ("/tmp/amadapters/qwen","/Users/midas/Desktop/cowork/jev/work/kev_mutable"): sys.path.insert(0,p)
os.environ.setdefault("QWEN_MODEL_ID","Qwen/Qwen3-0.6B-Base")
from qwen_ane import Qwen, load as rload, D, NL, NH, NKV, HD
from safetensors.torch import load_file
from pack_folded import pack_folded
MODE,OUT,T=sys.argv[1],sys.argv[2],int(sys.argv[3]); os.makedirs(OUT,exist_ok=True); R=16
PROJ={"q":("self_attn.q_proj",NH*HD),"k":("self_attn.k_proj",NKV*HD),"v":("self_attn.v_proj",NKV*HD),"o":("self_attn.o_proj",D)}
ORDER=[(a,f,L) for L in range(NL) for a in PROJ for f in ("A","B")]
MD=f"{OUT}/kev_inputs.mlmodelc"

def factors_from_run(run):
    lora=load_file(f"{run}/adapter_model.safetensors"); cfg=json.load(open(f"{run}/adapter_config.json")); SC=cfg["lora_alpha"]/cfg["r"]
    assert cfg["r"]==R, cfg
    FA={a:[] for a in PROJ}; FB={a:[] for a in PROJ}
    for L in range(NL):
        for a,(hf,_) in PROJ.items():
            A=lora.get(f"base_model.model.layers.{L}.{hf}.lora_A.weight"); B=lora.get(f"base_model.model.layers.{L}.{hf}.lora_B.weight")
            assert A is not None, f"missing {hf} layer {L}: trained with --lora_targets attn?"
            FA[a].append(SC*A.float()); FB[a].append(B.float())
    return FA,FB
def random_factors():
    g=torch.Generator().manual_seed(0); FA={a:[] for a in PROJ}; FB={a:[] for a in PROJ}
    for L in range(NL):
        for a,(_,out) in PROJ.items():
            FA[a].append(torch.randn(R, D if a!="o" else NH*HD, generator=g)*1e-4); FB[a].append(torch.randn(out,R,generator=g)*1e-4)
    return FA,FB
def flat(FA,FB): return [(FA if f=="A" else FB)[a][L] for a,f,L in ORDER]

class KevIn(nn.Module):
    def __init__(s):
        super().__init__(); s.base=Qwen()
        for a,(_,out) in PROJ.items():
            setattr(s,f"{a}A",nn.ModuleList([nn.Conv2d(D if a!="o" else NH*HD,R,1,bias=False) for _ in range(NL)]))
            setattr(s,f"{a}B",nn.ModuleList([nn.Conv2d(R,out,1,bias=False) for _ in range(NL)]))
    def d(s,a,L,h): return getattr(s,f"{a}B")[L](getattr(s,f"{a}A")[L](h))
    def forward(s,x,cos,sin,neg):
        for L,b in enumerate(s.base.blocks):
            r=x; h=b.n1(x)
            q=(b.q(h)+s.d("q",L,h)).view(1,NH,HD,T); k=(b.k(h)+s.d("k",L,h)).view(1,NKV,HD,T); v=(b.v(h)+s.d("v",L,h)).view(1,NKV,HD,T)
            q=b.rmsh(q,b.qn); k=b.rmsh(k,b.kn)
            def roth(z): z1,z2=z[:,:,:HD//2],z[:,:,HD//2:]; return torch.cat([-z2,z1],2)
            q=q*cos+roth(q)*sin; k=k*cos+roth(k)*sin
            k=k.repeat_interleave(NH//NKV,1); v=v.repeat_interleave(NH//NKV,1)
            att=(q.transpose(-1,-2)@k)/np.sqrt(HD)+neg; att=att.softmax(-1)
            o=(v@att.transpose(-1,-2)).reshape(1,NH*HD,1,T)
            x=r+(b.o(o)+s.d("o",L,o)); r=x; h=b.n2(x)
            x=r+b.down(torch.nn.functional.silu(b.gate(h))*b.up(h))
        return s.base.nf(x)

def repoint(md, offs):
    s=open(f"{md}/model.mil").read()
    od={f"{a}{f}_{L}":i for i,(a,f,L) in enumerate(ORDER)}
    consts=sorted(set(re.findall(r'[qkvo][AB]_\d+_weight_to_fp16',s)),key=lambda z:od[z.replace("_weight_to_fp16","")])
    assert len(consts)==224, len(consts)
    for k,cn in enumerate(consts):
        i=s.find(cn+" = const"); e=s.find(";",i); st=s[i:e]; assert "weight.bin" in st, cn
        nw=re.sub(r'offset = uint64\(\d+\)',f'offset = uint64({offs[k]})',st.replace("@model_path/weights/weight.bin","@model_path/weights/adapter.bin"),count=1)
        s=s[:i]+nw+s[e:]
    mk='{"coremltools-version", "9.0"}})]'
    assert mk in s
    s=s.replace(mk,mk[:-1]+', BlobFileMutabilityInfo = tuple<string, dict<string, string>>(("Paths", {{"@model_path/weights/adapter.bin", "@model_path/weights/adapter.bin"}}))]')
    open(f"{md}/model.mil","w").write(s)

if MODE=="g0":
    FA,FB=random_factors(); m=KevIn().eval(); rload(m.base)
    with torch.no_grad():
        for a in PROJ:
            for L in range(NL): getattr(m,f"{a}A")[L].weight.copy_(FA[a][L][:,:,None,None]); getattr(m,f"{a}B")[L].weight.copy_(FB[a][L][:,:,None,None])
    ex=(torch.zeros(1,D,1,T),torch.zeros(1,1,HD,T),torch.zeros(1,1,HD,T),torch.zeros(1,1,T,T))
    ml=ct.convert(torch.jit.trace(m,ex),inputs=[ct.TensorType(name=n,shape=t.shape,dtype=np.float16) for n,t in zip(("x","cos","sin","neg"),ex)],
        outputs=[ct.TensorType(name="hs",dtype=np.float16)],convert_to="mlprogram",compute_precision=ct.precision.FLOAT16,
        compute_units=ct.ComputeUnit.CPU_AND_NE,minimum_deployment_target=ct.target.macOS15)
    pk=f"{OUT}/kev_inputs.mlpackage"; shutil.rmtree(pk,ignore_errors=True); ml.save(pk); shutil.rmtree(MD,ignore_errors=True)
    r=subprocess.run(f"xcrun coremlcompiler compile '{pk}' '{OUT}' && mv '{OUT}/kev_inputs.mlmodelc' '{MD}'",shell=True,capture_output=True,text=True); assert os.path.isdir(MD), r.stderr[-800:]
    binR,offs=pack_folded(flat(FA,FB),"g0",OUT,T)
    json.dump(offs,open(f"{OUT}/offsets.json","w")); open(f"{OUT}/adapter_g0.bin","wb").write(binR); open(f"{MD}/weights/adapter.bin","wb").write(binR)
    repoint(MD,offs); print(f"G0_BUILT {MD} T={T} 224 consts mutable, adapter {len(binR)/1e6:.1f} MB",flush=True)
elif MODE=="pack":
    tag,run=sys.argv[4],sys.argv[5]; FA,FB=factors_from_run(run)
    b,offs=pack_folded(flat(FA,FB),tag,OUT,T); assert offs==json.load(open(f"{OUT}/offsets.json")), "pack layout drifted from the base's repoint"
    open(f"{OUT}/adapter_{tag}.bin","wb").write(b); shutil.copy(f"{run}/head.pt",f"{OUT}/head_{tag}.pt"); print(f"PACKED {tag} {len(b)/1e6:.1f} MB (offsets identical to base)",flush=True)
