from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import reranker_preflight as rp


class PortablePathTests(unittest.TestCase):
    def test_portable_path_inside_repo_is_relative(self):
        repo_root = Path("/tmp/repo-root")
        path = repo_root / "embed" / "model.gguf"
        with mock.patch.object(rp, "REPO_ROOT", repo_root):
            self.assertEqual(rp._portable_path(path), "embed/model.gguf")

    def test_portable_path_external_redacts_parent(self):
        path = Path("/opt/private/model.gguf")
        with mock.patch.object(rp, "REPO_ROOT", Path("/tmp/repo-root")):
            cleaned = rp._portable_path(path)
        self.assertEqual(cleaned, "<external>/model.gguf")
        self.assertNotIn("/opt/private", cleaned)

    def test_portable_windows_path_redacts_parent(self):
        cleaned = rp._portable_path(r"C:\Users\alpha\models\model.gguf")
        self.assertEqual(cleaned, "<external>/model.gguf")
        self.assertNotIn("alpha", cleaned)

    def test_portable_candidate_does_not_mutate_source(self):
        repo_root = Path("/tmp/repo-root")
        source = {"path": str(repo_root / "rerank" / "model"), "bytes": 7}
        with mock.patch.object(rp, "REPO_ROOT", repo_root):
            cleaned = rp._portable_qwen_candidate(source)
        self.assertEqual(cleaned["path"], "rerank/model")
        self.assertTrue(Path(source["path"]).is_absolute())


class PreflightSerializationTests(unittest.TestCase):
    def test_preflight_persists_only_portable_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "checkout"
            project_root = repo_root / "benchmark" / "embedding-v3"
            results_dir = project_root / "results" / "reranker"
            reranker_path = repo_root / "rerank" / "qwen"
            reranker_path.mkdir(parents=True)
            project_root.mkdir(parents=True, exist_ok=True)
            captured = {}

            def capture(path, payload):
                captured["path"] = path
                captured["payload"] = payload

            args = argparse.Namespace(
                qwen_model_path="auto",
                candidate_top_k=50,
                rerank_top_k=20,
                instruction="rank",
                allow_voyage_rerank_api=False,
                api_key_path=repo_root / ".missing-key",
            )
            with mock.patch.object(rp, "REPO_ROOT", repo_root), mock.patch.object(
                rp, "PROJECT_ROOT", project_root
            ), mock.patch.object(rp, "RESULTS_DIR", results_dir), mock.patch.object(
                rp, "load_frozen_dataset", return_value=([{}] * 600, [{}] * 150)
            ), mock.patch.object(
                rp,
                "discover_qwen_rerankers",
                return_value=[{"path": str(reranker_path), "bytes": 7}],
            ), mock.patch.object(rp, "atomic_json", side_effect=capture):
                payload = rp.preflight(args)

        self.assertEqual(captured["payload"], payload)
        self.assertEqual(payload["qwen_candidates"][0]["path"], "rerank/qwen")
        self.assertEqual(payload["qwen_model_path_requested"], "auto")
        for item in payload["paths"].values():
            self.assertFalse(Path(item["path"]).is_absolute())
            self.assertNotIn(tmp, item["path"])


if __name__ == "__main__":
    unittest.main()
