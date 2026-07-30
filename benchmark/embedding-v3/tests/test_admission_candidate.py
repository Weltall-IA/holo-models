from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from holo_benchmark import admission_candidate
from holo_benchmark.metrics import DEFAULT_KS, evaluate_rankings


def _dataset():
    chunks = [
        {"chunk_id": f"chunk-{index:04d}", "text": f"document {index}"}
        for index in range(600)
    ]
    queries = [
        {
            "query_id": f"query-{index:04d}",
            "query": f"query {index}",
            "query_type": "semantic_event",
            "difficulty": "medium",
            "relevant_chunk_ids": [f"chunk-{index:04d}"],
            "hard_negative_chunk_ids": [f"chunk-{(index + 1) % 600:04d}"],
        }
        for index in range(150)
    ]
    rankings = []
    for index in range(150):
        row = [f"chunk-{index:04d}"]
        row.extend(
            f"chunk-{candidate:04d}"
            for candidate in range(600)
            if candidate != index
        )
        rankings.append(row[:50])
    return chunks, queries, rankings


def _payload(profile_id: str, queries, rankings):
    config = admission_candidate.PROFILE_CONFIG[profile_id]
    metrics = evaluate_rankings(queries, rankings, DEFAULT_KS)
    return {
        "state": "EXECUTED",
        "backend": config["source_backend"],
        "model": {
            "weight_file": f"/host/{config['weight_file']}",
            "bytes": config["bytes"],
            "sha256": config["sha256"],
            "license": config["license"],
        },
        "dataset": {
            "combined_sha256": admission_candidate.CORPUS_SHA256,
            "documents": 600,
            "queries": 150,
            "document_prefix": "passage: ",
            "query_prefix": "query: ",
        },
        "evaluation": {
            "metrics": metrics,
            "rankings_top50": rankings,
        },
    }


class AdmissionCandidateTests(unittest.TestCase):
    def test_valid_source_builds_rank_only_candidate(self):
        profile_id = "nemotron_3_embed_1b_nvfp4"
        chunks, queries, rankings = _dataset()
        payload = _payload(profile_id, queries, rankings)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.json"
            source.write_text(json.dumps(payload), encoding="utf-8")
            with mock.patch.object(admission_candidate, "PROJECT_ROOT", root):
                validated = admission_candidate.validate_admission_source(
                    profile_id, payload, chunks, queries
                )
                candidate = admission_candidate.build_candidate_payload(
                    profile_id, source, payload, queries, validated
                )
        self.assertEqual(candidate["variant"], profile_id)
        self.assertEqual(len(candidate["queries"]), 150)
        self.assertEqual(len(candidate["queries"][0]["candidates"]), 50)
        self.assertEqual(
            candidate["queries"][0]["candidates"][0],
            {"chunk_id": "chunk-0000", "rank": 1},
        )
        self.assertEqual(candidate["ranking_source"]["score_semantics"], "rank_only")

    def test_rejects_weight_hash_mismatch(self):
        profile_id = "nemotron_3_embed_1b_nvfp4"
        chunks, queries, rankings = _dataset()
        payload = _payload(profile_id, queries, rankings)
        payload["model"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "sha256"):
            admission_candidate.validate_admission_source(
                profile_id, payload, chunks, queries
            )

    def test_rejects_duplicate_ranking_ids(self):
        profile_id = "nemotron_3_embed_1b_q4_k_m_gguf"
        chunks, queries, rankings = _dataset()
        rankings[0][1] = rankings[0][0]
        payload = _payload(profile_id, queries, rankings)
        with self.assertRaisesRegex(ValueError, "duplicates"):
            admission_candidate.validate_admission_source(
                profile_id, payload, chunks, queries
            )

    def test_rejects_metric_mismatch(self):
        profile_id = "nemotron_3_embed_1b_q4_k_m_gguf"
        chunks, queries, rankings = _dataset()
        payload = _payload(profile_id, queries, rankings)
        payload["evaluation"]["metrics"]["summary"]["MRR@10"] = 0.0
        with self.assertRaisesRegex(ValueError, "MRR@10"):
            admission_candidate.validate_admission_source(
                profile_id, payload, chunks, queries
            )


if __name__ == "__main__":
    unittest.main()
