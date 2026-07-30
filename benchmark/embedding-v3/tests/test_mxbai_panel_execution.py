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

    def test_parser_defaults_to_model_native_raw_pairs(self):
        parser = module.build_parser()
        action = next(item for item in parser._actions if item.dest == "instruction")
        self.assertEqual(action.default, "")

    def test_execute_installs_protocol_and_passes_revision_to_runner(self):
        args = argparse.Namespace(model_revision="b" * 40)
        with mock.patch.object(module, "install_protocol") as install, mock.patch.object(
            module.benchmark, "benchmark_profile", return_value={"status": "PASS"}
        ) as runner:
            result = module.execute(args)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(module.benchmark.MODEL_REVISION, "b" * 40)
        install.assert_called_once_with(module.benchmark, "b" * 40)
        runner.assert_called_once_with(args)


if __name__ == "__main__":
    unittest.main()
