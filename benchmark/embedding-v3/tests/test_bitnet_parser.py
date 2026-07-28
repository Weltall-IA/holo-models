"""Tests for BitNet embedding output parser and runner."""
from __future__ import annotations

import unittest

import numpy as np

from holo_benchmark.bitnet_parser import detect_bitnet_dim, parse_bitnet_array_output
from pathlib import Path


class TestParseBitnetArrayOutput(unittest.TestCase):
    """Tests for the BitNet array output parser."""

    def _make_normalized(self, dim):
        """Create a L2-normalized vector of given dimension."""
        raw = [float(i * 0.001 - 0.5) for i in range(dim)]
        norm = sum(v ** 2 for v in raw) ** 0.5
        return ",".join(f"{v / norm:.7f}" for v in raw)

    def test_valid_single_vector_1024(self):
        vec = self._make_normalized(1024)
        arr = parse_bitnet_array_output(f"[{vec}]", 1, 1024)
        self.assertEqual(arr.shape, (1, 1024))

    def test_valid_single_vector_640(self):
        vec = self._make_normalized(640)
        arr = parse_bitnet_array_output(f"[{vec}]", 1, 640)
        self.assertEqual(arr.shape, (1, 640))

    def test_valid_multiple_vectors(self):
        vec = self._make_normalized(1024)
        text = f"[{vec}]\n[{vec}]"
        arr = parse_bitnet_array_output(text, 2, 1024)
        self.assertEqual(arr.shape, (2, 1024))

    def test_count_mismatch(self):
        vec = self._make_normalized(1024)
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(f"[{vec}]", 2, 1024)

    def test_dimension_mismatch(self):
        short = "[" + ",".join("0.001" for _ in range(512)) + "]"
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(f"[{short}]", 1, 1024)

    def test_empty_output(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output("", 1, 1024)

    def test_no_vectors_found(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output("hello world no vectors here", 1, 1024)

    def test_nan_rejected(self):
        vec = ",".join(["0.001"] * 1023) + ",NaN"
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(f"[{vec}]", 1, 1024)

    def test_inf_rejected(self):
        vec = ",".join(["0.001"] * 1023) + ",inf"
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(f"[{vec}]", 1, 1024)

    def test_zero_norm_rejected(self):
        vec = "[" + ",".join(["0.0"] * 1024) + "]"
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(f"[{vec}]", 1, 1024)


class TestDetectBitnetDim(unittest.TestCase):
    def test_06b_1024(self):
        self.assertEqual(detect_bitnet_dim(Path("bitnet-embeddings-0.6b-bf16-i2_s.gguf")), 1024)

    def test_270m_640(self):
        self.assertEqual(detect_bitnet_dim(Path("bitnet-embeddings-270m-bf16-i2_s.gguf")), 640)

    def test_unknown_raises(self):
        with self.assertRaises(ValueError):
            detect_bitnet_dim(Path("unknown-model.gguf"))


if __name__ == "__main__":
    unittest.main()
