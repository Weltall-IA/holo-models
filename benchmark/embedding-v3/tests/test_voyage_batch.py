from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from holo_benchmark.voyage_batch import (
    _sanitized_error,
    build_batch_jsonl,
    parse_batch_output,
)


class VoyageBatchTests(unittest.TestCase):
    def test_build_batch_jsonl_preserves_queries_and_candidates(self) -> None:
        queries = [
            {"query_id": "q1", "query": "primeira"},
            {"query_id": "q2", "query": "segunda"},
        ]
        union_ids = [["a", "b"], ["c"]]
        texts = {"a": "A", "b": "B", "c": "C"}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.jsonl"
            manifest = build_batch_jsonl(
                queries,
                union_ids,
                texts,
                "instrucao",
                path,
                lambda query, instruction: f"{instruction}:{query['query']}",
            )
            rows = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(manifest["requests"], 2)
        self.assertEqual(manifest["pairs"], 3)
        self.assertEqual(rows[0]["custom_id"], "q1")
        self.assertEqual(rows[0]["body"]["documents"], ["A", "B"])
        self.assertEqual(rows[1]["body"]["query"], "instrucao:segunda")

    def test_parse_batch_output_reorders_lines_and_result_indices(self) -> None:
        queries = [{"query_id": "q1"}, {"query_id": "q2"}]
        union_ids = [["a", "b"], ["c", "d"]]
        output = "\n".join(
            [
                json.dumps(
                    {
                        "custom_id": "q2",
                        "response": {
                            "status_code": 200,
                            "body": {
                                "data": [
                                    {"index": 1, "relevance_score": 0.9},
                                    {"index": 0, "relevance_score": 0.2},
                                ],
                                "usage": {"total_tokens": 20},
                            },
                        },
                        "error": None,
                    }
                ),
                json.dumps(
                    {
                        "custom_id": "q1",
                        "response": {
                            "status_code": 200,
                            "body": {
                                "results": [
                                    {"index": 0, "relevance_score": 0.7},
                                    {"index": 1, "relevance_score": 0.1},
                                ],
                                "total_tokens": 10,
                            },
                        },
                        "error": None,
                    }
                ),
            ]
        )
        rows, usage, errors = parse_batch_output(output, queries, union_ids)
        self.assertEqual(errors, [])
        self.assertEqual(rows, [{"a": 0.7, "b": 0.1}, {"c": 0.2, "d": 0.9}])
        self.assertEqual(usage, {"tokens": 30, "requests": 2})

    def test_parse_batch_output_reports_missing_requests(self) -> None:
        rows, usage, errors = parse_batch_output(
            "",
            [{"query_id": "q1"}],
            [["a"]],
        )
        self.assertEqual(rows, [])
        self.assertEqual(usage, {"tokens": 0, "requests": 0})
        self.assertEqual(errors[0]["custom_id"], "q1")

    def test_sanitized_error_extracts_message(self) -> None:
        raw = b'{"error":{"message":"rate limited"}}'
        self.assertEqual(_sanitized_error(raw), "rate limited")


if __name__ == "__main__":
    unittest.main()
