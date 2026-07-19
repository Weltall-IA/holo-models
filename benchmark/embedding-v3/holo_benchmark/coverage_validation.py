from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json

TERMINAL_STATUSES = {
    "BENCHMARKED",
    "HEALTHCHECK_PASSED",
    "BLOCKED",
    "LEGACY_EXCLUDED",
    "NOT_APPLICABLE",
}
PENDING_STATUSES = {"UNASSESSED", "PENDING_BENCHMARK", "PENDING_HEALTHCHECK"}
RUNNABLE_CATEGORIES = {
    "embed",
    "embedding",
    "reranker",
    "text",
    "text_llm",
    "audio",
    "image",
    "video",
}
MISSING_RUNNER_MARKERS = (
    "sem runner",
    "runner ausente",
    "no runner",
    "not implemented",
    "não implementado",
)


@dataclass(frozen=True)
class CoverageFinding:
    model_id: str
    code: str
    message: str


def _text(value: Any) -> str:
    return str(value or "").strip()


def _evidence(model: dict[str, Any]) -> dict[str, Any]:
    value = model.get("evidence")
    return value if isinstance(value, dict) else {}


def _has_execution_evidence(model: dict[str, Any]) -> bool:
    evidence = _evidence(model)
    return bool(
        evidence.get("artifact")
        and evidence.get("runtime")
        and (
            evidence.get("command")
            or evidence.get("endpoint")
            or evidence.get("adapter")
        )
        and evidence.get("result") is not None
    )


def _has_block_evidence(model: dict[str, Any]) -> bool:
    evidence = _evidence(model)
    attempts = evidence.get("attempts")
    return bool(
        _text(model.get("reason"))
        and evidence.get("runtime")
        and evidence.get("error")
        and isinstance(attempts, list)
        and attempts
    )


def _benchmark_identity_complete(model: dict[str, Any]) -> bool:
    evidence = _evidence(model)
    if evidence.get("alias_of"):
        return bool(evidence.get("identity_verified") and evidence.get("identity_method"))
    return bool(
        model.get("repo")
        and model.get("revision")
        and (
            evidence.get("artifact")
            or model.get("matched_result")
            or model.get("result")
        )
    )


def validate_inventory_payload(payload: dict[str, Any]) -> list[CoverageFinding]:
    findings: list[CoverageFinding] = []
    models = payload.get("models")
    if not isinstance(models, list):
        return [CoverageFinding("<inventory>", "INVALID_MODELS", "campo models deve ser uma lista")]

    seen: set[str] = set()
    for raw in models:
        if not isinstance(raw, dict):
            findings.append(CoverageFinding("<unknown>", "INVALID_MODEL", "registro de modelo não é objeto"))
            continue
        model_id = _text(raw.get("id")) or "<unknown>"
        status = _text(raw.get("status") or raw.get("coverage_status"))
        category = _text(raw.get("category")).lower()
        reason = _text(raw.get("reason"))
        if model_id in seen:
            findings.append(CoverageFinding(model_id, "DUPLICATE_ID", "ID duplicado no inventário"))
        seen.add(model_id)

        if status in PENDING_STATUSES or not status:
            findings.append(CoverageFinding(model_id, "PENDING", f"estado não terminal: {status or 'ausente'}"))
            continue
        if status not in TERMINAL_STATUSES:
            findings.append(CoverageFinding(model_id, "INVALID_STATUS", f"estado desconhecido: {status}"))
            continue

        if status == "NOT_APPLICABLE":
            lower_reason = reason.lower()
            if category in RUNNABLE_CATEGORIES:
                findings.append(
                    CoverageFinding(
                        model_id,
                        "RUNNABLE_MARKED_NOT_APPLICABLE",
                        f"categoria {category} exige benchmark, health check, legado ou bloqueio comprovado",
                    )
                )
            if any(marker in lower_reason for marker in MISSING_RUNNER_MARKERS):
                findings.append(
                    CoverageFinding(
                        model_id,
                        "MISSING_RUNNER_IS_NOT_NOT_APPLICABLE",
                        "ausência de runner é pendência de implementação ou bloqueio, não NOT_APPLICABLE",
                    )
                )

        elif status == "HEALTHCHECK_PASSED":
            if not _has_execution_evidence(raw):
                findings.append(
                    CoverageFinding(
                        model_id,
                        "HEALTHCHECK_WITHOUT_EVIDENCE",
                        "health check aprovado sem artefato, runtime, comando/endpoint e resultado",
                    )
                )

        elif status == "BLOCKED":
            if not _has_block_evidence(raw):
                findings.append(
                    CoverageFinding(
                        model_id,
                        "BLOCK_WITHOUT_EVIDENCE",
                        "bloqueio sem runtime, erro e lista de tentativas",
                    )
                )

        elif status == "BENCHMARKED":
            if not _benchmark_identity_complete(raw):
                findings.append(
                    CoverageFinding(
                        model_id,
                        "BENCHMARK_IDENTITY_INCOMPLETE",
                        "benchmark sem identidade reproduzível ou alias verificado",
                    )
                )

        elif status == "LEGACY_EXCLUDED":
            evidence = _evidence(raw)
            if not reason or not evidence.get("basis"):
                findings.append(
                    CoverageFinding(
                        model_id,
                        "LEGACY_WITHOUT_BASIS",
                        "exclusão por legado exige justificativa e base verificável",
                    )
                )

    declared_complete = bool(payload.get("coverage_complete"))
    summary = payload.get("summary")
    if isinstance(summary, dict):
        declared_complete = bool(summary.get("coverage_complete", declared_complete))
    if declared_complete and findings:
        findings.append(
            CoverageFinding(
                "<inventory>",
                "FALSE_COMPLETE",
                "coverage_complete=true apesar de pendências ou evidências insuficientes",
            )
        )
    return findings


def apply_validation(payload: dict[str, Any]) -> dict[str, Any]:
    findings = validate_inventory_payload(payload)
    result = dict(payload)
    serialized = [asdict(item) for item in findings]
    result["coverage_validation"] = {
        "passed": not findings,
        "finding_count": len(findings),
        "findings": serialized,
    }
    result["coverage_complete"] = not findings
    summary = result.get("summary")
    if isinstance(summary, dict):
        summary = dict(summary)
        summary["coverage_complete"] = not findings
        summary["coverage_finding_count"] = len(findings)
        result["summary"] = summary
    return result


def validate_inventory_file(path: Path) -> tuple[dict[str, Any], list[CoverageFinding]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload, validate_inventory_payload(payload)


__all__ = [
    "CoverageFinding",
    "apply_validation",
    "validate_inventory_file",
    "validate_inventory_payload",
]
