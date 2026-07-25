#!/usr/bin/env python3
"""CLI runner for production profile integration tests."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from holo_benchmark.production_profile_runtime import (
    DEFAULT_PROFILES_PATH,
    _find_gguf_path,
    _load_profiles,
    _find_profile,
    _sanitize,
    run_profile,
    run_all_profiles,
    summarize_results,
)

REPO = Path(__file__).resolve().parent.parent.parent
BENCH_RESULTS = REPO / "benchmark/embedding-v3/results/production_profile_integration"

DEFAULT_TEXTS = [
    "O capitão ordenou uma varredura completa do setor antes de iniciar a aproximação.",
    "A mensagem cifrada foi decodificada pela IA de bordo em menos de um ciclo.",
    "Os sensores detectaram uma anomalia gravitacional próxima ao terceiro planeta.",
    "A tripulação foi colocada em estado de prontidão máxima após o alerta.",
    "O conselho da federação debateu a aliança por três rotações padrão.",
]

DEFAULT_QUERIES = [
    "alerta de segurança na nave",
    "comunicação interceptada",
]

SMOKE_DOCUMENTS = [
    "O holodeque simulou uma floresta tropical com sons, cheiros e brisa.",
    "O engenheiro-chefe reportou falha no núcleo de warp durante o teste.",
    "A delegação vulcana propôs um tratado de não interferência.",
    "O tenente analisou os padrões de energia do objeto desconhecido.",
    "O protocolo de primeiro contato foi ativado automaticamente.",
    "A biossinatura indicava presença de carbono e nitrogênio na atmosfera.",
    "O oficial científico classificou o artefato como pré-guerra estelar.",
    "A transmissão subespacial continha coordenadas de uma base abandonada.",
]

SMOKE_QUERIES = [
    "falha no motor de dobra",
    "primeiro contato com civilização",
    "analisar ruína alienígena",
]


def _expect_ffi_dtype(value: object) -> str:
    return str(type(value))


def _run_smoke(profiles: list[dict], args: argparse.Namespace) -> list[dict]:
    results = []
    texts = SMOKE_DOCUMENTS[:3]
    qtexts = SMOKE_QUERIES[:2]
    for p in profiles:
        pid = p["id"]
        evaluation = "evaluation" in pid or "nemotron" in pid
        if pid == "quality_external_optional":
            r = run_profile(
                profiles, pid, texts, input_type="document",
                evaluation_mode=False, allow_external_api=False)
            results.append(r.to_evidence())
            continue
        r = run_profile(
            profiles, pid, texts, input_type="document",
            evaluation_mode=evaluation, allow_external_api=False)
        results.append(r.to_evidence())
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Runner de integração dos perfis de retrieval")
    parser.add_argument("--profile", default=None,
                        help="ID do perfil (executa um único perfil)")
    parser.add_argument("--evaluation-mode", action="store_true",
                        help="Permite executar perfis desabilitados para avaliação")
    parser.add_argument("--input", type=Path, default=None,
                        help="Arquivo JSON com payload de entrada")
    parser.add_argument("--output", type=Path, default=None,
                        help="Arquivo JSON de saída")
    parser.add_argument("--smoke", action="store_true",
                        help="Executa smoke test com textos do corpus congelado")
    parser.add_argument("--dry-run", action="store_true",
                        help="Valida configuração sem carregar pesos")
    parser.add_argument("--allow-external-api", action="store_true",
                        help="Permite API externa (não isoladamente suficiente)")
    args = parser.parse_args()

    profiles = _load_profiles()
    BENCH_RESULTS.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        for p in profiles:
            pid = p["id"]
            emb = p.get("embedding", {})
            bid = emb.get("backend", "?")
            dim = emb.get("dimension", 0)
            gguf = _find_gguf_path(p)
            weight_ok = gguf is not None and gguf.exists() if bid == "llama.cpp" else None
            print(f"PROFILE {pid}: backend={bid} dim={dim} weight_exists={weight_ok}")
        return 0

    if args.smoke:
        results = _run_smoke(profiles, args)
    elif args.profile:
        texts = DEFAULT_TEXTS
        input_type = "document"
        if args.input:
            with open(args.input) as f:
                payload = json.load(f)
            texts = payload.get("texts", texts)
            input_type = payload.get("input_type", "document")
        r = run_profile(
            profiles, args.profile, texts, input_type=input_type,
            evaluation_mode=args.evaluation_mode,
            allow_external_api=args.allow_external_api)
        results = [r.to_evidence()]
    else:
        texts = DEFAULT_TEXTS
        results = _run_smoke(profiles, args)

    summary = summarize_results(results)

    results_dir = BENCH_RESULTS
    for r in results:
        pid = r["profile_id"]
        out = results_dir / f"{pid.replace('-', '_')}.json"
        with open(out, "w") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)

    summary_path = results_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    if args.output:
        out = args.output
        with open(out, "w") as f:
            json.dump(results if len(results) > 1 else results[0],
                      f, ensure_ascii=False, indent=2)

    for r in results:
        s = r.get("status", "?")
        pid = r.get("profile_id", "?")
        icon = "✅" if s == "PASSED" else ("⛔" if s == "BLOCKED" else "❌")
        print(f"{icon} {pid}: {s}")
        if r.get("reason"):
            print(f"   motivo: {r['reason']}")

    return 0 if all(r.get("status") == "PASSED"
                     for r in results if r.get("profile_id") != "quality_external_optional") else 1


if __name__ == "__main__":
    raise SystemExit(main())
