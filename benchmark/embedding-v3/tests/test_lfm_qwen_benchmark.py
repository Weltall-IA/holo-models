from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from holo_benchmark import lfm_qwen_benchmark


class LfmQwenBenchmarkTests(unittest.TestCase):
    def _candidate(self, path: Path) -> None:
        rows = [
            {
                "query_id": f"query-{query_index:04d}",
                "candidates": [
                    {"chunk_id": f"chunk-{index:04d}", "score": 1.0 - index / 100.0}
                    for index in range(50)
                ],
            }
            for query_index in range(150)
        ]
        payload = {
            "schema_version": "1.0",
            "variant": lfm_qwen_benchmark.PROFILE_ID,
            "embedding": {"sha256": lfm_qwen_benchmark.EXPECTED_GGUF_SHA256},
            "dataset": {"corpus_sha256": lfm_qwen_benchmark.CORPUS_SHA256},
            "candidate_top_k": 50,
            "ranking_sha256": "a" * 64,
            "queries": rows,
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_validate_model_pins_revision_bytes_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / lfm_qwen_benchmark.QWEN_REVISION
            snapshot.mkdir()
            weight = snapshot / lfm_qwen_benchmark.QWEN_WEIGHT_FILE
            weight.write_bytes(b"weight")
            with mock.patch.object(
                lfm_qwen_benchmark, "QWEN_WEIGHT_BYTES", len(b"weight")
            ), mock.patch.object(
                lfm_qwen_benchmark,
                "_sha256",
                return_value=lfm_qwen_benchmark.QWEN_WEIGHT_SHA256,
            ):
                resolved, identity = lfm_qwen_benchmark.validate_qwen_model(snapshot)

        self.assertEqual(resolved.name, lfm_qwen_benchmark.QWEN_REVISION)
        self.assertEqual(identity["repository"], lfm_qwen_benchmark.QWEN_REPOSITORY)
        self.assertNotIn("path", identity)

    def test_benchmark_scores_top50_and_outputs_top20(self):
        chunks = [
            {"chunk_id": f"chunk-{index:04d}", "text": f"document {index}"}
            for index in range(600)
        ]
        queries = [
            {
                "query_id": f"query-{index:04d}",
                "query": f"query {index}",
                "relevant_chunk_ids": ["chunk-0024"],
            }
            for index in range(150)
        ]
        scores = [
            {
                f"chunk-{index:04d}": (100.0 if index == 24 else -float(index))
                for index in range(50)
            }
            for _ in range(150)
        ]
        runtime = {"device": "cuda", "peak_vram_bytes": 1, "pairs": 7500}
        captured: dict[str, object] = {}

        def fake_evaluate(queries_arg, base, reranked, cutoff):
            captured.update({"base": base, "reranked": reranked, "cutoff": cutoff})
            return {
                "base_metrics": {"summary": {"HitRate@1": 0.0}},
                "reranked_metrics": {"summary": {"HitRate@1": 1.0}},
                "effect": {"candidate_cutoff": cutoff},
                "per_query_effect": [],
            }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / "candidate.json"
            self._candidate(candidate)
            args = argparse.Namespace(
                model_path=root / "model",
                candidate=candidate,
                score_output=root / "score.json",
                pipeline_output=root / "pipeline.json",
                batch_size=8,
                instruction="instruction",
            )
            with mock.patch.object(
                lfm_qwen_benchmark,
                "load_frozen_dataset",
                return_value=(chunks, queries),
            ), mock.patch.object(
                lfm_qwen_benchmark,
                "validate_qwen_model",
                return_value=(
                    root / "model",
                    {
                        "id": "qwen",
                        "repository": "Qwen/Qwen3-Reranker-0.6B",
                        "revision": "revision",
                        "weight_files": [],
                    },
                ),
            ), mock.patch.object(
                lfm_qwen_benchmark,
                "score_qwen_cross_encoder",
                return_value=(scores, runtime),
            ), mock.patch.object(
                lfm_qwen_benchmark,
                "evaluate_reranker_effect",
                side_effect=fake_evaluate,
            ):
                output = lfm_qwen_benchmark.benchmark_profile(args)

            score_payload = json.loads(args.score_output.read_text(encoding="utf-8"))
            pipeline = json.loads(args.pipeline_output.read_text(encoding="utf-8"))

        self.assertEqual(output["pairs"], 7500)
        self.assertEqual(len(captured["base"][0]), 50)
        self.assertEqual(len(captured["reranked"][0]), 20)
        self.assertEqual(captured["reranked"][0][0], "chunk-0024")
        self.assertEqual(captured["cutoff"], 50)
        self.assertEqual(len(score_payload["queries"]), 150)
        self.assertEqual(len(score_payload["queries"][0]["candidate_ids"]), 50)
        self.assertEqual(pipeline["candidate_ranking_sha256"], "a" * 64)
        self.assertEqual(pipeline["rerank_top_k"], 20)

    def test_score_validation_accepts_exact_finite_sets(self):
        rows = [[{"chunk_id": f"chunk-{index}", "score": 0.0} for index in range(50)]]
        scores = [{f"chunk-{index}": 0.0 for index in range(50)}]
        lfm_qwen_benchmark._validate_score_rows(rows, scores)
        self.assertEqual(len(scores[0]), 50)


if __name__ == "__main__":
    unittest.main()
