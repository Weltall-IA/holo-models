from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from holo_benchmark.gate2 import (
    Gate2ModelSpec,
    ResolvedModel,
    _document_text,
    _ensure_destination,
    _query_text,
    _run_model_worker,
    _select_dataset,
    _status_for_results,
    load_gate2_specs,
    resolve_model,
)


class Gate2ConfigurationTests(unittest.TestCase):
    def test_loads_only_enabled_gate2_models(self) -> None:
        payload = {
            "models": [
                {"id": "a", "repo": "org/a", "backend": "sentence-transformers", "dimension": 768, "gate": 2, "enabled": True},
                {"id": "b", "repo": "org/b", "backend": "llama.cpp", "dimension": 768, "file": "b.gguf", "gate": 3, "enabled": True},
                {"id": "c", "repo": "org/c", "backend": "sentence-transformers", "dimension": 768, "gate": 2, "enabled": False},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "models.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            specs = load_gate2_specs(path)
        self.assertEqual([spec.id for spec in specs], ["a"])

    def test_loads_llama_cpp_optional_model_without_fixed_dimension(self) -> None:
        payload = {
            "models": [
                {
                    "id": "bitnet",
                    "repo": "microsoft/bitnet",
                    "backend": "llama.cpp",
                    "dimension": 0,
                    "file": "bitnet.gguf",
                    "required": False,
                    "gate": 2,
                    "enabled": True,
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "models.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            specs = load_gate2_specs(path)
        self.assertEqual(specs[0].backend, "llama.cpp")
        self.assertEqual(specs[0].file, "bitnet.gguf")
        self.assertFalse(specs[0].required)

    def test_unknown_selection_is_rejected(self) -> None:
        payload = {"models": [{"id": "a", "repo": "org/a", "backend": "sentence-transformers", "dimension": 768, "gate": 2, "enabled": True}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "models.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_gate2_specs(path, ["missing"])

    def test_destination_cannot_escape_embed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.assertEqual(_ensure_destination(repo, "model-a"), (repo / "embed" / "model-a").resolve())
            with self.assertRaises(ValueError):
                _ensure_destination(repo, "../escape")

    def test_resolves_revision_size_license_and_gate(self) -> None:
        spec = Gate2ModelSpec(id="a", repo="org/a", backend="sentence-transformers", dimension=768)
        api = SimpleNamespace(model_info=lambda *args, **kwargs: SimpleNamespace(sha="abcdef1234567890", siblings=[SimpleNamespace(size=10), SimpleNamespace(size=20), SimpleNamespace(size=None)], card_data={"license": "apache-2.0"}, gated=False))
        resolved = resolve_model(spec, Path("/tmp/embed/a"), api=api)
        self.assertEqual(resolved.revision, "abcdef1234567890")
        self.assertEqual(resolved.expected_size_bytes, 30)
        self.assertEqual(resolved.license, "apache-2.0")
        self.assertFalse(resolved.gated)

    def test_resolves_only_configured_gguf_file(self) -> None:
        spec = Gate2ModelSpec(id="bitnet", repo="microsoft/bitnet", backend="llama.cpp", dimension=0, file="model.gguf", required=False)
        api = SimpleNamespace(model_info=lambda *args, **kwargs: SimpleNamespace(sha="abcdef1234567890", siblings=[SimpleNamespace(rfilename="model.gguf", size=100), SimpleNamespace(rfilename="other.gguf", size=200)], card_data={"license": "mit"}, gated=False))
        resolved = resolve_model(spec, Path("/tmp/embed/bitnet"), api=api)
        self.assertEqual(resolved.expected_size_bytes, 100)
        self.assertEqual(resolved.file, "model.gguf")

    def test_model_specific_text_formatting(self) -> None:
        prompts = {
            "embeddinggemma_document": "title: {title_or_none} | text: {text}",
            "embeddinggemma_query": "task: search result | query: {query}",
            "qwen3_query_instruction": "Retrieve Portuguese scenes.",
            "e5_query_instruction": "Busque cenas em português brasileiro.",
        }
        chunk = {"title": "Obra", "text": "Cena"}
        query = {"query": "Onde ocorreu?"}
        self.assertEqual(_document_text(chunk, "embeddinggemma", prompts), "title: Obra | text: Cena")
        self.assertEqual(_document_text(chunk, "colibri_ptbr", prompts, "colibri"), "title: Obra | text: Cena")
        self.assertEqual(_query_text(query, "qwen3_embedding_06", prompts, "qwen3"), "Instruct: Retrieve Portuguese scenes.\nQuery: Onde ocorreu?")
        self.assertEqual(_query_text(query, "multilingual_e5_large_instruct", prompts, "e5_instruct"), "Instruct: Busque cenas em português brasileiro.\nQuery: Onde ocorreu?")

    def test_dataset_slice_keeps_only_evaluable_queries(self) -> None:
        chunks = [{"chunk_id": "c1"}, {"chunk_id": "c2"}, {"chunk_id": "c3"}]
        queries = [{"query_id": "q1", "relevant_chunk_ids": ["c1"]}, {"query_id": "q2", "relevant_chunk_ids": ["c3"]}]
        selected_chunks, selected_queries, full = _select_dataset(chunks, queries, max_documents=2, max_queries=None)
        self.assertEqual([row["chunk_id"] for row in selected_chunks], ["c1", "c2"])
        self.assertEqual([row["query_id"] for row in selected_queries], ["q1"])
        self.assertFalse(full)

    def test_optional_failure_does_not_block_required_pass(self) -> None:
        specs = [
            Gate2ModelSpec("required", "org/required", "sentence-transformers", 768, required=True),
            Gate2ModelSpec("optional", "org/optional", "llama.cpp", 0, required=False, file="o.gguf"),
        ]
        results = [{"model": {"id": "required"}}]
        failures = [{"model_id": "optional", "required": False}]
        self.assertEqual(_status_for_results(specs, results, failures, True, True), "PASS")

    def test_required_failure_blocks_completion(self) -> None:
        specs = [Gate2ModelSpec("required", "org/required", "sentence-transformers", 768, required=True)]
        failures = [{"model_id": "required", "required": True}]
        self.assertEqual(_status_for_results(specs, [], failures, True, True), "BLOCKED")

    def test_worker_error_payload_is_preserved_on_exit_code_two(self) -> None:
        spec = Gate2ModelSpec(
            "optional",
            "org/optional",
            "sentence-transformers",
            768,
            required=False,
        )
        resolved = ResolvedModel(
            id=spec.id,
            repo=spec.repo,
            revision="abcdef1234567890",
            expected_size_bytes=1,
            license="apache-2.0",
            gated=False,
            destination="/tmp/embed/optional",
            trust_remote_code=False,
            backend=spec.backend,
            dimension=spec.dimension,
            required=False,
        )

        def fake_run(argv: list[str], **kwargs: object) -> SimpleNamespace:
            output = Path(argv[argv.index("--output") + 1])
            output.write_text(
                json.dumps(
                    {
                        "status": "error",
                        "error": {
                            "type": "ActualModelError",
                            "message": "causa real",
                            "traceback": "trace real",
                        },
                    }
                ),
                encoding="utf-8",
            )
            return SimpleNamespace(returncode=2, stderr="warning irrelevante")

        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "holo_benchmark.gate2.subprocess.run",
            side_effect=fake_run,
        ):
            root = Path(tmp)
            result, failure = _run_model_worker(
                project_root=root,
                repo_root=root,
                resolved=resolved,
                spec=spec,
                model_path=root / "model",
                chunks=[],
                queries=[],
                prompts={},
                device="cuda",
                batch_size=1,
                corpus_hash="hash",
                timeout_seconds=30,
            )

        self.assertIsNone(result)
        self.assertIsNotNone(failure)
        assert failure is not None
        self.assertEqual(failure["error_type"], "ActualModelError")
        self.assertEqual(failure["error_message"], "causa real")
        self.assertEqual(failure["returncode"], 2)
        self.assertIn("trace real", failure["stderr_tail"])


if __name__ == "__main__":
    unittest.main()
