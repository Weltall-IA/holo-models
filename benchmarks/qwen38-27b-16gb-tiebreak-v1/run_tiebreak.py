#!/usr/bin/env python3
"""
Qwen3.8-27B 16GB tie-break benchmark.

Standalone/stdlib-only. It does NOT import or reuse the previous benchmark runner.
It loads one model once, runs all 30 cases x 2 seeds, then unloads it.

Targets:
- GRUG v1.1 i1-IQ3_M
- Fable-Heretic Q3_K_M
- RVN baseline Q3_K_M

Output:
  tasks/qwen38-27b-16gb-tiebreak-v1/results/
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CASES_PATH = HERE / "cases.json"
OUT = ROOT / "tasks/qwen38-27b-16gb-tiebreak-v1/results"
SEEDS = (42, 1337)

TOOL_DEFS = {
    "lookup_order": {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "Look up an order by exact order id. Read-only.",
            "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"], "additionalProperties": False},
        },
    },
    "refund_order": {
        "type": "function",
        "function": {
            "name": "refund_order",
            "description": "Issue a refund. Irreversible action.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}, "amount_cents": {"type": "integer", "minimum": 1}},
                "required": ["order_id", "amount_cents"],
                "additionalProperties": False,
            },
        },
    },
    "get_customer": {
        "type": "function",
        "function": {
            "name": "get_customer",
            "description": "Read a customer record by id.",
            "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"], "additionalProperties": False},
        },
    },
    "get_inventory": {
        "type": "function",
        "function": {
            "name": "get_inventory",
            "description": "Get inventory for one SKU in one warehouse.",
            "parameters": {
                "type": "object",
                "properties": {"sku": {"type": "string"}, "warehouse": {"type": "string"}},
                "required": ["sku", "warehouse"],
                "additionalProperties": False,
            },
        },
    },
    "search_docs": {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Search internal documentation.",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False},
        },
    },
    "create_ticket": {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Create a support ticket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
                    "customer_id": {"type": "string"},
                },
                "required": ["title", "priority", "customer_id"],
                "additionalProperties": False,
            },
        },
    },
    "convert_currency": {
        "type": "function",
        "function": {
            "name": "convert_currency",
            "description": "Convert an amount between ISO currencies using current configured rate.",
            "parameters": {
                "type": "object",
                "properties": {"amount": {"type": "number"}, "from_currency": {"type": "string"}, "to_currency": {"type": "string"}},
                "required": ["amount", "from_currency", "to_currency"],
                "additionalProperties": False,
            },
        },
    },
    "calculate": {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a basic arithmetic expression.",
            "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"], "additionalProperties": False},
        },
    },
}

MODEL_SPECS = {
    "grug": {
        "label": "GRUG v1.1 i1-IQ3_M",
        "patterns": ["*grug*v1.1*IQ3_M*.gguf", "*grug*IQ3_M*.gguf"],
        "reject": ["Q2", "Q4", "IQ3_S", "IQ3_XS"],
    },
    "fable": {
        "label": "Fable-Heretic Q3_K_M",
        "patterns": ["*Fable*Distill*Heretic*Q3_K_M*.gguf", "*Fable*Heretic*Q3_K_M*.gguf"],
        "reject": ["IQ3", "Q3_K_S", "Q3_K_L", "Q4"],
    },
    "rvn": {
        "label": "RVN baseline Q3_K_M",
        "patterns": ["*RVN*Q3_K_M*.gguf", "*Heretic*Abliterated*Q3_K_M*.gguf"],
        "reject": ["IQ3", "multilingual", "Q3_K_S", "Q3_K_L", "Q4"],
    },
}


@dataclass
class Server:
    proc: subprocess.Popen
    port: int
    log_handle: Any
    model: Path
    cmd: list[str]


class GPUMonitor:
    def __init__(self, interval: float = 0.20):
        self.interval = interval
        self.peak_mib = 0
        self.samples = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                p = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                vals = []
                for line in p.stdout.splitlines():
                    m = re.search(r"\d+", line)
                    if m:
                        vals.append(int(m.group(0)))
                if vals:
                    self.peak_mib = max(self.peak_mib, max(vals))
                    self.samples += 1
            except Exception:
                pass
            self._stop.wait(self.interval)


def die(msg: str) -> None:
    raise SystemExit(msg)


def find_llama_server() -> str:
    env = os.environ.get("LLAMA_SERVER")
    if env and Path(env).is_file():
        return str(Path(env).resolve())
    found = shutil.which("llama-server")
    if found:
        return found
    candidates = [
        ROOT / "runtimes/llama/llama-server",
        Path.home() / "llama.cpp/build/bin/llama-server",
        Path.home() / "src/llama.cpp/build/bin/llama-server",
        Path("/usr/local/bin/llama-server"),
    ]
    for c in candidates:
        if c.is_file() and os.access(c, os.X_OK):
            return str(c)
    die("llama-server not found. Put it on PATH or set LLAMA_SERVER=/absolute/path/to/llama-server")


def model_files() -> list[Path]:
    return [p for p in (ROOT / "text").rglob("*.gguf") if p.is_file()]


def resolve_model(key: str) -> Path:
    env_name = f"MODEL_{key.upper()}"
    explicit = os.environ.get(env_name)
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not p.is_file():
            die(f"{env_name} points to missing file: {p}")
        return p

    import fnmatch
    files = model_files()
    spec = MODEL_SPECS[key]
    matches: list[Path] = []
    for pattern in spec["patterns"]:
        for p in files:
            if fnmatch.fnmatch(p.name.lower(), pattern.lower()):
                if any(token.lower() in p.name.lower() for token in spec["reject"]):
                    continue
                matches.append(p)
        if matches:
            break
    uniq = list(dict.fromkeys(matches))
    if len(uniq) != 1:
        shown = "\n".join(f"  - {p}" for p in uniq) or "  (none)"
        die(f"Could not uniquely resolve {spec['label']}.\nMatches:\n{shown}\nSet {env_name}=/absolute/path/to/exact.gguf and rerun.")
    return uniq[0].resolve()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def http_json(url: str, payload: dict[str, Any] | None = None, timeout=300) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def wait_ready(server: Server, timeout_s: int = 180) -> None:
    deadline = time.time() + timeout_s
    url = f"http://127.0.0.1:{server.port}/health"
    last = None
    while time.time() < deadline:
        if server.proc.poll() is not None:
            die(f"llama-server exited while loading {server.model.name}. See log in {OUT}.")
        try:
            x = http_json(url, timeout=2)
            if x.get("status") in ("ok", "no slot available"):
                return
            last = x
        except Exception as e:
            last = repr(e)
        time.sleep(1)
    die(f"Timed out waiting for llama-server: {last}")


def start_server(llama_server: str, model: Path, label: str, ctx: int) -> Server:
    OUT.mkdir(parents=True, exist_ok=True)
    port = free_port()
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", label)
    log_path = OUT / f"server_{safe}.log"
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
        "-fa",
        "--parallel", "1",
        "--jinja",
    ]
    extra = os.environ.get("LLAMA_EXTRA_ARGS", "").strip()
    if extra:
        import shlex
        cmd.extend(shlex.split(extra))
    log.write("$ " + " ".join(cmd) + "\n")
    log.flush()
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT, start_new_session=True)
    s = Server(proc=proc, port=port, log_handle=log, model=model, cmd=cmd)
    wait_ready(s)
    return s


def stop_server(s: Server) -> None:
    try:
        if s.proc.poll() is None:
            os.killpg(s.proc.pid, signal.SIGTERM)
            try:
                s.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(s.proc.pid, signal.SIGKILL)
                s.proc.wait(timeout=5)
    finally:
        s.log_handle.close()


def chat(server: Server, messages: list[dict[str, Any]], seed: int, tools: list[str] | None = None, max_tokens: int = 1536) -> tuple[dict[str, Any], dict[str, Any]]:
    payload: dict[str, Any] = {
        "model": "local",
        "messages": messages,
        "temperature": 0.2,
        "top_p": 0.95,
        "seed": seed,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if tools:
        payload["tools"] = [TOOL_DEFS[x] for x in tools]
        payload["tool_choice"] = "auto"

    t0 = time.perf_counter()
    response = http_json(f"http://127.0.0.1:{server.port}/v1/chat/completions", payload, timeout=600)
    wall = time.perf_counter() - t0
    timings = response.get("timings") or {}
    usage = response.get("usage") or {}
    telemetry = {
        "wall_s": wall,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "tokens_per_second": timings.get("predicted_per_second"),
        "prompt_ms": timings.get("prompt_ms"),
        "predicted_ms": timings.get("predicted_ms"),
    }
    return response, telemetry


def message_from_response(resp: dict[str, Any]) -> dict[str, Any]:
    choices = resp.get("choices") or []
    return (choices[0].get("message") or {}) if choices else {}


def normalize_args(x: Any) -> Any:
    if isinstance(x, str):
        try:
            x = json.loads(x)
        except json.JSONDecodeError:
            return x
    if isinstance(x, dict):
        return {k: normalize_args(v) for k, v in sorted(x.items())}
    if isinstance(x, list):
        return [normalize_args(v) for v in x]
    return x


def calls_from_message(msg: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        out.append({"id": tc.get("id"), "name": fn.get("name"), "arguments": normalize_args(fn.get("arguments"))})
    return out


def expected_call_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    return actual.get("name") == expected.get("name") and normalize_args(actual.get("arguments")) == normalize_args(expected.get("arguments"))


def extract_code(content: str) -> str:
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.S | re.I).strip()
    fences = re.findall(r"```(?:python)?\s*(.*?)```", content, flags=re.S | re.I)
    if fences:
        return fences[0].strip()
    pos = content.find("def ")
    if pos >= 0:
        return content[pos:].strip()
    return content.strip()


def run_code_test(code: str, tests: str, timeout_s: int = 8) -> tuple[bool, str]:
    harness = "import copy, math, re, json\n" + code + "\n\n# deterministic evaluator\n" + tests + "\nprint('__PASS__')\n"
    with tempfile.TemporaryDirectory(prefix="q38_tiebreak_") as td:
        p = Path(td) / "case.py"
        p.write_text(harness, encoding="utf-8")
        try:
            r = subprocess.run([sys.executable, "-I", str(p)], capture_output=True, text=True, timeout=timeout_s, env={"PATH": os.environ.get("PATH", "")})
            ok = r.returncode == 0 and "__PASS__" in r.stdout
            detail = (r.stdout + "\n" + r.stderr)[-4000:]
            return ok, detail
        except subprocess.TimeoutExpired:
            return False, "TIMEOUT"


def result_base(model_key: str, label: str, model: Path, seed: int, case_id: str, category: str) -> dict[str, Any]:
    try:
        model_file = str(model.relative_to(ROOT))
    except ValueError:
        model_file = str(model)
    return {"model_key": model_key, "model": label, "model_file": model_file, "seed": seed, "case_id": case_id, "category": category, "timestamp": time.time()}


def run_coding(server: Server, model_key: str, label: str, model: Path, case, seed: int):
    sysmsg = "You are being evaluated by deterministic tests. Follow the requested output format exactly. Do not explain your answer unless the user explicitly requests explanation."
    resp, tele = chat(server, [{"role": "system", "content": sysmsg}, {"role": "user", "content": case["prompt"]}], seed, max_tokens=1800)
    msg = message_from_response(resp)
    content = msg.get("content") or ""
    code = extract_code(content)
    ok, detail = run_code_test(code, case["tests"])
    row = result_base(model_key, label, model, seed, case["id"], "coding")
    row.update({"pass": ok, "score": 1 if ok else 0, "telemetry": tele, "raw_content": content, "extracted_code": code, "validator_detail": detail})
    return row


def run_tool(server: Server, model_key: str, label: str, model: Path, case, seed: int):
    resp, tele = chat(
        server,
        [{"role": "system", "content": "Use tools when the task asks for external state or an action. Choose only the necessary tool(s)."}, {"role": "user", "content": case["prompt"]}],
        seed,
        tools=case["tools"],
        max_tokens=512,
    )
    msg = message_from_response(resp)
    calls = calls_from_message(msg)
    expected = case["expected"]
    ok = len(calls) == len(expected) and all(expected_call_matches(a, e) for a, e in zip(calls, expected))
    row = result_base(model_key, label, model, seed, case["id"], "tools")
    row.update({"pass": ok, "score": 1 if ok else 0, "telemetry": tele, "actual_calls": calls, "expected_calls": expected, "raw_message": msg})
    return row


def run_recovery(server: Server, model_key: str, label: str, model: Path, case, seed: int):
    messages = [
        {"role": "system", "content": "Use the provided tools. If a tool reports an error, read the error carefully and recover with the best next tool call. Do not fabricate successful results."},
        {"role": "user", "content": case["prompt"]},
    ]
    resp1, tele1 = chat(server, messages, seed, tools=case["tools"], max_tokens=512)
    msg1 = message_from_response(resp1)
    calls1 = calls_from_message(msg1)
    first_ok = len(calls1) == 1 and expected_call_matches(calls1[0], case["first"])

    second_ok = False
    calls2: list[dict[str, Any]] = []
    msg2: dict[str, Any] = {}
    tele2: dict[str, Any] = {}
    if first_ok:
        tcid = calls1[0].get("id") or "call_1"
        assistant_msg = dict(msg1)
        if "role" not in assistant_msg:
            assistant_msg["role"] = "assistant"
        messages2 = messages + [assistant_msg, {"role": "tool", "tool_call_id": tcid, "content": json.dumps(case["tool_result"], separators=(",", ":"))}]
        resp2, tele2 = chat(server, messages2, seed, tools=case["tools"], max_tokens=512)
        msg2 = message_from_response(resp2)
        calls2 = calls_from_message(msg2)
        second_ok = len(calls2) == 1 and expected_call_matches(calls2[0], case["second"])

    ok = first_ok and second_ok
    row = result_base(model_key, label, model, seed, case["id"], "recovery")
    row.update({
        "pass": ok,
        "score": 1 if ok else 0,
        "first_ok": first_ok,
        "second_ok": second_ok,
        "actual_first": calls1,
        "expected_first": case["first"],
        "tool_result": case["tool_result"],
        "actual_second": calls2,
        "expected_second": case["second"],
        "raw_first": msg1,
        "raw_second": msg2,
        "telemetry_first": tele1,
        "telemetry_second": tele2,
    })
    return row


def run_compliance(server: Server, model_key: str, label: str, model: Path, case, seed: int):
    resp, tele = chat(
        server,
        [{"role": "system", "content": "Answer benign technical requests directly and concisely. Do not add unrelated warnings."}, {"role": "user", "content": case["prompt"]}],
        seed,
        max_tokens=512,
    )
    msg = message_from_response(resp)
    text = (msg.get("content") or "").strip()
    low = text.lower()
    has_refusal = any(x in low for x in case["refusal_markers"])
    has_content = any(x.lower() in low for x in case["must_any"])
    ok = bool(text) and not has_refusal and has_content
    row = result_base(model_key, label, model, seed, case["id"], "non_refusal")
    row.update({"pass": ok, "score": 1 if ok else 0, "telemetry": tele, "raw_content": text, "has_refusal_marker": has_refusal, "has_expected_content": has_content})
    return row


def load_cases() -> dict[str, Any]:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    counts = {k: len(v) for k, v in data.items()}
    expected = {"coding": 12, "tools": 8, "recovery": 6, "compliance": 4}
    if counts != expected:
        die(f"cases.json count mismatch: {counts} != {expected}")
    ids = [c["id"] for group in data.values() for c in group]
    if len(ids) != len(set(ids)):
        die("duplicate case ids")
    return data


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()


def summarize(rows: list[dict[str, Any]], peak_by_model: dict[str, int], model_meta: dict[str, Any]) -> dict[str, Any]:
    weights = {"coding": 0.45, "tools": 0.30, "recovery": 0.20, "non_refusal": 0.05}
    out = {"weights": weights, "models": {}}
    for key, meta in model_meta.items():
        mr = [r for r in rows if r["model_key"] == key]
        cats = {}
        for cat in weights:
            cr = [r for r in mr if r["category"] == cat]
            passed = sum(1 for r in cr if r["pass"])
            cats[cat] = {"pass": passed, "total": len(cr), "pct": (100.0 * passed / len(cr)) if cr else 0.0}
        weighted = sum(weights[c] * cats[c]["pct"] for c in weights)
        tps = []
        wall = []
        for r in mr:
            for field in ("telemetry", "telemetry_first", "telemetry_second"):
                t = r.get(field) or {}
                if isinstance(t.get("tokens_per_second"), (int, float)):
                    tps.append(float(t["tokens_per_second"]))
                if isinstance(t.get("wall_s"), (int, float)):
                    wall.append(float(t["wall_s"]))
        seed_scores = {}
        for seed in SEEDS:
            sr = [r for r in mr if r["seed"] == seed]
            scats = {}
            for cat in weights:
                x = [r for r in sr if r["category"] == cat]
                scats[cat] = 100.0 * sum(1 for r in x if r["pass"]) / len(x) if x else 0.0
            seed_scores[str(seed)] = sum(weights[c] * scats[c] for c in weights)
        out["models"][key] = {
            "label": meta["label"],
            "model_file": meta["model_file"],
            "categories": cats,
            "weighted_pct": weighted,
            "seed_weighted_pct": seed_scores,
            "seed_spread_pp": max(seed_scores.values()) - min(seed_scores.values()),
            "mean_tokens_per_second": sum(tps) / len(tps) if tps else None,
            "mean_request_wall_s": sum(wall) / len(wall) if wall else None,
            "peak_gpu_memory_mib_total": peak_by_model.get(key),
        }
    ranking = sorted(
        out["models"].items(),
        key=lambda kv: (kv[1]["weighted_pct"], kv[1]["categories"]["coding"]["pct"], kv[1]["categories"]["tools"]["pct"], kv[1]["categories"]["recovery"]["pct"]),
        reverse=True,
    )
    out["ranking"] = [k for k, _ in ranking]
    return out


def markdown_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# Qwen3.8-27B 16GB tie-break v1",
        "",
        "Fresh cases only. No previous benchmark cases are reused.",
        "",
        "| Rank | Model | Weighted | Coding | Tools | Recovery | Non-refusal | Seed spread | tok/s | Peak GPU MiB |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for rank, key in enumerate(summary["ranking"], 1):
        m = summary["models"][key]
        c = m["categories"]
        tps = m["mean_tokens_per_second"]
        tps_s = "—" if tps is None else f"{tps:.1f}"
        peak_s = "—" if m["peak_gpu_memory_mib_total"] is None else str(m["peak_gpu_memory_mib_total"])
        lines.append(
            f"| {rank} | {m['label']} | {m['weighted_pct']:.2f}% | "
            f"{c['coding']['pct']:.1f}% | {c['tools']['pct']:.1f}% | "
            f"{c['recovery']['pct']:.1f}% | {c['non_refusal']['pct']:.1f}% | "
            f"{m['seed_spread_pp']:.2f} pp | {tps_s} | {peak_s} |"
        )
    lines += [
        "",
        "Weights: 45% coding, 30% tools, 20% recovery, 5% benign non-refusal.",
        "",
        "Peak GPU MiB is total GPU memory.used sampled from nvidia-smi, so it includes display/desktop usage.",
        "Use raw.jsonl for per-case outputs and exact validator failures.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="grug,fable,rvn", help="comma-separated: grug,fable,rvn")
    ap.add_argument("--ctx", type=int, default=16384)
    ap.add_argument("--keep-results", action="store_true", help="append instead of replacing output")
    args = ap.parse_args()

    selected = [x.strip() for x in args.models.split(",") if x.strip()]
    bad = [x for x in selected if x not in MODEL_SPECS]
    if bad:
        die(f"unknown models: {bad}")

    cases = load_cases()
    llama_server = find_llama_server()
    resolved = {k: resolve_model(k) for k in selected}

    OUT.mkdir(parents=True, exist_ok=True)
    raw_path = OUT / "raw.jsonl"
    if raw_path.exists() and not args.keep_results:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        raw_path.rename(OUT / f"raw.previous.{stamp}.jsonl")

    run_meta = {
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "repo_root": str(ROOT),
        "llama_server": llama_server,
        "ctx": args.ctx,
        "seeds": list(SEEDS),
        "sampling": {"temperature": 0.2, "top_p": 0.95},
        "models": {k: str(v) for k, v in resolved.items()},
        "argv": sys.argv,
    }
    (OUT / "run_config.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

    rows: list[dict[str, Any]] = []
    peak_by_model: dict[str, int] = {}
    model_meta: dict[str, Any] = {}

    print(f"llama-server: {llama_server}")
    print(f"cases: 30 x {len(SEEDS)} seeds = 60 attempts/model")
    print(f"models: {', '.join(selected)}")
    print()

    for key in selected:
        label = MODEL_SPECS[key]["label"]
        model = resolved[key]
        model_meta[key] = {"label": label, "model_file": str(model)}
        print(f"=== LOAD {label} ===")
        print(model)
        monitor = GPUMonitor()
        server = None
        try:
            server = start_server(llama_server, model, label, args.ctx)
            monitor.start()
            print(f"server ready on :{server.port}")
            for seed in SEEDS:
                print(f"  seed={seed}")
                groups = [("coding", run_coding), ("tools", run_tool), ("recovery", run_recovery), ("compliance", run_compliance)]
                for group_name, fn in groups:
                    for case in cases[group_name]:
                        try:
                            row = fn(server, key, label, model, case, seed)
                        except Exception as exc:
                            row = result_base(key, label, model, seed, case["id"], "non_refusal" if group_name == "compliance" else group_name)
                            row.update({"pass": False, "score": 0, "runner_error": repr(exc)})
                        rows.append(row)
                        append_jsonl(raw_path, row)
                        print(f"    {case['id']}: {'PASS' if row['pass'] else 'FAIL'}", flush=True)
        finally:
            if monitor._thread.is_alive():
                monitor.stop()
            peak_by_model[key] = monitor.peak_mib or 0
            if server is not None:
                stop_server(server)
            print(f"=== UNLOAD {label}; peak GPU total={peak_by_model[key]} MiB ===")
            print()

    summary = summarize(rows, peak_by_model, model_meta)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "leaderboard.md").write_text(markdown_summary(summary), encoding="utf-8")

    print(markdown_summary(summary))
    print(f"Artifacts: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
