"""Repo-relative paths and endpoints for documents/. Every script imports this first, so nothing is tied to one machine.
Override any of these with the environment variables named below."""
import os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))                      # documents/
SRC = os.path.join(ROOT, "..", "src")                                   # kev_ane package (trunk, encode, merge)
MUTABLE = os.path.join(ROOT, "..", "mutable")                           # deploy_inputs.py (base build + adapter pack), ui/kevd
KEVD = os.environ.get("KEV_KEVD", os.path.join(MUTABLE, "ui", "kevd"))  # resident ANE daemon, built from mutable/ui/kevd.mm
BASE_MLMODELC = os.environ.get("KEV_BASE_MLMODELC", "/Library/Caches/com.apple.aned/kev_inputs.mlmodelc")   # compiled mutable base
TRUST_DIR = os.environ.get("KEV_TRUST_DIR", "/var/db/AppleIntelligencePlatform/AppModelAssets/w2d")        # where adapter .bin files are bound from
LLM_URL = os.environ.get("KEV_LLM_URL", "http://127.0.0.1:8000/v1/chat/completions")   # any OpenAI-compatible chat endpoint
LLM_MODEL = os.environ.get("KEV_LLM_MODEL", "incoai/Qwen3.8-27B-Splash")               # the 27B used for every number in results/
GATE0 = f"{sys.executable} {os.path.join(ROOT, 'gate0.py')}"            # memory-pressure gate every run asserts before starting
SENTINEL = os.path.join(ROOT, "red_sentinel.sh")                        # kills a run the moment the gate reads RED
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "")                  # SEC EDGAR requires "name email"; set it before edgar_fetch.py
