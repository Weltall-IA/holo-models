from __future__ import annotations

import argparse
import json
from pathlib import Path

from holo_benchmark.local_inventory import write_inventory

PROJECT_ROOT = Path(__file__).resolve().parent


def find_repo_root(start: Path) -> Path:
    for candidate in [start.resolve(), *start.resolve().parents]:
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("checkout Git não encontrado")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventário completo dos modelos locais do Projeto Holo")
    parser.add_argument("--root", action="append", default=[], help="raiz adicional a escanear; pode ser repetida")
    parser.add_argument("--skip-ollama", action="store_true")
    parser.add_argument("--output-json", default=str(PROJECT_ROOT / "local_model_inventory.json"))
    parser.add_argument("--output-report", default=str(PROJECT_ROOT / "LOCAL_MODEL_INVENTORY_REPORT.md"))
    args = parser.parse_args()

    payload = write_inventory(
        repo_root=find_repo_root(PROJECT_ROOT),
        output_json=Path(args.output_json),
        output_report=Path(args.output_report),
        extra_roots=[Path(value) for value in args.root],
        include_ollama=not args.skip_ollama,
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
