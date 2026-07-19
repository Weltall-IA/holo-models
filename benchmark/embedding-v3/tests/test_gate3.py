from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from holo_benchmark.gate3 import (
    Gate3ModelSpec,
    _baseline_comparisons,
    _status_for_results,
    load_gate3_specs,
    resolve_gate3_model,
)
from holo_benchmark.gate3_worker import (
    _quantization_from_filename,
    _truncate_and_normalize,
)


class Gate3Tests(unittest.TestCase):
    def _models_file(self, models: list[dict]) -> Path:
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / "models.json"
        path.write_text(json.dumps({"models": models}), encoding="utf-8")
        return path

    def tearDown(self) -> None:
        tmp = getattr(self, "tmp", None)
        if tmp is not None:
            tmp.cleanup()

    def test_versioned_gate3_configuration(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        config_path = project_root / "config" / "models.json"
        if not config_path.exists():
            config_path = project_root / "models.json"
        specs = load_gate3_specs(config_path)
        self.assertEqual(
            [spec.id for spec in specs],
            ["qwen3_embedding_8b_gguf", "embeddinggemma_gguf", "qwen3_embedding_06_gguf"],
        )
        self.assertEqual(specs[0].pooling, "last")
        self.assertEqual(specs[0].dimension, 1024)
        self.assertEqual(specs[0].native_dimension, 4096)
        self.assertEqual(specs[1].pooling, "mean")
        self.assertEqual(specs[1].prompt_profile, "embeddinggemma")
        self.assertEqual(specs[2].prompt_profile, "qwen3")

    def test_loads_only_enabled_gate3_llama_models(self) -> None:
        path = self._models_file([
            {"id":"a","repo":"org/a","file":"a.gguf","dimension":1024,"native_dimension":4096,"license":"apache-2.0","backend":"llama.cpp","gate":3,"enabled":True},
            {"id":"b","repo":"org/b","file":"b.gguf","dimension":768,"backend":"llama.cpp","gate":2,"enabled":True},
            {"id":"c","repo":"org/c","file":"c.gguf","dimension":768,"backend":"llama.cpp","gate":3,"enabled":False},
        ])
        specs = load_gate3_specs(path)
        self.assertEqual([spec.id for spec in specs], ["a"])
        self.assertEqual(specs[0].native_dimension, 4096)

    def test_rejects_non_llama_backend(self) -> None:
        path = self._models_file([
            {"id":"a","repo":"org/a","file":"a.gguf","dimension":768,"license":"apache-2.0","backend":"sentence-transformers","gate":3,"enabled":True}
        ])
        with self.assertRaisesRegex(ValueError, "somente llama.cpp"):
            load_gate3_specs(path)

    def test_rejects_invalid_target_dimension(self) -> None:
        path = self._models_file([
            {"id":"a","repo":"org/a","file":"a.gguf","dimension":4096,"native_dimension":1024,"license":"apache-2.0","backend":"llama.cpp","gate":3,"enabled":True}
        ])
        with self.assertRaisesRegex(ValueError, "dimensão inválida"):
            load_gate3_specs(path)

    def test_resolve_prefers_primary_file(self) -> None:
        spec = Gate3ModelSpec("a", "org/a", "q8.gguf", 1024, 4096, "apache-2.0", fallback_file="q6.gguf")
        api = SimpleNamespace(model_info=lambda *a, **k: SimpleNamespace(
            sha="abcdef1234567890",
            siblings=[SimpleNamespace(rfilename="q8.gguf", size=800), SimpleNamespace(rfilename="q6.gguf", size=600)],
            card_data={"license":"apache-2.0"}, gated=False,
        ))
        resolved = resolve_gate3_model(spec, Path("/tmp/a"), api=api)
        self.assertEqual(resolved.file, "q8.gguf")
        self.assertFalse(resolved.fallback_used)
        self.assertEqual(resolved.expected_size_bytes, 800)

    def test_resolve_uses_fallback_when_primary_absent(self) -> None:
        spec = Gate3ModelSpec("a", "org/a", "q8.gguf", 1024, 4096, "apache-2.0", fallback_file="q6.gguf")
        api = SimpleNamespace(model_info=lambda *a, **k: SimpleNamespace(
            sha="abcdef1234567890",
            siblings=[SimpleNamespace(rfilename="q6.gguf", size=600)],
            card_data={"license":"apache-2.0"}, gated=False,
        ))
        resolved = resolve_gate3_model(spec, Path("/tmp/a"), api=api)
        self.assertEqual(resolved.file, "q6.gguf")
        self.assertTrue(resolved.fallback_used)

    def test_resolve_rejects_missing_configured_files(self) -> None:
        spec = Gate3ModelSpec("a", "org/a", "q8.gguf", 1024, 4096, "apache-2.0", fallback_file="q6.gguf")
        api = SimpleNamespace(model_info=lambda *a, **k: SimpleNamespace(
            sha="abcdef1234567890", siblings=[], card_data={}, gated=False,
        ))
        with self.assertRaisesRegex(RuntimeError, "nenhum GGUF"):
            resolve_gate3_model(spec, Path("/tmp/a"), api=api)

    def test_matryoshka_truncation_renormalizes(self) -> None:
        matrix = np.asarray([[3.0, 4.0, 12.0], [0.0, 2.0, 2.0]], dtype=np.float32)
        truncated = _truncate_and_normalize(matrix, 2)
        np.testing.assert_allclose(np.linalg.norm(truncated, axis=1), [1.0, 1.0], atol=1e-6)
        self.assertEqual(truncated.shape, (2, 2))

    def test_full_cuda_required_set_passes(self) -> None:
        specs = [
            Gate3ModelSpec("a", "org/a", "a.gguf", 768, 768, "apache-2.0"),
            Gate3ModelSpec("b", "org/b", "b.gguf", 1024, 1024, "apache-2.0"),
        ]
        results = [{"model":{"id":"a"}}, {"model":{"id":"b"}}]
        self.assertEqual(_status_for_results(specs, results, [], full_dataset=True, full_model_set=True, device="cuda"), "PASS")

    def test_partial_selection_never_passes(self) -> None:
        specs = [Gate3ModelSpec("a", "org/a", "a.gguf", 768, 768, "apache-2.0")]
        results = [{"model":{"id":"a"}}]
        self.assertEqual(_status_for_results(specs, results, [], full_dataset=True, full_model_set=False, device="cuda"), "PARTIAL")

    def test_cpu_never_passes(self) -> None:
        specs = [Gate3ModelSpec("a", "org/a", "a.gguf", 768, 768, "apache-2.0")]
        results = [{"model":{"id":"a"}}]
        self.assertEqual(_status_for_results(specs, results, [], full_dataset=True, full_model_set=True, device="cpu"), "PARTIAL")

    def test_direct_baseline_comparison_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            baseline_path = project / "results" / "gate2" / "native.json"
            baseline_path.parent.mkdir(parents=True)
            baseline_path.write_text(json.dumps({
                "metrics": {"summary": {
                    "HitRate@1": 0.5, "HitRate@10": 0.8, "MRR@10": 0.6,
                    "nDCG@10": 0.65, "hard_negative_error_rate": 0.25
                }}
            }), encoding="utf-8")
            specs = [Gate3ModelSpec(
                "gguf", "org/gguf", "model.gguf", 1024, 1024, "apache-2.0",
                baseline_model_id="native"
            )]
            results = [{
                "model": {"id": "gguf"},
                "metrics": {"summary": {
                    "HitRate@1": 0.55, "HitRate@10": 0.82, "MRR@10": 0.61,
                    "nDCG@10": 0.66, "hard_negative_error_rate": 0.20
                }}
            }]
            comparison = _baseline_comparisons(project, specs, results)[0]
            self.assertEqual(comparison["status"], "COMPARED")
            self.assertAlmostEqual(comparison["deltas"]["MRR@10"], 0.01)
            self.assertAlmostEqual(comparison["deltas"]["hard_negative_error_rate"], -0.05)

    def test_quantization_is_read_from_filename(self) -> None:
        self.assertEqual(_quantization_from_filename("Qwen3-Embedding-8B-Q8_0.gguf"), "Q8_0")
        self.assertEqual(_quantization_from_filename("Qwen3-Embedding-8B-Q6_K.gguf"), "Q6_K")


if __name__ == "__main__":
    unittest.main()
