#!/usr/bin/env python3
"""Update only the two canonical README decision tables from canonical data."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

TABLE1_HEADING = "### Tabela 1 — embeddings bons ou reutilizáveis"
TABLE2_HEADING = "### Tabela 2 — blacklist de artefatos e configurações"
REVISION_PREFIX = "Revisão desta classificação: **"

TABLE1_SPECS: Sequence[tuple[str, str, str, str]] = (
    (
        "nemotron_3_embed_1b_nvfp4",
        "A",
        "alta",
        "Melhor baseline local; vLLM/NVFP4; melhor pipeline atual usa NVIDIA Nemotron Rerank.",
    ),
    (
        "voyage-4-large",
        "A",
        "média",
        "API; resultado completo, sem pipeline sob o mesmo ID.",
    ),
    (
        "voyage_4_large_1024_float32",
        "A",
        "média",
        "Variante histórica 1024/F32; melhor reranker Voyage 2.5.",
    ),
    (
        "nemotron_3_embed_1b_q4_k_m_gguf",
        "A",
        "alta",
        "GGUF reproduzível; menor consumo e cold start; pipeline Qwen publicado.",
    ),
    (
        "voyage4_nano_2048_int8",
        "A",
        "média",
        "Variante histórica INT8; desempenho forte.",
    ),
    (
        "embeddinggemma",
        "A",
        "alta",
        "Resultado coerente com a família; melhor pipeline usa NVIDIA Nemotron Rerank.",
    ),
    (
        "pplx_embed_v1_4b_q8_0",
        "A",
        "média-alta",
        "Resultado histórico válido; novas variantes seguem NVFP4/Q4 antes de Q8.",
    ),
    (
        "voyage4_nano_2048_float32",
        "A",
        "média",
        "Variante histórica 2048/F32.",
    ),
    (
        "voyage4_nano",
        "A",
        "alta",
        "Bom equilíbrio entre qualidade e custo.",
    ),
    (
        "voyage4_nano_1024_float32",
        "A",
        "média",
        "Variante histórica 1024/F32.",
    ),
    (
        "voyage-context-4",
        "A",
        "média",
        "API; baseline completo e pipeline Qwen recomposto offline.",
    ),
    (
        "nomic_embed_text_v2_moe_q4",
        "A",
        "alta",
        "Escolha operacional validada; melhor pipeline usa NVIDIA Nemotron Rerank.",
    ),
    (
        "embeddinggemma_768_float32",
        "A",
        "média",
        "Variante histórica; melhor pipeline histórico usa Voyage 2.5.",
    ),
    (
        "embeddinggemma_gguf",
        "A",
        "alta",
        "Baixo consumo e resultado coerente.",
    ),
    (
        "bge_m3_dense",
        "A",
        "alta",
        "Boa cobertura; modelo oficial recomenda híbrido com reranking.",
    ),
    (
        "snowflake_arctic_embed_l_v2_q4",
        "A",
        "média-alta",
        "Resultado compatível com modelo multilíngue forte.",
    ),
    (
        "qwen3_embedding_4b_q8_0",
        "A",
        "alta",
        "Melhor MRR@10 reranqueado publicado; novas seleções devem preferir NVFP4/Q4.",
    ),
    (
        "colibri_ptbr",
        "B",
        "alta",
        "Especializado em PT-BR; forte com NVIDIA Nemotron Rerank.",
    ),
    (
        "jina_embeddings_v5_text_small",
        "B",
        "média-alta",
        "Resultado compatível com MMTEB declarado pelo modelo.",
    ),
    (
        "octen_embedding_8b_q8_0",
        "B",
        "média",
        "Resultado histórico; Q8 não deve ser repetido se houver Q4/NVFP4.",
    ),
    (
        "granite_embedding_311m_r2",
        "B",
        "média-alta",
        "Opção compacta; ganho grande com NVIDIA Nemotron Rerank.",
    ),
    (
        "pplx_embed_v1_06b_native",
        "B",
        "média-alta",
        "Compacto e forte com reranker.",
    ),
    (
        "giga_embeddings_instruct",
        "B",
        "média",
        "Útil com instrução; suporte oficial é sobretudo russo/inglês.",
    ),
    (
        "bidirlm_17b_embedding",
        "B",
        "média-alta",
        "Ordem relativa coerente com MTEB-BR.",
    ),
    (
        "multilingual_e5_large_instruct",
        "B",
        "alta",
        "Requer instrução de consulta; forte com reranker.",
    ),
    (
        "qwen3_embedding_06",
        "C",
        "alta",
        "Baseline modesto; útil com reranker.",
    ),
    (
        "qwen3_embedding_06_gguf",
        "C",
        "alta",
        "Q8 histórico aceitável pelo tamanho pequeno; controle GGUF coerente.",
    ),
    (
        "lfm_25_embedding_350m_q4_k_m_official",
        "C",
        "alta",
        "Reexecução oficial com CLS e prefixos corretos; reutilizável com Qwen.",
    ),
    (
        "gte_multilingual_base",
        "C",
        "alta",
        "Baseline fraco no corpus, mas pipeline útil e fonte oficial forte.",
    ),
    (
        "granite_embedding_97m_r2",
        "C",
        "média-alta",
        "Muito rápido; manter apenas para perfil leve/reranqueado.",
    ),
)

TABLE2_SPECS: Sequence[tuple[str, str, str, str]] = (
    (
        "qwen3_embedding_8b_gguf",
        "AUDIT_REQUIRED",
        "O Q8_0 8B ficou abaixo do 4B; faltam controle dimensional e instrução exata no artefato.",
        "Reexecutar em Q4_K_M, com instrução oficial registrada, 4096 e 1024 dimensões e cache novo. Não repetir Q8_0.",
    ),
    (
        "nemotron_8b_abiray_q4",
        "BLACKLIST_PROVISÓRIA",
        "Candidates e métricas idênticos ao Aqua00; sem hash, runtime, pooling, dimensão ou comando.",
        "Reexecutar do zero em NVFP4 comprovadamente 8B; na ausência, Q4_K_M. Q8 é proibido.",
    ),
    (
        "nemotron_8b_aqua00_q4",
        "BLACKLIST_PROVISÓRIA",
        "Candidates e métricas idênticos ao Abiray; proveniência insuficiente.",
        "Reexecutar do zero em NVFP4 comprovadamente 8B; na ausência, Q4_K_M. Q8 é proibido.",
    ),
    (
        "lfm_25_embedding_350m_q4",
        "BLACKLIST_DO_ARTEFATO",
        "Artefato antigo não prova prefixos nem pooling CLS; a execução oficial corrigida usa outro ID e permanece na Tabela 1.",
        "Não reabilitar este artefato. Reutilizar somente lfm_25_embedding_350m_q4_k_m_official ou uma nova execução equivalente.",
    ),
    (
        "kalm_embedding_gemma3_12b_q4",
        "BLACKLIST_DO_ARTEFATO",
        "Resultado incompatível com o topo do MTEB-BR; metadados de execução ausentes.",
        "Reexecução reproduzível em NVFP4 confiável ou Q4 com instruções e pooling oficiais.",
    ),
    (
        "kalm_embedding_gemma3_12b_i1_q4",
        "BLACKLIST_DO_ARTEFATO",
        "Execução local catastrófica e sem proveniência suficiente.",
        "Reexecução reproduzível; não herdar o resultado do outro Q4.",
    ),
    (
        "boom_4b_v1_q8_0",
        "BLACKLIST_DO_ARTEFATO",
        "Q8 local indica configuração ou artefato inválido para uma família externamente forte.",
        "Reexecutar em NVFP4 ou Q4, com last-token pooling, instrução e hash do peso. Não repetir Q8.",
    ),
    (
        "bitnet_270m_current",
        "GATE_FAIL",
        "Execução completa e reproduzível, mas qualidade insuficiente: HR@50 0,8467 e alta taxa de erro em hard negatives.",
        "Novo peso, runtime ou protocolo precisa superar o gate completo; não promover este artefato.",
    ),
    (
        "bitnet_06b_current",
        "GATE_FAIL",
        "Execução completa e reproduzível, mas qualidade insuficiente: HR@50 0,7667.",
        "Novo peso, runtime ou protocolo precisa superar o gate completo; não promover este artefato.",
    ),
)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def format_metric(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.4f}"
    return "—"


def raw_map(canonical: Mapping[str, Any]) -> Mapping[str, Any]:
    value = canonical.get("raw_embedding_profiles_by_id")
    if not isinstance(value, Mapping):
        raise ValueError("canonical raw_embedding_profiles_by_id is missing")
    return value


def best_pipeline_map(canonical: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    value = canonical.get("embedding_index")
    if not isinstance(value, list):
        raise ValueError("canonical embedding_index is missing")
    for item in value:
        if not isinstance(item, Mapping):
            continue
        profile = item.get("embedding")
        best = item.get("best_published_pipeline")
        if isinstance(profile, str) and isinstance(best, Mapping):
            result[profile] = best
    return result


def table1(canonical: Mapping[str, Any]) -> str:
    raw = raw_map(canonical)
    best = best_pipeline_map(canonical)
    lines = [
        "| Perfil | MRR@10 sozinho | Melhor MRR@10 com reranker | Faixa | Confiança | Decisão |",
        "|---|---:|---:|---|---|---|",
    ]
    for profile, band, confidence, decision in TABLE1_SPECS:
        record = raw.get(profile)
        if not isinstance(record, Mapping):
            raise ValueError(f"raw profile is missing from canonical data: {profile}")
        metrics = record.get("metrics")
        if not isinstance(metrics, Mapping):
            raise ValueError(f"raw metrics are missing for: {profile}")
        best_record = best.get(profile)
        best_metrics = (
            best_record.get("metrics")
            if isinstance(best_record, Mapping)
            and isinstance(best_record.get("metrics"), Mapping)
            else {}
        )
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} |".format(
                profile,
                format_metric(metrics.get("mrr_at_10")),
                format_metric(best_metrics.get("mrr_at_10")),
                band,
                confidence,
                decision,
            )
        )
    return "\n".join(lines)


def table2(canonical: Mapping[str, Any]) -> str:
    raw = raw_map(canonical)
    lines = [
        "| Perfil local | MRR@10 | Estado | Motivo | Condição para reabilitação |",
        "|---|---:|---|---|---|",
    ]
    for profile, state, reason, rehabilitation in TABLE2_SPECS:
        record = raw.get(profile)
        if not isinstance(record, Mapping):
            raise ValueError(f"blacklisted profile is missing: {profile}")
        metrics = record.get("metrics")
        if not isinstance(metrics, Mapping):
            raise ValueError(f"blacklisted profile metrics are missing: {profile}")
        lines.append(
            "| `{}` | {} | `{}` | {} | {} |".format(
                profile,
                format_metric(metrics.get("mrr_at_10")),
                state,
                reason,
                rehabilitation,
            )
        )
    return "\n".join(lines)


def replace_markdown_table(text: str, heading: str, replacement: str) -> str:
    heading_index = text.find(heading)
    if heading_index < 0:
        raise ValueError(f"README heading was not found: {heading}")
    table_start = text.find("\n|", heading_index)
    if table_start < 0:
        raise ValueError(f"README table was not found after: {heading}")
    table_start += 1
    table_end = text.find("\n\n", table_start)
    if table_end < 0:
        raise ValueError(f"README table terminator was not found: {heading}")
    return text[:table_start] + replacement + text[table_end:]


def update_readme(text: str, canonical: Mapping[str, Any], revision: str) -> str:
    updated = replace_markdown_table(text, TABLE1_HEADING, table1(canonical))
    updated = replace_markdown_table(updated, TABLE2_HEADING, table2(canonical))
    revision_start = updated.find(REVISION_PREFIX)
    if revision_start < 0:
        raise ValueError("README classification revision line was not found")
    revision_end = updated.find("**.", revision_start)
    if revision_end < 0:
        raise ValueError("README classification revision terminator was not found")
    revision_end += 3
    replacement = f"Revisão desta classificação: **{revision}**."
    updated = updated[:revision_start] + replacement + updated[revision_end:]
    if updated.count(TABLE1_HEADING) != 1 or updated.count(TABLE2_HEADING) != 1:
        raise ValueError("README canonical headings are not unique")
    return updated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[3]
    parser.add_argument(
        "--canonical",
        type=Path,
        default=root / "benchmark" / "embedding-v3" / "ALL_BENCHMARK_RESULTS.json",
    )
    parser.add_argument(
        "--readme",
        type=Path,
        default=root / "benchmark" / "embedding-v3" / "README.md",
    )
    parser.add_argument("--revision", default=date.today().isoformat())
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    canonical = load_json(args.canonical)
    original = args.readme.read_text(encoding="utf-8")
    updated = update_readme(original, canonical, args.revision)
    if not args.validate_only:
        args.readme.write_text(updated, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "readme": str(args.readme),
                "table1_rows": len(TABLE1_SPECS),
                "table2_rows": len(TABLE2_SPECS),
                "revision": args.revision,
                "changed": updated != original,
                "validate_only": args.validate_only,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
