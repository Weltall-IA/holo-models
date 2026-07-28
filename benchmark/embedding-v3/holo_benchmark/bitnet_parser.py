"""BitNet embedding output parser — strict full-consumption implementation.

Parses the exact output format of `llama-embedding --embd-output-format array`:
a single line containing [[f1,f2,...,fD],[f1,f2,...,fD],...].

The parser consumes the ENTIRE stdout. Any residual bytes, ambiguous text,
truncation, duplicate vectors for distinct inputs, NaN, infinity, or zero
norm causes an immediate ValueError.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np


def parse_bitnet_array_output(
    text: str,
    expected_count: int,
    expected_dim: int,
    *,
    allow_identical: bool = False,
) -> np.ndarray:
    """Parse the exact `[[...],[...]]` output of llama-embedding --embd-output-format array.

    Strict rules:
      - All non-whitespace content must be a single valid [[...],[...],...] block.
      - Exactly `expected_count` vectors, each of length `expected_dim`.
      - No NaN, no infinity, no zero-norm vectors.
      - L2-normalized within tolerance (0.05).
      - No duplicate vectors for distinct inputs (unless allow_identical=True).
    """
    if not text:
        raise ValueError("BitNet output is empty")

    # Strip only leading/trailing whitespace; everything else must be structure
    stripped = text.strip()
    if not stripped:
        raise ValueError("BitNet output is whitespace-only")

    # The canonical format is: [[f,f,...],[f,f,...]]
    # No other content is permitted outside the outer brackets.
    if not stripped.startswith("[[") or not stripped.endswith("]]"):
        raise ValueError(
            f"BitNet output does not match expected [[...],[...]] format. "
            f"First 100 chars: {stripped[:100]!r}  Last 100 chars: {stripped[-100:]!r}"
        )

    # Split into individual vector strings: "[f,f,...]"
    # The outer [[...]] must decompose cleanly into inner [f,f,...] blocks.
    inner = stripped[1:-1]  # strip outer [[ and ]]
    if not inner.startswith("[") or not inner.endswith("]"):
        raise ValueError(
            f"Inner content does not start with [ or end with ]. "
            f"First 80: {inner[:80]!r}  Last 80: {inner[-80:]!r}"
        )

    # Split on "],[" to get individual vectors
    parts = inner.split("],[")

    vectors = []
    for i, part in enumerate(parts):
        # Clean brackets
        vstr = part.strip()
        if i == 0:
            vstr = vstr[1:]  # remove leading [
        if i == len(parts) - 1:
            vstr = vstr[:-1]  # remove trailing ]
        vstr = vstr.strip()

        if not vstr:
            raise ValueError(f"Empty vector string at position {i}")

        # Parse comma-separated floats, allowing whitespace
        vals = []
        for tok in vstr.split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                v = float(tok)
            except ValueError:
                raise ValueError(
                    f"Cannot parse float at vector {i}: {tok!r}"
                )
            if not math.isfinite(v):
                raise ValueError(
                    f"Non-finite value at vector {i}: {tok!r}"
                )
            vals.append(v)

        if len(vals) != expected_dim:
            raise ValueError(
                f"Vector {i} has {len(vals)} dimensions, expected {expected_dim}"
            )
        vectors.append(vals)

    n_vectors = len(vectors)
    if n_vectors != expected_count:
        raise ValueError(
            f"Got {n_vectors} vectors, expected {expected_count}"
        )

    arr = np.array(vectors, dtype=np.float32)

    # Zero-norm check
    norms = np.linalg.norm(arr, axis=1)
    zero_mask = norms < 1e-12
    if np.any(zero_mask):
        bad = int(np.argmax(zero_mask))
        raise ValueError(f"Vector {bad} has zero norm")

    # L2-normalization check (within tolerance)
    max_dev = float(np.max(np.abs(norms - 1.0)))
    if max_dev > 0.05:
        raise ValueError(
            f"Vectors not L2-normalized: max norm deviation = {max_dev:.4f}"
        )

    # Duplicate detection for distinct inputs (warn if any pair is identical)
    if not allow_identical:
        seen = {}
        for i, vec in enumerate(vectors):
            key = tuple(vec)
            if key in seen:
                raise ValueError(
                    f"Vector {i} is identical to vector {seen[key]} "
                    f"(possible duplication for distinct inputs)"
                )
            seen[key] = i

    return arr


def detect_bitnet_dim(profile_id: str) -> int:
    """Return expected dimension for a BitNet profile, configured explicitly."""
    dim_map = {
        "bitnet_06b_current": 1024,
        "bitnet_270m_current": 640,
    }
    if profile_id in dim_map:
        return dim_map[profile_id]
    raise ValueError(
        f"Unknown BitNet profile: {profile_id}. "
        f"Known profiles: {list(dim_map.keys())}"
    )
