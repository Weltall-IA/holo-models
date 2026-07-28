"""Canonical BitNet embedding runner used by the benchmark entrypoint."""
from __future__ import annotations

import hashlib
import os
import resource
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .bitnet_parser import detect_bitnet_dim, parse_bitnet_array_output


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _require_file(path: Path, label: str, *, executable: bool = False) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{label} is not a regular file: {resolved}")
    if executable and not os.access(resolved, os.X_OK):
        raise PermissionError(f"{label} is not executable: {resolved}")
    return resolved


def _validate_partition(
    count: int,
    doc_indices: Sequence[int] | None,
    query_indices: Sequence[int] | None,
) -> tuple[list[int], list[int]]:
    if (doc_indices is None) != (query_indices is None):
        raise ValueError("doc_indices and query_indices must be provided together")
    if doc_indices is None and query_indices is None:
        return list(range(count)), []

    documents = [int(index) for index in doc_indices or []]
    queries = [int(index) for index in query_indices or []]
    if len(documents) != len(set(documents)):
        raise ValueError("doc_indices contains duplicates")
    if len(queries) != len(set(queries)):
        raise ValueError("query_indices contains duplicates")

    all_indices = documents + queries
    invalid = [index for index in all_indices if index < 0 or index >= count]
    if invalid:
        raise ValueError(f"input index out of range: {invalid[0]}")
    overlap = set(documents) & set(queries)
    if overlap:
        raise ValueError(f"document/query index overlap: {min(overlap)}")
    missing = set(range(count)) - set(all_indices)
    if missing:
        raise ValueError(f"document/query indices do not cover input index: {min(missing)}")
    return documents, queries


def _single_line(text: str) -> str:
    if "\x00" in text:
        raise ValueError("input text contains a NUL byte")
    return " ".join(text.replace("\r", "\n").splitlines())


def _child_peak_ram_bytes() -> int:
    # Linux reports ru_maxrss in KiB.
    return int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) * 1024


def _vram_residual_bytes() -> int | None:
    """Return best-effort residual VRAM without affecting benchmark success."""
    binary = shutil.which("nvidia-smi")
    if binary is None:
        return None
    try:
        result = subprocess.run(
            [
                binary,
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except Exception:
        # Telemetry is optional. A missing, mocked or incompatible nvidia-smi
        # must not invalidate otherwise valid CPU embeddings.
        return None
    if result.returncode != 0:
        return None
    values = [
        int(line.strip())
        for line in result.stdout.splitlines()
        if line.strip().isdigit()
    ]
    return sum(values) * 1024 * 1024 if values else None


def bitnet_embed_texts(
    texts: Sequence[str],
    *,
    profile_id: str,
    gguf_path: Path,
    bitnet_bin: Path,
    bitnet_commit: str,
    expected_dim: int | None = None,
    normalize: bool = True,
    instruction_prefix: str = "",
    doc_indices: Sequence[int] | None = None,
    query_indices: Sequence[int] | None = None,
    timeout_seconds: int = 3600,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Encode one deterministic document/query partition with BitNet.

    The runtime receives one combined input file. Consequently, the telemetry
    reports a single combined encode duration rather than fabricated separate
    document/query timings.
    """
    if not texts:
        raise ValueError("at least one input text is required")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    configured_dim = detect_bitnet_dim(profile_id)
    if expected_dim is None:
        expected_dim = configured_dim
    elif expected_dim != configured_dim:
        raise ValueError(
            f"expected_dim {expected_dim} does not match profile {profile_id} "
            f"dimension {configured_dim}"
        )
    if not bitnet_commit.strip():
        raise ValueError("bitnet_commit must be provided")

    binary = _require_file(bitnet_bin, "BitNet llama-embedding binary", executable=True)
    model = _require_file(gguf_path, "BitNet GGUF")
    document_indices, query_indices_list = _validate_partition(
        len(texts), doc_indices, query_indices
    )

    encoded_texts = [_single_line(str(text)) for text in texts]
    for index in query_indices_list:
        encoded_texts[index] = instruction_prefix + encoded_texts[index]

    input_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8", newline="\n"
    )
    started = time.monotonic()
    try:
        for text in encoded_texts:
            input_file.write(text + "\n")
        input_file.close()

        actual_command = [
            str(binary),
            "-m",
            str(model),
            "-f",
            input_file.name,
            "--embd-normalize",
            "2" if normalize else "0",
            "--embd-output-format",
            "array",
        ]
        try:
            result = subprocess.run(
                actual_command,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"BitNet llama-embedding timed out after {timeout_seconds}s"
            ) from exc

        elapsed = time.monotonic() - started
        if result.returncode != 0:
            stderr_tail = (result.stderr or "")[-2000:]
            raise RuntimeError(
                "BitNet llama-embedding failed "
                f"(exit={result.returncode}): {stderr_tail}"
            )

        embeddings = parse_bitnet_array_output(
            result.stdout,
            expected_count=len(encoded_texts),
            expected_dim=expected_dim,
            inputs=encoded_texts,
        )
        sanitized_command = [
            "<bitnet-embedding-binary>",
            "-m",
            "<gguf-model>",
            "-f",
            "<temporary-input-file>",
            "--embd-normalize",
            "2" if normalize else "0",
            "--embd-output-format",
            "array",
        ]
        info: dict[str, Any] = {
            "backend": "bitnet.cpp",
            "device": "cpu",
            "profile_id": profile_id,
            "bitnet_commit": bitnet_commit,
            "dimension": expected_dim,
            "normalization": "l2" if normalize else "none",
            "pooling": "last_non_padding_token",
            "instruction_prefix": instruction_prefix if query_indices_list else "",
            "document_prompt": "",
            "input_line_normalization": "embedded newlines replaced with spaces",
            "n_texts": len(encoded_texts),
            "n_queries": len(query_indices_list),
            "n_documents": len(document_indices),
            "combined_encode_seconds": round(elapsed, 6),
            "throughput_texts_per_second": round(len(encoded_texts) / elapsed, 6),
            "peak_ram_bytes": _child_peak_ram_bytes(),
            "peak_vram_bytes": 0,
            "vram_residual_bytes": _vram_residual_bytes(),
            "command": sanitized_command,
            "exit_code": result.returncode,
            "binary_path": str(binary),
            "binary_sha256": _sha256(binary),
            "gguf_path": str(model),
            "gguf_sha256": _sha256(model),
            "gguf_size_bytes": model.stat().st_size,
        }
        return embeddings, info
    finally:
        try:
            input_file.close()
        except OSError:
            pass
        try:
            os.unlink(input_file.name)
        except OSError:
            pass


def bitnet_embed_queries_and_docs(
    queries: Sequence[str],
    documents: Sequence[str],
    *,
    profile_id: str,
    gguf_path: Path,
    bitnet_bin: Path,
    bitnet_commit: str,
    query_instruction: str = "",
    timeout_seconds: int = 3600,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Encode documents without instruction and queries with instruction."""
    combined = list(documents) + list(queries)
    document_count = len(documents)
    embeddings, info = bitnet_embed_texts(
        combined,
        profile_id=profile_id,
        gguf_path=gguf_path,
        bitnet_bin=bitnet_bin,
        bitnet_commit=bitnet_commit,
        instruction_prefix=query_instruction,
        doc_indices=range(document_count),
        query_indices=range(document_count, len(combined)),
        timeout_seconds=timeout_seconds,
    )
    return embeddings[document_count:], embeddings[:document_count], info
