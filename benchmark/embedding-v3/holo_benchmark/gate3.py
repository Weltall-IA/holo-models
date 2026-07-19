from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .gate2_runtime import (
    MIN_FREE_MARGIN_BYTES,
    _atomic_json,
    _card_license,
    _ensure_destination,
    _read_json,
    _resolve_device,
    _select_dataset,
)


@dataclass(frozen=True)
class Gate3ModelSpec:
    id: str
    repo: str
    file: str
    dimension: int
    native_dimension: int
    license: str
    fallback_file: str | None = None
    backend: str = "llama.cpp"
    pooling: str = "last"
    prompt_profile: str | None = None
    baseline_model_id: str | None = None
    required: bool = True
    enabled: bool = True
    context_size: int = 4096
    server_batch_size: int = 512
    server_ubatch_size: int = 512
    gpu_layers: int = 99


@dataclass(frozen=True)
class Gate3ResolvedModel:
    id: str
    repo: str
    revision: str
    expected_size_bytes: int
    license: str | None
    gated: bool | str | None
    destination: str
    file: str
    fallback_used: bool
    backend: str
    dimension: int
    native_dimension: int
    pooling: str
    prompt_profile: str | None
    required: bool
    context_size: int
    server_batch_size: int
    server_ubatch_size: int
    gpu_layers: int


def load_gate3_specs(models_path: Path, selected_ids: Sequence[str] | None = None) -> list[Gate3ModelSpec]:
    payload = _read_json(models_path)
    selected = set(selected_ids or [])
    specs: list[Gate3ModelSpec] = []
    known: set[str] = set()
    for raw in payload.get("models", []):
        model_id = str(raw.get("id") or "")
        if not model_id:
            raise ValueError("modelo sem id em config/models.json")
        if model_id in known:
            raise ValueError(f"id de modelo duplicado: {model_id}")
        known.add(model_id)
        if raw.get("gate") != 3 or not raw.get("enabled", False):
            continue
        if selected and model_id not in selected:
            continue
        backend = str(raw.get("backend") or "")
        if backend != "llama.cpp":
            raise ValueError(f"Gate 3 aceita somente llama.cpp: {model_id} usa {backend}")
        file_name = str(raw.get("file") or "")
        if not file_name.endswith(".gguf"):
            raise ValueError(f"arquivo GGUF inválido para {model_id}")
        dimension = int(raw.get("dimension") or 0)
        native_dimension = int(raw.get("native_dimension") or dimension)
        license_name = str(raw.get("license") or "").strip()
        if not license_name:
            raise ValueError(f"licença não configurada para {model_id}")
        if dimension <= 0 or native_dimension < dimension:
            raise ValueError(f"dimensão inválida para {model_id}: alvo={dimension} nativa={native_dimension}")
        specs.append(Gate3ModelSpec(
            id=model_id,
            repo=str(raw["repo"]),
            file=file_name,
            fallback_file=str(raw["fallback_file"]) if raw.get("fallback_file") else None,
            dimension=dimension,
            native_dimension=native_dimension,
            license=license_name,
            backend=backend,
            pooling=str(raw.get("pooling") or "last"),
            prompt_profile=str(raw["prompt_profile"]) if raw.get("prompt_profile") else None,
            baseline_model_id=str(raw["baseline_model_id"]) if raw.get("baseline_model_id") else None,
            required=bool(raw.get("required", True)),
            context_size=int(raw.get("context_size") or 4096),
            server_batch_size=int(raw.get("server_batch_size") or 512),
            server_ubatch_size=int(raw.get("server_ubatch_size") or 512),
            gpu_layers=int(raw.get("gpu_layers") or 99),
        ))
    missing = selected - {spec.id for spec in specs}
    if missing:
        raise ValueError("modelos solicitados não habilitados no Gate 3: " + ", ".join(sorted(missing)))
    if not specs:
        raise ValueError("nenhum modelo habilitado para o Gate 3")
    return specs


def resolve_gate3_model(spec: Gate3ModelSpec, destination: Path, api: Any | None = None) -> Gate3ResolvedModel:
    if api is None:
        from huggingface_hub import HfApi
        api = HfApi()
    info = api.model_info(spec.repo, files_metadata=True)
    revision = str(getattr(info, "sha", "") or "")
    if len(revision) < 7:
        raise RuntimeError(f"revisão não resolvida para {spec.repo}")
    siblings: dict[str, int] = {}
    for sibling in getattr(info, "siblings", []) or []:
        name = str(getattr(sibling, "rfilename", "") or "")
        size = getattr(sibling, "size", None)
        if name and isinstance(size, int) and size > 0:
            siblings[name] = size
    candidates = [spec.file] + ([spec.fallback_file] if spec.fallback_file else [])
    chosen = next((name for name in candidates if name in siblings), None)
    if chosen is None:
        raise RuntimeError(f"nenhum GGUF configurado encontrado em {spec.repo}: " + ", ".join(candidates))
    return Gate3ResolvedModel(
        id=spec.id,
        repo=spec.repo,
        revision=revision,
        expected_size_bytes=siblings[chosen],
        license=_card_license(getattr(info, "card_data", None)) or spec.license,
        gated=getattr(info, "gated", None),
        destination=str(destination),
        file=chosen,
        fallback_used=chosen != spec.file,
        backend=spec.backend,
        dimension=spec.dimension,
        native_dimension=spec.native_dimension,
        pooling=spec.pooling,
        prompt_profile=spec.prompt_profile,
        required=spec.required,
        context_size=spec.context_size,
        server_batch_size=spec.server_batch_size,
        server_ubatch_size=spec.server_ubatch_size,
        gpu_layers=spec.gpu_layers,
    )


def download_gate3_model(resolved: Gate3ResolvedModel, repo_root: Path) -> Path:
    from huggingface_hub import hf_hub_download
    destination = Path(resolved.destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = destination / ".holo-model.json"
    model_file = destination / resolved.file
    if destination.exists() and metadata_path.exists():
        metadata = _read_json(metadata_path)
        if (metadata.get("repo") == resolved.repo and metadata.get("revision") == resolved.revision
                and metadata.get("file") == resolved.file and model_file.exists()):
            return destination
        raise RuntimeError(f"destino existente contém outra revisão ou arquivo: {destination}")
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError(f"destino não vazio sem metadados verificáveis: {destination}")
    free = shutil.disk_usage(repo_root).free
    required = resolved.expected_size_bytes + MIN_FREE_MARGIN_BYTES
    if free < required:
        raise RuntimeError(f"espaço insuficiente: livre={free} necessário={required}")
    destination.mkdir(parents=True, exist_ok=True)
    downloaded = Path(hf_hub_download(
        repo_id=resolved.repo,
        filename=resolved.file,
        revision=resolved.revision,
        local_dir=str(destination),
    ))
    if not downloaded.exists():
        raise RuntimeError(f"download não produziu {resolved.file}")
    _atomic_json(metadata_path, {
        "schema_version": "1.0", "repo": resolved.repo, "revision": resolved.revision,
        "file": resolved.file, "expected_size_bytes": resolved.expected_size_bytes,
        "license": resolved.license, "gated": resolved.gated,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
    })
    return destination


def _failure(spec: Gate3ModelSpec, phase: str, exc: BaseException | None = None, **extra: Any) -> dict[str, Any]:
    payload = {
        "model_id": spec.id, "required": spec.required, "phase": phase,
        "error_type": extra.pop("error_type", None) or (type(exc).__name__ if exc else "Error"),
        "error_message": extra.pop("error_message", None) or (str(exc) if exc else "erro desconhecido"),
    }
    payload.update(extra)
    return payload


def _llama_server_identity() -> dict[str, Any]:
    explicit = os.environ.get("LLAMA_SERVER")
    candidates = [
        shutil.which(explicit) if explicit else None,
        explicit if explicit and Path(explicit).exists() else None,
        shutil.which("llama-server"),
        shutil.which("llama-server-cuda"),
    ]
    binary = next((str(path) for path in candidates if path), None)
    if binary is None:
        raise RuntimeError("llama-server não encontrado; defina LLAMA_SERVER para o binário estável")
    proc = subprocess.run([binary, "--version"], capture_output=True, text=True, check=False, timeout=30)
    return {
        "path": binary,
        "version": (proc.stdout or proc.stderr).strip(),
        "returncode": proc.returncode,
    }


def _run_model_worker(
    project_root: Path,
    repo_root: Path,
    resolved: Gate3ResolvedModel,
    spec: Gate3ModelSpec,
    model_path: Path,
    chunks: list[dict[str, Any]],
    queries: list[dict[str, Any]],
    prompts: dict[str, Any],
    device: str,
    batch_size: int,
    corpus_hash: str,
    timeout_seconds: int,
    system_info: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    raw_dir = project_root / "results" / "raw" / "gate3"
    raw_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{spec.id}-", dir=raw_dir) as tmp:
        request_path = Path(tmp) / "request.json"
        output_path = Path(tmp) / "result.json"
        _atomic_json(request_path, {
            "resolved": asdict(resolved), "spec": asdict(spec), "model_path": str(model_path),
            "chunks": chunks, "queries": queries, "prompts": prompts, "device": device,
            "batch_size": batch_size, "corpus_hash": corpus_hash, "repo_root": str(repo_root),
            "system_info": system_info,
        })
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "holo_benchmark.gate3_worker", "--request", str(request_path), "--output", str(output_path)],
                cwd=project_root, capture_output=True, text=True, timeout=timeout_seconds,
                check=False, env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired as exc:
            return None, _failure(spec, "benchmark_worker", error_type="WorkerTimeout",
                                  error_message=f"worker excedeu {timeout_seconds}s",
                                  stderr_tail=str(exc.stderr or "")[-12000:])
        stderr_tail = "\n".join(proc.stderr.splitlines()[-80:])
        if not output_path.exists():
            return None, _failure(spec, "benchmark_worker", error_type="WorkerProcessError",
                                  error_message=f"worker terminou com código {proc.returncode} sem resultado estruturado",
                                  returncode=proc.returncode, stderr_tail=stderr_tail)
        try:
            payload = _read_json(output_path)
        except Exception as exc:
            return None, _failure(spec, "benchmark_worker", exc, error_type="WorkerOutputError",
                                  returncode=proc.returncode, stderr_tail=stderr_tail)
        if payload.get("status") != "ok":
            error = payload.get("error") or {}
            return None, _failure(spec, "benchmark_worker",
                                  error_type=str(error.get("type") or "WorkerError"),
                                  error_message=str(error.get("message") or "worker falhou"),
                                  returncode=proc.returncode,
                                  stderr_tail=str(error.get("traceback") or stderr_tail)[-12000:])
        if proc.returncode != 0:
            return None, _failure(spec, "benchmark_worker", error_type="WorkerProtocolError",
                                  error_message=f"status ok com exit code {proc.returncode}",
                                  returncode=proc.returncode, stderr_tail=stderr_tail)
        return payload["result"], None


def _status_for_results(
    specs: Sequence[Gate3ModelSpec],
    results: Sequence[dict[str, Any]],
    failures: Sequence[dict[str, Any]],
    full_dataset: bool,
    full_model_set: bool,
    device: str,
) -> str:
    completed = {str(result["model"]["id"]) for result in results}
    required = {spec.id for spec in specs if spec.required}
    required_failed = {str(f["model_id"]) for f in failures if f.get("required", True)}
    if device == "cuda" and full_dataset and full_model_set and required.issubset(completed) and not required_failed:
        return "PASS"
    return "PARTIAL" if results else "BLOCKED"


_COMPARISON_METRICS = ("HitRate@1", "HitRate@10", "MRR@10", "nDCG@10", "hard_negative_error_rate")


def _baseline_comparisons(project_root: Path, specs: Sequence[Gate3ModelSpec], results: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    specs_by_id = {spec.id: spec for spec in specs}
    comparisons: list[dict[str, Any]] = []
    for result in results:
        spec = specs_by_id[result["model"]["id"]]
        if not spec.baseline_model_id:
            continue
        baseline_path = project_root / "results" / "gate2" / f"{spec.baseline_model_id}.json"
        if not baseline_path.exists():
            comparisons.append({"model_id": spec.id, "baseline_model_id": spec.baseline_model_id, "status": "MISSING_BASELINE"})
            continue
        baseline = _read_json(baseline_path)["metrics"]["summary"]
        current = result["metrics"]["summary"]
        comparisons.append({
            "model_id": spec.id,
            "baseline_model_id": spec.baseline_model_id,
            "status": "COMPARED",
            "deltas": {name: current[name] - baseline[name] for name in _COMPARISON_METRICS},
        })
    return comparisons


def _render_report(status: str, results: Sequence[dict[str, Any]], failures: Sequence[dict[str, Any]], corpus_hash: str, dry_run: bool, server: dict[str, Any] | None) -> str:
    lines = [
        "# GATE 3 REPORT", "", f"- modo: {'dry-run' if dry_run else 'execução'}",
        f"- resultado: {status}", f"- corpus SHA-256: `{corpus_hash}`",
        f"- llama-server: `{(server or {}).get('version') or 'indisponível'}`", "",
        "## Modelos", "",
        "| modelo | GGUF | quant | dimensão | HitRate@10 | MRR@10 | nDCG@10 | docs/s | consultas/s |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        model, metrics, runtime = result["model"], result["metrics"]["summary"], result["runtime"]
        lines.append(
            f"| {model['id']} | `{model['file']}` | {model['quantization']} | {model['actual_dimension']} | "
            f"{metrics['HitRate@10']:.6f} | {metrics['MRR@10']:.6f} | {metrics['nDCG@10']:.6f} | "
            f"{runtime['documents_per_second']} | {runtime['queries_per_second']} |"
        )
    if not results:
        lines.append("| nenhum | - | - | - | - | - | - | - | - |")
    lines += ["", "## Falhas e bloqueios"]
    lines += [f"- `{f['model_id']}`: {f['error_type']}: {f['error_message']}" for f in failures] or ["- nenhuma"]
    lines += ["", "Pesos e caches permanecem fora do Git. Gates 4 a 6 não foram executados.", ""]
    return "\n".join(lines)


def _write_outputs(project_root: Path, selected_ids: list[str], manifest: dict[str, Any], summary: dict[str, Any] | None, report: str) -> None:
    if not selected_ids:
        _atomic_json(project_root / "download_manifest_gate3.resolved.json", manifest)
        if summary is not None:
            _atomic_json(project_root / "results" / "gate3" / "summary.json", summary)
        (project_root / "GATE_3_REPORT.md").write_text(report, encoding="utf-8")
        return
    diagnostics = project_root / "results" / "gate3" / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    _atomic_json(diagnostics / "selected_models_manifest.json", manifest)
    if summary is not None:
        _atomic_json(diagnostics / "selected_models_summary.json", summary)
    (diagnostics / "GATE_3_SELECTED_MODELS_REPORT.md").write_text(report, encoding="utf-8")


def run_gate3(project_root: Path, repo_root: Path, args: Any) -> tuple[int, dict[str, Any]]:
    gate_status_path = project_root / "gate_status.json"
    gate_status = _read_json(gate_status_path)
    if any(gate_status.get(f"gate_{gate}") != "PASS" for gate in (0, 1, 2)):
        raise RuntimeError("Gates 0, 1 e 2 devem estar em PASS antes do Gate 3")
    hashes = _read_json(project_root / "data" / "holo_fake_scenes_v3" / "hashes.json")
    corpus_hash = str(hashes.get("combined_sha256") or "")
    review = hashes.get("semantic_review_summary") or {}
    if not corpus_hash or not review.get("complete") or review.get("errors") != []:
        raise RuntimeError("corpus congelado ou revisão semântica inválidos")

    selected_ids = [value.strip() for value in str(getattr(args, "models", "") or "").split(",") if value.strip()]
    specs = load_gate3_specs(project_root / "config" / "models.json", selected_ids or None)
    prompts = _read_json(project_root / "config" / "prompts.json")
    corpus_dir = project_root / "data" / "holo_fake_scenes_v3"
    chunks = [json.loads(line) for line in (corpus_dir / "corpus.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    queries = [json.loads(line) for line in (corpus_dir / "queries.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    chunks, queries, full_dataset = _select_dataset(chunks, queries, getattr(args, "max_documents", None), getattr(args, "max_queries", None))

    failures: list[dict[str, Any]] = []
    try:
        server = _llama_server_identity()
    except Exception as exc:
        server = None
        failures.extend(_failure(spec, "runtime", exc) for spec in specs)

    resolved_models: list[Gate3ResolvedModel] = []
    if server is not None:
        for spec in specs:
            try:
                resolved_models.append(resolve_gate3_model(spec, _ensure_destination(repo_root, spec.id)))
            except Exception as exc:
                failures.append(_failure(spec, "resolve", exc))

    free_bytes = shutil.disk_usage(repo_root).free
    download_bytes = sum(model.expected_size_bytes for model in resolved_models)
    required_bytes = download_bytes + MIN_FREE_MARGIN_BYTES
    if free_bytes < required_bytes:
        for spec in specs:
            if spec.id not in {f["model_id"] for f in failures}:
                failures.append(_failure(spec, "disk", error_type="InsufficientDiskSpace",
                                         error_message=f"livre={free_bytes} necessário={required_bytes}"))

    manifest = {
        "schema_version": "1.0", "gate": 3, "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus_sha256": corpus_hash, "llama_server": server,
        "disk_space": {"free_bytes": free_bytes, "download_bytes": download_bytes, "required_bytes": required_bytes},
        "models": [asdict(model) for model in resolved_models], "failures": failures,
    }
    if getattr(args, "dry_run", False):
        status = "READY" if not any(f.get("required", True) for f in failures) else "BLOCKED"
        report = _render_report(status, [], failures, corpus_hash, True, server)
        _write_outputs(project_root, selected_ids, manifest, None, report)
        if not selected_ids:
            gate_status.update({"gate_3": status, "updated_at": datetime.now(timezone.utc).isoformat(), "errors": failures})
            _atomic_json(gate_status_path, gate_status)
        return (0 if status == "READY" else 2), manifest

    device = _resolve_device(str(getattr(args, "device", "auto")))
    batch_size = int(getattr(args, "batch_size", 16))
    timeout_seconds = int(getattr(args, "model_timeout", 21600))
    system_info = _read_json(project_root / "system_info.json")
    results_dir = project_root / "results" / "gate3"
    results_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    specs_by_id = {spec.id: spec for spec in specs}
    for resolved in resolved_models:
        spec = specs_by_id[resolved.id]
        if resolved.gated:
            failures.append(_failure(spec, "access", error_type="GatedRepoSkipped", error_message=f"modelo gated: {resolved.repo}"))
            continue
        try:
            model_path = download_gate3_model(resolved, repo_root)
        except Exception as exc:
            failures.append(_failure(spec, "download", exc))
            continue
        result, worker_failure = _run_model_worker(
            project_root, repo_root, resolved, spec, model_path, chunks, queries, prompts,
            device, batch_size, corpus_hash, timeout_seconds, system_info,
        )
        if worker_failure:
            failures.append(worker_failure)
            continue
        assert result is not None
        _atomic_json(results_dir / f"{spec.id}.json", result)
        results.append(result)

    status = _status_for_results(specs, results, failures, full_dataset, not selected_ids, device)
    summary = {
        "schema_version": "1.0", "gate": 3, "status": status, "corpus_sha256": corpus_hash,
        "full_dataset": full_dataset, "device": device,
        "models_requested": [spec.id for spec in specs],
        "models_completed": [result["model"]["id"] for result in results],
        "failures": failures,
        "results": [{
            "model_id": result["model"]["id"], "revision": result["model"]["revision"],
            "file": result["model"]["file"], "dimension": result["model"]["actual_dimension"],
            "metrics": result["metrics"]["summary"], "runtime": result["runtime"],
        } for result in results],
        "baseline_comparisons": _baseline_comparisons(project_root, specs, results),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    report = _render_report(status, results, failures, corpus_hash, False, server)
    _write_outputs(project_root, selected_ids, manifest, summary, report)
    if not selected_ids:
        gate_status.pop("gates_3_to_6", None)
        gate_status.update({
            "gate_3": status, "gates_4_to_6": "BLOCKED_BY_DIRECTOR",
            "updated_at": datetime.now(timezone.utc).isoformat(), "errors": failures,
        })
        _atomic_json(gate_status_path, gate_status)
    return (0 if status == "PASS" else 2), summary


__all__ = [
    "Gate3ModelSpec", "Gate3ResolvedModel", "load_gate3_specs", "resolve_gate3_model",
    "download_gate3_model", "_status_for_results", "_baseline_comparisons", "run_gate3",
]
