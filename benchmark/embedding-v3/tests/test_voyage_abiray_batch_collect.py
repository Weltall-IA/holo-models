from __future__ import annotations

import json
import unittest

from holo_benchmark.voyage_abiray_batch_collect import (
    _parse_output,
    _partial_rankings,
    _response_scores,
)


class VoyageAbirayBatchCollectTests(unittest.TestCase):
    def test_response_scores_accepts_top20_of_larger_union(self) -> None:
        ids = [f"chunk-{index:02d}" for index in range(33)]
        body = {
            "data": [
                {"index": index, "relevance_score": 1.0 - index / 100.0}
                for index in range(20)
            ]
        }
        scores = _response_scores(body, ids)
        self.assertEqual(len(scores), 20)
        self.assertEqual(set(scores), set(ids[:20]))

    def test_response_scores_rejects_duplicate_indices(self) -> None:
        ids = [f"chunk-{index:02d}" for index in range(20)]
        body = {
            "data": [
                {"index": 0, "relevance_score": 1.0},
                {"index": 0, "relevance_score": 0.9},
            ]
        }
        with self.assertRaisesRegex(ValueError, "returned 2 rows; expected 20"):
            _response_scores(body, ids)

    def test_parse_output_accepts_partial_union_scores(self) -> None:
        query_ids = ["query-0001"]
        union_ids = [[f"chunk-{index:02d}" for index in range(25)]]
        row = {
            "custom_id": "query-0001",
            "response": {
                "status_code": 200,
                "body": {
                    "data": [
                        {"index": index, "relevance_score": float(20 - index)}
                        for index in range(20)
                    ]
                },
            },
            "error": None,
        }
        scores = _parse_output(
            (json.dumps(row) + "\n").encode("utf-8"), query_ids, union_ids
        )
        self.assertEqual(len(scores), 1)
        self.assertEqual(len(scores[0]), 20)

    def test_partial_rankings_appends_unscored_in_base_order(self) -> None:
        candidates = [[
            {"chunk_id": "a", "rank": 1},
            {"chunk_id": "b", "rank": 2},
            {"chunk_id": "c", "rank": 3},
            {"chunk_id": "d", "rank": 4},
        ]]
        scores = [{"c": 0.9, "a": 0.8}]
        self.assertEqual(
            _partial_rankings(candidates, scores),
            [["c", "a", "b", "d"]],
        )


if __name__ == "__main__":
    unittest.main()
