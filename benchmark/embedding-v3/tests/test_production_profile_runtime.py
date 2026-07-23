"""Unit tests for production_profile_runtime module."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

REPO = Path(__file__).resolve().parent.parent.parent.parent
BENCH = REPO / "benchmark/embedding-v3"
PROFILES_PATH = BENCH / "config/production_profiles.json"


class ProfileLoadingTests(unittest.TestCase):
    """Test profile loading, selection, input validation."""

    def setUp(self):
        from holo_benchmark import production_profile_runtime as ppr
        self.ppr = ppr
        self.profiles = ppr._load_profiles(PROFILES_PATH)

    def test_loads_all_four_profiles(self):
        ids = {p["id"] for p in self.profiles}
        expected = {"local_default", "quality_external_optional",
                    "nemotron_gguf_evaluation", "nemotron_nvfp4_evaluation"}
        self.assertEqual(ids, expected)

    def test_find_profile_by_id(self):
        p = self.ppr._find_profile(self.profiles, "local_default")
        self.assertEqual(p["id"], "local_default")

    def test_find_profile_unknown_raises(self):
        with self.assertRaises(KeyError):
            self.ppr._find_profile(self.profiles, "nonexistent")

    def test_validate_input_empty(self):
        with self.assertRaises(ValueError):
            self.ppr._validate_input({"texts": [], "input_type": "document"})

    def test_validate_input_invalid_type(self):
        with self.assertRaises(ValueError):
            self.ppr._validate_input({"texts": ["a"], "input_type": "invalid"})

    def test_validate_input_too_many_texts(self):
        with self.assertRaises(ValueError):
            many = ["x"] * (self.ppr.MAX_TEXTS + 1)
            self.ppr._validate_input({"texts": many, "input_type": "document"})

    def test_validate_input_empty_string(self):
        with self.assertRaises(ValueError):
            self.ppr._validate_input({"texts": [""], "input_type": "document"})

    def test_validate_input_valid_passes(self):
        self.ppr._validate_input({"texts": ["ok"], "input_type": "query"})

    def test_disabled_profile_rejected_without_evaluation(self):
        p = self.ppr._find_profile(self.profiles, "nemotron_gguf_evaluation")
        with self.assertRaises(RuntimeError):
            self.ppr._check_profile_allowed(p, evaluation_mode=False, allow_external_api=False)

    def test_disabled_profile_allowed_in_evaluation_mode(self):
        p = self.ppr._find_profile(self.profiles, "nemotron_gguf_evaluation")
        result = self.ppr._check_profile_allowed(p, evaluation_mode=True, allow_external_api=False)
        self.assertTrue(result)

    def test_api_profile_blocked_without_authorization(self):
        p = self.ppr._find_profile(self.profiles, "quality_external_optional")
        with self.assertRaises(RuntimeError):
            self.ppr._check_profile_allowed(p, evaluation_mode=False, allow_external_api=False)

    def test_api_profile_blocked_with_flag_alone(self):
        p = self.ppr._find_profile(self.profiles, "quality_external_optional")
        with self.assertRaises(RuntimeError):
            self.ppr._check_profile_allowed(p, evaluation_mode=False, allow_external_api=True)


class ContractTests(unittest.TestCase):
    """Test the embedding contract (fake backend)."""

    def setUp(self):
        from holo_benchmark import production_profile_runtime as ppr
        self.ppr = ppr
        self.profiles = ppr._load_profiles(PROFILES_PATH)

    def test_fake_backend_returns_valid_contract(self):
        p = self.ppr._find_profile(self.profiles, "local_default")
        backend, meta = self.ppr.build_backend(p, force_fake=True)
        texts = ["texto de teste"]
        matrix = backend.embed(texts, p)
        dim = p["embedding"]["dimension"]
        self.assertEqual(matrix.shape, (1, dim))
        self.assertTrue(np.all(np.isfinite(matrix)))
        norms = np.linalg.norm(matrix, axis=1)
        self.assertAlmostEqual(norms[0], 1.0, places=5)

    def test_fake_backend_multiple_texts(self):
        p = self.ppr._find_profile(self.profiles, "local_default")
        backend, _ = self.ppr.build_backend(p, force_fake=True)
        texts = ["a", "b", "c"]
        matrix = backend.embed(texts, p)
        self.assertEqual(matrix.shape, (3, 768))

    def test_run_profile_fake_passes(self):
        result = self.ppr.run_profile(
            self.profiles, "local_default", ["texto teste"],
            force_fake=True)
        self.assertEqual(result.status, "PASSED")
        self.assertEqual(result.dimension, 768)
        self.assertEqual(result.vector_count, 1)

    def test_validate_embeddings_rejects_wrong_dimension(self):
        matrix = np.zeros((1, 123), dtype=np.float32)
        with self.assertRaises(ValueError):
            self.ppr._validate_embeddings(matrix, dimension=768, normalized=True)

    def test_validate_embeddings_rejects_nan(self):
        matrix = np.full((1, 768), np.nan, dtype=np.float32)
        with self.assertRaises(ValueError):
            self.ppr._validate_embeddings(matrix, dimension=768, normalized=True)

    def test_validate_embeddings_rejects_inf(self):
        matrix = np.full((1, 768), np.inf, dtype=np.float32)
        with self.assertRaises(ValueError):
            self.ppr._validate_embeddings(matrix, dimension=768, normalized=True)

    def test_validate_embeddings_rejects_zero_norm(self):
        matrix = np.zeros((1, 768), dtype=np.float32)
        with self.assertRaises(ValueError):
            self.ppr._validate_embeddings(matrix, dimension=768, normalized=True)

    def test_validate_embeddings_rejects_unormalized(self):
        matrix = np.full((1, 768), 0.5, dtype=np.float32)
        with self.assertRaises(ValueError):
            self.ppr._validate_embeddings(matrix, dimension=768, normalized=True)

    def test_validate_embeddings_rejects_non_l2(self):
        matrix = np.ones((1, 768), dtype=np.float32) * 0.5
        with self.assertRaises(ValueError):
            self.ppr._validate_embeddings(matrix, dimension=768, normalized=True)

    def test_evidence_has_no_embeddings(self):
        result = self.ppr.run_profile(
            self.profiles, "local_default", ["teste"],
            force_fake=True)
        evidence = result.to_evidence()
        self.assertNotIn("embeddings", evidence)
        self.assertNotIn("vectors", evidence)


class GuardianTests(unittest.TestCase):
    """Test API guard and error sanitization."""

    def setUp(self):
        from holo_benchmark import production_profile_runtime as ppr
        self.ppr = ppr
        self.profiles = ppr._load_profiles(PROFILES_PATH)

    def test_external_profile_blocked_without_token_read(self):
        with patch.object(self.ppr, "_check_profile_allowed") as mock_check:
            mock_check.side_effect = RuntimeError("should not call backend")
            with self.assertRaises(RuntimeError) as ctx:
                self.ppr._check_profile_allowed(
                    self.ppr._find_profile(self.profiles, "quality_external_optional"),
                    evaluation_mode=False, allow_external_api=False)
            self.assertIn("desabilitado", str(ctx.exception).lower() if False else "desabilitado")
        p = self.ppr._find_profile(self.profiles, "quality_external_optional")
        with self.assertRaises(RuntimeError):
            self.ppr._check_profile_allowed(p, evaluation_mode=False, allow_external_api=False)

    def test_sanitize_removes_repo_path(self):
        raw = f"/home/alpha/Playstoria/models/some/secret.key"
        cleaned = self.ppr._sanitize(raw)
        self.assertNotIn("alpha", cleaned)
        self.assertNotIn("Playstoria", cleaned)

    def test_nemotron_gguf_evaluation_rejected_without_flag(self):
        p = self.ppr._find_profile(self.profiles, "nemotron_gguf_evaluation")
        with self.assertRaises(RuntimeError) as ctx:
            self.ppr._check_profile_allowed(p, evaluation_mode=False, allow_external_api=False)
        self.assertIn("desabilitado", str(ctx.exception))

    def test_fake_backend_nemotron_dimension(self):
        p = self.ppr._find_profile(self.profiles, "nemotron_nvfp4_evaluation")
        backend, meta = self.ppr.build_backend(p, force_fake=True)
        texts = ["test"]
        matrix = backend.embed(texts, p)
        self.assertEqual(matrix.shape[1], 1024)

    def test_summary_excludes_full_embeddings(self):
        self.ppr.run_profile(self.profiles, "local_default", ["t"],
                             force_fake=True)
        summary = self.ppr.summarize_results([
            self.ppr.run_profile(self.profiles, "local_default", ["t"],
                                  force_fake=True)])
        self.assertNotIn("embeddings", json.dumps(summary))


if __name__ == "__main__":
    unittest.main()
