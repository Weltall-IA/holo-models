from __future__ import annotations

import hashlib
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

WEIGHT_SUFFIXES = {".safetensors", ".bin", ".pt", ".pth", ".gguf"}
MIN_FREE_MARGIN_BYTES = 5 * 1024**3


@dataclass(frozen=True)
class Gate2ModelSpec:
    id: str
    repo: str
    backend: str
    dimension: int
    trust_remote_code: bool = False
    enabled: bool = True
    mode: str | None = None
    required: bool = True
    file: str | None = None
    prompt_profile: str | None = None
    encode_api: str | None = None
    pooling: str | None = None


@dataclass(frozen=True)
class ResolvedModel:
    id: str
    repo: str
    revision: str
    expected_size_bytes: int
    license: str | None
    gated: bool | str | None
    destination: str
    trust_remote_code: bool
    backend: str
    dimension: int
    required: bool = True
    file: str | None = None
    prompt_profile: str | None = None
    encode_api: str | None = None
    pooling: str | None = None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def load_gate2_specs(
    models_path: Path,
    selected_ids: Sequence[str] | None = None,
) -> list[Gate2ModelSpec]:
    payload = _read_json(models_path)
    selected = set(selected_ids or [])
    specs: list[Gate2ModelSpec] = []
    known_ids: set[str] = set()

    for raw in payload.get("models", []):
        model_id = str(raw.get("id") or "")
        if not model_id:
            raise ValueError("modelo sem id em config/models.json")
        if model_id in known_ids:
            raise ValueError(f"id de modelo duplicado: {model_id}")
        known_ids.add(model_id)

        if raw.get("gate") != 2 or not raw.get("enabled", False):
            continue
        if selected and model_id not in selected:
            continue

        backend = str(raw.get("backend") or "sentence-transformers")
        dimension = int(raw.get("dimension") or 0)
        if backend == "sentence-transformers" and dimension <= 0:
            raise ValueError(f"dimensão inválida para {model_id}")
        if backend not in {"sentence-transformers", "llama.cpp"}:
            raise ValueError(f"backend inválido para {model_id}: {backend}")
        if backend == "llama.cpp" and not raw.get("file"):
            raise ValueError(f"arquivo GGUF ausente para {model_id}")

        specs.append(
            Gate2ModelSpec(
                id=model_id,
                repo=str(raw["repo"]),
                backend=backend,
                dimension=dimension,
                trust_remote_code=bool(raw.get("trust_remote_code", False)),
                enabled=True,
                mode=str(raw["mode"]) if raw.get("mode") else None,
                required=bool(raw.get("required", True)),
                file=str(raw["file"]) if raw.get("file") else None,
                prompt_profile=str(raw["prompt_profile"]) if raw.get("prompt_profile") else None,
                encode_api=str(raw["encode_api"]) if raw.get("encode_api") else None,
                pooling=str(raw["pooling"]) if raw.get("pooling") else None,
            )
        )

    missing = selected - {spec.id for spec in specs}
    if missing:
        raise ValueError(
            "modelos solicitados não habilitados no Gate 2: "
            + ", ".join(sorted(missing))
        )
    if not specs:
        raise ValueError("nenhum modelo habilitado para o Gate 2")
    return specs


def _card_license(card_data: Any) -> str | None:
    if card_data is None:
        return None
    value = getattr(card_data, "license", None)
    if value:
        return str(value)
    if isinstance(card_data, dict):
        raw = card_data.get("license")
        return str(raw) if raw else None
    to_dict = getattr(card_data, "to_dict", None)
    if callable(to_dict):
        raw = to_dict().get("license")
        return str(raw) if raw else None
    return None


def resolve_model(
    spec: Gate2ModelSpec,
    destination: Path,
    api: Any | None = None,
) -> ResolvedModel:
    if api is None:
        from huggingface_hub import HfApi

        api = HfApi()
    info = api.model_info(spec.repo, files_metadata=True)
    revision = str(getattr(info, "sha", "") or "")
    if len(revision) < 7:
        raise RuntimeError(f"revisão não resolvida para {spec.repo}")

    total_size = 0
    matched_file = False
    for sibling in getattr(info, "siblings", []) or []:
        name = str(getattr(sibling, "rfilename", "") or "")
        if spec.file and name != spec.file:
            continue
        if spec.file and name == spec.file:
            matched_file = True
        size = getattr(sibling, "size", None)
        if isinstance(size, int) and size > 0:
            total_size += size
    if spec.file and not matched_file:
        raise RuntimeError(f"arquivo {spec.file} não encontrado em {spec.repo}")
    if total_size <= 0:
        raise RuntimeError(f"tamanho não resolvido para {spec.repo}")

    return ResolvedModel(
        id=spec.id,
        repo=spec.repo,
        revision=revision,
        expected_size_bytes=total_size,
        license=_card_license(getattr(info, "card_data", None)),
        gated=getattr(info, "gated", None),
        destination=str(destination),
        trust_remote_code=spec.trust_remote_code,
        backend=spec.backend,
        dimension=spec.dimension,
        required=spec.required,
        file=spec.file,
        prompt_profile=spec.prompt_profile,
        encode_api=spec.encode_api,
        pooling=spec.pooling,
    )


def _ensure_destination(repo_root: Path, model_id: str) -> Path:
    base = (repo_root / "embed").resolve()
    destination = (base / model_id).resolve()
    if destination.parent != base:
        raise ValueError(f"destino inválido para modelo: {model_id}")
    return destination


def _download_margin_ok(repo_root: Path, expected_size_bytes: int) -> tuple[bool, int, int]:
    free_bytes = shutil.disk_usage(repo_root).free
    required_bytes = expected_size_bytes * 2 + MIN_FREE_MARGIN_BYTES
    return free_bytes >= required_bytes, free_bytes, required_bytes


def download_snapshot(resolved: ResolvedModel, repo_root: Path) -> Path:
    from huggingface_hub import hf_hub_download, snapshot_download

    destination = Path(resolved.destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = destination / ".holo-model.json"

    if destination.exists() and metadata_path.exists():
        metadata = _read_json(metadata_path)
        if metadata.get("repo") == resolved.repo and metadata.get("revision") == resolved.revision and metadata.get("file") == resolved.file:
            return destination
        raise RuntimeError(f"destino existente contém outra revisão: {destination}")
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError(f"destino não vazio sem metadados verificáveis: {destination}")

    ok, free_bytes, required_bytes = _download_margin_ok(repo_root, resolved.expected_size_bytes)
    if not ok:
        raise RuntimeError(
            "espaço insuficiente para download com margem temporária: "
            f"livre={free_bytes} necessário={required_bytes}"
        )

    destination.mkdir(parents=True, exist_ok=True)
    if resolved.file:
        downloaded = Path(
            hf_hub_download(
                repo_id=resolved.repo,
                filename=resolved.file,
                revision=resolved.revision,
                local_dir=str(destination),
            )
        )
        if not downloaded.exists():
            raise RuntimeError(f"download não produziu {resolved.file}")
    else:
        snapshot_download(
            repo_id=resolved.repo,
            revision=resolved.revision,
            local_dir=str(destination),
        )

    _atomic_json(
        metadata_path,
        {
            "schema_version": "1.0",
            "repo": resolved.repo,
            "revision": resolved.revision,
            "file": resolved.file,
            "expected_size_bytes": resolved.expected_size_bytes,
            "license": resolved.license,
            "gated": resolved.gated,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return destination


def sha256_file(path: Path, block_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def hash_weight_files(model_path: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for path in sorted(model_path.rglob("*")):
        if path.is_file() and path.suffix.lower() in WEIGHT_SUFFIXES:
            files.append({"file": str(path.relative_to(model_path)), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    if not files:
        raise RuntimeError(f"nenhum arquivo de peso encontrado em {model_path}")
    return files


def _document_text(chunk: dict[str, Any], model_id: str, prompts: dict[str, Any], prompt_profile: str | None = None) -> str:
    text = str(chunk["text"])
    profile = prompt_profile or model_id
    if profile in {"embeddinggemma", "colibri"}:
        template = str(prompts.get("embeddinggemma_document", "title: {title_or_none} | text: {text}"))
        return template.format(title_or_none=chunk.get("title") or "none", text=text)
    return text


def _query_text(query: dict[str, Any], model_id: str, prompts: dict[str, Any], prompt_profile: str | None = None) -> str:
    text = str(query["query"])
    profile = prompt_profile or model_id
    if profile in {"qwen3", "e5_instruct"} or model_id == "qwen3_embedding_06":
        key = "e5_query_instruction" if profile == "e5_instruct" else "qwen3_query_instruction"
        instruction = str(prompts.get(key, "Retrieve scenes in Brazilian Portuguese that match the query."))
        return f"Instruct: {instruction}\nQuery: {text}"
    if profile in {"embeddinggemma", "colibri"}:
        template = str(prompts.get("embeddinggemma_query", "task: search result | query: {query}"))
        return template.format(query=text)
    return text


def _select_dataset(chunks: list[dict[str, Any]], queries: list[dict[str, Any]], max_documents: int | None, max_queries: int | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    full = max_documents is None and max_queries is None
    selected_chunks = chunks[:max_documents] if max_documents else chunks
    selected_ids = {chunk["chunk_id"] for chunk in selected_chunks}
    eligible_queries = [query for query in queries if set(query.get("relevant_chunk_ids") or []).issubset(selected_ids)]
    selected_queries = eligible_queries[:max_queries] if max_queries else eligible_queries
    if not selected_chunks or not selected_queries:
        raise ValueError("recorte não contém documentos e consultas avaliáveis")
    return selected_chunks, selected_queries, full


def _resolve_device(requested: str) -> str:
    if requested in {"cpu", "cuda"}:
        if requested == "cuda":
            import torch
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA solicitada, mas indisponível no PyTorch")
        return requested
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _failure(spec: Gate2ModelSpec, phase: str, exc: BaseException | None = None, *, error_type: str | None = None, error_message: str | None = None, returncode: int | None = None, stderr_tail: str | None = None) -> dict[str, Any]:
    return {
        "model_id": spec.id,
        "required": spec.required,
        "phase": phase,
        "error_type": error_type or (type(exc).__name__ if exc else "Error"),
        "error_message": error_message or (str(exc) if exc else "erro desconhecido"),
        "returncode": returncode,
        "stderr_tail": stderr_tail,
    }


def _run_model_worker(project_root: Path, repo_root: Path, resolved: ResolvedModel, spec: Gate2ModelSpec, model_path: Path, chunks: list[dict[str, Any]], queries: list[dict[str, Any]], prompts: dict[str, Any], device: str, batch_size: int, corpus_hash: str, timeout_seconds: int) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    raw_dir = project_root / "results" / "raw" / "gate2"
    raw_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{spec.id}-", dir=raw_dir) as tmp:
        work = Path(tmp)
        request_path = work / "request.json"
        output_path = work / "result.json"
        _atomic_json(
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
        proc = subprocess.run(
            [sys.executable, "-m", "holo_benchmark.gate2_worker", "--request", str(request_path), "--output", str(output_path)],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=os.environ.copy(),
        )
        stderr_tail = "\n".join(proc.stderr.splitlines()[-80:])
        if proc.returncode != 0 or not output_path.exists():
            return None, _failure(
                spec,
                "benchmark_worker",
                error_type="WorkerProcessError",
                error_message=f"worker terminou com código {proc.returncode}; o próximo modelo continuará em processo limpo",
                returncode=proc.returncode,
                stderr_tail=stderr_tail,
            )
        payload = _read_json(output_path)
        if payload.get("status") != "ok":
            error = payload.get("error") or {}
            return None, _failure(
                spec,
                "benchmark_worker",
                error_type=str(error.get("type") or "WorkerError"),
                error_message=str(error.get("message") or "worker falhou"),
                returncode=proc.returncode,
                stderr_tail=str(error.get("traceback") or stderr_tail)[-12000:],
            )
        return payload["result"], None


def _status_for_results(specs: Sequence[Gate2ModelSpec], results: Sequence[dict[str, Any]], failures: Sequence[dict[str, Any]], full_dataset: bool, full_model_set: bool) -> str:
    completed = {str(result["model"]["id"]) for result in results}
    required_ids = {spec.id for spec in specs if spec.required}
    required_failed = {str(failure["model_id"]) for failure in failures if bool(failure.get("required", True))}
    if full_dataset and full_model_set and required_ids.issubset(completed) and not required_failed:
        return "PASS"
    if results:
        return "PARTIAL"
    return "BLOCKED"


def _render_report(status: str, results: Sequence[dict[str, Any]], failures: Sequence[dict[str, Any]], corpus_hash: str, dry_run: bool) -> str:
    lines = [
        "# GATE 2 REPORT",
        "",
        f"- modo: {'dry-run' if dry_run else 'execução'}",
        f"- resultado: {status}",
        f"- corpus SHA-256: `{corpus_hash}`",
        "",
        "## Modelos",
        "",
        "| modelo | backend | revisão | dimensão | HitRate@10 | MRR@10 | nDCG@10 | docs/s | consultas/s |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        model = result["model"]
        metrics = result["metrics"]["summary"]
        runtime = result["runtime"]
        lines.append(
            "| {id} | {backend} | `{rev}` | {dim} | {hit:.6f} | {mrr:.6f} | {ndcg:.6f} | {docs} | {queries} |".format(
                id=model["id"], backend=model["backend"], rev=model["revision"][:12], dim=model["actual_dimension"], hit=metrics["HitRate@10"], mrr=metrics["MRR@10"], ndcg=metrics["nDCG@10"], docs=runtime["documents_per_second"], queries=runtime["queries_per_second"]
            )
        )
    if not results:
        lines.append("| nenhum | - | - | - | - | - | - | - | - |")
    lines.extend(["", "## Falhas e bloqueios"])
    if failures:
        for failure in failures:
            requirement = "obrigatório" if failure.get("required", True) else "opcional"
            lines.append(f"- `{failure['model_id']}` ({requirement}): {failure['error_type']}: {failure['error_message']}")
    else:
        lines.append("- nenhuma")
    lines.extend([
        "",
        "Cada modelo foi executado em processo isolado. Uma falha CUDA não contamina os modelos seguintes.",
        "Nenhuma API paga foi chamada. Pesos e caches permanecem fora do Git.",
        "",
    ])
    return "\n".join(lines)


def run_gate2(project_root: Path, repo_root: Path, args: Any) -> tuple[int, dict[str, Any]]:
    gate_status_path = project_root / "gate_status.json"
    gate_status = _read_json(gate_status_path)
    if gate_status.get("gate_0") != "PASS" or gate_status.get("gate_1") != "PASS":
        raise RuntimeError("Gates 0 e 1 devem estar em PASS antes do Gate 2")

    hashes_path = project_root / "data" / "holo_fake_scenes_v3" / "hashes.json"
    hashes = _read_json(hashes_path)
    corpus_hash = str(hashes.get("combined_sha256") or "")
    review = hashes.get("semantic_review_summary") or {}
    if not corpus_hash or not review.get("complete") or review.get("errors") != []:
        raise RuntimeError("corpus congelado ou revisão semântica inválidos")

    selected_ids = [value.strip() for value in str(getattr(args, "models", "") or "").split(",") if value.strip()]
    full_model_set = not selected_ids
    specs = load_gate2_specs(project_root / "config" / "models.json", selected_ids or None)
    prompts = _read_json(project_root / "config" / "prompts.json")
    chunks = [json.loads(line) for line in (project_root / "data" / "holo_fake_scenes_v3" / "corpus.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    queries = [json.loads(line) for line in (project_root / "data" / "holo_fake_scenes_v3" / "queries.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    chunks, queries, full_dataset = _select_dataset(chunks, queries, getattr(args, "max_documents", None), getattr(args, "max_queries", None))

    resolved_models: list[ResolvedModel] = []
    failures: list[dict[str, Any]] = []
    for spec in specs:
        try:
            destination = _ensure_destination(repo_root, spec.id)
            resolved_models.append(resolve_model(spec, destination))
        except Exception as exc:
            failures.append(_failure(spec, "resolve", exc))

    manifest = {
        "schema_version": "1.1",
        "gate": 2,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus_sha256": corpus_hash,
        "models": [asdict(model) for model in resolved_models],
        "failures": failures,
    }
    _atomic_json(project_root / "download_manifest.resolved.json", manifest)

    if getattr(args, "dry_run", False):
        required_failures = [failure for failure in failures if failure.get("required", True)]
        status = "READY" if not required_failures else "BLOCKED"
        report = _render_report(status, [], failures, corpus_hash, True)
        (project_root / "GATE_2_REPORT.md").write_text(report, encoding="utf-8")
        gate_status["gate_2"] = status
        gate_status["updated_at"] = datetime.now(timezone.utc).isoformat()
        gate_status["errors"] = failures
        _atomic_json(gate_status_path, gate_status)
        return (0 if status == "READY" else 2), manifest

    device = _resolve_device(str(getattr(args, "device", "auto")))
    batch_size = int(getattr(args, "batch_size", 16))
    timeout_seconds = int(getattr(args, "model_timeout", 21600))
    results_dir = project_root / "results" / "gate2"
    results_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    specs_by_id = {spec.id: spec for spec in specs}

    for resolved in resolved_models:
        spec = specs_by_id[resolved.id]
        if resolved.gated:
            failures.append(_failure(spec, "access", error_type="GatedRepoSkipped", error_message=f"modelo gated sem acesso válido: {resolved.repo}"))
            continue
        try:
            model_path = download_snapshot(resolved, repo_root)
        except Exception as exc:
            failures.append(_failure(spec, "download", exc))
            continue
        result, worker_failure = _run_model_worker(
            project_root=project_root,
            repo_root=repo_root,
            resolved=resolved,
            spec=spec,
            model_path=model_path,
            chunks=chunks,
            queries=queries,
            prompts=prompts,
            device=device,
            batch_size=batch_size,
            corpus_hash=corpus_hash,
            timeout_seconds=timeout_seconds,
        )
        if worker_failure:
            failures.append(worker_failure)
            continue
        assert result is not None
        _atomic_json(results_dir / f"{spec.id}.json", result)
        results.append(result)

    status = _status_for_results(specs, results, failures, full_dataset=full_dataset, full_model_set=full_model_set)
    summary = {
        "schema_version": "1.1",
        "gate": 2,
        "status": status,
        "corpus_sha256": corpus_hash,
        "full_dataset": full_dataset,
        "models_requested": [spec.id for spec in specs],
        "required_models": [spec.id for spec in specs if spec.required],
        "optional_models": [spec.id for spec in specs if not spec.required],
        "models_completed": [result["model"]["id"] for result in results],
        "failures": failures,
        "results": [
            {
                "model_id": result["model"]["id"],
                "revision": result["model"]["revision"],
                "backend": result["model"]["backend"],
                "dimension": result["model"]["actual_dimension"],
                "metrics": result["metrics"]["summary"],
                "runtime": result["runtime"],
            }
            for result in results
        ],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _atomic_json(results_dir / "summary.json", summary)
    report = _render_report(status, results, failures, corpus_hash, False)
    (project_root / "GATE_2_REPORT.md").write_text(report, encoding="utf-8")
    gate_status["gate_2"] = status
    gate_status["gates_3_to_6"] = "BLOCKED_BY_DIRECTOR"
    gate_status.pop("gates_2_to_6", None)
    gate_status["updated_at"] = datetime.now(timezone.utc).isoformat()
    gate_status["errors"] = failures
    _atomic_json(gate_status_path, gate_status)
    return (0 if status == "PASS" else 2), summary


__all__ = [
    "Gate2ModelSpec",
    "ResolvedModel",
    "load_gate2_specs",
    "resolve_model",
    "download_snapshot",
    "hash_weight_files",
    "_document_text",
    "_query_text",
    "_ensure_destination",
    "_select_dataset",
    "_status_for_results",
    "run_gate2",
]
