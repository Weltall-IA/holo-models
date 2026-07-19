from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from holo_benchmark.gate2 import (
    Gate2ModelSpec,
    _document_text,
    _ensure_destination,
    _query_text,
    _select_dataset,
    load_gate2_specs,
    resolve_model,
)


class Gate2ConfigurationTests(unittest.TestCase):
    def test_loads_only_enabled_gate2_models(self) -> None:
        payload = {
            "models": [
                {
                    "id": "a",
                    "repo": "org/a",
                    "backend": "sentence-transformers",
                    "dimension": 768,
                    "gate": 2,
                    "enabled": True,
                },
                {
                    "id": "b",
                    "repo": "org/b",
                    "backend": "llama.cpp",
                    "dimension": 768,
                    "gate": 3,
                    "enabled": True,
                },
                {
                    "id": "c",
                    "repo": "org/c",
                    "backend": "sentence-transformers",
                    "dimension": 768,
                    "gate": 2,
                    "enabled": False,
                },
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "models.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            specs = load_gate2_specs(path)
        self.assertEqual([spec.id for spec in specs], ["a"])

    def test_unknown_selection_is_rejected(self) -> None:
        payload = {
            "models": [
                {
                    "id": "a",
                    "repo": "org/a",
                    "backend": "sentence-transformers",
                    "dimension": 768,
                    "gate": 2,
                    "enabled": True,
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "models.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_gate2_specs(path, ["missing"])

    def test_destination_cannot_escape_embed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.assertEqual(
                _ensure_destination(repo, "model-a"),
                (repo / "embed" / "model-a").resolve(),
            )
            with self.assertRaises(ValueError):
                _ensure_destination(repo, "../escape")

    def test_resolves_revision_size_license_and_gate(self) -> None:
        spec = Gate2ModelSpec(
            id="a",
            repo="org/a",
            backend="sentence-transformers",
            dimension=768,
        )
        api = SimpleNamespace(
            model_info=lambda *args, **kwargs: SimpleNamespace(
                sha="abcdef1234567890",
                siblings=[
                    SimpleNamespace(size=10),
                    SimpleNamespace(size=20),
                    SimpleNamespace(size=None),
                ],
                card_data={"license": "apache-2.0"},
                gated=False,
            )
        )
        resolved = resolve_model(spec, Path("/tmp/embed/a"), api=api)
        self.assertEqual(resolved.revision, "abcdef1234567890")
        self.assertEqual(resolved.expected_size_bytes, 30)
        self.assertEqual(resolved.license, "apache-2.0")
        self.assertFalse(resolved.gated)

    def test_model_specific_text_formatting(self) -> None:
        prompts = {
            "embeddinggemma_document": "title: {title_or_none} | text: {text}",
            "qwen3_query_instruction": "Retrieve Portuguese scenes.",
        }
        chunk = {"title": "Obra", "text": "Cena"}
        query = {"query": "Onde ocorreu?"}
        self.assertEqual(
            _document_text(chunk, "embeddinggemma", prompts),
            "title: Obra | text: Cena",
        )
        self.assertEqual(
            _query_text(query, "qwen3_embedding_06", prompts),
            "Instruct: Retrieve Portuguese scenes.\nQuery: Onde ocorreu?",
        )

    def test_dataset_slice_keeps_only_evaluable_queries(self) -> None:
        chunks = [{"chunk_id": "c1"}, {"chunk_id": "c2"}, {"chunk_id": "c3"}]
        queries = [
            {"query_id": "q1", "relevant_chunk_ids": ["c1"]},
            {"query_id": "q2", "relevant_chunk_ids": ["c3"]},
        ]
        selected_chunks, selected_queries, full = _select_dataset(
            chunks,
            queries,
            max_documents=2,
            max_queries=None,
        )
        self.assertEqual(
            [row["chunk_id"] for row in selected_chunks],
            ["c1", "c2"],
        )
        self.assertEqual(
            [row["query_id"] for row in selected_queries],
            ["q1"],
        )
        self.assertFalse(full)


if __name__ == "__main__":
    unittest.main()
