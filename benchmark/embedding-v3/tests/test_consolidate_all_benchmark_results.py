from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "consolidate_all_benchmark_results.py"
)
SPEC = importlib.util.spec_from_file_location("canonical_consolidator", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


SUMMARY_BASE = {
    "HitRate@1": 0.1,
    "HitRate@10": 0.2,
    "MRR@10": 0.15,
    "nDCG@10": 0.16,
}
SUMMARY_RERANKED = {
    "HitRate@1": 0.8,
    "HitRate@10": 0.9,
    "MRR@10": 0.85,
    "nDCG@10": 0.86,
}


class CanonicalConsolidationTests(unittest.TestCase):
    def write_json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_build_document_prefers_reranked_metrics_and_preserves_raw_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bench = root / "benchmark" / "embedding-v3"
            pipeline = (
                bench
                / "results"
                / "reranker"
                / "pipelines"
                / "test_reranker"
                / "embed_a.json"
            )
            self.write_json(
                pipeline,
                {
                    "pipeline_id": "embed_a__test_reranker",
                    "embedding_variant": "embed_a",
                    "reranker_id": "test_reranker",
                    "evaluation": {
                        "base_metrics": {"summary": SUMMARY_BASE},
                        "reranked_metrics": {
                            "summary": SUMMARY_RERANKED,
                            "by_query_type": {},
                        },
                    },
                },
            )
            for group, profile, mrr in (
                ("gate2", "gate2_profile", 0.5),
                ("gate3", "gate3_profile", 0.4),
            ):
                self.write_json(
                    bench / "results" / group / f"{profile}.json",
                    {
                        "id": profile,
                        "metrics": {
                            "summary": {
                                **SUMMARY_BASE,
                                "MRR@10": mrr,
                            }
                        },
                        "runtime": {"path": "/home/operator/model"},
                    },
                )
            baseline = {
                "schema_version": "2.0.0",
                "leaders_published": {
                    "selected_operational_pipeline": {
                        "pipeline_id": "kept",
                        "reason": "preserved",
                    }
                },
                "raw_embedding_profiles_ranked_by_mrr_at_10": [
                    {
                        "profile_id": "historical_profile",
                        "source_group": "historical_raw_none",
                        "source_path": "historical.json",
                        "metrics": {
                            "mrr_at_10": 0.3,
                            "hit_rate_at_1": 0.2,
                            "hit_rate_at_10": 0.4,
                            "ndcg_at_10": 0.31,
                        },
                        "runtime": {},
                        "metadata": {"path": "/home/operator/old"},
                        "rank_by_mrr_at_10": 99,
                    }
                ],
            }
            document = module.build_document(
                root,
                bench,
                baseline,
                generated_at="2026-07-29T00:00:00+00:00",
                source_commit="a" * 40,
                expected_pipeline_count=1,
                expected_pipeline_embeddings=1,
                expected_raw_profile_count=3,
                expected_reranker_counts={"test_reranker": 1},
                expected_raw_source_counts={
                    "gate2": 1,
                    "gate3": 1,
                    "historical_raw_none": 1,
                },
                required_raw_profile_ids={
                    "gate2_profile",
                    "gate3_profile",
                    "historical_profile",
                },
            )
            leader = document["leaders_published"]["best_by_mrr_at_10"]
            self.assertEqual(leader["metrics"]["mrr_at_10"], 0.85)
            self.assertEqual(
                leader["metric_summary_path"],
                "$.evaluation.reranked_metrics.summary",
            )
            self.assertEqual(document["canonical_scope"]["raw_embedding_profiles"], 3)
            self.assertEqual(document["canonical_scope"]["benchmark_records_total"], 4)
            self.assertEqual(
                document["leaders_published"]["selected_operational_pipeline"][
                    "pipeline_id"
                ],
                "kept",
            )
            serialized = json.dumps(document)
            self.assertNotIn("/home/operator", serialized)

    def test_strict_panel_rejects_incomplete_pipeline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = (
                root
                / "benchmark"
                / "embedding-v3"
                / "results"
                / "reranker"
                / "pipelines"
                / "mxbai_rerank_base_v2"
                / "profile.json"
            )
            self.write_json(
                path,
                {
                    "pipeline_id": "profile__mxbai_rerank_base_v2",
                    "embedding_variant": "profile",
                    "reranker_id": "mxbai_rerank_base_v2",
                    "candidate_top_k": 50,
                    "rerank_top_k": 20,
                    "evaluation": {
                        "base_metrics": {
                            "summary": SUMMARY_BASE,
                            "per_query": [],
                            "by_query_type": {},
                        },
                        "reranked_metrics": {
                            "summary": SUMMARY_RERANKED,
                            "per_query": [],
                            "by_query_type": {},
                        },
                        "per_query_effect": [],
                    },
                },
            )
            with self.assertRaisesRegex(ValueError, "per_query must contain 150"):
                module.pipeline_record(root, path)

    def test_strict_panel_accepts_complete_shape(self):
        section = {
            "summary": SUMMARY_RERANKED,
            "per_query": [{} for _ in range(150)],
            "by_query_type": {str(index): {} for index in range(7)},
        }
        module.validate_strict_pipeline(
            {
                "candidate_top_k": 50,
                "rerank_top_k": 20,
                "evaluation": {
                    "base_metrics": section,
                    "reranked_metrics": section,
                    "per_query_effect": [{} for _ in range(150)],
                },
            },
            "llama_nemotron_rerank_1b_v2",
        )

    def test_metric_container_never_uses_base_when_reranked_exists(self):
        path, summary, _ = module.metric_container(
            {
                "evaluation": {
                    "base_metrics": {"summary": SUMMARY_BASE},
                    "reranked_metrics": {"summary": SUMMARY_RERANKED},
                }
            },
            pipeline=True,
        )
        self.assertEqual(path, "$.evaluation.reranked_metrics.summary")
        self.assertEqual(summary["MRR@10"], 0.85)


if __name__ == "__main__":
    unittest.main()
