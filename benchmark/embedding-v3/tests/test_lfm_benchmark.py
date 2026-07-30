from __future__ import annotations

import argparse
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from holo_benchmark import lfm_benchmark


def _unit_vectors(count: int, dim: int) -> np.ndarray:
    matrix = np.zeros((count, dim), dtype=np.float32)
    for index in range(count):
        matrix[index, index % dim] = 1.0
        if index >= dim:
            matrix[index, (index + 1) % dim] = 0.5
            matrix[index] /= np.linalg.norm(matrix[index])
    return matrix


class LfmRunnerTests(unittest.TestCase):
    def _files(self) -> tuple[Path, Path]:
        server = tempfile.NamedTemporaryFile(delete=False)
        server.write(b"server")
        server.close()
        os.chmod(server.name, 0o755)

        model = tempfile.NamedTemporaryFile(delete=False, suffix=".gguf")
        model.write(b"model")
        model.truncate(lfm_benchmark.EXPECTED_GGUF_BYTES)
        model.close()

        self.addCleanup(lambda: os.path.exists(server.name) and os.unlink(server.name))
        self.addCleanup(lambda: os.path.exists(model.name) and os.unlink(model.name))
        return Path(server.name), Path(model.name)

    def test_prefixes_are_asymmetric_and_single_line(self):
        queries, documents = lfm_benchmark._prefixed_inputs(
            ["hello\nworld"], ["doc\r\nline"]
        )
        self.assertEqual(queries, ["query: hello world"])
        self.assertEqual(documents, ["document: doc line"])

    def test_prefixes_reject_nul(self):
        with self.assertRaises(ValueError):
            lfm_benchmark._prefixed_inputs(["bad\x00query"], ["document"])

    def test_duplicate_vectors_for_distinct_inputs_rejected(self):
        matrix = np.asarray([[1.0, 0.0], [1.0, 0.0]], dtype=np.float32)
        with self.assertRaises(ValueError):
            lfm_benchmark._reject_unexpected_duplicates(
                matrix, ["first", "second"], "encoder"
            )

    def test_duplicate_vectors_for_identical_inputs_allowed(self):
        matrix = np.asarray([[1.0, 0.0], [1.0, 0.0]], dtype=np.float32)
        lfm_benchmark._reject_unexpected_duplicates(
            matrix, ["same", "same"], "encoder"
        )

    def test_runner_uses_cuda_cls_and_sanitized_command(self):
        server, model = self._files()
        documents = _unit_vectors(2, lfm_benchmark.DIMENSION)
        queries = _unit_vectors(1, lfm_benchmark.DIMENSION)
        captured: list[list[str]] = []

        class FakeProcess:
            pid = 4321
            returncode = -15

            def poll(self):
                return None

            def terminate(self):
                return None

            def wait(self, timeout=None):
                return self.returncode

            def kill(self):
                return None

        class FakeSampler:
            peak_mib = 256

            def __init__(self, pid):
                self.pid = pid

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        def fake_encode(port, texts, batch_size):
            captured.append(list(texts))
            return documents if len(captured) == 1 else queries

        with mock.patch.object(
            lfm_benchmark,
            "_sha256",
            side_effect=[
                lfm_benchmark.EXPECTED_GGUF_SHA256,
                "b" * 64,
            ],
        ), mock.patch.object(
            lfm_benchmark, "_free_port", return_value=12345
        ), mock.patch.object(
            lfm_benchmark.subprocess, "Popen", return_value=FakeProcess()
        ) as popen_mock, mock.patch.object(
            lfm_benchmark, "_VramSampler", FakeSampler
        ), mock.patch.object(
            lfm_benchmark, "_wait_server"
        ), mock.patch.object(
            lfm_benchmark, "_encode", side_effect=fake_encode
        ), mock.patch.object(
            lfm_benchmark, "_server_version", return_value="llama.cpp test"
        ), mock.patch.object(
            lfm_benchmark, "_child_peak_ram_bytes", return_value=1024
        ):
            query_matrix, document_matrix, runtime = (
                lfm_benchmark.lfm_embed_queries_and_docs(
                    ["query"],
                    ["doc one", "doc two"],
                    gguf_path=model,
                    llama_server=server,
                )
            )

        self.assertEqual(query_matrix.shape, (1, lfm_benchmark.DIMENSION))
        self.assertEqual(document_matrix.shape, (2, lfm_benchmark.DIMENSION))
        self.assertEqual(captured[0], ["document: doc one", "document: doc two"])
        self.assertEqual(captured[1], ["query: query"])
        actual_command = popen_mock.call_args.args[0]
        self.assertIn("--pooling", actual_command)
        self.assertEqual(actual_command[actual_command.index("--pooling") + 1], "cls")
        self.assertGreater(runtime["peak_vram_bytes"], 0)
        self.assertNotIn(str(server), json.dumps(runtime["command"]))
        self.assertNotIn(str(model), json.dumps(runtime["command"]))
        self.assertEqual(runtime["benchmark_exit_code"], 0)

    def test_runner_rejects_missing_cuda_evidence(self):
        server, model = self._files()
        vector = _unit_vectors(1, lfm_benchmark.DIMENSION)

        class FakeProcess:
            pid = 1
            returncode = -15

            def poll(self):
                return None

            def terminate(self):
                return None

            def wait(self, timeout=None):
                return self.returncode

            def kill(self):
                return None

        class FakeSampler:
            peak_mib = None

            def __init__(self, pid):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        with mock.patch.object(
            lfm_benchmark,
            "_sha256",
            return_value=lfm_benchmark.EXPECTED_GGUF_SHA256,
        ), mock.patch.object(
            lfm_benchmark, "_free_port", return_value=12345
        ), mock.patch.object(
            lfm_benchmark.subprocess, "Popen", return_value=FakeProcess()
        ), mock.patch.object(
            lfm_benchmark, "_VramSampler", FakeSampler
        ), mock.patch.object(
            lfm_benchmark, "_wait_server"
        ), mock.patch.object(
            lfm_benchmark, "_encode", return_value=vector
        ):
            with self.assertRaisesRegex(RuntimeError, "CUDA offload"):
                lfm_benchmark.lfm_embed_queries_and_docs(
                    ["query"],
                    ["document"],
                    gguf_path=model,
                    llama_server=server,
                )


class LfmBenchmarkTests(unittest.TestCase):
    def _args(self, root: Path) -> argparse.Namespace:
        gguf = root / "model.gguf"
        with gguf.open("wb") as handle:
            handle.write(b"model")
            handle.truncate(lfm_benchmark.EXPECTED_GGUF_BYTES)
        server = root / "llama-server"
        server.write_bytes(b"server")
        server.chmod(0o755)
        return argparse.Namespace(
            gguf_path=gguf,
            llama_server=server,
            candidate_top_k=50,
            batch_size=16,
            timeout_seconds=21600,
            context_size=2048,
            server_batch_size=512,
            server_ubatch_size=512,
            gpu_layers=99,
            hardware_json=None,
            result_output=root / "result.json",
            candidate_output=root / "candidate.json",
            validate_canonical_loader=False,
        )

    def _dataset(self):
        chunks = [
            {"chunk_id": f"chunk-{index:04d}", "text": f"document {index}"}
            for index in range(600)
        ]
        queries = [
            {"query_id": f"query-{index:04d}", "query": f"query {index}"}
            for index in range(150)
        ]
        return chunks, queries

    def test_pass_writes_complete_result_and_candidate(self):
        chunks, queries = self._dataset()
        document_embeddings = _unit_vectors(600, 32)
        query_embeddings = document_embeddings[:150].copy()
        metrics = {
            "summary": {
                "HitRate@50": 0.95,
                "queries_without_relevant": 0,
            },
            "by_query_type": {"semantic_event": {"count": 150}},
            "per_query": [{"query_id": row["query_id"]} for row in queries],
        }
        runtime = {
            "backend": "llama.cpp",
            "backend_version": "test",
            "binary_sha256": "b" * 64,
            "gguf_sha256": lfm_benchmark.EXPECTED_GGUF_SHA256,
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)
            with mock.patch.object(
                lfm_benchmark,
                "load_frozen_dataset",
                return_value=(chunks, queries),
            ), mock.patch.object(
                lfm_benchmark,
                "lfm_embed_queries_and_docs",
                return_value=(query_embeddings, document_embeddings, runtime),
            ), mock.patch.object(
                lfm_benchmark, "evaluate_rankings", return_value=metrics
            ):
                output = lfm_benchmark.benchmark_profile(args)

            result = json.loads(args.result_output.read_text(encoding="utf-8"))
            candidate = json.loads(args.candidate_output.read_text(encoding="utf-8"))

        self.assertEqual(output["status"], "PASS")
        self.assertEqual(result["gate_result"], "PASS")
        self.assertEqual(result["dataset"]["documents"], 600)
        self.assertEqual(len(result["metrics"]["per_query"]), 150)
        self.assertEqual(candidate["variant"], lfm_benchmark.PROFILE_ID)
        self.assertEqual(len(candidate["queries"]), 150)
        self.assertEqual(len(candidate["queries"][0]["candidates"]), 50)
        self.assertEqual(candidate["ranking_source"]["backend"], "llama.cpp")

    def test_fail_removes_matching_stale_candidate(self):
        chunks, queries = self._dataset()
        document_embeddings = _unit_vectors(600, 32)
        query_embeddings = document_embeddings[:150].copy()
        metrics = {
            "summary": {
                "HitRate@50": 0.80,
                "queries_without_relevant": 0,
            },
            "by_query_type": {"semantic_event": {"count": 150}},
            "per_query": [{"query_id": row["query_id"]} for row in queries],
        }
        runtime = {
            "backend": "llama.cpp",
            "backend_version": "test",
            "binary_sha256": "b" * 64,
            "gguf_sha256": lfm_benchmark.EXPECTED_GGUF_SHA256,
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self._args(root)
            args.candidate_output.write_text(
                json.dumps(
                    {
                        "variant": lfm_benchmark.PROFILE_ID,
                        "queries": [],
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(
                lfm_benchmark,
                "load_frozen_dataset",
                return_value=(chunks, queries),
            ), mock.patch.object(
                lfm_benchmark,
                "lfm_embed_queries_and_docs",
                return_value=(query_embeddings, document_embeddings, runtime),
            ), mock.patch.object(
                lfm_benchmark, "evaluate_rankings", return_value=metrics
            ):
                output = lfm_benchmark.benchmark_profile(args)

            self.assertEqual(output["status"], "FAIL")
            self.assertTrue(output["stale_candidate_removed"])
            self.assertFalse(args.candidate_output.exists())


if __name__ == "__main__":
    unittest.main()
