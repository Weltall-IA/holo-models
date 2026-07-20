from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from holo_benchmark.reranker_candidates import _scalar_int8_roundtrip
from holo_benchmark.reranker_metrics import (
    build_union_candidates,
    evaluate_reranker_effect,
    scores_to_rankings,
    stable_top_k,
)
from holo_benchmark.reranker_runtime import (
    DEFAULT_RERANK_INSTRUCTION,
    discover_qwen_rerankers,
    rerank_query_text,
)


class RerankerMetricsTests(unittest.TestCase):
    def test_stable_top_k_preserves_input_order_on_ties(self) -> None:
        rows = stable_top_k(
            np.array([[0.5, 0.5, 0.2]], dtype=np.float32),
            ["a", "b", "c"],
            2,
        )
        self.assertEqual([item["chunk_id"] for item in rows[0]], ["a", "b"])
        self.assertEqual([item["rank"] for item in rows[0]], [1, 2])

    def test_union_is_stable_and_deduplicated(self) -> None:
        manifests = {
            "first": [[{"chunk_id": "a"}, {"chunk_id": "b"}]],
            "second": [[{"chunk_id": "b"}, {"chunk_id": "c"}]],
        }
        self.assertEqual(build_union_candidates(manifests, 2), [["a", "b", "c"]])

    def test_scores_to_rankings_uses_original_rank_as_tie_breaker(self) -> None:
        candidates = [
            [
                {"chunk_id": "a", "rank": 1},
                {"chunk_id": "b", "rank": 2},
                {"chunk_id": "c", "rank": 3},
            ]
        ]
        rankings = scores_to_rankings(
            candidates,
            [{"a": 0.1, "b": 0.9, "c": 0.9}],
        )
        self.assertEqual(rankings, [["b", "c", "a"]])

    def test_effect_counts_rescue_damage_and_candidate_ceiling(self) -> None:
        queries = [
            {"query_id": "q1", "query_type": "x", "relevant_chunk_ids": ["a"]},
            {"query_id": "q2", "query_type": "x", "relevant_chunk_ids": ["d"]},
            {"query_id": "q3", "query_type": "x", "relevant_chunk_ids": ["g"]},
        ]
        base = [["b", "a", "c"], ["d", "e", "f"], ["h", "i", "j"]]
        reranked = [["a", "b", "c"], ["e", "d", "f"], ["h", "i", "j"]]
        result = evaluate_reranker_effect(queries, base, reranked, 3)
        effect = result["effect"]
        self.assertEqual(effect["rescue_count"], 1)
        self.assertEqual(effect["rescue_rate"], 1.0)
        self.assertEqual(effect["damage_count"], 1)
        self.assertEqual(effect["damage_rate"], 1.0)
        self.assertAlmostEqual(effect["candidate_coverage"], 2 / 3)
        self.assertEqual(effect["conditional_HitRate@1"], 0.5)


class RerankerRuntimeTests(unittest.TestCase):
    def test_scalar_int8_roundtrip_has_expected_storage(self) -> None:
        documents = np.array(
            [[-1.0, 0.0, 1.0], [1.0, 0.5, -1.0], [0.0, -0.5, 0.25]],
            dtype=np.float32,
        )
        queries = np.array([[0.5, 0.1, -0.5]], dtype=np.float32)
        docs, qrys, metadata = _scalar_int8_roundtrip(documents, queries)
        self.assertEqual(docs.shape, documents.shape)
        self.assertEqual(qrys.shape, queries.shape)
        self.assertEqual(metadata["stored_dtype"], "int8")
        self.assertEqual(metadata["stored_bytes_per_vector"], 3)
        self.assertTrue(np.isfinite(docs).all())
        self.assertTrue(np.isfinite(qrys).all())

    def test_rerank_query_text_applies_same_instruction(self) -> None:
        text = rerank_query_text({"query": "uma cena"}, "ordene por contexto")
        self.assertEqual(text, "Instruct: ordene por contexto\nQuery: uma cena")
        self.assertIn("personagens", DEFAULT_RERANK_INSTRUCTION)

    def test_discovery_finds_transformers_and_gguf_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            transformers_model = root / "rerank" / "Qwen3-Reranker-4B"
            transformers_model.mkdir(parents=True)
            (transformers_model / "config.json").write_text("{}", encoding="utf-8")
            (transformers_model / "model.safetensors").write_bytes(b"weights")
            gguf_dir = root / "reranker" / "gguf"
            gguf_dir.mkdir(parents=True)
            (gguf_dir / "Qwen3-Reranker-8B-Q4_K_M.gguf").write_bytes(b"gguf")

            candidates = discover_qwen_rerankers(root)
            self.assertEqual(len(candidates), 2)
            self.assertEqual(candidates[0]["backend"], "llama.cpp")
            self.assertIn("8B", candidates[0]["name"])
            self.assertEqual(candidates[1]["backend"], "cross-encoder")


if __name__ == "__main__":
    unittest.main()
