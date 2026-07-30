"""Tests for embedding load memory measurement."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


class EmbeddingLoadMemoryTests(unittest.TestCase):
    """Validate the top10_embedding_load_memory artifact."""

    ARTIFACT = Path("results/load-memory/top10_embedding_load_memory.json")

    def test_artifact_exists(self):
        self.assertTrue(self.ARTIFACT.is_file(), f"Missing: {self.ARTIFACT}")

    def test_artifact_parseable(self):
        data = json.loads(self.ARTIFACT.read_text())
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 5)

    def test_no_model_has_zero_weight(self):
        data = json.loads(self.ARTIFACT.read_text())
        for entry in data:
            if entry.get("status") == "REMOTE_API_NO_LOCAL_LOAD":
                continue
            self.assertGreater(entry.get("total_bytes", 0), 0,
                               f"{entry['model_id']} has zero weight bytes")

    def test_pass_models_have_load_seconds(self):
        data = json.loads(self.ARTIFACT.read_text())
        for entry in data:
            if entry.get("status") == "PASS":
                self.assertGreater(entry.get("load_seconds", 0), 0,
                                   f"{entry['model_id']} PASS but load_seconds=0")

    def test_remote_model_registered(self):
        data = json.loads(self.ARTIFACT.read_text())
        remote = [e for e in data if e.get("status") == "REMOTE_API_NO_LOCAL_LOAD"]
        self.assertGreaterEqual(len(remote), 1, "No remote model registered")


if __name__ == "__main__":
    unittest.main()
