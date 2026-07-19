from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import gate2_runtime as _runtime

# Camada pública mantida para compatibilidade com benchmark.py, testes e worker.
# A implementação resiliente vive em gate2_runtime.py; cada modelo é executado
# por gate2_worker.py em processo separado para não propagar falhas CUDA.
from .gate2_runtime import *  # noqa: F401,F403
from .gate2_runtime import _atomic_json  # noqa: F401


def _run_model_worker(
    project_root: Path,
    repo_root: Path,
    resolved: ResolvedModel,
    spec: Gate2ModelSpec,
    model_path: Path,
    chunks: list[dict[str, Any]],
    queries: list[dict[str, Any]],
    prompts: dict[str, Any],
    device: str,
    batch_size: int,
    corpus_hash: str,
    timeout_seconds: int,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Execute um worker e preserve o erro estruturado mesmo com exit code 2."""
    raw_dir = project_root / "results" / "raw" / "gate2"
    raw_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{spec.id}-", dir=raw_dir) as tmp:
        work = Path(tmp)
        request_path = work / "request.json"
        output_path = work / "result.json"
        _runtime._atomic_json(
            request_path,
            {
                "resolved": asdict(resolved),
                "spec": asdict(spec),
                "model_path": str(model_path),
                "chunks": chunks,
                "queries": queries,
                "prompts": prompts,
                "device": device,
                "batch_size": batch_size,
                "corpus_hash": corpus_hash,
                "repo_root": str(repo_root),
            },
        )
        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "holo_benchmark.gate2_worker",
                    "--request",
                    str(request_path),
                    "--output",
                    str(output_path),
                ],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired as exc:
            return None, _runtime._failure(
                spec,
                "benchmark_worker",
                error_type="WorkerTimeout",
                error_message=(
                    f"worker excedeu {timeout_seconds}s; "
                    "o próximo modelo continuará em processo limpo"
                ),
                stderr_tail=str(exc.stderr or "")[-12000:],
            )

        stderr_tail = "\n".join(proc.stderr.splitlines()[-80:])
        if not output_path.exists():
            return None, _runtime._failure(
                spec,
                "benchmark_worker",
                error_type="WorkerProcessError",
                error_message=(
                    f"worker terminou com código {proc.returncode} sem produzir "
                    "resultado estruturado; o próximo modelo continuará em processo limpo"
                ),
                returncode=proc.returncode,
                stderr_tail=stderr_tail,
            )

        try:
            payload = _runtime._read_json(output_path)
        except Exception as exc:
            return None, _runtime._failure(
                spec,
                "benchmark_worker",
                exc,
                error_type="WorkerOutputError",
                error_message=f"resultado estruturado inválido: {exc}",
                returncode=proc.returncode,
                stderr_tail=stderr_tail,
            )

        if payload.get("status") != "ok":
            error = payload.get("error") or {}
            return None, _runtime._failure(
                spec,
                "benchmark_worker",
                error_type=str(error.get("type") or "WorkerError"),
                error_message=str(error.get("message") or "worker falhou"),
                returncode=proc.returncode,
                stderr_tail=str(error.get("traceback") or stderr_tail)[-12000:],
            )

        if proc.returncode != 0:
            return None, _runtime._failure(
                spec,
                "benchmark_worker",
                error_type="WorkerProtocolError",
                error_message=(
                    "worker produziu status ok, mas encerrou com código "
                    f"{proc.returncode}"
                ),
                returncode=proc.returncode,
                stderr_tail=stderr_tail,
            )
        return payload["result"], None


# run_gate2 foi definido no módulo original e consulta este global em tempo de
# execução. Substituí-lo aqui corrige o fluxo sem duplicar o restante do runner.
_runtime._run_model_worker = _run_model_worker
