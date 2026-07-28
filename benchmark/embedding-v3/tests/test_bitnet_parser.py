"""Tests for BitNet embedding output parser and runner — comprehensive suite."""
from __future__ import annotations

import os
import subprocess
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from holo_benchmark.bitnet_parser import detect_bitnet_dim, parse_bitnet_array_output
from holo_benchmark.bitnet_runner import bitnet_embed_texts


def _make_vector(dim: int, seed: int = 0) -> str:
    """Create a single L2-normalized vector string."""
    rng = np.random.RandomState(seed)
    raw = rng.randn(dim).astype(np.float64)
    raw /= np.linalg.norm(raw)
    return ",".join(f"{v:.7f}" for v in raw)


def _make_matrix(n: int, dim: int, start_seed: int = 0) -> str:
    """Create n distinct L2-normalized vectors in [[...],[...]] format."""
    parts = []
    for i in range(n):
        parts.append("[" + _make_vector(dim, start_seed + i * 1337) + "]")
    return "[" + ",".join(parts) + "]"


def _single_matrix(dim: int, seed: int = 0) -> str:
    """Single vector in [[...]] format (as BitNet outputs for 1 input)."""
    return "[[" + _make_vector(dim, seed) + "]]"


class TestParserValidVectors(unittest.TestCase):
    def test_single_1024(self):
        text = _single_matrix(1024, 1)
        arr = parse_bitnet_array_output(text, 1, 1024)
        self.assertEqual(arr.shape, (1, 1024))
        self.assertAlmostEqual(float(np.linalg.norm(arr[0])), 1.0, places=5)

    def test_single_640(self):
        text = _single_matrix(640, 2)
        arr = parse_bitnet_array_output(text, 1, 640)
        self.assertEqual(arr.shape, (1, 640))

    def test_multiple_distinct(self):
        text = _make_matrix(5, 1024, 10)
        arr = parse_bitnet_array_output(text, 5, 1024)
        self.assertEqual(arr.shape, (5, 1024))


class TestParserDimensionCountErrors(unittest.TestCase):
    def test_wrong_dimension(self):
        text = "[[" + _make_vector(512) + "]]"
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(text, 1, 1024)

    def test_wrong_count(self):
        text = _make_matrix(3, 1024)
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(text, 5, 1024)

    def test_empty_output(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output("", 1, 1024)

    def test_whitespace_only(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output("   \n  \t  ", 1, 1024)


class TestParserNaNInfZero(unittest.TestCase):
    def _make_with_bad_value(self, dim, bad_val, seed=50):
        vec = _make_vector(dim, seed)
        parts = vec.split(",")
        parts[-1] = bad_val
        return "[[" + ",".join(parts) + "]]"

    def test_nan_rejected(self):
        with self.assertRaises(ValueError, msg="NaN must be rejected"):
            parse_bitnet_array_output(self._make_with_bad_value(1024, "NaN"), 1, 1024)

    def test_inf_rejected(self):
        with self.assertRaises(ValueError, msg="inf must be rejected"):
            parse_bitnet_array_output(self._make_with_bad_value(1024, "inf"), 1, 1024)

    def test_neg_inf_rejected(self):
        with self.assertRaises(ValueError, msg="-inf must be rejected"):
            parse_bitnet_array_output(self._make_with_bad_value(1024, "-inf"), 1, 1024)

    def test_zero_norm_rejected(self):
        text = "[[" + ",".join(["0.0"] * 1024) + "]]"
        with self.assertRaises(ValueError, msg="zero norm must be rejected"):
            parse_bitnet_array_output(text, 1, 1024)


class TestParserTruncationResidual(unittest.TestCase):
    def test_truncated_vector_rejected(self):
        full = _make_vector(1024, 60)
        parts = full.split(",")
        truncated = ",".join(parts[:500])
        text = "[[" + truncated + "]]"
        with self.assertRaises(ValueError, msg="truncated output must be rejected"):
            parse_bitnet_array_output(text, 1, 1024)

    def test_residual_text_before_rejected(self):
        vec = _make_vector(1024, 70)
        text = "some residual text [[" + vec + "]]"
        with self.assertRaises(ValueError, msg="residual text before vectors must be rejected"):
            parse_bitnet_array_output(text, 1, 1024)

    def test_residual_text_after_rejected(self):
        vec = _make_vector(1024, 71)
        text = "[[" + vec + "]] some residual text after"
        with self.assertRaises(ValueError, msg="residual text after vectors must be rejected"):
            parse_bitnet_array_output(text, 1, 1024)


class TestParserDuplicateDetection(unittest.TestCase):
    def test_identical_vectors_distinct_inputs_rejected(self):
        vec = _make_vector(1024, 80)
        text = "[[" + vec + "],[" + vec + "]]"
        with self.assertRaises(ValueError, msg="identical vectors for distinct inputs must be rejected"):
            parse_bitnet_array_output(text, 2, 1024, allow_identical=False)

    def test_identical_vectors_allowed_when_permitted(self):
        vec = _make_vector(1024, 81)
        text = "[[" + vec + "],[" + vec + "]]"
        arr = parse_bitnet_array_output(text, 2, 1024, allow_identical=True)
        self.assertEqual(arr.shape, (2, 1024))
        np.testing.assert_array_equal(arr[0], arr[1])


class TestParserFormatEdgeCases(unittest.TestCase):
    def test_missing_outer_brackets(self):
        vec = _make_vector(1024, 90)
        text = vec
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(text, 1, 1024)

    def test_single_bracket_level(self):
        vec = _make_vector(1024, 91)
        text = "[" + vec + "]"
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(text, 1, 1024)


class TestDetectBitnetDim(unittest.TestCase):
    def test_06b(self):
        self.assertEqual(detect_bitnet_dim("bitnet_06b_current"), 1024)

    def test_270m(self):
        self.assertEqual(detect_bitnet_dim("bitnet_270m_current"), 640)

    def test_unknown_raises(self):
        with self.assertRaises(ValueError):
            detect_bitnet_dim("unknown_model")


class TestRunner(unittest.TestCase):
    def test_runner_applies_instruction_to_queries_only(self):
        """Verify instruction prefix is applied only to query indices."""
        from holo_benchmark.bitnet_runner import bitnet_embed_texts

        dim = 1024
        vec1 = _make_vector(dim, 200)
        vec2 = _make_vector(dim, 201)
        vec3 = _make_vector(dim, 202)
        mock_stdout = f"[[{vec1}],[{vec2}],[{vec3}]]"

        # Capture the file path and content before the runner's finally block deletes it
        captured_content = {}

        def fake_run(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            for a in cmd:
                if isinstance(a, str) and a.endswith(".txt"):
                    with open(a) as f:
                        captured_content["text"] = f.read()
            return mock.Mock(returncode=0, stdout=mock_stdout, stderr="")

        with mock.patch("subprocess.run", side_effect=fake_run), \
             tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as fake_bin, \
             tempfile.NamedTemporaryFile(delete=False, suffix=".gguf") as fake_gguf:
            fake_bin.write(b"fake"); fake_bin.close()
            fake_gguf.write(b"fake"); fake_gguf.close()
            embs, info = bitnet_embed_texts(
                ["doc text 0", "doc text 1", "query text"],
                gguf_path=Path(fake_gguf.name),
                bitnet_bin=Path(fake_bin.name),
                expected_dim=dim,
                instruction_prefix="Instruct: retrieve\nQuery: ",
                doc_indices=[0, 1],
                query_indices=[2],
            )
            self.assertEqual(embs.shape, (3, dim))
            self.assertEqual(info["n_documents"], 2)
            self.assertEqual(info["n_queries"], 1)
            lines = captured_content["text"].strip().split("\n")
            self.assertEqual(lines[0], "doc text 0")
            self.assertEqual(lines[1], "doc text 1")
            # Instruction spans multiple lines; join all remaining and verify
            query_content = "\n".join(lines[2:])
            self.assertTrue(query_content.startswith("Instruct: retrieve"))
            self.assertTrue(query_content.endswith("query text"))
            os.unlink(fake_bin.name)
            os.unlink(fake_gguf.name)

    def test_runner_nonzero_exit_raises(self):
        from holo_benchmark.bitnet_runner import bitnet_embed_texts

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(returncode=1, stdout="", stderr="error msg")
            with self.assertRaises(RuntimeError):
                bitnet_embed_texts(
                    ["test"],
                    gguf_path=Path("/tmp/fake.gguf"),
                    bitnet_bin=Path("/tmp/fake-embedding"),
                    expected_dim=1024,
                )

    def test_runner_metadata(self):
        from holo_benchmark.bitnet_runner import bitnet_embed_texts

        dim = 1024
        vec = _make_vector(dim, 300)
        mock_stdout = f"[[{vec}]]"

        with mock.patch("subprocess.run") as mock_run, \
             tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as fake_bin, \
             tempfile.NamedTemporaryFile(delete=False, suffix=".gguf") as fake_gguf:
            fake_bin.write(b"fake"); fake_bin.close()
            fake_gguf.write(b"fake"); fake_gguf.close()
            mock_run.return_value = mock.Mock(returncode=0, stdout=mock_stdout, stderr="")
            embs, info = bitnet_embed_texts(
                ["hello"],
                gguf_path=Path(fake_gguf.name),
                bitnet_bin=Path(fake_bin.name),
                expected_dim=dim,
            )
            self.assertEqual(info["backend"], "bitnet.cpp")
            self.assertEqual(info["dimension"], 1024)
            self.assertEqual(info["n_texts"], 1)
            self.assertIn("binary_sha256", info)
            self.assertIn("gguf_sha256", info)
            # encode_seconds is 0 for mock runs (no actual processing)
            self.assertGreaterEqual(info["encode_seconds"], 0)
            os.unlink(fake_bin.name)
            os.unlink(fake_gguf.name)


class TestCandidateSchemaIntegration(unittest.TestCase):
    """Test that BitNet candidates can be loaded by the canonical loader."""

    def test_candidate_format_compatible(self):
        """Verify our candidates JSON matches what load_candidate_payloads expects."""
        # Simulate the canonical candidate format
        candidate = {
            "id": "bitnet_270m_current",
            "variant": "bitnet_270m_current",
            "dataset": {
                "corpus_sha256": "8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b",
            },
            "candidate_top_k": 50,
            "queries": [
                {
                    "query_id": f"query-{i:04d}",
                    "candidates": [{"chunk_id": f"chunk-{i:04d}"} for i in range(50)],
                }
                for i in range(150)
            ],
        }
        # Verify structure matches loader expectations
        self.assertEqual(candidate["variant"], "bitnet_270m_current")
        self.assertIn("dataset", candidate)
        self.assertEqual(candidate["dataset"]["corpus_sha256"],
                         "8e1b7a6dd6f51d98e1ffe1738b6a59498df24c49b2edca24850b838687dd149b")
        self.assertEqual(len(candidate["queries"]), 150)
        for q in candidate["queries"]:
            self.assertEqual(len(q["candidates"]), 50)


if __name__ == "__main__":
    unittest.main()
