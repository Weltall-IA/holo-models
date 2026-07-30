from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from holo_benchmark import lfm_artifact_finalize


class LfmArtifactFinalizeTests(unittest.TestCase):
    def _payload(self):
        return {
            "schema_version": "1.0",
            "id": lfm_artifact_finalize.PROFILE_ID,
            "status": "COMPLETED",
            "gate_result": "PASS",
            "model": {
                "id": lfm_artifact_finalize.PROFILE_ID,
                "revision": lfm_artifact_finalize.REVISION,
                "bytes": lfm_artifact_finalize.EXPECTED_GGUF_BYTES,
                "sha256": lfm_artifact_finalize.EXPECTED_GGUF_SHA256,
            },
            "dataset": {
                "combined_sha256": lfm_artifact_finalize.CORPUS_SHA256,
                "documents": 600,
                "queries": 150,
            },
            "runtime": {
                "device": "cuda",
                "peak_vram_bytes": 1,
                "gguf_sha256": lfm_artifact_finalize.EXPECTED_GGUF_SHA256,
            },
            "metrics": {
                "summary": {"HitRate@50": 0.9866666666666667},
                "by_query_type": {"semantic_event": {"count": 150}},
                "per_query": [{"query_id": f"query-{index:04d}"} for index in range(150)],
            },
            "hardware": {
                "filesystem": {"path": "/home/alpha/Playstoria/models"},
                "python": {"executable": "/home/alpha/.venv/bin/python"},
                "url": "https://example.com/",
            },
        }

    def test_finalizer_sanitizes_only_host_specific_strings(self):
        payload = self._payload()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = lfm_artifact_finalize.finalize_result(path)
            cleaned = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["sanitized_string_count"], 2)
        self.assertEqual(cleaned["hardware"]["filesystem"]["path"], "<path>")
        self.assertEqual(cleaned["hardware"]["python"]["executable"], "<path>")
        self.assertEqual(cleaned["hardware"]["url"], "https://example.com/")
        self.assertEqual(cleaned["metrics"], payload["metrics"])

    def test_finalizer_rejects_wrong_model_hash(self):
        payload = self._payload()
        payload["model"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "model SHA-256"):
                lfm_artifact_finalize.finalize_result(path)


if __name__ == "__main__":
    unittest.main()
