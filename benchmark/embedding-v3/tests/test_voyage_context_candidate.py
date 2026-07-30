from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from holo_benchmark import voyage_context_candidate


def _dataset():
    chunks = [
        {"chunk_id": f"chunk-{index:04d}", "text": f"document {index}"}
        for index in range(600)
    ]
    queries = [
        {
            "query_id": f"query-{index:04d}",
            "query": f"query {index}",
            "query_type": "semantic_event",
            "difficulty": "medium",
            "relevant_chunk_ids": [f"chunk-{index:04d}"],
            "hard_negative_chunk_ids": [],
        }
        for index in range(150)
    ]
    return chunks, queries


def _rankings():
    return [
        [f"chunk-{index:04d}"]
        + [f"chunk-{other:04d}" for other in range(600) if other != index]
        for index in range(150)
    ]


def _checkpoint(path: Path, input_type: str, item_ids: list[str], dim: int = 2):
    payload = {
        "schema_version": "1.0",
        "model": voyage_context_candidate.PROFILE_ID,
        "input_type": input_type,
        "dimension": dim,
        "rows": {
            item_id: [1.0, float((index % 7) + 1)]
            for index, item_id in enumerate(item_ids)
        },
        "usage": {"requests": 1},
        "updated_at": "2026-07-01T00:00:00+00:00",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _published(queries, rankings, dim: int = 2):
    return {
        "schema_version": "1.0",
        "model": {
            "id": voyage_context_candidate.PROFILE_ID,
            "provider": "Voyage AI",
            "backend": "voyage-api",
            "endpoint": "Client.contextualized_embed",
            "sdk_version": "0.5.0",
            "dimension": dim,
            "dtype": "float",
            "auto_chunking": False,
        },
        "dataset": {
            "corpus_version": "holo_fake_scenes_v3",
            "combined_sha256": voyage_context_candidate.CORPUS_SHA256,
            "documents": 600,
            "queries": 150,
            "works": 30,
        },
        "metrics": voyage_context_candidate.evaluate_rankings(
            queries, rankings, voyage_context_candidate.DEFAULT_KS
        ),
    }


class VoyageContextCandidateTests(unittest.TestCase):
    def test_checkpoint_matrix_rejects_nonfinite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkpoint.json"
            item_ids = ["a", "b"]
            _checkpoint(path, "document", item_ids)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["rows"]["b"][1] = float("nan")
            path.write_text(json.dumps(payload), encoding="utf-8")
            with mock.patch.object(voyage_context_candidate, "DIMENSION", 2):
                with self.assertRaisesRegex(ValueError, "non-finite"):
                    voyage_context_candidate._checkpoint_matrix(
                        path, input_type="document", expected_ids=item_ids
                    )

    def test_published_metrics_must_match_recomputed_rankings(self):
        _, queries = _dataset()
        rankings = _rankings()
        payload = _published(queries, rankings)
        payload["metrics"]["summary"]["MRR@10"] = 0.0
        with mock.patch.object(voyage_context_candidate, "DIMENSION", 2):
            with self.assertRaisesRegex(ValueError, "summary MRR@10"):
                voyage_context_candidate._validate_published_result(
                    payload, rankings, queries
                )

    def test_materialize_writes_portable_rank_only_candidate(self):
        chunks, queries = _dataset()
        rankings = _rankings()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            documents = root / "results/raw/voyage/voyage-context-4/documents.json"
            query_checkpoint = root / "results/raw/voyage/voyage-context-4/queries.json"
            published = root / "results/voyage/voyage-context-4.json"
            output = root / "results/reranker/candidates/voyage-context-4.json"
            _checkpoint(documents, "document", [row["chunk_id"] for row in chunks])
            _checkpoint(query_checkpoint, "query", [row["query_id"] for row in queries])
            published.parent.mkdir(parents=True, exist_ok=True)
            published.write_text(
                json.dumps(_published(queries, rankings)), encoding="utf-8"
            )

            with mock.patch.object(voyage_context_candidate, "DIMENSION", 2), mock.patch.object(
                voyage_context_candidate, "PROJECT_ROOT", root
            ), mock.patch.object(
                voyage_context_candidate,
                "load_frozen_dataset",
                return_value=(chunks, queries),
            ), mock.patch.object(
                voyage_context_candidate,
                "_rankings_from_embeddings",
                return_value=rankings,
            ):
                result = voyage_context_candidate.materialize_profile(
                    documents_checkpoint=documents,
                    queries_checkpoint=query_checkpoint,
                    published_result=published,
                    output=output,
                )

            candidate = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(candidate["variant"], "voyage-context-4")
        self.assertEqual(len(candidate["embedding"]["identity_sha256"]), 64)
        self.assertEqual(
            candidate["embedding"]["sha256"],
            candidate["embedding"]["identity_sha256"],
        )
        self.assertEqual(
            candidate["embedding"]["sha256_scope"],
            "model_endpoint_and_effective_checkpoint_vectors",
        )
        self.assertEqual(
            candidate["ranking_source"]["documents_checkpoint"],
            "results/raw/voyage/voyage-context-4/documents.json",
        )
        self.assertEqual(len(candidate["queries"]), 150)
        self.assertEqual(len(candidate["queries"][0]["candidates"]), 50)
        self.assertEqual(
            candidate["queries"][0]["candidates"][0],
            {"chunk_id": "chunk-0000", "rank": 1},
        )

    def test_external_checkpoint_path_redacts_parent(self):
        with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as external:
            path = Path(external) / "documents.json"
            with mock.patch.object(
                voyage_context_candidate, "PROJECT_ROOT", Path(project)
            ):
                self.assertEqual(
                    voyage_context_candidate._portable_path(path),
                    "<external>/documents.json",
                )


if __name__ == "__main__":
    unittest.main()
