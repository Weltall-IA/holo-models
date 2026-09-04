from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH_DIR))

from metrics import paired_bootstrap_delta, per_query_metrics


class MetricsTest(unittest.TestCase):
    def test_perfect_first_hit(self) -> None:
        m = per_query_metrics(["p", "n1", "n2"], ["p"])
        self.assertEqual(m["ndcg@10"], 1.0)
        self.assertEqual(m["mrr@10"], 1.0)
        self.assertEqual(m["hit@1"], 1.0)
        self.assertEqual(m["recall@10"], 1.0)

    def test_relevant_at_rank_two(self) -> None:
        m = per_query_metrics(["n", "p", "x"], ["p"])
        self.assertAlmostEqual(m["mrr@10"], 0.5)
        self.assertAlmostEqual(m["ndcg@10"], 1.0 / math.log2(3.0))
        self.assertEqual(m["hit@1"], 0.0)

    def test_paired_identical_is_inconclusive(self) -> None:
        a = {
            "q1": {"ndcg@10": 1.0},
            "q2": {"ndcg@10": 0.0},
        }
        b = {
            "q1": {"ndcg@10": 1.0},
            "q2": {"ndcg@10": 0.0},
        }
        out = paired_bootstrap_delta(a, b, "ndcg@10", resamples=200)
        self.assertEqual(out["mean_delta"], 0.0)
        self.assertEqual(out["verdict"], "inconclusive")


if __name__ == "__main__":
    unittest.main()
