"""BitNet embedding runner.

Runs llama-embedding from the Microsoft BitNet runtime and parses its output
using bitnet_parser.  Designed for I2_S architecture-native GGUF files on CPU.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .bitnet_parser import detect_bitnet_dim, parse_bitnet_array_output

logger = logging.getLogger(__name__)


def _find_bitnet_binary() -> Path:
    """Locate the llama-embedding binary from the BitNet runtime build."""
    candidates = [
        Path(__file__).resolve().parents[2] / "runtimes/BitNet/build/bin/llama-embedding",
        Path.home() / "Playstoria/models-embed-batch2-light/runtimes/BitNet/build/bin/llama-embedding",
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError(
        "BitNet llama-embedding binary not found. "
        "Expected at runtimes/BitNet/build/bin/llama-embedding"
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def bitnet_embed(
    texts: Sequence[str],
    gguf_path: Path,
    bitnet_bin: Path | None = None,
    normalize: bool = True,
    instruction_prefix: str = "",
) -> tuple[np.ndarray, dict[str, Any]]:
    """Encode texts using BitNet llama-embedding.

    Returns
    -------
    embeddings : np.ndarray
        Shape (len(texts), expected_dim), float32, L2-normalized.
    info : dict
        Runtime metadata: timing, dim, binary SHA-256, backend='bitnet.cpp'.
    """
    if bitnet_bin is None:
        bitnet_bin = _find_bitnet_binary()
    expected_dim = detect_bitnet_dim(gguf_path)

    texts_to_encode = []
    for t in texts:
        if instruction_prefix and texts.index(t) >= 0:
            texts_to_encode.append(instruction_prefix + t)
        else:
            texts_to_encode.append(t)

    infile = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    try:
        for t in texts_to_encode:
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
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,
        )
        elapsed = time.monotonic() - t0

        if result.returncode != 0:
            stderr_tail = (result.stderr or "")[-500:]
            raise RuntimeError(
                f"BitNet llama-embedding failed (exit={result.returncode}): {stderr_tail}"
            )

        embeddings = parse_bitnet_array_output(
            result.stdout,
            expected_count=len(texts),
            expected_dim=expected_dim,
        )

        info = {
            "backend": "bitnet.cpp",
            "backend_version": "microsoft/BitNet commit-0b341e5",
            "binary_path": str(bitnet_bin),
            "binary_sha256": _sha256(bitnet_bin),
            "gguf_path": str(gguf_path),
            "gguf_sha256": _sha256(gguf_path),
            "gguf_size_bytes": gguf_path.stat().st_size,
            "device": "CPU",
            "dimension": expected_dim,
            "normalize": normalize,
            "n_texts": len(texts),
            "encode_seconds": round(elapsed, 3),
            "throughput_texts_per_sec": round(len(texts) / elapsed, 2) if elapsed > 0 else 0,
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
    gguf_path: Path,
    bitnet_bin: Path | None = None,
    query_instruction: str = "",
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Encode queries and documents separately (instruction only on queries).

    Returns (query_embs, doc_embs, info).
    """
    doc_embs, info = bitnet_embed(
        documents, gguf_path, bitnet_bin, normalize=True, instruction_prefix=""
    )

    q_texts = [query_instruction + q for q in queries] if query_instruction else list(queries)
    q_embs, q_info = bitnet_embed(
        q_texts, gguf_path, bitnet_bin, normalize=True, instruction_prefix=""
    )

    info["query_encode_seconds"] = q_info["encode_seconds"]
    info["doc_encode_seconds"] = info["encode_seconds"]
    info["total_encode_seconds"] = round(q_info["encode_seconds"] + info["encode_seconds"], 3)
    return q_embs, doc_embs, info
