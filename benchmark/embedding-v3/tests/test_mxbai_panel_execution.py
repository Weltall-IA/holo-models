from __future__ import annotations

import argparse
import unittest
from unittest import mock

from holo_benchmark import mxbai_panel_execution as module


class MixedbreadExecutionTests(unittest.TestCase):
    def test_revision_must_be_full_sha(self):
        self.assertEqual(module.validate_revision("A" * 40), "a" * 40)
        with self.assertRaisesRegex(ValueError, "40-character SHA"):
            module.validate_revision("main")

    def test_execute_passes_proven_revision_to_runner(self):
        args = argparse.Namespace(model_revision="b" * 40)
        with mock.patch.object(
            module.benchmark, "benchmark_profile", return_value={"status": "PASS"}
        ) as runner:
            result = module.execute(args)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(module.benchmark.MODEL_REVISION, "b" * 40)
        runner.assert_called_once_with(args)


if __name__ == "__main__":
    unittest.main()
