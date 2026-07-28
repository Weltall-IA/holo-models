"""Strict parser for Microsoft BitNet ``llama-embedding`` array output."""
from __future__ import annotations

import json
import math
from typing import Sequence

import numpy as np


PROFILE_DIMENSIONS: dict[str, int] = {
    "bitnet_06b_current": 1024,
    "bitnet_270m_current": 640,
}


def detect_bitnet_dim(profile_id: str) -> int:
    """Return the configured embedding dimension for a supported BitNet profile."""
    try:
        return PROFILE_DIMENSIONS[profile_id]
    except KeyError as exc:
        known = ", ".join(sorted(PROFILE_DIMENSIONS))
        raise ValueError(f"Unknown BitNet profile: {profile_id}. Known profiles: {known}") from exc


def _reject_non_finite(token: str) -> float:
    raise ValueError(f"Non-finite JSON number is not allowed: {token}")


def parse_bitnet_array_output(
    text: str,
    expected_count: int,
    expected_dim: int,
    *,
    inputs: Sequence[str] | None = None,
    allow_identical: bool | None = None,
    normalization_tolerance: float = 0.05,
) -> np.ndarray:
    """Parse one complete JSON array of embedding vectors.

    The parser consumes the entire non-whitespace output through ``json.loads``.
    Empty tokens, duplicate/trailing commas, malformed brackets, residual text,
    truncation, NaN and infinity are rejected by the JSON grammar or explicit
    validation.

    Duplicate vectors are accepted only when the corresponding input texts are
    identical. ``allow_identical`` remains as a compatibility fallback for old
    isolated callers that cannot provide ``inputs``; production callers should
    always pass ``inputs``.
    """
    if expected_count <= 0:
        raise ValueError("expected_count must be positive")
    if expected_dim <= 0:
        raise ValueError("expected_dim must be positive")
    if normalization_tolerance < 0:
        raise ValueError("normalization_tolerance must be non-negative")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("BitNet output is empty or whitespace-only")

    try:
        payload = json.loads(text, parse_constant=_reject_non_finite)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Invalid BitNet array output: {exc}") from exc

    if not isinstance(payload, list):
        raise ValueError("BitNet output must be an outer JSON array")
    if len(payload) != expected_count:
        raise ValueError(
            f"Vector count mismatch: got {len(payload)}, expected {expected_count}"
        )
    if inputs is not None and len(inputs) != expected_count:
        raise ValueError(
            f"Input count mismatch: got {len(inputs)}, expected {expected_count}"
        )

    vectors: list[list[float]] = []
    for vector_index, raw_vector in enumerate(payload):
        if not isinstance(raw_vector, list):
            raise ValueError(f"Vector {vector_index} must be a JSON array")
        if len(raw_vector) != expected_dim:
            raise ValueError(
                f"Vector {vector_index} dimension mismatch: "
                f"got {len(raw_vector)}, expected {expected_dim}"
            )
        vector: list[float] = []
        for value_index, raw_value in enumerate(raw_vector):
            if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                raise ValueError(
                    f"Vector {vector_index} element {value_index} is not numeric"
                )
            value = float(raw_value)
            if not math.isfinite(value):
                raise ValueError(
                    f"Vector {vector_index} element {value_index} is not finite"
                )
            vector.append(value)
        vectors.append(vector)

    array = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(array, axis=1)
    zero_indices = np.flatnonzero(norms < 1e-12)
    if zero_indices.size:
        raise ValueError(f"Vector {int(zero_indices[0])} has zero norm")

    max_deviation = float(np.max(np.abs(norms - 1.0)))
    if max_deviation > normalization_tolerance:
        raise ValueError(
            "Vectors are not L2-normalized: "
            f"max norm deviation={max_deviation:.6f}, "
            f"tolerance={normalization_tolerance:.6f}"
        )

    first_index_by_vector: dict[bytes, int] = {}
    for index, row in enumerate(array):
        key = row.tobytes()
        previous = first_index_by_vector.get(key)
        if previous is None:
            first_index_by_vector[key] = index
            continue
        if inputs is not None:
            if str(inputs[previous]) != str(inputs[index]):
                raise ValueError(
                    f"Vector {index} duplicates vector {previous} for distinct inputs"
                )
        elif allow_identical is not True:
            raise ValueError(
                f"Vector {index} duplicates vector {previous}; input identity is unknown"
            )

    return array
