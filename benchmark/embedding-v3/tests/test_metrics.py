from __future__ import annotations

import unittest

from holo_benchmark.metrics import evaluate_rankings


class RetrievalMetricsTests(unittest.TestCase):
    def test_perfect_ranking(self) -> None:
        queries = [
            {
                "query_id": "q1",
                "query_type": "semantic_event",
                "relevant_chunk_ids": ["c1"],
                "hard_negative_chunk_ids": ["c2"],
            },
            {
                "query_id": "q2",
                "query_type": "semantic_event",
                "relevant_chunk_ids": ["c3", "c4"],
                "hard_negative_chunk_ids": ["c1"],
            },
        ]
        rankings = [
            ["c1", "c2", "c3", "c4"],
            ["c3", "c4", "c1", "c2"],
        ]
        result = evaluate_rankings(queries, rankings)
        self.assertEqual(result["summary"]["HitRate@1"], 1.0)
        self.assertEqual(result["summary"]["Recall@3"], 1.0)
        self.assertEqual(result["summary"]["MRR@10"], 1.0)
        self.assertEqual(result["summary"]["nDCG@10"], 1.0)
        self.assertEqual(result["summary"]["hard_negative_error_rate"], 0.0)

    def test_hard_negative_before_relevant_is_error(self) -> None:
        queries = [
            {
                "query_id": "q1",
                "query_type": "similar_scene",
                "relevant_chunk_ids": ["c1"],
                "hard_negative_chunk_ids": ["c2"],
            }
        ]
        result = evaluate_rankings(queries, [["c2", "c1", "c3"]])
        self.assertEqual(result["summary"]["HitRate@1"], 0.0)
        self.assertEqual(result["summary"]["HitRate@3"], 1.0)
        self.assertEqual(result["summary"]["MRR@10"], 0.5)
        self.assertEqual(result["summary"]["hard_negative_error_rate"], 1.0)
        self.assertEqual(result["summary"]["mean_first_relevant_rank"], 2.0)

    def test_query_without_relevant_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_rankings(
                [{"query_id": "q1", "relevant_chunk_ids": []}],
                [["c1"]],
            )


if __name__ == "__main__":
    unittest.main()
