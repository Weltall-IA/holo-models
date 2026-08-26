#!/usr/bin/env python3
"""
Compare three uncensored Qwen3.8-27B candidates on the exact same 30-case tie-break battery.

Targets:
- Ektome PristinelyUncensored i1-IQ3_M
- ULTIMATE UNCENSORED hybrid 16GB
- Heretic ARA i1-IQ3_M

This wrapper intentionally reuses the already-versioned fresh tie-break cases so results are
comparable to GRUG/Fable/RVN. It limits llama.cpp CPU threads to 8.
"""
from __future__ import annotations

import importlib.util
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "benchmarks/qwen38-27b-16gb-tiebreak-v1/run_tiebreak.py"

spec = importlib.util.spec_from_file_location("q38_tiebreak_base", BASE)
if spec is None or spec.loader is None:
    raise SystemExit(f"Could not load base runner: {BASE}")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)

base.OUT = ROOT / "tasks/qwen38-27b-16gb-uncensored-round-v1/results"
base.MODEL_SPECS = {
    "ektome": {
        "label": "Ektome PristinelyUncensored i1-IQ3_M",
        "patterns": ["*Ektome*PristinelyUncensored*i1-IQ3_M*.gguf", "*Ektome*IQ3_M*.gguf"],
        "reject": ["IQ3_S", "IQ4", "Q3_K", "Q2"],
    },
    "ultimate": {
        "label": "ULTIMATE UNCENSORED Hybrid 16GB",
        "patterns": ["*ULTIMATE*UNCENSORED*MTP*IQ4*16GB*.gguf", "*ULTIMATE*UNCENSORED*16GB*.gguf"],
        "reject": ["mmproj"],
    },
    "ara": {
        "label": "Heretic ARA i1-IQ3_M",
        "patterns": ["*Qwen3.8*27B*heretic*ara*i1-IQ3_M*.gguf", "*heretic*ara*IQ3_M*.gguf"],
        "reject": ["IQ3_S", "IQ4", "Q3_K", "Q2"],
    },
}


def start_server(llama_server: str, model: Path, label: str, ctx: int):
    base.OUT.mkdir(parents=True, exist_ok=True)
    port = base.free_port()
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", label)
    log_path = base.OUT / f"server_{safe}.log"
    log = log_path.open("w", encoding="utf-8")

    cmd = [
        llama_server,
        "-m", str(model),
        "--host", "127.0.0.1",
        "--port", str(port),
        "-c", str(ctx),
        "-ngl", "999",
        "--cache-type-k", "q4_0",
        "--cache-type-v", "q4_0",
        "-fa", "on",
        "--parallel", "1",
        "--threads", "8",
        "--threads-batch", "8",
        "--jinja",
    ]

    # The ULTIMATE repository ships an explicit Qwen3.8 chat template. If downloaded next
    # to the GGUF, prefer it over embedded metadata.
    if "ULTIMATE" in model.name.upper():
        tpl = model.parent / "chat_template.jinja"
        if tpl.is_file():
            cmd.extend(["--chat-template-file", str(tpl)])

    extra = os.environ.get("LLAMA_EXTRA_ARGS", "").strip()
    if extra:
        import shlex
        cmd.extend(shlex.split(extra))

    env = os.environ.copy()
    server_dir = str(Path(llama_server).resolve().parent)
    env["LD_LIBRARY_PATH"] = f"{server_dir}:{env.get('LD_LIBRARY_PATH', '')}"
    env["OMP_NUM_THREADS"] = "8"
    env["OPENBLAS_NUM_THREADS"] = "8"
    env["MKL_NUM_THREADS"] = "8"
    env["NUMEXPR_NUM_THREADS"] = "8"

    log.write("$ " + " ".join(cmd) + "\n")
    log.flush()
    proc = subprocess.Popen(
        cmd,
        stdout=log,
        stderr=subprocess.STDOUT,
        cwd=ROOT,
        env=env,
        start_new_session=True,
    )
    s = base.Server(proc=proc, port=port, log_handle=log, model=model, cmd=cmd)
    base.wait_ready(s)
    return s


base.start_server = start_server

_orig_markdown = base.markdown_summary

def markdown_summary(summary):
    text = _orig_markdown(summary)
    return text.replace("# Qwen3.8-27B 16GB tie-break v1", "# Qwen3.8-27B 16GB uncensored round v1", 1)

base.markdown_summary = markdown_summary

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv += ["--models", "ektome,ultimate,ara"]
    raise SystemExit(base.main())
