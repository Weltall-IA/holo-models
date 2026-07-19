from __future__ import annotations

import gc
import hashlib
import json
import os
import shutil
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .metrics import DEFAULT_KS, evaluate_rankings


WEIGHT_SUFFIXES = {".safetensors", ".bin", ".pt", ".pth"}
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

        dimension = int(raw.get("dimension") or 0)
        if dimension <= 0:
            raise ValueError(f"dimensão inválida para {model_id}")
        specs.append(
            Gate2ModelSpec(
                id=model_id,
                repo=str(raw["repo"]),
                backend=str(raw.get("backend") or "sentence-transformers"),
                dimension=dimension,
                trust_remote_code=bool(raw.get("trust_remote_code", False)),
                enabled=True,
                mode=str(raw["mode"]) if raw.get("mode") else None,
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
    for sibling in getattr(info, "siblings", []) or []:
        size = getattr(sibling, "size", None)
        if isinstance(size, int) and size > 0:
            total_size += size
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
    )


def _ensure_destination(repo_root: Path, model_id: str) -> Path:
    base = (repo_root / "embed").resolve()
    destination = (base / model_id).resolve()
    if destination.parent != base:
        raise ValueError(f"destino inválido para modelo: {model_id}")
    return destination


def _download_margin_ok(
    repo_root: Path,
    expected_size_bytes: int,
) -> tuple[bool, int, int]:
    free_bytes = shutil.disk_usage(repo_root).free
    required_bytes = expected_size_bytes * 2 + MIN_FREE_MARGIN_BYTES
    return free_bytes >= required_bytes, free_bytes, required_bytes


def download_snapshot(resolved: ResolvedModel, repo_root: Path) -> Path:
    from huggingface_hub import snapshot_download

    destination = Path(resolved.destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = destination / ".holo-model.json"

    if destination.exists() and metadata_path.exists():
        metadata = _read_json(metadata_path)
        if (
            metadata.get("repo") == resolved.repo
            and metadata.get("revision") == resolved.revision
        ):
            return destination
        raise RuntimeError(
            f"destino existente contém outra revisão: {destination}"
        )
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError(
            f"destino não vazio sem metadados verificáveis: {destination}"
        )

    ok, free_bytes, required_bytes = _download_margin_ok(
        repo_root,
        resolved.expected_size_bytes,
    )
    if not ok:
        raise RuntimeError(
            "espaço insuficiente para download com margem temporária: "
            f"livre={free_bytes} necessário={required_bytes}"
        )

    # snapshot_download com HF_XET_DISABLE evita que erros 403
    # de modelos gated contaminem downloads subsequentes via Xet cache.
    old_xet = os.environ.pop("HF_XET_DISABLE", None)
    os.environ["HF_XET_DISABLE"] = "1"
    try:
        snapshot_download(
            repo_id=resolved.repo,
            revision=resolved.revision,
            local_dir=str(destination),
        )
    finally:
        if old_xet is None:
            os.environ.pop("HF_XET_DISABLE", None)
        else:
            os.environ["HF_XET_DISABLE"] = old_xet
    _atomic_json(
        metadata_path,
        {
            "schema_version": "1.0",
            "repo": resolved.repo,
            "revision": resolved.revision,
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
            files.append(
                {
                    "file": str(path.relative_to(model_path)),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    if not files:
        raise RuntimeError(f"nenhum arquivo de peso encontrado em {model_path}")
    return files


def _document_text(
    chunk: dict[str, Any],
    model_id: str,
    prompts: dict[str, Any],
) -> str:
    text = str(chunk["text"])
    if model_id == "embeddinggemma":
        template = str(
            prompts.get(
                "embeddinggemma_document",
                "title: {title_or_none} | text: {text}",
            )
        )
        return template.format(
            title_or_none=chunk.get("title") or "none",
            text=text,
        )
    return text


def _query_text(
    query: dict[str, Any],
    model_id: str,
    prompts: dict[str, Any],
) -> str:
    text = str(query["query"])
    if model_id == "qwen3_embedding_06":
        instruction = str(
            prompts.get(
                "qwen3_query_instruction",
                "Retrieve relevant passages for the query.",
            )
        )
        return f"Instruct: {instruction}\nQuery: {text}"
    return text


def _normalize_rows(matrix: Any) -> Any:
    import numpy as np

    array = np.asarray(matrix, dtype=np.float32)
    if array.ndim != 2:
        raise ValueError(f"matriz de embeddings inválida: shape={array.shape}")
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("embedding com norma zero")
    return array / norms


def _encode(
    model: Any,
    texts: Sequence[str],
    kind: str,
    spec: Gate2ModelSpec,
    batch_size: int,
) -> Any:
    kwargs = {
        "batch_size": batch_size,
        "show_progress_bar": True,
        "convert_to_numpy": True,
        "normalize_embeddings": True,
    }

    if spec.id in {"embeddinggemma", "voyage4_nano"}:
        method = getattr(model, f"encode_{kind}", None)
        if callable(method):
            try:
                return method(list(texts), **kwargs)
            except TypeError:
                reduced = dict(kwargs)
                reduced.pop("normalize_embeddings", None)
                return method(list(texts), **reduced)

    return model.encode(list(texts), **kwargs)


def _load_sentence_transformer(
    model_path: Path,
    spec: Gate2ModelSpec,
    device: str,
) -> Any:
    from sentence_transformers import SentenceTransformer

    kwargs: dict[str, Any] = {
        "trust_remote_code": spec.trust_remote_code,
        "device": device,
    }
    if spec.id == "voyage4_nano":
        kwargs["truncate_dim"] = spec.dimension
    return SentenceTransformer(str(model_path), **kwargs)


def _rankings_from_embeddings(
    document_embeddings: Any,
    query_embeddings: Any,
    chunk_ids: Sequence[str],
) -> list[list[str]]:
    import numpy as np

    documents = _normalize_rows(document_embeddings)
    queries = _normalize_rows(query_embeddings)
    scores = queries @ documents.T
    order = np.argsort(-scores, axis=1, kind="stable")
    return [[chunk_ids[int(index)] for index in row] for row in order]


def _select_dataset(
    chunks: list[dict[str, Any]],
    queries: list[dict[str, Any]],
    max_documents: int | None,
    max_queries: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    full = max_documents is None and max_queries is None
    selected_chunks = chunks[:max_documents] if max_documents else chunks
    selected_ids = {chunk["chunk_id"] for chunk in selected_chunks}
    eligible_queries = [
        query
        for query in queries
        if set(query.get("relevant_chunk_ids") or []).issubset(selected_ids)
    ]
    selected_queries = (
        eligible_queries[:max_queries] if max_queries else eligible_queries
    )
    if not selected_chunks or not selected_queries:
        raise ValueError("recorte não contém documentos e consultas avaliáveis")
    return selected_chunks, selected_queries, full


def _peak_vram_bytes(device: str) -> int | None:
    if device != "cuda":
        return None
    try:
        import torch

        return int(torch.cuda.max_memory_allocated())
    except Exception:
        return None


def _reset_peak_vram(device: str) -> None:
    if device == "cuda":
        try:
            import torch

            torch.cuda.reset_peak_memory_stats()
        except Exception:
            pass


def _release_model(model: Any, device: str) -> None:
    del model
    gc.collect()
    if device == "cuda":
        try:
            import torch

            torch.cuda.empty_cache()
        except Exception:
            pass


def _model_dtype(model: Any) -> str | None:
    try:
        parameter = next(model.parameters())
        return str(parameter.dtype)
    except Exception:
        return None


def benchmark_model(
    resolved: ResolvedModel,
    spec: Gate2ModelSpec,
    model_path: Path,
    chunks: list[dict[str, Any]],
    queries: list[dict[str, Any]],
    prompts: dict[str, Any],
    device: str,
    batch_size: int,
    corpus_hash: str,
) -> dict[str, Any]:
    chunk_ids = [str(chunk["chunk_id"]) for chunk in chunks]
    document_texts = [
        _document_text(chunk, spec.id, prompts)
        for chunk in chunks
    ]
    query_texts = [
        _query_text(query, spec.id, prompts)
        for query in queries
    ]

    started = time.monotonic()
    _reset_peak_vram(device)
    model = _load_sentence_transformer(model_path, spec, device)
    model_dtype = _model_dtype(model)
    load_seconds = time.monotonic() - started

    encode_documents_started = time.monotonic()
    document_embeddings = _encode(
        model,
        document_texts,
        "document",
        spec,
        batch_size,
    )
    document_seconds = time.monotonic() - encode_documents_started

    encode_queries_started = time.monotonic()
    query_embeddings = _encode(
        model,
        query_texts,
        "query",
        spec,
        batch_size,
    )
    query_seconds = time.monotonic() - encode_queries_started

    rankings = _rankings_from_embeddings(
        document_embeddings,
        query_embeddings,
        chunk_ids,
    )
    evaluation = evaluate_rankings(queries, rankings, DEFAULT_KS)
    actual_dimension = int(_normalize_rows(document_embeddings).shape[1])
    if actual_dimension != spec.dimension:
        raise RuntimeError(
            f"dimensão divergente para {spec.id}: "
            f"esperada={spec.dimension} obtida={actual_dimension}"
        )
    peak_vram = _peak_vram_bytes(device)

    result = {
        "schema_version": "1.0",
        "gate": 2,
        "model": {
            "id": spec.id,
            "repo": spec.repo,
            "revision": resolved.revision,
            "backend": spec.backend,
            "mode": spec.mode,
            "configured_dimension": spec.dimension,
            "actual_dimension": actual_dimension,
            "trust_remote_code": spec.trust_remote_code,
            "license": resolved.license,
            "gated": resolved.gated,
            "weight_files": hash_weight_files(model_path),
        },
        "dataset": {
            "corpus_version": "holo_fake_scenes_v3",
            "combined_sha256": corpus_hash,
            "documents": len(chunks),
            "queries": len(queries),
        },
        "runtime": {
            "device": device,
            "dtype": model_dtype,
            "normalization": "l2",
            "batch_size": batch_size,
            "load_seconds": round(load_seconds, 4),
            "document_encode_seconds": round(document_seconds, 4),
            "query_encode_seconds": round(query_seconds, 4),
            "documents_per_second": (
                round(len(chunks) / document_seconds, 4)
                if document_seconds
                else None
            ),
            "queries_per_second": (
                round(len(queries) / query_seconds, 4)
                if query_seconds
                else None
            ),
            "peak_vram_bytes": peak_vram,
        },
        "metrics": evaluation,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    _release_model(model, device)
    return result


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


def _render_report(
    status: str,
    results: Sequence[dict[str, Any]],
    failures: Sequence[dict[str, Any]],
    corpus_hash: str,
    dry_run: bool,
) -> str:
    lines = [
        "# GATE 2 REPORT",
        "",
        f"- modo: {'dry-run' if dry_run else 'execução'}",
        f"- resultado: {status}",
        f"- corpus SHA-256: `{corpus_hash}`",
        "",
        "## Modelos",
        "",
        "| modelo | revisão | dimensão | HitRate@10 | MRR@10 | nDCG@10 | docs/s | consultas/s |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        model = result["model"]
        metrics = result["metrics"]["summary"]
        runtime = result["runtime"]
        lines.append(
            "| {id} | `{rev}` | {dim} | {hit:.6f} | {mrr:.6f} | "
            "{ndcg:.6f} | {docs} | {queries} |".format(
                id=model["id"],
                rev=model["revision"][:12],
                dim=model["actual_dimension"],
                hit=metrics["HitRate@10"],
                mrr=metrics["MRR@10"],
                ndcg=metrics["nDCG@10"],
                docs=runtime["documents_per_second"],
                queries=runtime["queries_per_second"],
            )
        )
    if not results:
        lines.append("| nenhum | - | - | - | - | - | - | - |")

    lines.extend(["", "## Falhas"])
    if failures:
        for failure in failures:
            lines.append(
                f"- `{failure['model_id']}`: {failure['error_type']}: "
                f"{failure['error_message']}"
            )
    else:
        lines.append("- nenhuma")

    lines.extend(
        [
            "",
            "Nenhuma API paga foi chamada. Pesos e caches permanecem fora do Git.",
            "",
        ]
    )
    return "\n".join(lines)


def run_gate2(
    project_root: Path,
    repo_root: Path,
    args: Any,
) -> tuple[int, dict[str, Any]]:
    gate_status_path = project_root / "gate_status.json"
    gate_status = _read_json(gate_status_path)
    if gate_status.get("gate_0") != "PASS" or gate_status.get("gate_1") != "PASS":
        raise RuntimeError("Gates 0 e 1 devem estar em PASS antes do Gate 2")

    hashes_path = (
        project_root / "data" / "holo_fake_scenes_v3" / "hashes.json"
    )
    hashes = _read_json(hashes_path)
    corpus_hash = str(hashes.get("combined_sha256") or "")
    review = hashes.get("semantic_review_summary") or {}
    if (
        not corpus_hash
        or not review.get("complete")
        or review.get("errors") != []
    ):
        raise RuntimeError("corpus congelado ou revisão semântica inválidos")

    selected_ids = [
        value.strip()
        for value in str(getattr(args, "models", "") or "").split(",")
        if value.strip()
    ]
    full_model_set = not selected_ids
    specs = load_gate2_specs(
        project_root / "config" / "models.json",
        selected_ids or None,
    )
    prompts = _read_json(project_root / "config" / "prompts.json")
    chunks = [
        json.loads(line)
        for line in (
            project_root / "data" / "holo_fake_scenes_v3" / "corpus.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    queries = [
        json.loads(line)
        for line in (
            project_root / "data" / "holo_fake_scenes_v3" / "queries.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    chunks, queries, full_dataset = _select_dataset(
        chunks,
        queries,
        getattr(args, "max_documents", None),
        getattr(args, "max_queries", None),
    )

    resolved_models: list[ResolvedModel] = []
    failures: list[dict[str, Any]] = []
    for spec in specs:
        try:
            destination = _ensure_destination(repo_root, spec.id)
            resolved_models.append(resolve_model(spec, destination))
        except Exception as exc:
            failures.append(
                {
                    "model_id": spec.id,
                    "phase": "resolve",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )

    manifest = {
        "schema_version": "1.0",
        "gate": 2,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus_sha256": corpus_hash,
        "models": [asdict(model) for model in resolved_models],
        "failures": failures,
    }
    _atomic_json(
        project_root / "download_manifest.resolved.json",
        manifest,
    )

    if getattr(args, "dry_run", False):
        status = (
            "READY"
            if not failures and len(resolved_models) == len(specs)
            else "BLOCKED"
        )
        report = _render_report(status, [], failures, corpus_hash, True)
        (project_root / "GATE_2_REPORT.md").write_text(
            report,
            encoding="utf-8",
        )
        gate_status["gate_2"] = status
        gate_status["updated_at"] = datetime.now(timezone.utc).isoformat()
        gate_status["errors"] = failures
        _atomic_json(gate_status_path, gate_status)
        return (0 if status == "READY" else 2), manifest

    device = _resolve_device(str(getattr(args, "device", "auto")))
    batch_size = int(getattr(args, "batch_size", 16))
    results_dir = project_root / "results" / "gate2"
    results_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    specs_by_id = {spec.id: spec for spec in specs}
    # Filtra modelos gated antes de qualquer download para evitar que o
    # cliente Xet do Hugging Face Hub propague erros 403 entre chamadas.
    filtered: list[ResolvedModel] = []
    for r in resolved_models:
        if r.gated and isinstance(r.gated, str):
            failures.append({
                "model_id": r.id,
                "phase": "download_or_benchmark",
                "error_type": "GatedRepoSkipped",
                "error_message": (
                    f"modelo gated ({r.gated}) sem credenciais de acesso "
                    f"válidas para {r.repo}"
                ),
            })
        else:
            filtered.append(r)
    resolved_models = filtered
    for resolved in resolved_models:
        spec = specs_by_id[resolved.id]
        try:
            model_path = download_snapshot(resolved, repo_root)
            result = benchmark_model(
                resolved=resolved,
                spec=spec,
                model_path=model_path,
                chunks=chunks,
                queries=queries,
                prompts=prompts,
                device=device,
                batch_size=batch_size,
                corpus_hash=corpus_hash,
            )
            _atomic_json(results_dir / f"{spec.id}.json", result)
            results.append(result)
        except Exception as exc:
            failures.append(
                {
                    "model_id": spec.id,
                    "phase": "download_or_benchmark",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
            # Após falha de GPU, tenta restaurar o estado CUDA para
            # evitar que o erro se propague para o próximo modelo.
            try:
                import torch
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
            except Exception:
                pass

    all_models_completed = len(results) == len(specs) and not failures
    status = (
        "PASS"
        if all_models_completed and full_dataset and full_model_set
        else "PARTIAL"
        if results
        else "BLOCKED"
    )
    summary = {
        "schema_version": "1.0",
        "gate": 2,
        "status": status,
        "corpus_sha256": corpus_hash,
        "full_dataset": full_dataset,
        "models_requested": [spec.id for spec in specs],
        "models_completed": [result["model"]["id"] for result in results],
        "failures": failures,
        "results": [
            {
                "model_id": result["model"]["id"],
                "revision": result["model"]["revision"],
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
    (project_root / "GATE_2_REPORT.md").write_text(
        report,
        encoding="utf-8",
    )

    gate_status["gate_2"] = status
    gate_status["gates_3_to_6"] = "BLOCKED_BY_DIRECTOR"
    gate_status.pop("gates_2_to_6", None)
    gate_status["updated_at"] = datetime.now(timezone.utc).isoformat()
    gate_status["errors"] = failures
    _atomic_json(gate_status_path, gate_status)
    return (0 if status == "PASS" else 2), summary
