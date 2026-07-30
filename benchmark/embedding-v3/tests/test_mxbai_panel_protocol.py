from __future__ import annotations

import argparse
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from holo_benchmark import mxbai_panel_protocol as module


class LogitScore:
    pass


class GoodModel:
    def named_modules(self):
        return [("", self), ("1", LogitScore())]

    def predict(self, pairs, **kwargs):
        self.last_pairs = pairs
        self.last_kwargs = kwargs
        return np.asarray([0.1, 5.0, 0.4, -0.2], dtype=np.float32)


class BadModel(GoodModel):
    def predict(self, pairs, **kwargs):
        return np.asarray([5.0, 0.1, 0.4, -0.2], dtype=np.float32)


class MixedbreadProtocolTests(unittest.TestCase):
    def _snapshot(self, root: Path, revision: str = "a" * 40) -> Path:
        for relative in module.CRITICAL_MODEL_FILES:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"fixture:{relative}".encode("utf-8"))
            metadata = (
                root
                / ".cache"
                / "huggingface"
                / "download"
                / f"{relative}.metadata"
            )
            metadata.parent.mkdir(parents=True, exist_ok=True)
            metadata.write_text(f"{revision}\netag\n0\n", encoding="utf-8")
        return root

    def test_complete_snapshot_requires_one_revision_and_records_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._snapshot(Path(directory))
            expected_weight_sha = hashlib.sha256(
                (root / module.MODEL_WEIGHT_FILE).read_bytes()
            ).hexdigest()
            with mock.patch.object(module, "MODEL_WEIGHT_SHA256", expected_weight_sha):
                resolved, identity = module.validate_complete_model(root, "a" * 40)
        self.assertEqual(resolved, root.resolve())
        self.assertEqual(identity["revision"], "a" * 40)
        self.assertEqual(
            len(identity["critical_snapshot_files"]), len(module.CRITICAL_MODEL_FILES)
        )

    def test_complete_snapshot_rejects_divergent_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._snapshot(Path(directory))
            metadata = (
                root
                / ".cache"
                / "huggingface"
                / "download"
                / "modules.json.metadata"
            )
            metadata.write_text(f"{'b' * 40}\netag\n0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "divergent revisions"):
                module.validate_complete_model(root, "a" * 40)

    def test_native_query_rejects_generic_instruction(self):
        self.assertEqual(module.native_query_text({"query": "consulta"}), "consulta")
        with self.assertRaisesRegex(ValueError, "raw query-document pair"):
            module.native_query_text({"query": "consulta"}, "classifique")

    def test_logit_score_module_is_required(self):
        names = module.require_logit_score_module(GoodModel())
        self.assertTrue(any("LogitScore" in name for name in names))
        with self.assertRaisesRegex(RuntimeError, "LogitScore"):
            module.require_logit_score_module(SimpleNamespace(named_modules=lambda: []))

    def test_official_semantic_smoke_requires_mars_top1(self):
        model = GoodModel()
        result = module.official_semantic_smoke(model, identity_activation=object())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["top_index"], 1)
        self.assertEqual(model.last_pairs[1][1].split(",", 1)[0], "Mars")

    def test_official_semantic_smoke_rejects_wrong_top1(self):
        with self.assertRaisesRegex(RuntimeError, "Mars passage was not top-1"):
            module.official_semantic_smoke(BadModel(), identity_activation=object())

    def test_install_protocol_replaces_runtime_hooks(self):
        target = SimpleNamespace(validate_model=None, score_cross_encoder=None)
        module.install_protocol(target, "c" * 40)
        self.assertTrue(callable(target.validate_model))
        self.assertIs(target.score_cross_encoder, module.score_cross_encoder_native)


if __name__ == "__main__":
    unittest.main()
