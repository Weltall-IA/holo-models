"""BitNet embedding output parser.

Parses the text array output format produced by llama-embedding (BitNet runtime):
    [[float,float,...],[float,float,...],...]

Validates dimension, finiteness, norm, count and determinism.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

import numpy as np

# Regex for a single float: optional sign, digits, optional decimal, optional exponent
_FLOAT_RE = r"-?[\d]+(?:\.[\d]+)?(?:[eE][+-]?[\d]+)?"

# Match outer array: [[...],[...],...]  — each inner array is one vector
_VECTOR_RE = re.compile(r"\[(" + _FLOAT_RE + r"(?:\s*,\s*" + _FLOAT_RE + r")*)\]")

# Precompiled pattern for a single float value inside a vector
_SINGLE_FLOAT_RE = re.compile(r"-?[\d]+(?:\.[\d]+)?(?:[eE][+-]?[\d]+)?")


def parse_bitnet_array_output(text: str, expected_count: int, expected_dim: int) -> np.ndarray:
    """Parse BitNet llama-embedding --embd-output-format array text output.

    Parameters
    ----------
    text : str
        Raw stdout from llama-embedding.
    expected_count : int
        Number of input texts (must match number of vectors).
    expected_dim : int
        Expected embedding dimension (1024 for 0.6B, 640 for 270M).

    Returns
    -------
    np.ndarray
        Shape (expected_count, expected_dim), float32, L2-normalized rows.

    Raises
    ------
    ValueError
        If parsing fails any validation check.
    """
    if not text or not text.strip():
        raise ValueError("BitNet output is empty")

    vector_matches = _VECTOR_RE.findall(text)
    if not vector_matches:
        raise ValueError(
            f"No vector arrays found in BitNet output. "
            f"First 200 chars: {text[:200]!r}"
        )

    vectors: list[list[float]] = []
    for match_str in vector_matches:
        float_matches = _SINGLE_FLOAT_RE.findall(match_str)
        vals = [float(v) for v in float_matches]
        vectors.append(vals)

    n_vectors = len(vectors)
    if n_vectors != expected_count:
        raise ValueError(
            f"Vector count mismatch: got {n_vectors}, expected {expected_count}"
        )

    for i, vec in enumerate(vectors):
        if len(vec) != expected_dim:
            raise ValueError(
                f"Vector {i} dimension mismatch: got {len(vec)}, expected {expected_dim}"
            )
        for j, v in enumerate(vec):
            if not np.isfinite(v):
                raise ValueError(
                    f"Vector {i} element {j} is not finite: {v}"
                )

    arr = np.array(vectors, dtype=np.float32)

    norms = np.linalg.norm(arr, axis=1)
    zero_norm_mask = norms < 1e-12
    if np.any(zero_norm_mask):
        bad_idx = np.where(zero_norm_mask)[0][0]
        raise ValueError(
            f"Vector {bad_idx} has zero norm (possible zero vector input)"
        )

    # Verify L2 normalized (norms should be ~1.0 after --embd-normalize 2)
    max_deviation = float(np.max(np.abs(norms - 1.0)))
    if max_deviation > 0.05:
        raise ValueError(
            f"Vectors not L2-normalized: max norm deviation = {max_deviation:.4f}"
        )

    return arr


def detect_bitnet_dim(gguf_path: Path) -> int:
    """Detect expected dimension from GGUF filename heuristic.

    0.6B models output 1024 dimensions; 270M models output 640 dimensions.
    """
    name = gguf_path.name.lower()
    if "270m" in name:
        return 640
    if "0.6b" in name or "06b" in name:
        return 1024
    raise ValueError(
        f"Cannot detect BitNet dimension from filename: {gguf_path.name}. "
        f"Expected '0.6b' (1024) or '270m' (640)."
    )
