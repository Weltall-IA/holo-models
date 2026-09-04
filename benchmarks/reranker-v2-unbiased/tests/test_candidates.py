from __future__ import annotations

import sys
import unittest
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH_DIR))

from prepare_holo import BM25, positive_complete_pool


class CandidatePoolTest(unittest.TestCase):
    def test_positive_complete_injects_missing_positive_at_tail(self) -> None:
        ranked = [f"d{i}" for i in range(60)]
        pool = positive_complete_pool(ranked, ["d59"], 50)
        self.assertEqual(len(pool), 50)
        self.assertEqual(len(pool), len(set(pool)))
        self.assertIn("d59", pool)
        self.assertEqual(pool[-1], "d59")

    def test_positive_complete_keeps_more_positives_than_top_k(self) -> None:
        ranked = [f"d{i}" for i in range(50)]
        positives = [f"d{i}" for i in range(60)]
        pool = positive_complete_pool(ranked, positives, 50)
        self.assertEqual(len(pool), 60)
        self.assertTrue(set(positives).issubset(pool))

    def test_bm25_prefers_matching_document(self) -> None:
        bm25 = BM25([
            "alpha beta gamma",
            "unrelated cooking recipe",
            "architecture audit trust boundaries",
        ])
        self.assertEqual(bm25.rank("trust architecture")[0], 2)


if __name__ == "__main__":
    unittest.main()
