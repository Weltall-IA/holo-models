from __future__ import annotations

import unittest

from holo_benchmark.coverage_validation import apply_validation, validate_inventory_payload


class CoverageValidationTests(unittest.TestCase):
    def test_rejects_missing_runner_as_not_applicable(self):
        payload = {
            "coverage_complete": True,
            "models": [{
                "id": "model.gguf",
                "category": "text_llm",
                "status": "NOT_APPLICABLE",
                "reason": "GGUF sem runner local",
            }],
        }
        codes = {item.code for item in validate_inventory_payload(payload)}
        self.assertIn("RUNNABLE_MARKED_NOT_APPLICABLE", codes)
        self.assertIn("MISSING_RUNNER_IS_NOT_NOT_APPLICABLE", codes)
        self.assertIn("FALSE_COMPLETE", codes)

    def test_requires_healthcheck_evidence(self):
        payload = {
            "models": [{
                "id": "chat",
                "category": "text_llm",
                "status": "HEALTHCHECK_PASSED",
            }],
        }
        codes = {item.code for item in validate_inventory_payload(payload)}
        self.assertIn("HEALTHCHECK_WITHOUT_EVIDENCE", codes)

    def test_requires_block_evidence(self):
        payload = {
            "models": [{
                "id": "broken",
                "category": "embedding",
                "status": "BLOCKED",
                "reason": "falhou",
            }],
        }
        codes = {item.code for item in validate_inventory_payload(payload)}
        self.assertIn("BLOCK_WITHOUT_EVIDENCE", codes)

    def test_verified_alias_can_be_benchmarked(self):
        payload = {
            "models": [{
                "id": "alias",
                "category": "embedding",
                "status": "BENCHMARKED",
                "evidence": {
                    "alias_of": "canonical",
                    "identity_verified": True,
                    "identity_method": "sha256",
                },
            }],
        }
        self.assertEqual(validate_inventory_payload(payload), [])

    def test_complete_payload_passes(self):
        payload = {
            "coverage_complete": True,
            "models": [{
                "id": "chat",
                "category": "text_llm",
                "status": "HEALTHCHECK_PASSED",
                "evidence": {
                    "artifact": "results/chat.json",
                    "runtime": "ollama",
                    "endpoint": "/api/generate",
                    "result": {"response": "OK"},
                },
            }],
        }
        self.assertEqual(validate_inventory_payload(payload), [])
        self.assertTrue(apply_validation(payload)["coverage_complete"])


if __name__ == "__main__":
    unittest.main()
