"""Architecture constants and artifact resolution. No machine-specific paths."""
import os, glob, subprocess, sys
from pathlib import Path

# Qwen3-0.6B-Base, verified byte-identical in config to Qwen3-0.6B
D, NL, NH, NKV, HD, IM = 1024, 28, 16, 8, 128, 3072
EPS, THETA, VOCAB = 1e-6, 1e6, 151936
BASE_REPO = "Qwen/Qwen3-0.6B-Base"
KEV_RELEASE = ("jaredpalmer/kev", "kev-family", "kev-0.6b.tar.gz")
BUCKETS = (64, 256)          # fixed-shape CoreML buckets; Kev buckets for MPS the same way

def cache_dir() -> Path:
    return Path(os.environ.get("KEV_ANE_CACHE", Path.home() / ".cache" / "kev-ane"))

def base_snapshot() -> Path:
    """Download Qwen3-0.6B-Base if absent. Weights are NOT vendored in this repo."""
    from huggingface_hub import snapshot_download
    return Path(snapshot_download(BASE_REPO,
                allow_patterns=["*.safetensors", "*.json", "*.txt"]))

def kev_dir() -> Path:
    """Fetch Kev-0.6B from its GitHub release (Apache-2.0, jaredpalmer/kev). Not redistributed."""
    d = cache_dir() / "kev-0.6b"
    if (d / "adapter_model.safetensors").exists():
        return d
    d.parent.mkdir(parents=True, exist_ok=True)
    repo, tag, asset = KEV_RELEASE
    subprocess.run(["gh", "release", "download", tag, "-R", repo, "-p", asset,
                    "-D", str(d.parent), "--clobber"], check=True)
    subprocess.run(["tar", "xzf", str(d.parent / asset), "-C", str(d.parent)], check=True)
    if not (d / "adapter_model.safetensors").exists():
        sys.exit(f"expected {d}/adapter_model.safetensors after extracting {asset}")
    return d
