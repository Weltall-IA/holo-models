from __future__ import annotations

import unittest

from holo_benchmark.nemotron_8b_abiray_finalize_optional import expected_counts


class OptionalVoyageFinalizationTests(unittest.TestCase):
    def test_counts_without_voyage(self) -> None:
        self.assertEqual(expected_counts(False), (105, 9))

    def test_counts_with_voyage(self) -> None:
        self.assertEqual(expected_counts(True), (107, 11))


if __name__ == "__main__":
    unittest.main()
