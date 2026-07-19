from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

WEIGHT_SUFFIXES = {".gguf", ".safetensors", ".bin", ".onnx", ".pt", ".pth", ".ckpt", ".engine"}
DEFAULT_CATEGORY_DIRS = ("embed", "text", "audio", "video", "image", "standalone")
EMBED_TOKENS = (
    "embed", "embedding", "bge", "e5-", "e5_", "gte", "colibri", "voyage",
    "jina-embeddings", "nomic-embed", "mxbai-embed", "minilm", "stella",
    "snowflake-arctic-embed", "multilingual-e5",
)
RERANK_TOKENS = ("rerank", "cross-encoder", "bge-reranker", "qwen3-reranker")
ASR_TOKENS = ("whisper", "wav2vec", "parakeet", "asr")
IMAGE_TOKENS = ("clip", "siglip", "dinov2", "image", "vision")
VIDEO_TOKENS = ("video", "videomae")
LEGACY_TOKENS = ("deprecated", "obsolete", "legacy")


@dataclass(frozen=True)
class DiscoveredModel:
    id: str
    source: str
    category: str
    runtime: str
    format: str
    path: str | None
    canonical_path: str | None
    size_bytes: int | None
    benchmark_eligible: bool
    healthcheck_eligible: bool
    legacy: bool
    reason: str
    coverage_status: str
    matched_result: str | None
    metadata: dict[str, Any]


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _slug(value: str) -> str:
    value = value.strip().replace("\\", "/")
    value = re.sub(r"[^A-Za-z0-9._/-]+", "-", value)
    value = value.strip("-/")
    return value or "unknown-model"


def _classify(name: str, hinted_category: str | None = None) -> str:
    lower = name.lower()
    if hinted_category in {"embed", "text", "audio", "video", "image"}:
        if hinted_category == "text" and any(token in lower for token in EMBED_TOKENS):
            return "embed"
        return hinted_category
    if any(token in lower for token in RERANK_TOKENS):
        return "reranker"
    if any(token in lower for token in EMBED_TOKENS):
        return "embed"
    if any(token in lower for token in ASR_TOKENS):
        return "audio"
    if any(token in lower for token in VIDEO_TOKENS):
        return "video"
    if any(token in lower for token in IMAGE_TOKENS):
        return "image"
    return "text"


def _format_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".gguf":
        return "gguf"
    if suffix == ".safetensors":
        return "safetensors"
    if suffix == ".onnx":
        return "onnx"
    if suffix in {".bin", ".pt", ".pth", ".ckpt"}:
        return suffix.lstrip(".")
    if path.name == ".holo-model.json":
        return "metadata"
    return suffix.lstrip(".") or "directory"


def _path_size(path: Path) -> int | None:
    try:
        if path.is_file():
            return path.stat().st_size
        total = 0
        for candidate in path.rglob("*"):
            if candidate.is_file() and candidate.suffix.lower() in WEIGHT_SUFFIXES:
                total += candidate.stat().st_size
        return total or None
    except OSError:
        return None


def _read_holo_metadata(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _record_from_path(path: Path, source: str, hinted_category: str | None = None) -> DiscoveredModel:
    canonical = path.resolve()
    metadata: dict[str, Any] = {}
    model_root = path if path.is_dir() else path.parent
    metadata_path = model_root / ".holo-model.json"
    if metadata_path.exists():
        metadata = _read_holo_metadata(metadata_path)
    name = str(metadata.get("repo") or metadata.get("id") or model_root.name or path.stem)
    category = _classify(f"{name} {path.name}", hinted_category)
    legacy = any(token in f"{name} {path}".lower() for token in LEGACY_TOKENS)
    fmt = "directory" if path.is_dir() else _format_for_path(path)
    runtime = "llama.cpp" if fmt == "gguf" else "transformers"
    if category == "audio" and "whisper" in name.lower():
        runtime = "whisper.cpp" if fmt == "gguf" else "transformers"
    eligible = category == "embed" and fmt in {"gguf", "safetensors", "onnx", "directory"} and not legacy
    health = fmt in {"gguf", "safetensors", "onnx", "directory"} and not legacy
    if legacy:
        reason = "modelo marcado como legado/obsoleto; não entra no benchmark atual"
    elif eligible:
        reason = "modelo local de embeddings elegível para benchmark de recuperação"
    elif category == "reranker":
        reason = "reranker; deve usar benchmark de reranking, não métricas de embedding"
    else:
        reason = f"categoria {category}; exige health check/benchmark próprio, não o corpus de embeddings"
    return DiscoveredModel(
        id=_slug(name),
        source=source,
        category=category,
        runtime=runtime,
        format=fmt,
        path=str(path),
        canonical_path=str(canonical),
        size_bytes=_path_size(path),
        benchmark_eligible=eligible,
        healthcheck_eligible=health,
        legacy=legacy,
        reason=reason,
        coverage_status="UNASSESSED",
        matched_result=None,
        metadata=metadata,
    )


def _iter_weight_candidates(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    candidates: list[Path] = []
    metadata_roots = [metadata.parent for metadata in root.rglob(".holo-model.json")]
    candidates.extend(metadata_roots)
    for suffix in WEIGHT_SUFFIXES:
        for path in root.rglob(f"*{suffix}"):
            if any(model_root == path.parent or model_root in path.parents for model_root in metadata_roots):
                continue
            candidates.append(path)
    return candidates


def discover_filesystem_models(roots: Sequence[Path], repo_root: Path | None = None) -> list[DiscoveredModel]:
    records: list[DiscoveredModel] = []
    seen: set[str] = set()
    for root in roots:
        root = root.expanduser()
        if not root.exists():
            continue
        hinted = root.name if root.name in DEFAULT_CATEGORY_DIRS else None
        for candidate in _iter_weight_candidates(root):
            try:
                canonical = str(candidate.resolve())
            except OSError:
                canonical = str(candidate.absolute())
            if canonical in seen:
                continue
            seen.add(canonical)
            source = "repo" if repo_root and str(candidate).startswith(str(repo_root)) else "filesystem"
            records.append(_record_from_path(candidate, source, hinted))
    return records


def _run(command: Sequence[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)


def discover_ollama_models() -> list[DiscoveredModel]:
    if not shutil.which("ollama"):
        return []
    proc = _run(["ollama", "list"], timeout=30)
    if proc.returncode != 0:
        return []
    records: list[DiscoveredModel] = []
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    for line in lines[1:]:
        name = line.split()[0]
        if not name:
            continue
        category = _classify(name)
        records.append(
            DiscoveredModel(
                id=_slug(name),
                source="ollama",
                category=category,
                runtime="ollama",
                format="ollama-manifest",
                path=None,
                canonical_path=None,
                size_bytes=None,
                benchmark_eligible=category == "embed",
                healthcheck_eligible=True,
                legacy=any(token in name.lower() for token in LEGACY_TOKENS),
                reason=(
                    "modelo Ollama de embeddings elegível para benchmark"
                    if category == "embed"
                    else f"modelo Ollama da categoria {category}; requer health check/benchmark próprio"
                ),
                coverage_status="UNASSESSED",
                matched_result=None,
                metadata={"ollama_name": name, "raw_line": line},
            )
        )
    return records


def default_roots(repo_root: Path) -> list[Path]:
    home = Path.home()
    roots = [repo_root / category for category in DEFAULT_CATEGORY_DIRS]
    roots += [
        home / ".cache" / "huggingface" / "hub",
        home / ".cache" / "lm-studio" / "models",
        home / ".lmstudio" / "models",
        home / "LM Studio" / "models",
    ]
    extra = os.environ.get("HOLO_MODEL_ROOTS", "")
    roots += [Path(value) for value in extra.split(os.pathsep) if value.strip()]
    return roots


def _deduplicate(records: Sequence[DiscoveredModel]) -> list[DiscoveredModel]:
    chosen: dict[tuple[str, str | None], DiscoveredModel] = {}
    for record in records:
        key = (record.id, record.canonical_path)
        current = chosen.get(key)
        if current is None or (record.benchmark_eligible and not current.benchmark_eligible):
            chosen[key] = record
    return sorted(chosen.values(), key=lambda item: (item.category, item.id, item.path or ""))


def _load_benchmark_results(repo_root: Path) -> list[dict[str, Any]]:
    project_root = repo_root / "benchmark" / "embedding-v3"
    results: list[dict[str, Any]] = []
    for gate in ("gate2", "gate3"):
        result_dir = project_root / "results" / gate
        if not result_dir.exists():
            continue
        for path in result_dir.glob("*.json"):
            if path.name == "summary.json":
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                continue
            model = payload.get("model") if isinstance(payload, dict) else None
            if isinstance(model, dict) and model.get("id"):
                results.append({
                    "path": str(path.relative_to(repo_root)),
                    "id": str(model.get("id")),
                    "repo": str(model.get("repo") or ""),
                    "file": str(model.get("file") or ""),
                    "revision": str(model.get("revision") or ""),
                })
    return results


def _match_result(record: DiscoveredModel, results: Sequence[dict[str, Any]]) -> str | None:
    repo = str(record.metadata.get("repo") or "")
    filename = Path(record.path).name if record.path else ""
    for result in results:
        if record.id == result["id"]:
            return result["path"]
        if repo and repo == result["repo"]:
            if not result["file"] or result["file"] == filename or record.format == "directory":
                return result["path"]
        if filename and result["file"] and filename == result["file"]:
            return result["path"]
    return None


def _with_coverage(record: DiscoveredModel, results: Sequence[dict[str, Any]]) -> DiscoveredModel:
    matched = _match_result(record, results)
    if record.legacy:
        status = "LEGACY_EXCLUDED"
    elif record.benchmark_eligible and matched:
        status = "BENCHMARKED"
    elif record.benchmark_eligible:
        status = "PENDING_BENCHMARK"
    elif record.healthcheck_eligible:
        status = "PENDING_HEALTHCHECK"
    else:
        status = "NOT_APPLICABLE"
    values = asdict(record)
    values["coverage_status"] = status
    values["matched_result"] = matched
    return DiscoveredModel(**values)


def inventory(repo_root: Path, extra_roots: Sequence[Path] = (), include_ollama: bool = True) -> dict[str, Any]:
    roots = default_roots(repo_root) + list(extra_roots)
    records = discover_filesystem_models(roots, repo_root=repo_root)
    if include_ollama:
        records.extend(discover_ollama_models())
    records = _deduplicate(records)
    benchmark_results = _load_benchmark_results(repo_root)
    records = [_with_coverage(record, benchmark_results) for record in records]
    eligible = [record.id for record in records if record.benchmark_eligible]
    health = [record.id for record in records if record.healthcheck_eligible]
    benchmarked = [record.id for record in records if record.coverage_status == "BENCHMARKED"]
    pending_benchmark = [record.id for record in records if record.coverage_status == "PENDING_BENCHMARK"]
    pending_health = [record.id for record in records if record.coverage_status == "PENDING_HEALTHCHECK"]
    categories: dict[str, int] = {}
    for record in records:
        categories[record.category] = categories.get(record.category, 0) + 1
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root.resolve()),
        "roots_scanned": [str(path.expanduser()) for path in roots],
        "models": [asdict(record) for record in records],
        "summary": {
            "total_models": len(records),
            "embedding_benchmark_eligible": len(eligible),
            "healthcheck_eligible": len(health),
            "categories": categories,
            "embedding_model_ids": eligible,
            "benchmarked_embedding_model_ids": benchmarked,
            "pending_embedding_model_ids": pending_benchmark,
            "pending_healthcheck_model_ids": pending_health,
            "coverage_complete": not pending_benchmark and not pending_health,
        },
    }


def render_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Inventário local de modelos",
        "",
        f"- total descoberto: {summary['total_models']}",
        f"- elegíveis para benchmark de embeddings: {summary['embedding_benchmark_eligible']}",
        f"- elegíveis para health check: {summary['healthcheck_eligible']}",
        f"- embeddings já benchmarkados: {len(summary['benchmarked_embedding_model_ids'])}",
        f"- embeddings pendentes: {len(summary['pending_embedding_model_ids'])}",
        f"- health checks pendentes: {len(summary['pending_healthcheck_model_ids'])}",
        f"- cobertura completa: {'sim' if summary['coverage_complete'] else 'não'}",
        "",
        "## Cobertura",
        "",
        "| ID | origem | categoria | runtime | formato | tamanho | status | resultado | motivo |",
        "|---|---|---|---|---|---:|---|---|---|",
    ]
    for model in payload["models"]:
        size = model["size_bytes"]
        size_text = str(size) if size is not None else "-"
        lines.append(
            f"| `{model['id']}` | {model['source']} | {model['category']} | {model['runtime']} | "
            f"{model['format']} | {size_text} | {model['coverage_status']} | "
            f"{model['matched_result'] or '-'} | {model['reason']} |"
        )
    lines += [
        "",
        "Nenhum modelo descoberto pode ser omitido silenciosamente. Cada item deve terminar como benchmark concluído, health check concluído, legado justificado ou bloqueio técnico com evidência.",
        "",
    ]
    return "\n".join(lines)


def write_inventory(repo_root: Path, output_json: Path, output_report: Path, extra_roots: Sequence[Path] = (), include_ollama: bool = True) -> dict[str, Any]:
    payload = inventory(repo_root, extra_roots=extra_roots, include_ollama=include_ollama)
    _atomic_json(output_json, payload)
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(render_report(payload), encoding="utf-8")
    return payload


__all__ = [
    "DiscoveredModel",
    "discover_filesystem_models",
    "discover_ollama_models",
    "inventory",
    "render_report",
    "write_inventory",
    "_classify",
]
