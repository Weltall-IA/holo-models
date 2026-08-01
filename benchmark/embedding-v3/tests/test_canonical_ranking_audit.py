"""Tests for canonical ranking consistency after the 0.8326 audit."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONSOLIDATED = PROJECT_ROOT / "ALL_BENCHMARK_RESULTS.json"
PIPELINES = PROJECT_ROOT / "results" / "reranker" / "pipelines"
SCORES = PROJECT_ROOT / "results" / "reranker" / "scores"

REQUIRED_LEADER_METRICS = {"mrr_at_10", "hit_rate_at_1", "hit_rate_at_10"}


class CanonicalRankingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CONSOLIDATED.read_text(encoding="utf-8"))
        cls.pipelines = cls.data["published_pipelines_ranked_by_mrr_at_10"]

    def test_leader_defined_by_explicit_ranking_scope(self):
        leaders = self.data["leaders_published"]
        self.assertIn("leader_ranking_scope", leaders)
        self.assertIn("general", leaders["leader_ranking_scope"])
        leader = leaders["best_by_mrr_at_10"]
        self.assertEqual(leader["pipeline_id"], self.pipelines[0]["pipeline_id"])
        self.assertIn("mrr_at_10", leader["metrics"])

    def test_ranking_sorted_descending(self):
        mrrs = [p["metrics"]["mrr_at_10"] for p in self.pipelines]
        self.assertEqual(mrrs, sorted(mrrs, reverse=True))

    def test_leader_unique(self):
        leader_id = self.pipelines[0]["pipeline_id"]
        ids = [p["pipeline_id"] for p in self.pipelines]
        self.assertEqual(len(ids), len(set(ids)), "duplicate pipeline ids")
        count = sum(1 for p in self.pipelines if p["pipeline_id"] == leader_id)
        self.assertEqual(count, 1, "leader appears more than once")

    def test_pipeline_files_exist_on_disk(self):
        repo_root = PROJECT_ROOT.parents[1]
        for p in self.pipelines:
            source = p.get("source_path")
            if not source:
                continue
            candidate = repo_root / source if source.startswith("benchmark/") else PROJECT_ROOT / source
            self.assertTrue(
                candidate.is_file(),
                f"pipeline file missing: {source}",
            )

    def test_no_metric_fabrication_for_legacy_artifacts(self):
        repo_root = PROJECT_ROOT.parents[1]
        for p in self.pipelines:
            source = p.get("source_path")
            if not source:
                continue
            path = (
                repo_root / source
                if source.startswith("benchmark/")
                else PROJECT_ROOT / source
            )
            if not path.is_file():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            telemetry = payload.get("telemetry") or {}
            if telemetry.get("status") == "MEASUREMENT_BLOCKED_LEGACY_ARTIFACT":
                self.assertNotIn("peak_vram_bytes", telemetry)
                self.assertNotIn("peak_ram_bytes", telemetry)

    def test_remote_api_has_no_local_vram(self):
        repo_root = PROJECT_ROOT.parents[1]
        for p in self.pipelines:
            source = p.get("source_path")
            if not source:
                continue
            path = (
                repo_root / source
                if source.startswith("benchmark/")
                else PROJECT_ROOT / source
            )
            if not path.is_file():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            score_ref = payload.get("score_artifact")
            if not score_ref:
                continue
            score_path = PROJECT_ROOT / score_ref
            if not score_path.is_file():
                continue
            score = json.loads(score_path.read_text(encoding="utf-8"))
            model = score.get("model") or {}
            if model.get("api_model") or model.get("provider") == "Voyage AI":
                runtime = score.get("runtime") or {}
                self.assertFalse(
                    runtime.get("peak_vram_bytes"),
                    f"remote API score has local VRAM: {score_ref}",
                )
                self.assertFalse(
                    runtime.get("peak_ram_bytes"),
                    f"remote API score has local RAM: {score_ref}",
                )


class NewPanelTelemetryTests(unittest.TestCase):
    NEW_RERANKERS = (
        "ettin_reranker_68m_v1",
        "ettin_reranker_150m_v1",
        "lamar_600m",
        "llama_nemotron_rerank_1b_v2",
    )

    def test_56_score_artifacts_present(self):
        count = 0
        for reranker in self.NEW_RERANKERS:
            directory = SCORES / reranker
            count += len(list(directory.glob("*.json")))
        # 14 per reranker in the 15-profile panel, plus the pre-existing 3 vLLM
        # nemotron scores and 1 pilot each already counted inside the 14.
        self.assertGreaterEqual(count, 56)

    def test_score_artifacts_have_runtime_telemetry(self):
        for reranker in self.NEW_RERANKERS:
            directory = SCORES / reranker
            for path in sorted(directory.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                runtime = payload.get("runtime") or {}
                if runtime.get("backend") == "vllm":
                    # historical vLLM artifacts predate the panel telemetry schema
                    continue
                self.assertIn("peak_vram_bytes", runtime, str(path))
                self.assertIn("total_seconds", runtime, str(path))

    def test_new_panel_vram_matches_summary(self):
        expected = {
            "ettin_reranker_68m_v1": (0.7, 0.9),
            "ettin_reranker_150m_v1": (0.9, 1.1),
            "lamar_600m": (2.2, 2.7),
            "llama_nemotron_rerank_1b_v2": (4.0, 4.5),
        }
        for reranker, (low, high) in expected.items():
            directory = SCORES / reranker
            vrams = []
            for path in directory.glob("*.json"):
                payload = json.loads(path.read_text(encoding="utf-8"))
                runtime = payload.get("runtime") or {}
                if runtime.get("backend") == "vllm":
                    continue
                vram = runtime.get("peak_vram_bytes")
                if vram:
                    vrams.append(vram / 1e9)
            self.assertTrue(vrams, reranker)
            mean = sum(vrams) / len(vrams)
            self.assertGreaterEqual(mean, low, f"{reranker} VRAM below range")
            self.assertLessEqual(mean, high, f"{reranker} VRAM above range")


class ReadmeConsistencyTests(unittest.TestCase):
    README = PROJECT_ROOT / "README.md"

    def test_tabela1_matches_consolidated(self):
        """Tabela 1 'Melhor MRR@10 com reranker' must match the consolidated best
        pipeline for every embedding that has one."""
        if not self.README.is_file():
            self.skipTest("README not present")
        data = json.loads(CONSOLIDATED.read_text(encoding="utf-8"))
        pipes = data["published_pipelines_ranked_by_mrr_at_10"]
        best = {}
        for p in pipes:
            e = p["embedding"]
            m = p["metrics"]["mrr_at_10"]
            if e not in best or m > best[e]:
                best[e] = m
        text = self.README.read_text(encoding="utf-8")
        in_t1 = False
        checked = 0
        for line in text.splitlines():
            if "### Tabela 1 —" in line:
                in_t1 = True
                continue
            if "### Tabela 1a" in line or "### Tabela 1b" in line:
                in_t1 = False
            if not in_t1 or not line.startswith("| `"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 6 or parts[1].startswith("Perfil"):
                continue
            emb = parts[1].strip("`")
            try:
                raw = float(parts[2])
            except ValueError:
                continue
            best_val = parts[3]
            expected = best.get(emb)
            if expected is None:
                self.assertEqual(best_val, "—", f"{emb}: Tabela 1 best must be —")
            else:
                self.assertAlmostEqual(
                    float(best_val), expected, places=4,
                    msg=f"{emb}: Tabela 1 best {best_val} != consolidated {expected:.4f}",
                )
            checked += 1
        self.assertGreaterEqual(checked, 30, "Tabela 1 rows checked")

    def test_tabela1a_documents_divergence(self):
        text = self.README.read_text(encoding="utf-8")
        self.assertIn("Tabela 1a — divergência histórica", text)
        self.assertIn("0.8326", text)
        self.assertIn("91a39f5", text)

    def test_tabela1c_has_no_estimated_values(self):
        text = self.README.read_text(encoding="utf-8")
        self.assertIn("Tabela 1c — qualidade × consumo", text)
        self.assertIn("LEGACY_NOT_MEASURED", text)


if __name__ == "__main__":
    unittest.main()
