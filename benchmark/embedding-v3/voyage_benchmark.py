from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import stat
import sys
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from holo_benchmark.gate2_worker import _rankings_from_embeddings
from holo_benchmark.metrics import DEFAULT_KS, evaluate_rankings

PROJECT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_ROOT.parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "holo_fake_scenes_v3"
RESULTS_DIR = PROJECT_ROOT / "results" / "voyage"
CHECKPOINT_DIR = PROJECT_ROOT / "results" / "raw" / "voyage"
DEFAULT_KEY_PATH = REPO_ROOT / ".voyage4_token"
CORPUS_SHA256 = "8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b"
MODELS = ("voyage-4-large", "voyage-context-4")
DIMENSION = 1024
MAX_REQUEST_TOKENS = 9_000
REQUEST_INTERVAL_SECONDS = 65.0


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def configure_key(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or resolved.stat().st_size == 0:
        raise RuntimeError(f"chave Voyage ausente ou vazia: {resolved}")
    mode = stat.S_IMODE(resolved.stat().st_mode)
    if mode & 0o077:
        raise PermissionError(
            f"permissão insegura em {resolved}; use chmod 600"
        )
    os.environ["VOYAGE_API_KEY_PATH"] = str(resolved)
    return resolved


def load_dataset() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hashes = json.loads((DATA_DIR / "hashes.json").read_text(encoding="utf-8"))
    if hashes.get("combined_sha256") != CORPUS_SHA256:
        raise RuntimeError("hash do corpus congelado divergiu")
    chunks = read_jsonl(DATA_DIR / "corpus.jsonl")
    queries = read_jsonl(DATA_DIR / "queries.jsonl")
    if len(chunks) != 600 or len(queries) != 150:
        raise RuntimeError(
            f"contagens inválidas: {len(chunks)} documentos, {len(queries)} consultas"
        )
    return chunks, queries


def count_tokens(client: Any, texts: Sequence[str], model: str) -> int:
    tokens = int(client.count_tokens(list(texts), model=model))
    if tokens <= 0:
        raise RuntimeError(f"contagem de tokens inválida para {model}")
    return tokens


def pack_texts(
    client: Any,
    model: str,
    items: Sequence[tuple[str, str]],
) -> list[list[tuple[str, str]]]:
    batches: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    current_tokens = 0
    for item_id, text in items:
        tokens = count_tokens(client, [text], model)
        if tokens > MAX_REQUEST_TOKENS:
            raise RuntimeError(
                f"item {item_id} tem {tokens} tokens e excede o limite operacional"
            )
        if current and current_tokens + tokens > MAX_REQUEST_TOKENS:
            batches.append(current)
            current = []
            current_tokens = 0
        current.append((item_id, text))
        current_tokens += tokens
    if current:
        batches.append(current)
    return batches


def group_by_work(
    chunks: Sequence[dict[str, Any]],
) -> list[tuple[str, list[tuple[str, str]]]]:
    groups: OrderedDict[str, list[tuple[str, str]]] = OrderedDict()
    for chunk in chunks:
        groups.setdefault(str(chunk["work_id"]), []).append(
            (str(chunk["chunk_id"]), str(chunk["text"]))
        )
    return list(groups.items())


def pack_context_groups(
    client: Any,
    model: str,
    groups: Sequence[tuple[str, list[tuple[str, str]]]],
) -> list[list[tuple[str, list[tuple[str, str]]]]]:
    batches: list[list[tuple[str, list[tuple[str, str]]]]] = []
    current: list[tuple[str, list[tuple[str, str]]]] = []
    current_tokens = 0
    for group_id, members in groups:
        tokens = count_tokens(client, [text for _, text in members], model)
        if tokens > MAX_REQUEST_TOKENS:
            raise RuntimeError(
                f"obra {group_id} tem {tokens} tokens e não pode ser dividida sem alterar o benchmark"
            )
        if current and current_tokens + tokens > MAX_REQUEST_TOKENS:
            batches.append(current)
            current = []
            current_tokens = 0
        current.append((group_id, members))
        current_tokens += tokens
    if current:
        batches.append(current)
    return batches


def wait_for_slot(last_request_at: float | None) -> None:
    if last_request_at is None:
        return
    remaining = REQUEST_INTERVAL_SECONDS - (time.monotonic() - last_request_at)
    if remaining > 0:
        time.sleep(remaining)


def status_code(exc: BaseException) -> int | None:
    direct = getattr(exc, "status_code", None)
    response = getattr(exc, "response", None)
    nested = getattr(response, "status_code", None)
    if isinstance(direct, int):
        return direct
    if isinstance(nested, int):
        return nested
    message = str(exc).lower()
    return 429 if "429" in message or "rate limit" in message else None


def api_call(operation: Any, last_request_at: float | None) -> tuple[Any, float, int]:
    retries = 0
    while True:
        wait_for_slot(last_request_at)
        last_request_at = time.monotonic()
        try:
            return operation(), last_request_at, retries
        except Exception as exc:
            if status_code(exc) != 429 or retries >= 1:
                raise
            retries += 1
            time.sleep(REQUEST_INTERVAL_SECONDS + 30.0)


def load_checkpoint(
    path: Path,
    model: str,
    input_type: str,
    resume: bool,
) -> tuple[dict[str, list[float]], dict[str, Any]]:
    empty = {"tokens": 0, "requests": 0, "retries": 0, "seconds": 0.0}
    if not resume or not path.exists():
        return {}, empty
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("model") != model or payload.get("input_type") != input_type:
        raise RuntimeError(f"checkpoint incompatível: {path}")
    rows = {
        str(item_id): [float(value) for value in embedding]
        for item_id, embedding in dict(payload.get("rows") or {}).items()
    }
    usage = dict(empty)
    usage.update(dict(payload.get("usage") or {}))
    return rows, usage


def save_checkpoint(
    path: Path,
    model: str,
    input_type: str,
    rows: dict[str, list[float]],
    usage: dict[str, Any],
) -> None:
    atomic_json(
        path,
        {
            "schema_version": "1.0",
            "model": model,
            "input_type": input_type,
            "dimension": DIMENSION,
            "rows": rows,
            "usage": usage,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def validate_row(item_id: str, embedding: Sequence[float]) -> list[float]:
    row = [float(value) for value in embedding]
    if len(row) != DIMENSION:
        raise RuntimeError(f"dimensão inválida para {item_id}: {len(row)}")
    return row


def embed_standard(
    client: Any,
    model: str,
    input_type: str,
    items: Sequence[tuple[str, str]],
    checkpoint: Path,
    resume: bool,
    last_request_at: float | None,
) -> tuple[list[list[float]], dict[str, Any], float | None]:
    rows, usage = load_checkpoint(checkpoint, model, input_type, resume)
    pending = [(item_id, text) for item_id, text in items if item_id not in rows]
    for batch in pack_texts(client, model, pending):
        ids = [item_id for item_id, _ in batch]
        texts = [text for _, text in batch]
        started = time.monotonic()
        response, last_request_at, retries = api_call(
            lambda: client.embed(
                texts=texts,
                model=model,
                input_type=input_type,
                truncation=False,
                output_dimension=DIMENSION,
                output_dtype="float",
            ),
            last_request_at,
        )
        embeddings = list(response.embeddings)
        if len(embeddings) != len(ids):
            raise RuntimeError("resposta Voyage com quantidade divergente")
        for item_id, embedding in zip(ids, embeddings, strict=True):
            rows[item_id] = validate_row(item_id, embedding)
        usage["tokens"] += int(response.total_tokens)
        usage["requests"] += 1
        usage["retries"] += retries
        usage["seconds"] += time.monotonic() - started
        save_checkpoint(checkpoint, model, input_type, rows, usage)
    missing = [item_id for item_id, _ in items if item_id not in rows]
    if missing:
        raise RuntimeError(f"checkpoint incompleto: {missing[:5]}")
    return [rows[item_id] for item_id, _ in items], usage, last_request_at


def embed_contextual(
    client: Any,
    model: str,
    input_type: str,
    groups: Sequence[tuple[str, list[tuple[str, str]]]],
    checkpoint: Path,
    resume: bool,
    last_request_at: float | None,
) -> tuple[list[list[float]], dict[str, Any], float | None]:
    rows, usage = load_checkpoint(checkpoint, model, input_type, resume)
    pending = [
        (group_id, members)
        for group_id, members in groups
        if any(item_id not in rows for item_id, _ in members)
    ]
    for group_id, members in pending:
        completed = [item_id for item_id, _ in members if item_id in rows]
        if completed:
            raise RuntimeError(f"checkpoint parcial na obra {group_id}")
    for batch in pack_context_groups(client, model, pending):
        inputs = [[text for _, text in members] for _, members in batch]
        started = time.monotonic()
        response, last_request_at, retries = api_call(
            lambda: client.contextualized_embed(
                inputs=inputs,
                model=model,
                input_type=input_type,
                output_dimension=DIMENSION,
                output_dtype="float",
                enable_auto_chunking=False,
            ),
            last_request_at,
        )
        results = sorted(response.results, key=lambda result: result.index)
        if len(results) != len(batch):
            raise RuntimeError("resposta contextual com quantidade divergente")
        for (_, members), result in zip(batch, results, strict=True):
            if len(result.embeddings) != len(members):
                raise RuntimeError("embeddings contextualizados divergentes")
            for (item_id, _), embedding in zip(
                members, result.embeddings, strict=True
            ):
                rows[item_id] = validate_row(item_id, embedding)
        usage["tokens"] += int(response.total_tokens)
        usage["requests"] += 1
        usage["retries"] += retries
        usage["seconds"] += time.monotonic() - started
        save_checkpoint(checkpoint, model, input_type, rows, usage)
    ordered_ids = [item_id for _, members in groups for item_id, _ in members]
    missing = [item_id for item_id in ordered_ids if item_id not in rows]
    if missing:
        raise RuntimeError(f"checkpoint contextual incompleto: {missing[:5]}")
    return [rows[item_id] for item_id in ordered_ids], usage, last_request_at


def run_model(
    client: Any,
    model: str,
    chunks: Sequence[dict[str, Any]],
    queries: Sequence[dict[str, Any]],
    resume: bool,
    last_request_at: float | None,
    sdk_version: str,
) -> tuple[dict[str, Any], float | None]:
    docs = [(str(row["chunk_id"]), str(row["text"])) for row in chunks]
    query_items = [(str(row["query_id"]), str(row["query"])) for row in queries]
    base = CHECKPOINT_DIR / model
    started = time.monotonic()
    if model == "voyage-4-large":
        doc_embeddings, doc_usage, last_request_at = embed_standard(
            client, model, "document", docs, base / "documents.json", resume, last_request_at
        )
        query_embeddings, query_usage, last_request_at = embed_standard(
            client, model, "query", query_items, base / "queries.json", resume, last_request_at
        )
        endpoint = "Client.embed"
    elif model == "voyage-context-4":
        doc_embeddings, doc_usage, last_request_at = embed_contextual(
            client, model, "document", group_by_work(chunks), base / "documents.json", resume, last_request_at
        )
        query_groups = [(item_id, [(item_id, text)]) for item_id, text in query_items]
        query_embeddings, query_usage, last_request_at = embed_contextual(
            client, model, "query", query_groups, base / "queries.json", resume, last_request_at
        )
        endpoint = "Client.contextualized_embed"
    else:
        raise ValueError(f"modelo não autorizado: {model}")

    rankings = _rankings_from_embeddings(
        doc_embeddings,
        query_embeddings,
        [item_id for item_id, _ in docs],
    )
    metrics = evaluate_rankings(queries, rankings, DEFAULT_KS)
    usage = {
        key: doc_usage[key] + query_usage[key]
        for key in ("tokens", "requests", "retries", "seconds")
    }
    result = {
        "schema_version": "1.0",
        "gate": "voyage",
        "model": {
            "id": model,
            "provider": "Voyage AI",
            "backend": "voyage-api",
            "endpoint": endpoint,
            "sdk_version": sdk_version,
            "dimension": DIMENSION,
            "dtype": "float",
            "auto_chunking": False,
        },
        "dataset": {
            "corpus_version": "holo_fake_scenes_v3",
            "combined_sha256": CORPUS_SHA256,
            "documents": len(chunks),
            "queries": len(queries),
            "works": len({str(row["work_id"]) for row in chunks}),
        },
        "rate_limit": {
            "tokens_per_minute": 10_000,
            "requests_per_minute": 3,
            "operational_tokens_per_request": MAX_REQUEST_TOKENS,
            "interval_seconds": REQUEST_INTERVAL_SECONDS,
            "shared_between_models": True,
        },
        "usage": usage,
        "runtime": {
            "device": "remote-api",
            "total_seconds": round(time.monotonic() - started, 4),
        },
        "metrics": metrics,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(RESULTS_DIR / f"{model}.json", result)
    return result, last_request_at


def parse_models(raw: str) -> list[str]:
    selected = [value.strip() for value in raw.split(",") if value.strip()]
    unknown = sorted(set(selected) - set(MODELS))
    if unknown or not selected:
        raise ValueError("modelos inválidos: " + ", ".join(unknown or ["nenhum"]))
    return selected


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark de voyage-4-large e voyage-context-4"
    )
    parser.add_argument("--models", default=",".join(MODELS))
    parser.add_argument("--api-key-path", type=Path, default=DEFAULT_KEY_PATH)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        selected = parse_models(args.models)
        configure_key(args.api_key_path)
        chunks, queries = load_dataset()
        import voyageai

        sdk_version = importlib.metadata.version("voyageai")
        client = voyageai.Client(max_retries=0)
        estimates = {
            model: {
                "documents": count_tokens(
                    client, [str(row["text"]) for row in chunks], model
                ),
                "queries": count_tokens(
                    client, [str(row["query"]) for row in queries], model
                ),
            }
            for model in selected
        }
        preflight = {
            "models": selected,
            "sdk_version": sdk_version,
            "corpus_sha256": CORPUS_SHA256,
            "estimated_tokens": estimates,
            "api_key_path_configured": True,
        }
        atomic_json(RESULTS_DIR / "preflight.json", preflight)
        print(json.dumps(preflight, ensure_ascii=False, indent=2))
        if args.dry_run:
            return 0

        results = []
        last_request_at: float | None = None
        for model in selected:
            result, last_request_at = run_model(
                client,
                model,
                chunks,
                queries,
                args.resume,
                last_request_at,
                sdk_version,
            )
            results.append(result)
        summary = {
            "schema_version": "1.0",
            "status": "PASS" if len(results) == len(selected) else "PARTIAL",
            "corpus_sha256": CORPUS_SHA256,
            "models_completed": [row["model"]["id"] for row in results],
            "results": [
                {
                    "model_id": row["model"]["id"],
                    "metrics": row["metrics"]["summary"],
                    "usage": row["usage"],
                    "runtime": row["runtime"],
                }
                for row in results
            ],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        atomic_json(RESULTS_DIR / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"Benchmark Voyage bloqueado: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
