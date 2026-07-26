from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import urllib.error

from holo_benchmark.voyage_batch import (
    VoyageBatchHTTPError,
    _sanitized_error,
    _text_request,
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


class VoyageBatchRedirectTests(unittest.TestCase):
    """Regression tests for output-file download after a 307 redirect.

    Voyage returns a 307 to a pre-signed URL for batch output content. The
    previous implementation used urllib, which dropped the Authorization
    header on the cross-host redirect and hung. The fix follows redirects
    (requests, with an urllib fallback) without altering reranking params.
    """

    def test_text_request_requests_path_follows_redirects_and_keeps_auth(self) -> None:
        import requests

        resp = mock.Mock()
        resp.status_code = 200
        resp.text = "CONTENT"
        resp.headers = {}
        with mock.patch.object(requests, "get", return_value=resp) as get:
            out = _text_request("/v1/files/x/content", "KEY")
        self.assertEqual(out, "CONTENT")
        _, kwargs = get.call_args
        self.assertTrue(kwargs.get("allow_redirects"))
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer KEY")

    def test_text_request_requests_path_raises_on_error_status(self) -> None:
        import requests

        resp = mock.Mock()
        resp.status_code = 402
        resp.content = b'{"error":{"message":"payment required"}}'
        resp.headers = {}
        with mock.patch.object(requests, "get", return_value=resp):
            with self.assertRaises(VoyageBatchHTTPError) as ctx:
                _text_request("/v1/files/x/content", "KEY")
        self.assertEqual(ctx.exception.status_code, 402)
        self.assertIn("payment required", str(ctx.exception))

    def test_text_request_urllib_fallback_follows_307_and_strips_auth(self) -> None:
        import holo_benchmark.voyage_batch as vb

        real_import = __builtins__["__import__"]

        def fake_import(name, *args, **kwargs):
            if name == "requests":
                raise ImportError("requests unavailable in this environment")
            return real_import(name, *args, **kwargs)

        response = mock.MagicMock()
        response.read.return_value = b"CONTENT"
        response.__enter__.return_value = response
        state = {"calls": 0}
        redirect = urllib.error.HTTPError(
            "http://api.voyageai.com/v1/files/x/content",
            307,
            "redirect",
            {"Location": "https://presigned.example/file"},
            None,
        )

        def open_side(req, timeout=None):
            state["calls"] += 1
            if state["calls"] == 1:
                raise redirect
            return response

        with mock.patch("builtins.__import__", side_effect=fake_import), \
                mock.patch("urllib.request.build_opener") as build_opener, \
                mock.patch("urllib.request.Request") as request_cls:
            opener = mock.Mock()
            opener.open.side_effect = open_side
            build_opener.return_value = opener
            out = vb._text_request("/v1/files/x/content", "KEY")
        self.assertEqual(out, "CONTENT")
        self.assertEqual(state["calls"], 2)
        # Second request targets the redirect (pre-signed) URL and must not
        # carry the Authorization header.
        second_headers = request_cls.call_args_list[1].kwargs.get("headers", {})
        self.assertNotIn("Authorization", second_headers)
        self.assertIn("Accept", second_headers)

    def test_text_request_urllib_fallback_propagates_non_redirect_error(self) -> None:
        import holo_benchmark.voyage_batch as vb

        real_import = __builtins__["__import__"]

        def fake_import(name, *args, **kwargs):
            if name == "requests":
                raise ImportError("requests unavailable")
            return real_import(name, *args, **kwargs)

        error = urllib.error.HTTPError(
            "http://api.voyageai.com/v1/files/x/content",
            429,
            "rate limit",
            {},
            None,
        )
        with mock.patch("builtins.__import__", side_effect=fake_import), \
                mock.patch("urllib.request.build_opener") as build_opener, \
                mock.patch("urllib.request.Request"):
            opener = mock.Mock()
            opener.open.side_effect = error
            build_opener.return_value = opener
            with self.assertRaises(VoyageBatchHTTPError) as ctx:
                vb._text_request("/v1/files/x/content", "KEY")
        self.assertEqual(ctx.exception.status_code, 429)


if __name__ == "__main__":
    unittest.main()
