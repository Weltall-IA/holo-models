from __future__ import annotations

import argparse
import json
from pathlib import Path

from holo_benchmark.coverage_validation import apply_validation, validate_inventory_file


PROJECT_ROOT = Path(__file__).resolve().parent


def _atomic_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida cobertura, evidências e consistência com resultados concluídos")
    parser.add_argument(
        "--inventory",
        default=str(PROJECT_ROOT / "local_model_inventory.json"),
    )
    parser.add_argument("--write", action="store_true", help="grava o bloco coverage_validation e corrige coverage_complete")
    args = parser.parse_args()

    path = Path(args.inventory)
    payload, findings = validate_inventory_file(path, project_root=PROJECT_ROOT)
    if args.write:
        _atomic_json(path, apply_validation(payload, findings))
    print(json.dumps(
        {
            "passed": not findings,
            "finding_count": len(findings),
            "findings": [
                {"model_id": item.model_id, "code": item.code, "message": item.message}
                for item in findings
            ],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0 if not findings else 2


if __name__ == "__main__":
    raise SystemExit(main())
