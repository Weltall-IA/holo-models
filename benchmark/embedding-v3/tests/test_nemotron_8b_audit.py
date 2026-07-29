from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from holo_benchmark import nemotron_8b_audit as module
from holo_benchmark.artifact_portability import assert_portable_payload


class Nemotron8BAuditTests(unittest.TestCase):
    def _model_file(self, root: Path, owner: str, content: bytes) -> Path:
        path = root / owner / "Nemotron-3-Embed-8B-Q4_K_M.gguf"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_model_identity_requires_exact_owner_revision_bytes_and_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self._model_file(Path(temporary), "Abiray", b"abiray-weight")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            identity = module.ModelIdentity(
                model_id="nemotron_8b_abiray_q4_audit",
                repo="Abiray/Nemotron-3-Embed-8B-GGUF",
                revision="a" * 40,
                model_file=path,
                expected_bytes=path.stat().st_size,
                expected_sha256=digest,
            ).validate()
        self.assertEqual(identity["repository"], "Abiray/Nemotron-3-Embed-8B-GGUF")
        self.assertEqual(identity["sha256"], digest)
        self.assertEqual(identity["quantization"], "Q4_K_M")

    def test_model_identity_rejects_wrong_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = self._model_file(Path(temporary), "wrong", b"weight")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            identity = module.ModelIdentity(
                model_id="nemotron_8b_aqua00_q4_audit",
                repo="Abiray/Nemotron-3-Embed-8B-GGUF",
                revision="b" * 40,
                model_file=path,
                expected_bytes=path.stat().st_size,
                expected_sha256=digest,
            )
            with self.assertRaisesRegex(ValueError, "owner mismatch"):
                identity.validate()

    def test_distinct_models_reject_same_weight_hash(self):
        common = {
            "revision": "c" * 40,
            "file": "Nemotron-3-Embed-8B-Q4_K_M.gguf",
            "sha256": "d" * 64,
        }
        identities = [
            {
                **common,
                "id": "nemotron_8b_abiray_q4_audit",
                "repository": "Abiray/Nemotron-3-Embed-8B-GGUF",
            },
            {
                **common,
                "id": "nemotron_8b_aqua00_q4_audit",
                "repository": "Aqua00/Nemotron-3-Embed-8B-GGUF",
            },
        ]
        with self.assertRaisesRegex(ValueError, "same weight SHA-256"):
            module.ensure_distinct_models(identities)

    def test_build_embedding_outputs_creates_4096_and_1024_candidates(self):
        rng = np.random.default_rng(42)
        chunks = [
            {"chunk_id": f"chunk-{index:04d}", "text": f"document {index}"}
            for index in range(50)
        ]
        queries = [
            {
                "query_id": "query-0001",
                "query": "first",
                "query_type": "semantic_event",
                "difficulty": "medium",
                "relevant_chunk_ids": ["chunk-0000"],
                "hard_negative_chunk_ids": ["chunk-0001"],
            },
            {
                "query_id": "query-0002",
                "query": "second",
                "query_type": "semantic_event",
                "difficulty": "medium",
                "relevant_chunk_ids": ["chunk-0002"],
                "hard_negative_chunk_ids": ["chunk-0003"],
            },
        ]
        documents = rng.normal(size=(50, 4096)).astype(np.float32)
        query_rows = rng.normal(size=(2, 4096)).astype(np.float32)
        identity = {
            "id": "nemotron_8b_abiray_q4_audit",
            "repository": "Abiray/Nemotron-3-Embed-8B-GGUF",
            "revision": "a" * 40,
            "file": "Nemotron-3-Embed-8B-Q4_K_M.gguf",
            "bytes": 123,
            "sha256": "1" * 64,
            "quantization": "Q4_K_M",
            "pooling": "mean",
            "native_dimension": 4096,
        }
        outputs = module.build_embedding_outputs(
            identity,
            documents,
            query_rows,
            {
                "backend": "llama.cpp",
                "command": [
                    "/home/operator/llama-server",
                    "-m",
                    "/home/operator/model.gguf",
                ],
            },
            chunks,
            queries,
        )
        self.assertEqual(
            set(outputs),
            {
                "nemotron_8b_abiray_q4_audit_4096",
                "nemotron_8b_abiray_q4_audit_1024",
            },
        )
        for raw, candidate in outputs.values():
            self.assertEqual(len(candidate["queries"]), 2)
            self.assertEqual(len(candidate["queries"][0]["candidates"]), 50)
            assert_portable_payload(raw)
            assert_portable_payload(candidate)

    def test_pipeline_writer_scores_only_rerank_top_k(self):
        candidates = [
            {"chunk_id": f"chunk-{index:02d}", "score": 1.0 - index / 100, "rank": index + 1}
            for index in range(50)
        ]
        payloads = {"audit": {"queries": [{"query_id": "query-1", "candidates": candidates}]}}
        queries = [
            {
                "query_id": "query-1",
                "query_type": "semantic_event",
                "relevant_chunk_ids": ["chunk-19"],
                "hard_negative_chunk_ids": [],
            }
        ]
        score_rows = [
            {f"chunk-{index:02d}": float(index) for index in range(module.RERANK_TOP_K)}
        ]
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            module, "AUDIT_VARIANTS", ("audit",)
        ), mock.patch.object(
            module, "PIPELINE_DIR", Path(temporary)
        ), mock.patch.object(
            module, "atomic_json"
        ) as write:
            result = module._write_pipelines(
                "qwen_local",
                module.PROJECT_ROOT / "results" / "reranker" / "scores" / "audit.json",
                payloads,
                queries,
                score_rows,
                module.RERANK_TOP_K,
            )
        self.assertEqual(len(result), 1)
        self.assertEqual(write.call_count, 1)

    def test_voyage_requires_explicit_no_charge_preflight(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "billing preflight"):
                module.run_voyage(
                    Path("/missing/key"),
                    resume=False,
                    rerank_top_k=module.RERANK_TOP_K,
                    instruction=module.DEFAULT_RERANK_INSTRUCTION,
                    request_interval_seconds=1.0,
                    confirm_no_charge=False,
                )


if __name__ == "__main__":
    unittest.main()
