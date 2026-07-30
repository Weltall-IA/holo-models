from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from holo_benchmark import qwen_candidate_benchmark


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
            "hard_negative_chunk_ids": [],
        }
        for index in range(150)
    ]
    return chunks, queries


def _candidate(profile_id: str):
    return {
        "schema_version": "1.0",
        "variant": profile_id,
        "embedding": {
            "profile_id": profile_id,
            "sha256": "a" * 64,
            "backend": "test",
        },
        "dataset": {
            "corpus_sha256": qwen_candidate_benchmark.CORPUS_SHA256,
            "documents": 600,
            "queries": 150,
        },
        "candidate_top_k": 50,
        "ranking_sha256": "b" * 64,
        "queries": [
            {
                "query_id": f"query-{index:04d}",
                "candidates": [
                    {
                        "chunk_id": f"chunk-{candidate_index:04d}",
                        "rank": rank,
                    }
                    for rank, candidate_index in enumerate(
                        [index]
                        + [value for value in range(600) if value != index][:49],
                        start=1,
                    )
                ],
            }
            for index in range(150)
        ],
    }


class QwenCandidateTests(unittest.TestCase):
    def test_candidate_rows_accept_rank_only(self):
        profile_id = "profile"
        payload = _candidate(profile_id)
        query_ids = [f"query-{index:04d}" for index in range(150)]
        rows = qwen_candidate_benchmark._candidate_rows(
            payload, query_ids, profile_id
        )
        self.assertEqual(len(rows), 150)
        self.assertEqual(rows[0][0]["rank"], 1)

    def test_candidate_rows_reject_bad_rank(self):
        profile_id = "profile"
        payload = _candidate(profile_id)
        payload["queries"][0]["candidates"][0]["rank"] = 2
        query_ids = [f"query-{index:04d}" for index in range(150)]
        with self.assertRaisesRegex(ValueError, "rank"):
            qwen_candidate_benchmark._candidate_rows(
                payload, query_ids, profile_id
            )

    def test_benchmark_writes_profile_scoped_artifacts(self):
        profile_id = "profile"
        chunks, queries = _dataset()
        candidate = _candidate(profile_id)
        score_rows = [
            {
                item["chunk_id"]: float(50 - offset)
                for offset, item in enumerate(row["candidates"])
            }
            for row in candidate["queries"]
        ]
        runtime = {
            "device": "cuda",
            "pairs": 7500,
            "peak_vram_bytes": 1,
        }
        evaluation = {
            "base_metrics": {"summary": {"HitRate@1": 0.1}},
            "reranked_metrics": {"summary": {"HitRate@1": 0.2}},
            "effect": {},
            "per_query_effect": [],
        }
        written = {}

        def fake_atomic(path, payload):
            written[str(path)] = payload

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = argparse.Namespace(
                profile_id=profile_id,
                model_path=root / "model",
                candidate=root / "candidate.json",
                score_output=root / "score.json",
                pipeline_output=root / "pipeline.json",
                batch_size=8,
                instruction="instruction",
            )
            with mock.patch.object(
                qwen_candidate_benchmark,
                "load_frozen_dataset",
                return_value=(chunks, queries),
            ), mock.patch.object(
                qwen_candidate_benchmark, "read_json", return_value=candidate
            ), mock.patch.object(
                qwen_candidate_benchmark,
                "validate_qwen_model",
                return_value=(root / "model", {"id": "qwen"}),
            ), mock.patch.object(
                qwen_candidate_benchmark,
                "score_qwen_cross_encoder",
                return_value=(score_rows, runtime),
            ), mock.patch.object(
                qwen_candidate_benchmark,
                "evaluate_reranker_effect",
                return_value=evaluation,
            ), mock.patch.object(
                qwen_candidate_benchmark, "atomic_json", side_effect=fake_atomic
            ), mock.patch.object(
                qwen_candidate_benchmark, "assert_portable_payload"
            ), mock.patch.object(
                qwen_candidate_benchmark, "PROJECT_ROOT", root
            ):
                result = qwen_candidate_benchmark.benchmark_profile(args)

        self.assertEqual(result["pipeline_id"], "profile__qwen_local")
        score = written[str(args.score_output)]
        pipeline = written[str(args.pipeline_output)]
        self.assertEqual(score["candidate"]["variant"], profile_id)
        self.assertEqual(pipeline["embedding_variant"], profile_id)
        self.assertEqual(pipeline["candidate_ranking_sha256"], "b" * 64)


if __name__ == "__main__":
    unittest.main()
