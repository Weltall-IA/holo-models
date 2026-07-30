from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from holo_benchmark import bitnet_artifact_finalize as module


def _payload(profile_id: str):
    return {
        "schema_version": "1.0",
        "id": profile_id,
        "gate": 3,
        "status": "COMPLETED",
        "gate_result": "FAIL",
        "model": {"id": profile_id, "sha256": "a" * 64},
        "dataset": {"documents": 600, "queries": 150},
        "runtime": {
            "binary_path": "/home/user/runtime/bin",
            "command": ["/home/user/runtime/bin"],
        },
        "hardware": {"path": "/home/user/project"},
        "metrics": {
            "summary": {
                "HitRate@50": 0.8,
                "MRR@10": 0.2,
                "nDCG@10": 0.3,
                "queries_without_relevant": 0,
            },
            "by_query_type": {"semantic_event": {"count": 150}},
            "per_query": [
                {"query_id": f"query-{index:04d}"} for index in range(150)
            ],
        },
        "completed_at": "2026-07-29T00:00:00+00:00",
    }


class BitNetFinalizeTests(unittest.TestCase):
    def test_finalize_sanitizes_only_host_strings(self):
        profile_id = "bitnet_06b_current"
        payload = _payload(profile_id)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with mock.patch.object(
                module,
                "host_specific_strings",
                return_value=[{"path": "$.runtime.binary_path"}],
            ), mock.patch.object(
                module,
                "sanitize_host_payload",
                side_effect=lambda value: {
                    **value,
                    "runtime": {"binary_path": "<path>", "command": ["<path>"]},
                    "hardware": {"path": "<path>"},
                },
            ), mock.patch.object(module, "assert_portable_payload"):
                result = module.finalize_result(path, profile_id)
            written = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(result["sanitized_strings"], 1)
        self.assertEqual(written["metrics"], payload["metrics"])
        self.assertEqual(written["model"], payload["model"])
        self.assertEqual(written["runtime"]["binary_path"], "<path>")

    def test_incomplete_per_query_is_rejected(self):
        payload = _payload("bitnet_270m_current")
        payload["metrics"]["per_query"] = []
        with self.assertRaisesRegex(ValueError, "per-query"):
            module._validate(payload, "bitnet_270m_current")

    def test_profile_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "profile mismatch"):
            module._validate(_payload("bitnet_06b_current"), "bitnet_270m_current")


if __name__ == "__main__":
    unittest.main()
