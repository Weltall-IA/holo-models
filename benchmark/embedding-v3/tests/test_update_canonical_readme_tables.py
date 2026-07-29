from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "update_canonical_readme_tables.py"
)
SPEC = importlib.util.spec_from_file_location("canonical_readme_updater", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class CanonicalReadmeTableTests(unittest.TestCase):
    def canonical(self):
        profiles = {
            profile
            for profile, *_ in module.TABLE1_SPECS
        } | {
            profile
            for profile, *_ in module.TABLE2_SPECS
        }
        raw = {
            profile: {
                "profile_id": profile,
                "metrics": {"mrr_at_10": 0.5},
            }
            for profile in profiles
        }
        return {
            "raw_embedding_profiles_by_id": raw,
            "embedding_index": [
                {
                    "embedding": "nemotron_3_embed_1b_nvfp4",
                    "best_published_pipeline": {
                        "pipeline_id": "nemotron__reranker",
                        "metrics": {"mrr_at_10": 0.9},
                    },
                }
            ],
        }

    def readme(self) -> str:
        return """# Header

Unrelated text before.

Revisão desta classificação: **2026-07-27**.

### Tabela 1 — embeddings bons ou reutilizáveis

Description one.

| Perfil | MRR@10 sozinho | Melhor MRR@10 com reranker | Faixa | Confiança | Decisão |
|---|---:|---:|---|---|---|
| `old` | 0.0000 | — | C | baixa | old |

### Tabela 2 — blacklist de artefatos e configurações

Description two.

| Perfil local | MRR@10 | Estado | Motivo | Condição para reabilitação |
|---|---:|---|---|---|
| `old` | — | `BLOCKED` | old | old |

### After

Unrelated text after.
"""

    def test_updates_only_revision_and_two_tables(self):
        original = self.readme()
        updated = module.update_readme(
            original,
            self.canonical(),
            "2026-07-29",
        )
        self.assertIn("Revisão desta classificação: **2026-07-29**.", updated)
        self.assertIn(
            "| `nemotron_3_embed_1b_nvfp4` | 0.5000 | 0.9000 |",
            updated,
        )
        self.assertIn("| `bitnet_270m_current` | 0.5000 | `GATE_FAIL` |", updated)
        self.assertIn("Unrelated text before.", updated)
        self.assertIn("Unrelated text after.", updated)
        self.assertNotIn("| `old` |", updated)
        self.assertEqual(updated.count(module.TABLE1_HEADING), 1)
        self.assertEqual(updated.count(module.TABLE2_HEADING), 1)

    def test_missing_profile_is_rejected(self):
        canonical = self.canonical()
        del canonical["raw_embedding_profiles_by_id"][
            "lfm_25_embedding_350m_q4_k_m_official"
        ]
        with self.assertRaisesRegex(ValueError, "raw profile is missing"):
            module.table1(canonical)

    def test_best_pipeline_is_optional(self):
        canonical = self.canonical()
        canonical["embedding_index"] = []
        rendered = module.table1(canonical)
        self.assertIn(
            "| `nemotron_3_embed_1b_nvfp4` | 0.5000 | — |",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
