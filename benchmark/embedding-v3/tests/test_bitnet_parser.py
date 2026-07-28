from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from holo_benchmark.bitnet_benchmark import (
    build_candidate_payload,
    validate_candidate_payload,
)
from holo_benchmark.bitnet_parser import detect_bitnet_dim, parse_bitnet_array_output
from holo_benchmark.bitnet_runner import bitnet_embed_texts
from holo_benchmark.reranker_runtime import CORPUS_SHA256, atomic_json


def _vector(dim: int, seed: int = 0) -> list[float]:
    rng = np.random.RandomState(seed)
    values = rng.randn(dim).astype(np.float64)
    values /= np.linalg.norm(values)
    return [float(f"{value:.7f}") for value in values]


def _payload(vectors: list[list[float]]) -> str:
    return json.dumps(vectors, separators=(",", ":"))


class ParserTests(unittest.TestCase):
    def test_valid_1024(self):
        result = parse_bitnet_array_output(_payload([_vector(1024, 1)]), 1, 1024)
        self.assertEqual(result.shape, (1, 1024))

    def test_valid_640(self):
        result = parse_bitnet_array_output(_payload([_vector(640, 2)]), 1, 640)
        self.assertEqual(result.shape, (1, 640))

    def test_multiple_distinct(self):
        result = parse_bitnet_array_output(
            _payload([_vector(640, 3), _vector(640, 4)]),
            2,
            640,
            inputs=["a", "b"],
        )
        self.assertEqual(result.shape, (2, 640))

    def test_wrong_dimension(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(_payload([_vector(12)]), 1, 640)

    def test_wrong_count(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(_payload([_vector(640)]), 2, 640)

    def test_empty(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output("", 1, 640)

    def test_whitespace(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(" \n\t", 1, 640)

    def test_nan(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output("[[NaN]]", 1, 1)

    def test_infinity(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output("[[Infinity]]", 1, 1)

    def test_negative_infinity(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output("[[-Infinity]]", 1, 1)

    def test_zero_norm(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(json.dumps([[0.0] * 640]), 1, 640)

    def test_residual_before(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output("log:" + _payload([_vector(640)]), 1, 640)

    def test_residual_after(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(_payload([_vector(640)]) + "log", 1, 640)

    def test_truncated(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(_payload([_vector(640)])[:-2], 1, 640)

    def test_double_comma(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output("[[1.0,,2.0]]", 1, 2)

    def test_trailing_comma(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output("[[1.0,]]", 1, 1)

    def test_invalid_separator(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output("[[1.0][2.0]]", 2, 1)

    def test_boolean_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output("[[true]]", 1, 1)

    def test_duplicate_distinct_inputs_rejected(self):
        vector = _vector(640, 7)
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(
                _payload([vector, vector]), 2, 640, inputs=["a", "b"]
            )

    def test_duplicate_identical_inputs_allowed(self):
        vector = _vector(640, 8)
        result = parse_bitnet_array_output(
            _payload([vector, vector]), 2, 640, inputs=["same", "same"]
        )
        self.assertEqual(result.shape, (2, 640))

    def test_duplicate_without_identity_rejected(self):
        vector = _vector(640, 9)
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(_payload([vector, vector]), 2, 640)

    def test_input_count_mismatch(self):
        with self.assertRaises(ValueError):
            parse_bitnet_array_output(
                _payload([_vector(640)]), 1, 640, inputs=["a", "b"]
            )

    def test_detect_dimensions(self):
        self.assertEqual(detect_bitnet_dim("bitnet_06b_current"), 1024)
        self.assertEqual(detect_bitnet_dim("bitnet_270m_current"), 640)
        with self.assertRaises(ValueError):
            detect_bitnet_dim("unknown")


class RunnerTests(unittest.TestCase):
    def _files(self):
        binary = tempfile.NamedTemporaryFile(delete=False)
        binary.write(b"binary")
        binary.close()
        os.chmod(binary.name, 0o755)
        model = tempfile.NamedTemporaryFile(delete=False, suffix=".gguf")
        model.write(b"model")
        model.close()
        self.addCleanup(lambda: os.path.exists(binary.name) and os.unlink(binary.name))
        self.addCleanup(lambda: os.path.exists(model.name) and os.unlink(model.name))
        return Path(binary.name), Path(model.name)

    def test_instruction_only_on_queries_and_metadata(self):
        binary, model = self._files()
        stdout = _payload([_vector(1024, 10), _vector(1024, 11)])
        captured = {}

        def fake_run(command, **kwargs):
            input_path = Path(command[command.index("-f") + 1])
            captured["lines"] = input_path.read_text(encoding="utf-8").splitlines()
            return mock.Mock(returncode=0, stdout=stdout, stderr="")

        with mock.patch(
            "holo_benchmark.bitnet_runner.subprocess.run", side_effect=fake_run
        ):
            embeddings, info = bitnet_embed_texts(
                ["document", "query"],
                profile_id="bitnet_06b_current",
                gguf_path=model,
                bitnet_bin=binary,
                bitnet_commit="abc123",
                instruction_prefix="query: ",
                doc_indices=[0],
                query_indices=[1],
            )
        self.assertEqual(embeddings.shape, (2, 1024))
        self.assertEqual(captured["lines"], ["document", "query: query"])
        self.assertEqual(info["bitnet_commit"], "abc123")
        self.assertEqual(info["exit_code"], 0)
        self.assertIn("combined_encode_seconds", info)
        self.assertNotIn("doc_encode_seconds", info)
        input_arg = info["command"][info["command"].index("-f") + 1]
        self.assertEqual(input_arg, "<temporary-input-file>")

    def test_nonzero_exit(self):
        binary, model = self._files()
        with mock.patch(
            "holo_benchmark.bitnet_runner.subprocess.run",
            return_value=mock.Mock(returncode=3, stdout="", stderr="bad"),
        ):
            with self.assertRaises(RuntimeError):
                bitnet_embed_texts(
                    ["x"],
                    profile_id="bitnet_06b_current",
                    gguf_path=model,
                    bitnet_bin=binary,
                    bitnet_commit="abc",
                    doc_indices=[0],
                    query_indices=[],
                )

    def test_timeout(self):
        binary, model = self._files()
        with mock.patch(
            "holo_benchmark.bitnet_runner.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["bin"], 1),
        ):
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                bitnet_embed_texts(
                    ["x"],
                    profile_id="bitnet_06b_current",
                    gguf_path=model,
                    bitnet_bin=binary,
                    bitnet_commit="abc",
                    doc_indices=[0],
                    query_indices=[],
                    timeout_seconds=1,
                )

    def test_missing_binary(self):
        _, model = self._files()
        with self.assertRaises(FileNotFoundError):
            bitnet_embed_texts(
                ["x"],
                profile_id="bitnet_06b_current",
                gguf_path=model,
                bitnet_bin=Path("/missing"),
                bitnet_commit="abc",
                doc_indices=[0],
                query_indices=[],
            )

    def test_index_overlap(self):
        binary, model = self._files()
        with self.assertRaises(ValueError):
            bitnet_embed_texts(
                ["a", "b"],
                profile_id="bitnet_06b_current",
                gguf_path=model,
                bitnet_bin=binary,
                bitnet_commit="abc",
                doc_indices=[0, 1],
                query_indices=[1],
            )

    def test_index_out_of_range(self):
        binary, model = self._files()
        with self.assertRaises(ValueError):
            bitnet_embed_texts(
                ["a"],
                profile_id="bitnet_06b_current",
                gguf_path=model,
                bitnet_bin=binary,
                bitnet_commit="abc",
                doc_indices=[2],
                query_indices=[],
            )

    def test_index_missing_coverage(self):
        binary, model = self._files()
        with self.assertRaises(ValueError):
            bitnet_embed_texts(
                ["a", "b"],
                profile_id="bitnet_06b_current",
                gguf_path=model,
                bitnet_bin=binary,
                bitnet_commit="abc",
                doc_indices=[0],
                query_indices=[],
            )

    def test_duplicate_index(self):
        binary, model = self._files()
        with self.assertRaises(ValueError):
            bitnet_embed_texts(
                ["a", "b"],
                profile_id="bitnet_06b_current",
                gguf_path=model,
                bitnet_bin=binary,
                bitnet_commit="abc",
                doc_indices=[0, 0],
                query_indices=[1],
            )

    def test_profile_dimension_mismatch(self):
        binary, model = self._files()
        with self.assertRaises(ValueError):
            bitnet_embed_texts(
                ["a"],
                profile_id="bitnet_270m_current",
                gguf_path=model,
                bitnet_bin=binary,
                bitnet_commit="abc",
                expected_dim=1024,
                doc_indices=[0],
                query_indices=[],
            )


class CandidateTests(unittest.TestCase):
    def _candidate(self):
        queries = [{"query_id": f"query-{i:04d}"} for i in range(1, 151)]
        rankings = [
            [f"chunk-{i:04d}-{j:03d}" for j in range(600)]
            for i in range(1, 151)
        ]
        scores = [[1.0 - j / 1000 for j in range(600)] for _ in range(150)]
        return queries, build_candidate_payload(
            profile_id="bitnet_270m_current",
            queries=queries,
            rankings=rankings,
            ranked_scores=scores,
            candidate_top_k=50,
            model_identity={"sha256": "a" * 64},
            runtime={"backend": "bitnet.cpp", "gguf_sha256": "a" * 64},
        )

    def test_candidate_schema(self):
        queries, payload = self._candidate()
        validate_candidate_payload(
            payload,
            expected_profile_id="bitnet_270m_current",
            expected_query_ids=[row["query_id"] for row in queries],
            expected_top_k=50,
        )
        self.assertEqual(payload["dataset"]["corpus_sha256"], CORPUS_SHA256)
        self.assertEqual(len(payload["queries"]), 150)
        self.assertEqual(len(payload["queries"][0]["candidates"]), 50)
        self.assertEqual(len(payload["ranking_sha256"]), 64)

    def test_candidate_duplicate_chunk_rejected(self):
        queries, payload = self._candidate()
        payload["queries"][0]["candidates"][1]["chunk_id"] = payload[
            "queries"
        ][0]["candidates"][0]["chunk_id"]
        with self.assertRaises(ValueError):
            validate_candidate_payload(
                payload,
                expected_profile_id="bitnet_270m_current",
                expected_query_ids=[row["query_id"] for row in queries],
                expected_top_k=50,
            )

    def test_real_canonical_loader(self):
        import reranker_execution

        queries, payload = self._candidate()
        with tempfile.TemporaryDirectory() as tmp:
            candidate_dir = Path(tmp)
            atomic_json(candidate_dir / "bitnet_270m_current.json", payload)
            with mock.patch.object(
                reranker_execution, "CANDIDATE_DIR", candidate_dir
            ), mock.patch.object(
                reranker_execution,
                "load_frozen_dataset",
                return_value=([], queries),
            ):
                loaded = reranker_execution.load_candidate_payloads(
                    ["bitnet_270m_current"], 50
                )
        self.assertIn("bitnet_270m_current", loaded)


if __name__ == "__main__":
    unittest.main()
