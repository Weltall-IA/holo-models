from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent


def _post_json(url: str, payload: dict[str, Any], timeout: int = 300) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _ollama_check(model: dict[str, Any]) -> dict[str, Any]:
    name = str(model.get("ollama_name") or model.get("repo") or model["id"])
    category = str(model.get("category") or "")
    started = time.monotonic()
    if category in {"embed", "embedding"}:
        endpoint = "http://127.0.0.1:11434/api/embed"
        payload = {"model": name, "input": ["teste de embedding em português"]}
    else:
        endpoint = "http://127.0.0.1:11434/api/generate"
        payload = {
            "model": name,
            "prompt": "Responda somente: OK",
            "stream": False,
            "options": {"temperature": 0, "num_predict": 8},
        }
    response = _post_json(endpoint, payload)
    if category in {"embed", "embedding"}:
        embeddings = response.get("embeddings")
        if not isinstance(embeddings, list) or not embeddings or not embeddings[0]:
            raise RuntimeError("Ollama não retornou embedding")
        result = {"embedding_dimension": len(embeddings[0])}
    else:
        text = str(response.get("response") or "").strip()
        if not text:
            raise RuntimeError("Ollama não retornou texto")
        result = {
            "response": text[:200],
            "eval_count": response.get("eval_count"),
            "eval_duration": response.get("eval_duration"),
        }
    return {
        "runtime": "ollama",
        "endpoint": endpoint,
        "result": result,
        "elapsed_seconds": round(time.monotonic() - started, 4),
    }


def _find_llama_server() -> str:
    configured = os.environ.get("LLAMA_SERVER")
    if configured and Path(configured).is_file():
        return configured
    found = shutil.which("llama-server")
    if found:
        return found
    raise RuntimeError("llama-server não encontrado")


def _free_port() -> int:
    import socket
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_server(port: int, process: subprocess.Popen, timeout: int = 180) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"llama-server encerrou com código {process.returncode}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.5)
    raise TimeoutError("llama-server não ficou pronto")


def _gguf_text_check(model: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(model.get("path") or ""))
    if not path.is_file():
        raise RuntimeError(f"GGUF ausente: {path}")
    server = _find_llama_server()
    port = _free_port()
    command = [
        server, "-m", str(path), "--host", "127.0.0.1", "--port", str(port),
        "-ngl", "99", "-c", "2048", "-np", "1",
    ]
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="holo-gguf-health-") as tmp:
        log_path = Path(tmp) / "server.log"
        with log_path.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, text=True)
            try:
                _wait_server(port, process)
                response = _post_json(
                    f"http://127.0.0.1:{port}/v1/chat/completions",
                    {
                        "model": "local",
                        "messages": [{"role": "user", "content": "Responda somente: OK"}],
                        "temperature": 0,
                        "max_tokens": 8,
                    },
                )
                choices = response.get("choices") or []
                text = str(((choices[0] if choices else {}).get("message") or {}).get("content") or "").strip()
                if not text:
                    raise RuntimeError("llama-server não retornou texto")
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=15)
        log_tail = log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
    return {
        "runtime": "llama.cpp",
        "command": command,
        "result": {"response": text[:200]},
        "elapsed_seconds": round(time.monotonic() - started, 4),
        "log_tail": log_tail,
    }


def _adapter_check(model: dict[str, Any], adapters: dict[str, Any]) -> dict[str, Any]:
    model_id = str(model["id"])
    adapter = adapters.get(model_id)
    if not isinstance(adapter, dict):
        raise RuntimeError("adaptador de health check não configurado")
    command = adapter.get("command")
    if not isinstance(command, list) or not command:
        raise RuntimeError("comando do adaptador ausente")
    timeout = int(adapter.get("timeout", 1800))
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in (adapter.get("env") or {}).items()})
    started = time.monotonic()
    proc = subprocess.run(
        [str(part) for part in command],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"adaptador retornou {proc.returncode}: "
            f"{(proc.stderr or proc.stdout)[-4000:]}"
        )
    return {
        "runtime": str(adapter.get("runtime") or "adapter"),
        "adapter": model_id,
        "command": command,
        "result": {
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
        },
        "elapsed_seconds": round(time.monotonic() - started, 4),
    }


def run_check(model: dict[str, Any], adapters: dict[str, Any]) -> dict[str, Any]:
    source = str(model.get("source") or "")
    fmt = str(model.get("format") or "")
    category = str(model.get("category") or "")
    if source == "ollama" or model.get("ollama_name"):
        return _ollama_check(model)
    if fmt == "gguf" and category in {"text", "text_llm"}:
        return _gguf_text_check(model)
    return _adapter_check(model, adapters)


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa health checks reais por runtime")
    parser.add_argument("--inventory", default=str(PROJECT_ROOT / "local_model_inventory.json"))
    parser.add_argument("--adapters", default=str(PROJECT_ROOT / "config" / "local_healthcheck_adapters.json"))
    parser.add_argument("--output", default=str(PROJECT_ROOT / "results" / "local_healthchecks.json"))
    parser.add_argument("--models", default="")
    parser.add_argument("--write-inventory", action="store_true")
    args = parser.parse_args()

    payload = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    adapter_path = Path(args.adapters)
    adapters = json.loads(adapter_path.read_text(encoding="utf-8")) if adapter_path.exists() else {}
    selected = {item.strip() for item in args.models.split(",") if item.strip()}
    output: list[dict[str, Any]] = []
    for model in payload.get("models", []):
        model_id = str(model.get("id") or "")
        status = str(model.get("status") or model.get("coverage_status") or "")
        if selected and model_id not in selected:
            continue
        if not selected and status not in {"PENDING_HEALTHCHECK", "NOT_APPLICABLE"}:
            continue
        try:
            evidence = run_check(model, adapters)
            evidence["artifact"] = str(Path(args.output))
            output.append({"id": model_id, "status": "HEALTHCHECK_PASSED", "evidence": evidence})
        except Exception as exc:
            output.append({
                "id": model_id,
                "status": "BLOCKED",
                "reason": str(exc),
                "evidence": {
                    "runtime": str(model.get("runtime") or "unknown"),
                    "error": f"{type(exc).__name__}: {exc}",
                    "attempts": [{"action": "healthcheck", "result": "failed"}],
                },
            })
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(out_path)

    if args.write_inventory:
        by_id = {str(item["id"]): item for item in output}
        updated_models = []
        for model in payload.get("models", []):
            update = by_id.get(str(model.get("id") or ""))
            if not update:
                updated_models.append(model)
                continue
            merged = dict(model)
            merged["status"] = update["status"]
            if update.get("reason"):
                merged["reason"] = update["reason"]
            merged["evidence"] = update.get("evidence") or {}
            updated_models.append(merged)
        payload["models"] = updated_models
        inventory_path = Path(args.inventory)
        inventory_tmp = inventory_path.with_suffix(inventory_path.suffix + ".tmp")
        inventory_tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        inventory_tmp.replace(inventory_path)

    print(json.dumps({"models_checked": len(output), "output": str(out_path)}, ensure_ascii=False))
    return 0 if all(item["status"] == "HEALTHCHECK_PASSED" for item in output) else 2


if __name__ == "__main__":
    raise SystemExit(main())
