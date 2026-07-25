"""Tests for the production profiles validator."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parent.parent.parent.parent
VALIDATOR_PATH = REPO / "benchmark/embedding-v3/config/validate_production_profiles.py"


class ProductionProfilesValidatorTests(unittest.TestCase):
    """Test the validate_production_profiles module directly via its functions."""

    maxDiff = None

    def _load_validator(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("vpp", VALIDATOR_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_profiles_file_exists(self):
        path = REPO / "benchmark/embedding-v3/config/production_profiles.json"
        self.assertTrue(path.exists(), "production_profiles.json not found")
        with open(path) as f:
            data = json.load(f)
        self.assertIn("profiles", data)
        self.assertGreater(len(data["profiles"]), 0)

    def test_each_profile_has_required_fields(self):
        path = REPO / "benchmark/embedding-v3/config/production_profiles.json"
        with open(path) as f:
            data = json.load(f)
        required = {"id", "label", "enabled", "embedding", "reason"}
        for profile in data["profiles"]:
            missing = required - set(profile.keys())
            self.assertSetEqual(missing, set(),
                                f"Profile {profile.get('id', '?')} missing: {missing}")

    def test_each_embedding_has_required_fields(self):
        path = REPO / "benchmark/embedding-v3/config/production_profiles.json"
        with open(path) as f:
            data = json.load(f)
        required = {"id", "backend", "normalization", "pooling"}
        for profile in data["profiles"]:
            emb = profile.get("embedding", {})
            missing = required - set(emb.keys())
            self.assertSetEqual(missing, set(),
                                f"Profile {profile.get('id', '?')} embedding missing: {missing}")

    def test_validator_passes_on_real_data(self):
        vpp = self._load_validator()
        exit_code = vpp.main()
        self.assertEqual(exit_code, 0, "Validator should pass on real production profiles")

    def test_validator_rejects_forbidden_state(self):
        vpp = self._load_validator()
        fake_path = REPO / "benchmark/embedding-v3/config/production_profiles.json"
        with open(fake_path) as f:
            original = json.load(f)
        injected = dict(original)
        injected["profiles"] = list(original["profiles"])
        injected["profiles"].append({
            "id": "fake_rejected",
            "label": "Fake rejected",
            "enabled": False,
            "state": "REJECTED",
            "embedding": {"id": "embeddinggemma_768_float32", "backend": "llama.cpp", "normalization": "L2", "pooling": "mean"},
            "reason": "test injection"
        })
        with patch.object(vpp, "PROFILES_PATH", fake_path):
            with patch("builtins.open", side_effect=lambda p, *a, **kw: (
                __import__("io").StringIO(json.dumps(injected)) if "production_profiles" in str(p)
                else open(p, *a, **kw)
            )):
                errors = vpp.validate_forbidden_states()
        self.assertGreater(len(errors), 0, "Should reject forbidden state")

    def test_validator_requires_authorization_with_api(self):
        vpp = self._load_validator()
        fake_path = REPO / "benchmark/embedding-v3/config/production_profiles.json"
        with open(fake_path) as f:
            original = json.load(f)
        injected = dict(original)
        injected["profiles"] = list(original["profiles"])
        injected["profiles"].append({
            "id": "fake_api_no_auth",
            "label": "API without auth",
            "enabled": True,
            "requires_api": True,
            "requires_authorization": False,
            "embedding": {"id": "embeddinggemma_768_float32", "backend": "llama.cpp", "normalization": "L2", "pooling": "mean"},
            "reranker": {"id": "voyage_rerank_2_5", "backend": "voyage_api", "purpose": "test"},
            "reason": "test injection"
        })
        with patch.object(vpp, "PROFILES_PATH", fake_path):
            with patch("builtins.open", side_effect=lambda p, *a, **kw: (
                __import__("io").StringIO(json.dumps(injected)) if "production_profiles" in str(p)
                else open(p, *a, **kw)
            )):
                errors = vpp.validate_authorization_gate()
        self.assertGreater(len(errors), 0, "API without authorization should be rejected")


if __name__ == "__main__":
    unittest.main()
