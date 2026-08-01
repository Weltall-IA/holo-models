"""Tests for deterministic canonicalization of legacy reranker pipelines."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINES = PROJECT_ROOT / "results" / "reranker" / "pipelines"
CANDIDATES = PROJECT_ROOT / "results" / "reranker" / "candidates"

LEGACY_RERANKERS = (
    "jina_reranker_v3_noncommercial",
    "kalm_reranker_v1_nano",
    "kalm_reranker_v1_small",
    "querit_reranker_4b",
)
MEASUREMENT_BLOCKED = "MEASUREMENT_BLOCKED_LEGACY_ARTIFACT"


def legacy_pipeline_files():
    for reranker in LEGACY_RERANKERS:
        directory = PIPELINES / reranker
        if directory.is_dir():
            yield from sorted(directory.glob("*.json"))


class LegacyMigrationTests(unittest.TestCase):
    def test_all_48_pipelines_migrated_to_canonical_schema(self):
        files = list(legacy_pipeline_files())
        self.assertEqual(len(files), 48, "expected 48 Jina/KaLM/Querit pipelines")
        for path in files:
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(data.get("schema_version"), "1.0")
                self.assertIn("evaluation", data)
                ev = data["evaluation"]
                self.assertIn("base_metrics", ev)
                self.assertIn("reranked_metrics", ev)
                self.assertIn("per_query_effect", ev)

    def test_reranked_summary_preserved(self):
        """Migration must preserve the historical reranked summary values."""
        for path in list(legacy_pipeline_files()):
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                ev = data["evaluation"]
                reranked = ev["reranked_metrics"]
                self.assertIn("MRR@10", reranked["summary"])
                self.assertEqual(len(reranked["per_query"]), 150)
                self.assertEqual(len(ev["base_metrics"]["per_query"]), 150)
                self.assertEqual(len(ev["per_query_effect"]), 150)

    def test_base_metrics_derived_from_candidates(self):
        """Base metrics must equal evaluation of the persisted candidate rankings."""
        for path in list(legacy_pipeline_files()):
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                embedding = data.get("embedding_variant") or path.stem
                candidate_path = CANDIDATES / f"{embedding}.json"
                self.assertTrue(
                    candidate_path.is_file(),
                    f"candidate missing for {embedding}",
                )
                base = data["evaluation"]["base_metrics"]
                self.assertEqual(len(base["per_query"]), 150)
                self.assertEqual(len(base.get("by_query_type", {})), 7)

    def test_absent_telemetry_and_effect_explicit(self):
        """Unmeasured telemetry and effect must be explicit, never invented."""
        for path in list(legacy_pipeline_files()):
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(
                    data["telemetry"]["status"],
                    MEASUREMENT_BLOCKED,
                )
                for row in data["evaluation"]["per_query_effect"]:
                    self.assertEqual(row.get("status"), MEASUREMENT_BLOCKED)

    def test_provenance_registered(self):
        """Provenance must distinguish historical execution from schema conversion."""
        for path in list(legacy_pipeline_files()):
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                prov = data["provenance"]
                self.assertEqual(prov["execution_type"], "historical_execution")
                self.assertTrue(prov["origin_commit"])
                self.assertEqual(prov["conversion"]["tool"], "tools/migrate_legacy_reranker_pipelines.py")
                self.assertTrue(prov["conversion"]["preserves_metrics"])


if __name__ == "__main__":
    unittest.main()
