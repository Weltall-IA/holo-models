from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from holo_benchmark import mxbai_panel_benchmark as module


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


def _rankings():
    return [
        [
            f"chunk-{value:04d}"
            for value in ([index] + [other for other in range(600) if other != index][:49])
        ]
        for index in range(150)
    ]


def _legacy(profile_id: str):
    return {
        "id": profile_id,
        "candidates": {
            f"query-{index:04d}": ranking
            for index, ranking in enumerate(_rankings())
        },
    }


def _canonical(profile_id: str):
    return {
        "raw_embedding_profiles_by_id": {
            profile_id: {
                "profile_id": profile_id,
                "source_group": "gate2",
                "source_path": f"benchmark/embedding-v3/results/gate2/{profile_id}.json",
                "metrics": {"mrr_at_10": 0.5},
                "metadata": {"model": {"sha256": "a" * 64}},
                "runtime": {"backend": "test", "backend_version": "1"},
            }
        }
    }


class MixedbreadPanelTests(unittest.TestCase):
    def test_legacy_candidate_is_validated_and_hashed(self):
        chunks, queries = _dataset()
        profile_id = "colibri_ptbr"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "candidate.json"
            path.write_text(json.dumps(_legacy(profile_id)), encoding="utf-8")
            with mock.patch.object(module, "PROJECT_ROOT", root):
                rows, provenance, identity = module.load_candidate(
                    path,
                    profile_id,
                    [row["query_id"] for row in queries],
                    {row["chunk_id"] for row in chunks},
                    _canonical(profile_id),
                )
        self.assertEqual(len(rows), 150)
        self.assertEqual(len(rows[0]), 50)
        self.assertEqual(provenance["source_schema"], "legacy-id-candidates")
        self.assertEqual(len(provenance["ranking_sha256"]), 64)
        self.assertEqual(identity["profile_id"], profile_id)

    def test_duplicate_candidate_is_rejected(self):
        chunks, queries = _dataset()
        profile_id = "colibri_ptbr"
        payload = _legacy(profile_id)
        payload["candidates"]["query-0000"][1] = payload["candidates"]["query-0000"][0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "candidate.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with mock.patch.object(module, "PROJECT_ROOT", root):
                with self.assertRaisesRegex(ValueError, "duplicates"):
                    module.load_candidate(
                        path,
                        profile_id,
                        [row["query_id"] for row in queries],
                        {row["chunk_id"] for row in chunks},
                        _canonical(profile_id),
                    )

    def test_model_validation_pins_weight_and_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in module._REQUIRED_MODEL_FILES:
                (root / name).write_bytes(b"x")
            with mock.patch.object(
                module, "_sha256", return_value=module.MODEL_WEIGHT_SHA256
            ):
                _, identity = module.validate_model(root)
        self.assertEqual(identity["revision"], module.MODEL_REVISION)
        self.assertEqual(
            identity["weight_files"][0]["sha256"], module.MODEL_WEIGHT_SHA256
        )

    def test_raw_identity_requires_measured_profile(self):
        with self.assertRaisesRegex(ValueError, "no measured metrics"):
            module._raw_profile_identity(
                {
                    "raw_embedding_profiles_by_id": {
                        "profile": {"metrics": {}, "metadata": {}, "runtime": {}}
                    }
                },
                "profile",
            )

    def test_benchmark_writes_scoped_score_and_pipeline(self):
        chunks, queries = _dataset()
        profile_id = "colibri_ptbr"
        candidate = _legacy(profile_id)
        canonical = _canonical(profile_id)
        rankings = _rankings()
        score_rows = [
            {
                chunk_id: float(50 - offset)
                for offset, chunk_id in enumerate(ranking)
            }
            for ranking in rankings
        ]
        runtime = {"device": "cuda", "pairs": 7500, "peak_vram_bytes": 1}
        evaluation = {
            "base_metrics": {"summary": {"HitRate@1": 0.1}},
            "reranked_metrics": {"summary": {"HitRate@1": 0.2}},
            "effect": {},
            "per_query_effect": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_path = root / "candidate.json"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            canonical_path = root / "all.json"
            canonical_path.write_text(json.dumps(canonical), encoding="utf-8")
            args = argparse.Namespace(
                profile_id=profile_id,
                model_path=root / "model",
                candidate=candidate_path,
                canonical=canonical_path,
                score_output=root / "score.json",
                pipeline_output=root / "pipeline.json",
                batch_size=8,
                instruction="instruction",
            )
            with mock.patch.object(module, "PROJECT_ROOT", root), mock.patch.object(
                module, "load_frozen_dataset", return_value=(chunks, queries)
            ), mock.patch.object(
                module,
                "validate_model",
                return_value=(root / "model", {"id": module.MODEL_ID}),
            ), mock.patch.object(
                module, "score_cross_encoder", return_value=(score_rows, runtime)
            ), mock.patch.object(
                module, "evaluate_reranker_effect", return_value=evaluation
            ):
                result = module.benchmark_profile(args)
            score = json.loads(args.score_output.read_text(encoding="utf-8"))
            pipeline = json.loads(args.pipeline_output.read_text(encoding="utf-8"))
        self.assertEqual(result["pairs"], 7500)
        self.assertEqual(score["reranker_id"], module.MODEL_ID)
        self.assertEqual(
            pipeline["pipeline_id"], f"{profile_id}__{module.MODEL_ID}"
        )
        self.assertEqual(pipeline["candidate_top_k"], 50)
        self.assertEqual(pipeline["rerank_top_k"], 20)


if __name__ == "__main__":
    unittest.main()
