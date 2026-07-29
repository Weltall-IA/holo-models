from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from holo_benchmark import nemotron_panel_benchmark as module
from holo_benchmark.artifact_portability import assert_portable_payload


class NemotronPanelBenchmarkTests(unittest.TestCase):
    def _model_dir(
        self, root: Path, revision: str = module.MODEL_REVISION
    ) -> Path:
        model = root / "model"
        for relative in module.REQUIRED_MODEL_FILES:
            path = model / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if relative == "config.json":
                path.write_text(
                    json.dumps(
                        {
                            "auto_map": {
                                "AutoModel": "llama_bidirectional_model.Model"
                            }
                        }
                    ),
                    encoding="utf-8",
                )
            else:
                path.write_bytes(relative.encode("utf-8"))
            metadata = module.metadata_path(model, relative)
            metadata.parent.mkdir(parents=True, exist_ok=True)
            metadata.write_text(revision + "\n", encoding="utf-8")
        return model

    def test_complete_model_requires_one_revision_and_expected_weight(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = self._model_dir(Path(temporary))
            weight = model / module.MODEL_WEIGHT_FILE
            resolved, identity = module.validate_complete_model(
                model,
                expected_weight_size=weight.stat().st_size,
                expected_weight_sha256=hashlib.sha256(
                    weight.read_bytes()
                ).hexdigest(),
            )
            self.assertEqual(resolved, model.resolve())
            self.assertEqual(identity["revision"], module.MODEL_REVISION)
            self.assertEqual(len(identity["critical_snapshot_files"]), 5)

    def test_complete_model_rejects_revision_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = self._model_dir(Path(temporary))
            module.metadata_path(model, "tokenizer.json").write_text(
                "0" * 40 + "\n", encoding="utf-8"
            )
            weight = model / module.MODEL_WEIGHT_FILE
            with self.assertRaisesRegex(ValueError, "revision mismatch"):
                module.validate_complete_model(
                    model,
                    expected_weight_size=weight.stat().st_size,
                    expected_weight_sha256=hashlib.sha256(
                        weight.read_bytes()
                    ).hexdigest(),
                )

    def test_score_template_must_match_official_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "template.jinja"
            path.write_text(module.SCORE_TEMPLATE + "\n", encoding="utf-8")
            identity = module.validate_score_template(path)
            self.assertEqual(
                identity["format"], "question_passage_score_template"
            )
            path.write_text("wrong", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "official format"):
                module.validate_score_template(path)

    def test_parse_rerank_response_restores_document_order(self):
        payload = {
            "results": [
                {"index": 2, "relevance_score": 0.2},
                {"index": 0, "relevance_score": 0.9},
                {"index": 1, "relevance_score": -0.1},
            ]
        }
        self.assertEqual(
            module.parse_rerank_response(payload, 3), [0.9, -0.1, 0.2]
        )

    def test_parse_rerank_response_rejects_duplicate_index(self):
        payload = {
            "results": [
                {"index": 0, "relevance_score": 0.9},
                {"index": 0, "relevance_score": 0.2},
            ]
        }
        with self.assertRaisesRegex(RuntimeError, "duplicated"):
            module.parse_rerank_response(payload, 2)

    def test_semantic_smoke_requires_relevant_passage_top1(self):
        with mock.patch.object(
            module, "score_documents", return_value=([0.1, 1.5], 0.25)
        ):
            smoke = module.official_semantic_smoke("http://localhost")
        self.assertEqual(smoke["status"], "PASS")
        self.assertEqual(smoke["top_index"], 1)
        with mock.patch.object(
            module, "score_documents", return_value=([2.0, 1.0], 0.25)
        ):
            with self.assertRaisesRegex(RuntimeError, "smoke failed"):
                module.official_semantic_smoke("http://localhost")

    def test_score_panel_records_scores_and_portable_runtime(self):
        queries = [{"query": "q1"}, {"query": "q2"}]
        ids = [["a", "b"], ["b", "c"]]
        texts = {"a": "A", "b": "B", "c": "C"}
        with mock.patch.object(
            module,
            "score_documents",
            side_effect=[([0.1, 0.2], 0.1), ([0.3, 0.4], 0.2)],
        ), mock.patch.object(
            module, "gpu_memory_bytes_for_process_tree", return_value=1024
        ):
            rows, runtime = module.score_panel_profile(
                "http://localhost", 123, queries, ids, texts, 10
            )
        self.assertEqual(rows[0], {"a": 0.1, "b": 0.2})
        self.assertEqual(runtime["pairs"], 4)
        self.assertEqual(runtime["peak_vram_bytes"], 1024)
        self.assertEqual(runtime["endpoint"], "/rerank")
        assert_portable_payload({"runtime": runtime})


if __name__ == "__main__":
    unittest.main()
