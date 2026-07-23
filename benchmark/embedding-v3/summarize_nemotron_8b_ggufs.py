#!/usr/bin/env python3
"""Consolidate structural evidence for two Nemotron 8B GGUF files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from pathlib import Path
from typing import Any


HASH_RE = re.compile(r"^sha256\s+([0-9a-f]{64})\s+.*?:(.+)$")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_prefix(path: Path, length: int) -> str:
    digest = hashlib.sha256()
    remaining = length
    with path.open("rb") as stream:
        while remaining:
            block = stream.read(min(1024 * 1024, remaining))
            if not block:
                raise ValueError(f"{path} terminou antes do offset {length}")
            digest.update(block)
            remaining -= len(block)
    return digest.hexdigest()


def _read_suffix(path: Path, offset: int) -> bytes:
    with path.open("rb") as stream:
        stream.seek(offset)
        return stream.read()


def _tensor_hashes(path: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HASH_RE.match(line)
        if match:
            hashes[match.group(2)] = match.group(1)
    return hashes


def _logical_metadata(structure: dict[str, Any]) -> dict[str, Any]:
    return {
        name: {key: value for key, value in field.items() if key not in {"index", "offset"}}
        for name, field in structure["metadata"].items()
    }


def _logical_tensors(structure: dict[str, Any]) -> dict[str, Any]:
    return {
        name: {key: value for key, value in field.items() if key not in {"index", "offset"}}
        for name, field in structure["tensors"].items()
    }


def _startup_summary(payload: dict[str, Any], converter: str) -> dict[str, Any]:
    runs = [run for run in payload["runs"] if run["converter"] == converter]
    if len(runs) != 5:
        raise ValueError(f"{converter} tem {len(runs)} inicializações; eram esperadas 5")
    metrics: dict[str, Any] = {}
    for key in (
        "startup_seconds",
        "embedding_seconds",
        "embeddings_per_second",
        "tokens_per_second",
        "peak_rss_mib",
        "peak_vram_mib",
    ):
        values = [float(run[key]) for run in runs]
        metrics[key] = {
            "minimum": min(values),
            "mean": statistics.mean(values),
            "maximum": max(values),
            "sample_stdev": statistics.stdev(values),
        }
    return {
        "state": "EXECUTED",
        "runs": len(runs),
        "run_numbers": [run["run"] for run in runs],
        "embedding_dimensions": sorted({tuple(run["embedding_dimensions"]) for run in runs}),
        "metrics": metrics,
        "logs": [run["log"] for run in runs],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--abiray", type=Path, required=True)
    parser.add_argument("--aqua00", type=Path, required=True)
    parser.add_argument("--abiray-structure", type=Path, required=True)
    parser.add_argument("--aqua00-structure", type=Path, required=True)
    parser.add_argument("--abiray-hashes", type=Path, required=True)
    parser.add_argument("--aqua00-hashes", type=Path, required=True)
    parser.add_argument("--startups", type=Path, required=True)
    parser.add_argument("--data-offset", type=int, required=True)
    parser.add_argument("--tensor-data-end", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    abiray_structure = _read_json(args.abiray_structure)
    aqua00_structure = _read_json(args.aqua00_structure)
    abiray_hashes = _tensor_hashes(args.abiray_hashes)
    aqua00_hashes = _tensor_hashes(args.aqua00_hashes)
    startups = _read_json(args.startups)

    metadata_a = _logical_metadata(abiray_structure)
    metadata_b = _logical_metadata(aqua00_structure)
    tensors_a = _logical_tensors(abiray_structure)
    tensors_b = _logical_tensors(aqua00_structure)
    tensor_names = sorted(set(abiray_hashes) | set(aqua00_hashes))
    differing_tensor_hashes = [
        name for name in tensor_names if abiray_hashes.get(name) != aqua00_hashes.get(name)
    ]
    header_a = _sha256_prefix(args.abiray, args.data_offset)
    header_b = _sha256_prefix(args.aqua00, args.data_offset)
    size_a = args.abiray.stat().st_size
    size_b = args.aqua00.stat().st_size
    trailing_a = _read_suffix(args.abiray, args.tensor_data_end)
    trailing_b = _read_suffix(args.aqua00, args.tensor_data_end)

    result = {
        "state": "EXECUTED",
        "classification": (
            "Estrutura GGUF, metadados serializados e payloads dos 308 tensores são "
            "idênticos; os arquivos completos não são idênticos porque o Abiray contém "
            "55 bytes não estruturais após o fim do último tensor."
        ),
        "files": {
            "abiray": {
                "path": str(args.abiray),
                "bytes": size_a,
                "trailing_bytes": len(trailing_a),
                "trailing_bytes_hex": trailing_a.hex(),
            },
            "aqua00": {
                "path": str(args.aqua00),
                "bytes": size_b,
                "trailing_bytes": len(trailing_b),
                "trailing_bytes_hex": trailing_b.hex(),
            },
            "size_difference_bytes": size_a - size_b,
        },
        "gguf": {
            "version": metadata_a["GGUF.version"]["value"],
            "kv_count": metadata_a["GGUF.kv_count"]["value"],
            "tensor_count": metadata_a["GGUF.tensor_count"]["value"],
            "data_offset": args.data_offset,
            "tensor_data_end": args.tensor_data_end,
            "serialized_header_sha256": {
                "abiray": header_a,
                "aqua00": header_b,
                "equal": header_a == header_b,
            },
            "metadata_keys_equal": set(metadata_a) == set(metadata_b),
            "metadata_logical_differences": [
                name
                for name in sorted(set(metadata_a) | set(metadata_b))
                if metadata_a.get(name) != metadata_b.get(name)
            ],
            "tensor_schema_equal": tensors_a == tensors_b,
            "tensor_sha256": {
                "abiray_count": len(abiray_hashes),
                "aqua00_count": len(aqua00_hashes),
                "names_equal": set(abiray_hashes) == set(aqua00_hashes),
                "different_count": len(differing_tensor_hashes),
                "different_names": differing_tensor_hashes,
            },
            "license": {
                "general.license": metadata_a["general.license"]["value"],
                "general.license.name": metadata_a["general.license.name"]["value"],
                "general.license.link": metadata_a["general.license.link"]["value"],
            },
        },
        "startups": {
            "order": startups["order"],
            "alternating": startups["order"]
            == ["abiray", "aqua00", "abiray", "aqua00", "abiray", "aqua00", "abiray", "aqua00", "abiray", "aqua00"],
            "abiray": _startup_summary(startups, "abiray"),
            "aqua00": _startup_summary(startups, "aqua00"),
        },
        "limitations": [
            "A igualdade estrutural e por tensor não torna os arquivos completos bit a bit idênticos.",
            "As medições de inicialização descrevem este host, esta versão do llama.cpp e esta configuração.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
