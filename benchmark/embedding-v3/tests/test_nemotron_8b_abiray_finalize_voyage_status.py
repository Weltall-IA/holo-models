"""Regression test for nemotron_8b_abiray_finalize Voyage status block."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


class VoyageStatusBlockTests(unittest.TestCase):
    """After finalize, the Voyage Nemotron 8B status must be COMPLETED."""

    CONSOLIDATED = Path("ALL_BENCHMARK_RESULTS.json")
    VOYAGE_BLOCKED = Path("results/reranker/voyage_rerank_2_5_nemotron_8b_abiray_blocked.json")

    def test_voyage_status_not_blocked_when_pipelines_exist(self):
        if not self.CONSOLIDATED.is_file():
            self.skipTest("consolidated not present")
        data = json.loads(self.CONSOLIDATED.read_text(encoding="utf-8"))
        voyage_count = data.get("canonical_scope", {}).get(
            "published_pipeline_artifacts", data.get("inventory", {}).get("published_pipeline_count", 0)
        )
        # Count Voyage pipelines specifically
        voyage_pipelines = [
            p for p in data.get("published_pipelines_ranked_by_mrr_at_10", [])
            if p.get("reranker") == "voyage_rerank_2_5"
        ]
        voyage_count_actual = len(voyage_pipelines)
        status_block = data.get("voyage_nemotron_8b_status", {})

        if voyage_count_actual > 0:
            # When 11+ Voyage pipelines exist, status must NOT be BLOCKED_RATE_LIMIT
            self.assertNotEqual(
                status_block.get("status"),
                "BLOCKED_RATE_LIMIT",
                f"Voyage has {voyage_count_actual} pipelines but status is BLOCKED_RATE_LIMIT",
            )
            self.assertEqual(
                status_block.get("status"),
                "COMPLETED_BATCH",
                f"Expected COMPLETED_BATCH, got {status_block.get('status')}",
            )
            self.assertEqual(
                status_block.get("published_pipeline_count"),
                2,
                f"Expected published_pipeline_count=2 for Nemotron scope, "
                f"got {status_block.get('published_pipeline_count')}",
            )

    def test_voyage_blocked_artifact_not_present_when_completed(self):
        if not self.CONSOLIDATED.is_file():
            self.skipTest("consolidated not present")
        data = json.loads(self.CONSOLIDATED.read_text(encoding="utf-8"))
        voyage_count = len([
            p for p in data.get("published_pipelines_ranked_by_mrr_at_10", [])
            if p.get("reranker") == "voyage_rerank_2_5"
        ])
        if voyage_count > 0:
            self.assertFalse(
                self.VOYAGE_BLOCKED.is_file(),
                "Blocked artifact should not exist when Voyage pipelines are published",
            )

    def test_voyage_status_references_existing_artifacts(self):
        if not self.CONSOLIDATED.is_file():
            self.skipTest("consolidated not present")
        data = json.loads(self.CONSOLIDATED.read_text(encoding="utf-8"))
        status_block = data.get("voyage_nemotron_8b_status", {})
        if status_block.get("status") == "COMPLETED_BATCH":
            checkpoint = status_block.get("checkpoint", "")
            if checkpoint:
                self.assertTrue(
                    Path(checkpoint).is_file(),
                    f"Checkpoint referenced but missing: {checkpoint}",
                )


if __name__ == "__main__":
    unittest.main()
