"""BitNet embedding runner — canonical integration for the benchmark."""
from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Sequence

import numpy as np

from .bitnet_parser import detect_bitnet_dim, parse_bitnet_array_output


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def bitnet_embed_texts(
    texts: Sequence[str],
    *,
    gguf_path: Path,
    bitnet_bin: Path,
    expected_dim: int,
    normalize: bool = True,
    instruction_prefix: str = "",
    doc_indices: Sequence[int] | None = None,
    query_indices: Sequence[int] | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Encode texts using BitNet llama-embedding.

    Parameters
    ----------
    texts : list[str]
        Texts to encode.
    gguf_path, bitnet_bin : Path
        Paths to GGUF model and llama-embedding binary.
    expected_dim : int
        1024 for 0.6B, 640 for 270M.
    normalize : bool
        Whether to use --embd-normalize 2.
    instruction_prefix : str
        Prefix to prepend to query texts only.
    doc_indices, query_indices : list[int]
        Indices into `texts` for docs vs queries. If None, no instruction
        prefix is applied to any text.
    """
    # Build texts with instruction applied ONLY to query indices
    encoded_texts = list(texts)
    if instruction_prefix and query_indices is not None:
        for idx in query_indices:
            encoded_texts[idx] = instruction_prefix + encoded_texts[idx]

    infile = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    try:
        for t in encoded_texts:
            infile.write(t + "\n")
        infile.close()

        cmd = [
            str(bitnet_bin),
            "-m", str(gguf_path),
            "-f", infile.name,
            "--embd-normalize", "2" if normalize else "0",
            "--embd-output-format", "array",
        ]

        t0 = time.monotonic()
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=3600
        )
        elapsed = time.monotonic() - t0

        if result.returncode != 0:
            stderr_tail = (result.stderr or "")[-500:]
            raise RuntimeError(
                f"BitNet llama-embedding failed (exit={result.returncode}): "
                f"{stderr_tail}"
            )

        embeddings = parse_bitnet_array_output(
            result.stdout,
            expected_count=len(texts),
            expected_dim=expected_dim,
        )

        info: dict[str, Any] = {
            "backend": "bitnet.cpp",
            "device": "CPU",
            "dimension": expected_dim,
            "normalize": normalize,
            "instruction_prefix": instruction_prefix if query_indices else "",
            "n_texts": len(texts),
            "n_queries": len(query_indices) if query_indices else 0,
            "n_documents": len(doc_indices) if doc_indices else 0,
            "encode_seconds": round(elapsed, 3),
            "throughput_texts_per_sec": (
                round(len(texts) / elapsed, 2) if elapsed > 0 else 0
            ),
            "binary_path": str(bitnet_bin),
            "binary_sha256": _sha256(bitnet_bin),
            "gguf_path": str(gguf_path),
            "gguf_sha256": _sha256(gguf_path),
            "gguf_size_bytes": gguf_path.stat().st_size,
        }
        return embeddings, info

    finally:
        try:
            os.unlink(infile.name)
        except OSError:
            pass


def bitnet_embed_queries_and_docs(
    queries: Sequence[str],
    documents: Sequence[str],
    *,
    gguf_path: Path,
    bitnet_bin: Path,
    expected_dim: int,
    query_instruction: str = "",
    normalize: bool = True,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Encode queries (with instruction) and documents (without) separately.

    Returns (query_embs, doc_embs, merged_info).
    """
    n_doc = len(documents)
    n_q = len(queries)
    combined = list(documents) + list(queries)
    doc_indices = list(range(n_doc))
    query_indices = list(range(n_doc, n_doc + n_q))

    all_embs, info = bitnet_embed_texts(
        combined,
        gguf_path=gguf_path,
        bitnet_bin=bitnet_bin,
        expected_dim=expected_dim,
        normalize=normalize,
        instruction_prefix=query_instruction,
        doc_indices=doc_indices,
        query_indices=query_indices,
    )

    doc_embs = all_embs[:n_doc]
    query_embs = all_embs[n_doc:]

    info["doc_encode_seconds"] = info["encode_seconds"]
    info["query_encode_seconds"] = info["encode_seconds"]  # batched together
    return query_embs, doc_embs, info
