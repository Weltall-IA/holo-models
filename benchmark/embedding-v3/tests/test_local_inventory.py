from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from holo_benchmark.local_inventory import _classify, discover_filesystem_models, inventory, render_report


class LocalInventoryTests(unittest.TestCase):
    def test_classifies_embedding_names(self):
        self.assertEqual(_classify("Qwen3-Embedding-8B-GGUF"), "embed")
        self.assertEqual(_classify("multilingual-e5-large-instruct"), "embed")
        self.assertEqual(_classify("bge-reranker-v2"), "reranker")

    def test_discovers_and_deduplicates_holo_model_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "embed"
            model = root / "colibri"
            model.mkdir(parents=True)
            (model / ".holo-model.json").write_text(
                json.dumps({"repo": "tardellirs/colibri-embed-ptbr"}), encoding="utf-8"
            )
            (model / "model.safetensors").write_bytes(b"x" * 16)
            records = discover_filesystem_models([root])
            self.assertEqual(len(records), 1)
            self.assertTrue(records[0].benchmark_eligible)
            self.assertEqual(records[0].category, "embed")

    def test_text_llm_is_not_embedding_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "text"
            root.mkdir()
            model = root / "Qwen3.5-4B-PTBR-Q6_K.gguf"
            model.write_bytes(b"x")
            records = discover_filesystem_models([root])
            self.assertEqual(len(records), 1)
            self.assertFalse(records[0].benchmark_eligible)
            self.assertTrue(records[0].healthcheck_eligible)
            self.assertEqual(records[0].category, "text")

    @patch("holo_benchmark.local_inventory.discover_ollama_models", return_value=[])
    @patch("holo_benchmark.local_inventory.default_roots", return_value=[])
    def test_inventory_summary(self, _roots, _ollama):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            embed = repo / "embed"
            embed.mkdir()
            (embed / "nomic-embed.gguf").write_bytes(b"x")
            payload = inventory(repo, extra_roots=[embed], include_ollama=True)
            self.assertEqual(payload["summary"]["total_models"], 1)
            self.assertEqual(payload["summary"]["embedding_benchmark_eligible"], 1)

    def test_report_requires_no_silent_omission(self):
        payload = {
            "summary": {
                "total_models": 0,
                "embedding_benchmark_eligible": 0,
                "healthcheck_eligible": 0,
                "categories": {},
                "embedding_model_ids": [],
                "benchmarked_embedding_model_ids": [],
                "pending_embedding_model_ids": [],
                "pending_healthcheck_model_ids": [],
                "coverage_complete": True,
            },
            "models": [],
        }
        report = render_report(payload)
        self.assertIn("omitido silenciosamente", report)


if __name__ == "__main__":
    unittest.main()
