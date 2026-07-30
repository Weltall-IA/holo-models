from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from holo_benchmark import lfm_smoke


def _dataset():
    chunks = [
        {"chunk_id": f"chunk-{index:04d}", "text": f"document {index}"}
        for index in range(40)
    ]
    queries = []
    for index in range(10):
        queries.append(
            {
                "query_id": f"query-{index:04d}",
                "query": f"query {index}",
                "relevant_chunk_ids": [f"chunk-{index:04d}"],
                "hard_negative_chunk_ids": [f"chunk-{index + 10:04d}"],
            }
        )
    return chunks, queries


class LfmSmokeSelectionTests(unittest.TestCase):
    def test_selection_contains_all_relevant_chunks(self):
        chunks, queries = _dataset()
        selected_chunks, selected_queries = lfm_smoke.select_smoke_dataset(
            chunks, queries
        )
        selected_ids = {row["chunk_id"] for row in selected_chunks}
        self.assertEqual(len(selected_chunks), 20)
        self.assertEqual(len(selected_queries), 10)
        for query in queries:
            self.assertTrue(set(query["relevant_chunk_ids"]).issubset(selected_ids))

    def test_selection_rejects_missing_relevant_chunk(self):
        chunks, queries = _dataset()
        queries[0]["relevant_chunk_ids"] = ["missing"]
        with self.assertRaises(ValueError):
            lfm_smoke.select_smoke_dataset(chunks, queries)


class LfmSmokeExecutionTests(unittest.TestCase):
    def _args(self, root: Path) -> argparse.Namespace:
        return argparse.Namespace(
            gguf_path=root / "model.gguf",
            llama_server=root / "llama-server",
            batch_size=10,
            timeout_seconds=3600,
            output=root / "smoke.json",
        )

    def test_smoke_passes_with_semantic_signal(self):
        chunks, queries = _dataset()
        selected_chunks, _ = lfm_smoke.select_smoke_dataset(chunks, queries)
        selected_ids = [row["chunk_id"] for row in selected_chunks]
        positions = {chunk_id: index for index, chunk_id in enumerate(selected_ids)}
        document_embeddings = np.zeros(
            (20, lfm_smoke.DIMENSION), dtype=np.float32
        )
        query_embeddings = np.zeros((10, lfm_smoke.DIMENSION), dtype=np.float32)
        for index in range(20):
            document_embeddings[index, index] = 1.0
        for index, query in enumerate(queries):
            query_embeddings[
                index, positions[query["relevant_chunk_ids"][0]]
            ] = 1.0
        runtime = {
            "peak_vram_bytes": 1024,
            "backend_version": "test",
            "binary_sha256": "b" * 64,
            "gguf_sha256": "g" * 64,
        }
        with tempfile.TemporaryDirectory() as tmp:
            args = self._args(Path(tmp))
            with mock.patch.object(
                lfm_smoke, "load_frozen_dataset", return_value=(chunks, queries)
            ), mock.patch.object(
                lfm_smoke,
                "lfm_embed_queries_and_docs",
                return_value=(query_embeddings, document_embeddings, runtime),
            ):
                payload = lfm_smoke.run_smoke(args)
            self.assertTrue(args.output.exists())
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["semantic_passes"], 10)

    def test_smoke_rejects_weak_semantic_signal(self):
        chunks, queries = _dataset()
        selected_chunks, _ = lfm_smoke.select_smoke_dataset(chunks, queries)
        selected_ids = [row["chunk_id"] for row in selected_chunks]
        positions = {chunk_id: index for index, chunk_id in enumerate(selected_ids)}
        document_embeddings = np.zeros(
            (20, lfm_smoke.DIMENSION), dtype=np.float32
        )
        query_embeddings = np.zeros((10, lfm_smoke.DIMENSION), dtype=np.float32)
        for index in range(20):
            document_embeddings[index, index] = 1.0
        for index, query in enumerate(queries):
            hard_negative = query["hard_negative_chunk_ids"][0]
            query_embeddings[index, positions[hard_negative]] = 1.0
        runtime = {
            "peak_vram_bytes": 1024,
            "backend_version": "test",
            "binary_sha256": "b" * 64,
            "gguf_sha256": "g" * 64,
        }
        with tempfile.TemporaryDirectory() as tmp:
            args = self._args(Path(tmp))
            with mock.patch.object(
                lfm_smoke, "load_frozen_dataset", return_value=(chunks, queries)
            ), mock.patch.object(
                lfm_smoke,
                "lfm_embed_queries_and_docs",
                return_value=(query_embeddings, document_embeddings, runtime),
            ):
                with self.assertRaisesRegex(RuntimeError, "semantic smoke"):
                    lfm_smoke.run_smoke(args)


if __name__ == "__main__":
    unittest.main()
