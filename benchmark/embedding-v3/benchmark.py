from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from holo_benchmark.corpus import (
    CORPUS_VERSION,
    build_corpus,
    build_queries,
    build_review_checklist,
    freeze_hashes,
    read_jsonl,
    validate_corpus,
    validate_semantic_review,
    write_jsonl,
)
from holo_benchmark.inventory import collect, gate0_passes, render_report, write_outputs

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data" / CORPUS_VERSION

def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)

def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    env = os.environ.get("HOLO_MODELS_REPO")
    if env:
        path = Path(env).expanduser().resolve()
        if (path / ".git").exists():
            return path
    raise RuntimeError("checkout Git não encontrado; defina HOLO_MODELS_REPO")

def confirm_force() -> None:
    if not sys.stdin.isatty():
        raise RuntimeError("--force-recompute exige terminal interativo")
    answer = input("Digite RECOMPUTAR para confirmar: ").strip()
    if answer != "RECOMPUTAR":
        raise RuntimeError("recomputação cancelada")

def gate0(args: argparse.Namespace) -> int:
    repo_root = find_repo_root(PROJECT_ROOT)
    system_info, environment = collect(
        project_root=PROJECT_ROOT,
        repo_root=repo_root,
        perform_cuda_allocation=not args.dry_run,
    )
    write_outputs(PROJECT_ROOT, system_info, environment)
    report = render_report(system_info, environment, args.dry_run)
    (PROJECT_ROOT / "GATE_0_REPORT.md").write_text(report, encoding="utf-8")
    ok, errors = gate0_passes(system_info, environment)
    status = {
        "gate_0": "PASS" if ok else "BLOCKED",
        "gate_1": "PENDING",
        "gates_2_to_6": "BLOCKED_BY_DIRECTOR",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "errors": errors,
    }
    atomic_json(PROJECT_ROOT / "gate_status.json", status)
    print(report)
    return 0 if ok else 2

def _write_gate1_report(validation: dict, review: dict | None, hashes: dict | None) -> None:
    completed = bool(validation.get("all_automated_checks_passed")) and bool(review and review.get("complete")) and hashes is not None
    lines = [
        "# GATE 1 REPORT",
        "",
        f"- resultado: {'PASS' if completed else 'AWAITING_REVIEW' if validation.get('all_automated_checks_passed') else 'BLOCKED'}",
        f"- obras: {validation['counts']['works']}",
        f"- chunks: {validation['counts']['chunks']}",
        f"- consultas: {validation['counts']['queries']}",
        f"- tokens estimados min/média/mediana/máx: {validation['token_distribution']['min']} / {validation['token_distribution']['mean']} / {validation['token_distribution']['median']} / {validation['token_distribution']['max']}",
        f"- sobreposição máxima 5-gram Jaccard: {validation['template_overlap']['max_jaccard_5gram']}",
        f"- erros automáticos: {len(validation['errors'])}",
        f"- avisos automáticos: {len(validation['warnings'])}",
        f"- revisão semântica: {review if review else 'pendente'}",
        f"- SHA-256 conjunto: {hashes['combined_sha256'] if hashes else 'pendente'}",
        "",
        "Nenhum embedding foi executado, nenhum checkpoint foi baixado e nenhuma chamada à Voyage foi realizada.",
        "",
    ]
    (PROJECT_ROOT / "GATE_1_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    brief = [
        "# DIRECTOR BRIEF — Gates 0 e 1",
        "",
        "- Gate 0: leia `GATE_0_REPORT.md`.",
        f"- Gate 1: {'concluído' if completed else 'pendente/bloqueado'}.",
        f"- corpus: `{CORPUS_VERSION}`",
        "- contagens: 30 obras, 600 chunks, 150 consultas.",
        f"- hash conjunto: `{hashes['combined_sha256'] if hashes else 'pendente'}`",
        "- decisão pendente: autorizar ou negar Gate 2 após revisão.",
        "- nenhum modelo foi escolhido.",
        "",
    ]
    (PROJECT_ROOT / "DIRECTOR_BRIEF.md").write_text("\n".join(brief), encoding="utf-8")

def gate1(args: argparse.Namespace) -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    corpus_path = DATA_DIR / "corpus.jsonl"
    queries_path = DATA_DIR / "queries.jsonl"
    validation_path = DATA_DIR / "validation.json"
    checklist_path = DATA_DIR / "semantic_review_checklist.json"
    review_path = DATA_DIR / "semantic_review.json"
    hashes_path = DATA_DIR / "hashes.json"

    if args.force_recompute:
        confirm_force()
    frozen = hashes_path.exists()
    if frozen and not args.force_recompute:
        print("Corpus já congelado. Use --force-recompute com confirmação explícita para recriar.", file=sys.stderr)
        return 2

    if not args.resume or not corpus_path.exists() or not queries_path.exists():
        chunks, id_map, quote_map = build_corpus()
        queries = build_queries(id_map, quote_map)
        validation = validate_corpus(chunks, queries)
        write_jsonl(corpus_path, chunks)
        write_jsonl(queries_path, queries)
        atomic_json(validation_path, validation)
        checklist = build_review_checklist(chunks, queries)
        atomic_json(checklist_path, checklist)
        if not validation["all_automated_checks_passed"]:
            _write_gate1_report(validation, None, None)
            print(json.dumps(validation, ensure_ascii=False, indent=2))
            return 2
        if review_path.exists() and args.force_recompute:
            review_path.unlink()
        _write_gate1_report(validation, None, None)
        print(f"Corpus candidato gerado. Preencha {review_path} a partir de {checklist_path} e execute novamente com --resume.")
        return 3

    chunks = read_jsonl(corpus_path)
    queries = read_jsonl(queries_path)
    validation = validate_corpus(chunks, queries)
    atomic_json(validation_path, validation)
    checklist = json.loads(checklist_path.read_text(encoding="utf-8"))
    review = validate_semantic_review(review_path, checklist)
    if not validation["all_automated_checks_passed"] or not review["complete"]:
        _write_gate1_report(validation, review, None)
        print(json.dumps({"validation": validation, "semantic_review": review}, ensure_ascii=False, indent=2))
        return 2
    hashes = freeze_hashes(DATA_DIR, review)
    atomic_json(hashes_path, hashes)
    for path in (corpus_path, queries_path, validation_path, review_path, hashes_path):
        path.chmod(0o444)
    _write_gate1_report(validation, review, hashes)
    status = {
        "gate_0": "SEE_GATE_0_REPORT",
        "gate_1": "PASS",
        "gates_2_to_6": "BLOCKED_BY_DIRECTOR",
        "corpus_version": CORPUS_VERSION,
        "combined_sha256": hashes["combined_sha256"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_json(PROJECT_ROOT / "gate_status.json", status)
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark de embeddings e reranking do Projeto Holo")
    parser.add_argument("--gate", type=int, required=True, choices=range(0, 7))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--models", default="")
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="auto")
    parser.add_argument("--max-documents", type=int)
    parser.add_argument("--max-queries", type=int)
    parser.add_argument("--skip-api", action="store_true")
    parser.add_argument("--only-api", action="store_true")
    parser.add_argument("--rerank-k", type=int, choices=[10, 20, 50])
    parser.add_argument("--force-recompute", action="store_true")
    return parser

def main() -> int:
    args = build_parser().parse_args()
    if args.only_api and args.skip_api:
        print("--only-api e --skip-api são incompatíveis", file=sys.stderr)
        return 2
    if args.gate == 0:
        return gate0(args)
    if args.gate == 1:
        return gate1(args)
    print(f"Gate {args.gate} bloqueado: exige autorização explícita do diretor e implementação posterior.", file=sys.stderr)
    return 4

if __name__ == "__main__":
    raise SystemExit(main())
