from __future__ import annotations

import gc
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

from . import gate2_worker as _worker
from .gate2 import Gate2ModelSpec


def _sentence_transformer_kwargs(spec: Gate2ModelSpec, device: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "trust_remote_code": spec.trust_remote_code,
        "device": device,
    }
    if spec.id == "voyage4_nano" and spec.dimension > 0:
        kwargs["truncate_dim"] = spec.dimension
    return kwargs


def _sentence_transformer_embeddings(
    model_path: Path,
    spec: Gate2ModelSpec,
    documents: Sequence[str],
    queries: Sequence[str],
    device: str,
    batch_size: int,
) -> tuple[Any, Any, dict[str, Any]]:
    import torch
    from sentence_transformers import SentenceTransformer

    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    kwargs = _sentence_transformer_kwargs(spec, device)

    load_started = time.monotonic()
    model = SentenceTransformer(str(model_path), **kwargs)
    load_seconds = time.monotonic() - load_started
    dtype = _worker._model_dtype(model)
    doc_started = time.monotonic()
    doc_embeddings = _worker._encode_sentence_transformer(
        model, documents, "document", spec, batch_size
    )
    doc_seconds = time.monotonic() - doc_started
    query_started = time.monotonic()
    query_embeddings = _worker._encode_sentence_transformer(
        model, queries, "query", spec, batch_size
    )
    query_seconds = time.monotonic() - query_started
    peak_vram = _worker._peak_vram_bytes(device)
    del model
    gc.collect()
    if device == "cuda":
        torch.cuda.empty_cache()
    return doc_embeddings, query_embeddings, {
        "dtype": dtype,
        "load_seconds": round(load_seconds, 4),
        "document_encode_seconds": round(doc_seconds, 4),
        "query_encode_seconds": round(query_seconds, 4),
        "peak_vram_bytes": peak_vram,
    }


def _log_tail(path: Path, limit: int = 12000) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[-limit:]


def _llama_cpp_embeddings(
    model_path: Path,
    spec: Gate2ModelSpec,
    documents: Sequence[str],
    queries: Sequence[str],
    device: str,
    batch_size: int,
) -> tuple[Any, Any, dict[str, Any]]:
    if not spec.file:
        raise RuntimeError("arquivo GGUF não configurado")
    model_file = model_path / spec.file
    if not model_file.exists():
        raise RuntimeError(f"arquivo GGUF ausente: {model_file}")
    server = _worker._find_llama_server()
    port = _worker._free_port()
    pooling = spec.pooling or "last"
    command = [
        server,
        "-m",
        str(model_file),
        "--embedding",
        "--pooling",
        pooling,
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "-np",
        "1",
        "-ngl",
        "99" if device == "cuda" else "0",
    ]

    with tempfile.TemporaryDirectory(prefix=f"{spec.id}-llama-") as tmp:
        log_path = Path(tmp) / "llama-server.log"
        with log_path.open("w", encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                command,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
            failure: BaseException | None = None
            try:
                load_started = time.monotonic()
                _worker._wait_server(port, process)
                load_seconds = time.monotonic() - load_started
                doc_started = time.monotonic()
                doc_embeddings = _worker._llama_cpp_encode(
                    port, documents, batch_size
                )
                doc_seconds = time.monotonic() - doc_started
                query_started = time.monotonic()
                query_embeddings = _worker._llama_cpp_encode(
                    port, queries, batch_size
                )
                query_seconds = time.monotonic() - query_started
            except BaseException as exc:
                failure = exc
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=15)
                log_handle.flush()

        if failure is not None:
            tail = _log_tail(log_path)
            detail = f"\nllama-server log tail:\n{tail}" if tail else ""
            raise RuntimeError(f"{failure}{detail}") from failure

    return doc_embeddings, query_embeddings, {
        "dtype": "gguf-i2_s/bf16",
        "load_seconds": round(load_seconds, 4),
        "document_encode_seconds": round(doc_seconds, 4),
        "query_encode_seconds": round(query_seconds, 4),
        "peak_vram_bytes": None,
        "llama_server": server,
        "pooling": pooling,
    }


_worker._sentence_transformer_embeddings = _sentence_transformer_embeddings
_worker._llama_cpp_embeddings = _llama_cpp_embeddings


def main() -> int:
    return _worker.main()


if __name__ == "__main__":
    raise SystemExit(main())
