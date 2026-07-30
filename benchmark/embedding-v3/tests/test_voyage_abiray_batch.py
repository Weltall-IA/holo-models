from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from holo_benchmark import voyage_abiray_batch as batch


class VoyageAbirayBatchTests(unittest.TestCase):
    def test_response_scores_maps_indices_to_chunk_ids(self) -> None:
        body = {
            "data": [
                {"index": 1, "relevance_score": 0.8},
                {"index": 0, "relevance_score": 0.3},
            ]
        }
        self.assertEqual(
            batch._response_scores(body, ["chunk-a", "chunk-b"]),
            {"chunk-a": 0.3, "chunk-b": 0.8},
        )

    def test_parse_output_restores_query_order(self) -> None:
        rows = [
            {
                "custom_id": "q2",
                "response": {
                    "status_code": 200,
                    "body": {
                        "data": [
                            {"index": 0, "relevance_score": 0.7},
                            {"index": 1, "relevance_score": 0.2},
                        ]
                    },
                },
                "error": None,
            },
            {
                "custom_id": "q1",
                "response": {
                    "status_code": 200,
                    "body": {
                        "data": [
                            {"index": 0, "relevance_score": 0.1},
                            {"index": 1, "relevance_score": 0.9},
                        ]
                    },
                },
                "error": None,
            },
        ]
        content = ("\n".join(json.dumps(row) for row in rows) + "\n").encode()
        parsed = batch._parse_output(
            content,
            ["q1", "q2"],
            [["a", "b"], ["c", "d"]],
        )
        self.assertEqual(parsed[0], {"a": 0.1, "b": 0.9})
        self.assertEqual(parsed[1], {"c": 0.7, "d": 0.2})

    def test_parse_output_rejects_failed_request(self) -> None:
        content = (
            json.dumps(
                {
                    "custom_id": "q1",
                    "response": None,
                    "error": {"code": "batch_expired"},
                }
            )
            + "\n"
        ).encode()
        with self.assertRaises(RuntimeError):
            batch._parse_output(content, ["q1"], [["a"]])

    def test_build_jsonl_uses_custom_id_query_and_documents(self) -> None:
        payloads = {variant: {} for variant in batch.VARIANTS}
        queries = [{"query_id": "q1", "query": "consulta"}]
        union_ids = [["c1", "c2"]]
        texts = {"c1": "documento 1", "c2": "documento 2"}
        with patch.object(
            batch,
            "_load_context",
            return_value=(payloads, queries, union_ids, texts),
        ):
            with self.assertRaisesRegex(ValueError, "expected 150"):
                batch.build_jsonl_lines()

    def test_terminal_statuses_include_completed(self) -> None:
        self.assertIn("completed", batch.TERMINAL_STATUSES)
        self.assertNotIn("in_progress", batch.TERMINAL_STATUSES)


if __name__ == "__main__":
    unittest.main()
