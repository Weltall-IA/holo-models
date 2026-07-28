from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from holo_benchmark.bitnet_benchmark import remove_stale_candidate


class StaleCandidateCleanupTests(unittest.TestCase):
    def test_missing_candidate_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bitnet_270m_current.json"
            self.assertFalse(remove_stale_candidate(path, "bitnet_270m_current"))

    def test_legacy_candidate_for_failed_profile_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bitnet_270m_current.json"
            path.write_text(
                json.dumps(
                    {
                        "id": "bitnet_270m_current",
                        "embedding": "bitnet_270m_current",
                        "candidate_top_k": 50,
                        "candidates": {},
                    }
                ),
                encoding="utf-8",
            )
            self.assertTrue(remove_stale_candidate(path, "bitnet_270m_current"))
            self.assertFalse(path.exists())

    def test_canonical_candidate_for_failed_profile_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bitnet_270m_current.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "variant": "bitnet_270m_current",
                        "embedding": {"profile_id": "bitnet_270m_current"},
                        "dataset": {},
                        "candidate_top_k": 50,
                        "queries": [],
                    }
                ),
                encoding="utf-8",
            )
            self.assertTrue(remove_stale_candidate(path, "bitnet_270m_current"))
            self.assertFalse(path.exists())

    def test_mismatched_candidate_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bitnet_270m_current.json"
            path.write_text(
                json.dumps({"variant": "another_profile"}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "mismatched identity"):
                remove_stale_candidate(path, "bitnet_270m_current")
            self.assertTrue(path.exists())

    def test_unreadable_candidate_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bitnet_270m_current.json"
            path.write_text("{not-json", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "cannot validate stale candidate"):
                remove_stale_candidate(path, "bitnet_270m_current")
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
