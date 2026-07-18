from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable

from .work_catalog import SCHEMA_VERSION, CORPUS_VERSION, SEED
from .scene_base import regex_tokens


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    tmp.replace(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: JSON inválido: {exc}") from exc
    return rows


def _shingles(text: str, size: int = 5) -> set[tuple[str, ...]]:
    tokens = [t.lower() for t in regex_tokens(text)]
    return {tuple(tokens[i:i + size]) for i in range(max(0, len(tokens) - size + 1))}


def max_pairwise_overlap(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chunk in chunks:
        groups[chunk["scene_type"]].append(chunk)
    best = (0.0, None, None)
    for group in groups.values():
        sh = [(c["chunk_id"], _shingles(c["text"])) for c in group]
        for i in range(len(sh)):
            for j in range(i + 1, len(sh)):
                a_id, a = sh[i]
                b_id, b = sh[j]
                union = len(a | b)
                score = len(a & b) / union if union else 0.0
                if score > best[0]:
                    best = (score, a_id, b_id)
    return {"max_jaccard_5gram": round(best[0], 6), "chunk_a": best[1], "chunk_b": best[2]}


def validate_corpus(chunks: list[dict[str, Any]], queries: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    chunk_ids = [c.get("chunk_id") for c in chunks]
    query_ids = [q.get("query_id") for q in queries]
    by_id = {c["chunk_id"]: c for c in chunks if "chunk_id" in c}

    if len(chunks) != 600:
        errors.append(f"chunks={len(chunks)}; esperado=600")
    if len(queries) != 150:
        errors.append(f"queries={len(queries)}; esperado=150")
    if len(set(c.get("work_id") for c in chunks)) != 30:
        errors.append("obras != 30")
    if len(chunk_ids) != len(set(chunk_ids)):
        errors.append("chunk_id duplicado")
    if len(query_ids) != len(set(query_ids)):
        errors.append("query_id duplicado")
    texts = [c.get("text", "") for c in chunks]
    if len(texts) != len(set(texts)):
        errors.append("texto duplicado")
    query_texts = [q.get("query", "") for q in queries]
    if len(query_texts) != len(set(query_texts)):
        errors.append("consulta duplicada")

    per_work = Counter(c["work_id"] for c in chunks)
    if set(per_work.values()) != {20}:
        errors.append(f"chunks por obra inválidos: {dict(per_work)}")

    token_counts = []
    timeline: dict[str, list[dict[str, Any]]] = defaultdict(list)
    character_names: dict[str, dict[str, str]] = defaultdict(dict)
    required_chunk_fields = {
        "schema_version", "chunk_id", "work_id", "episode_id", "sequence", "start_ms", "end_ms",
        "text", "characters", "themes", "scene_type", "emotion", "event", "requires_previous_context",
    }
    for c in chunks:
        missing = required_chunk_fields - set(c)
        if missing:
            errors.append(f"{c.get('chunk_id')}: campos ausentes {sorted(missing)}")
        if not isinstance(c.get("start_ms"), int) or not isinstance(c.get("end_ms"), int) or c.get("start_ms", 0) >= c.get("end_ms", 0):
            errors.append(f"{c.get('chunk_id')}: timestamps inválidos")
        if c.get("duration_ms") != c.get("end_ms", 0) - c.get("start_ms", 0):
            errors.append(f"{c.get('chunk_id')}: duration_ms inválido")
        count = len(regex_tokens(c.get("text", "")))
        token_counts.append(count)
        if count < 180 or count > 512:
            errors.append(f"{c.get('chunk_id')}: tokens_estimados={count}")
        elif count > 420:
            warnings.append(f"{c.get('chunk_id')}: acima do alvo 420 ({count})")
        timeline[c["episode_id"]].append(c)
        for char in c.get("characters", []):
            cid, name = char.get("character_id"), char.get("name")
            prev = character_names[c["work_id"]].get(cid)
            if prev is not None and prev != name:
                errors.append(f"{c['work_id']}: personagem inconsistente {cid}: {prev}/{name}")
            character_names[c["work_id"]][cid] = name

    for episode_id, rows in timeline.items():
        rows.sort(key=lambda x: x["sequence"])
        if [r["sequence"] for r in rows] != list(range(1, 21)):
            errors.append(f"{episode_id}: sequência inválida")
        for prev, cur in zip(rows, rows[1:]):
            if cur["start_ms"] < prev["end_ms"]:
                errors.append(f"{episode_id}: sobreposição {prev['chunk_id']} / {cur['chunk_id']}")

    dist = Counter(q.get("query_type") for q in queries)
    expected_dist = {
        "semantic_event": 40,
        "context_dependency": 30,
        "emotion_intention": 25,
        "indirect_dialogue": 20,
        "character_name": 15,
        "exact_phrase": 10,
        "similar_scene": 10,
    }
    if dict(dist) != expected_dist:
        errors.append(f"distribuição inválida: {dict(dist)}")
    required_query_fields = {
        "query_id", "query", "relevant_chunk_ids", "hard_negative_chunk_ids",
        "query_type", "difficulty", "requires_context", "expected_rationale",
    }
    for q in queries:
        missing = required_query_fields - set(q)
        if missing:
            errors.append(f"{q.get('query_id')}: campos ausentes {sorted(missing)}")
        rel = q.get("relevant_chunk_ids", [])
        neg = q.get("hard_negative_chunk_ids", [])
        if not 1 <= len(rel) <= 3:
            errors.append(f"{q.get('query_id')}: relevantes={len(rel)}")
        if len(neg) < 2:
            errors.append(f"{q.get('query_id')}: negativos={len(neg)}")
        if set(rel) & set(neg):
            errors.append(f"{q.get('query_id')}: relevante também negativo")
        for cid in rel + neg:
            if cid not in by_id:
                errors.append(f"{q.get('query_id')}: chunk inexistente {cid}")
        if not q.get("query", "").strip():
            errors.append(f"{q.get('query_id')}: consulta vazia")
        if q.get("query_type") != "exact_phrase":
            query_tokens = [t.lower() for t in regex_tokens(q.get("query", ""))]
            for cid in rel:
                text = by_id[cid]["text"].lower()
                for n in range(12, min(25, len(query_tokens)) + 1):
                    if any(" ".join(query_tokens[i:i + n]) in text for i in range(len(query_tokens) - n + 1)):
                        warnings.append(f"{q['query_id']}: possível cópia literal longa")
                        break

    overlap = max_pairwise_overlap(chunks)
    if overlap["max_jaccard_5gram"] > 0.55:
        warnings.append(f"sobreposição estrutural alta: {overlap}")

    return {
        "schema_version": SCHEMA_VERSION,
        "corpus_version": CORPUS_VERSION,
        "generator_seed": SEED,
        "token_estimator": "regex_word_tokens_ptbr_v2",
        "counts": {"works": len(per_work), "chunks": len(chunks), "queries": len(queries)},
        "query_distribution": dict(dist),
        "token_distribution": {
            "min": min(token_counts) if token_counts else 0,
            "max": max(token_counts) if token_counts else 0,
            "mean": round(mean(token_counts), 3) if token_counts else 0,
            "median": median(token_counts) if token_counts else 0,
        },
        "template_overlap": overlap,
        "errors": errors,
        "warnings": sorted(set(warnings)),
        "all_automated_checks_passed": not errors,
    }


def build_review_checklist(chunks: list[dict[str, Any]], queries: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {c["chunk_id"]: c for c in chunks}
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for q in queries:
        groups[q["query_type"]].append(q)
    sample: list[dict[str, Any]] = []
    for category in [
        "semantic_event", "context_dependency", "emotion_intention", "indirect_dialogue",
        "character_name", "exact_phrase", "similar_scene",
    ]:
        rows = groups[category]
        indexes = [0, len(rows) // 4, len(rows) // 2, (3 * len(rows)) // 4, len(rows) - 1]
        seen = set()
        for idx in indexes:
            q = rows[idx]
            if q["query_id"] in seen:
                continue
            seen.add(q["query_id"])
            sample.append({
                "query_id": q["query_id"],
                "query_type": category,
                "query": q["query"],
                "expected_rationale": q["expected_rationale"],
                "relevants": [{"chunk_id": cid, "text": by_id[cid]["text"]} for cid in q["relevant_chunk_ids"]],
                "hard_negatives": [{"chunk_id": cid, "text": by_id[cid]["text"]} for cid in q["hard_negative_chunk_ids"]],
                "review_fields": {
                    "status": "PREENCHER: approved|rejected",
                    "relevant_matches_query": "PREENCHER: true|false",
                    "negatives_are_hard_but_wrong": "PREENCHER: true|false",
                    "query_does_not_leak_answer": "PREENCHER: true|false",
                    "notes": "PREENCHER",
                },
            })
    return {
        "schema_version": SCHEMA_VERSION,
        "corpus_version": CORPUS_VERSION,
        "minimum_required": 30,
        "sample_count": len(sample),
        "instructions": (
            "Revise semanticamente cada item. Não altere corpus ou consultas. "
            "Copie somente query_id e os campos de revisão para semantic_review.json. "
            "Qualquer rejeição bloqueia o congelamento e exige nova versão autorizada."
        ),
        "items": sample,
    }


def validate_semantic_review(review_path: Path, checklist: dict[str, Any]) -> dict[str, Any]:
    if not review_path.exists():
        return {"complete": False, "errors": ["semantic_review.json ausente"], "approved": 0, "rejected": 0}
    data = json.loads(review_path.read_text(encoding="utf-8"))
    expected = {item["query_id"] for item in checklist["items"]}
    items = data.get("items", [])
    errors = []
    ids = [item.get("query_id") for item in items]
    if len(ids) != len(set(ids)):
        errors.append("query_id duplicado na revisão")
    unknown = set(ids) - expected
    if unknown:
        errors.append(f"query_id fora da checklist: {sorted(unknown)}")
    approved = rejected = 0
    for item in items:
        status = item.get("status")
        if status == "approved":
            approved += 1
        elif status == "rejected":
            rejected += 1
        else:
            errors.append(f"{item.get('query_id')}: status inválido")
        for field in ("relevant_matches_query", "negatives_are_hard_but_wrong", "query_does_not_leak_answer"):
            if not isinstance(item.get(field), bool):
                errors.append(f"{item.get('query_id')}: {field} deve ser boolean")
        if not str(item.get("notes", "")).strip():
            errors.append(f"{item.get('query_id')}: notes vazio")
    if len(items) < checklist["minimum_required"]:
        errors.append(f"revisões={len(items)}; mínimo={checklist['minimum_required']}")
    if rejected:
        errors.append(f"há {rejected} item(ns) rejeitado(s)")
    return {"complete": not errors, "errors": errors, "approved": approved, "rejected": rejected, "reviewed": len(items)}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def freeze_hashes(data_dir: Path, semantic_review: dict[str, Any]) -> dict[str, Any]:
    names = ["corpus.jsonl", "queries.jsonl", "validation.json", "semantic_review.json"]
    files = []
    combined = hashlib.sha256()
    for name in names:
        path = data_dir / name
        digest = sha256_file(path)
        size = path.stat().st_size
        files.append({"file": f"data/{CORPUS_VERSION}/{name}", "bytes": size, "sha256": digest})
        combined.update(name.encode("utf-8"))
        combined.update(b"\0")
        combined.update(digest.encode("ascii"))
        combined.update(b"\0")
    return {
        "schema_version": SCHEMA_VERSION,
        "algorithm": "SHA-256",
        "corpus_version": CORPUS_VERSION,
        "files": files,
        "combined_sha256": combined.hexdigest(),
        "semantic_review_summary": semantic_review,
    }
