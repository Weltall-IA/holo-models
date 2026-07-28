from __future__ import annotations

import os
import unittest
from unittest import mock

from holo_benchmark.artifact_portability import (
    assert_portable_payload,
    host_specific_strings,
    sanitize_host_payload,
    sanitize_host_text,
)


class ArtifactPortabilityTests(unittest.TestCase):
    def test_redacts_posix_and_windows_paths(self):
        raw = (
            "python /home/alpha/Playstoria/models/run.py "
            r"C:\Users\alpha\models\run.py"
        )
        cleaned = sanitize_host_text(raw)
        self.assertNotIn("/home/alpha", cleaned)
        self.assertNotIn(r"C:\Users", cleaned)
        self.assertEqual(cleaned.count("<path>"), 2)

    def test_preserves_urls_and_external_placeholders(self):
        raw = "https://cachyos.org/ <external>/model.safetensors"
        self.assertEqual(sanitize_host_text(raw), raw)

    def test_redacts_isolated_username_without_corrupting_substrings(self):
        with mock.patch.dict(os.environ, {"USER": "alpha", "LOGNAME": "alpha"}):
            self.assertEqual(
                sanitize_host_text("alphabet alpha alpha-model"),
                "alphabet <user> alpha-model",
            )

    def test_recursive_sanitization_and_assertion(self):
        payload = {
            "path": "/home/alpha/project",
            "nested": [r"C:\Users\alpha\project", "https://example.com/"],
        }
        self.assertEqual(len(host_specific_strings(payload)), 2)
        cleaned = sanitize_host_payload(payload)
        assert_portable_payload(cleaned)
        self.assertEqual(cleaned["path"], "<path>")
        self.assertEqual(cleaned["nested"][0], "<path>")
        self.assertEqual(cleaned["nested"][1], "https://example.com/")


if __name__ == "__main__":
    unittest.main()
