from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH_DIR))

from holo_gold import generate_gold_rows


class HoloGoldTest(unittest.TestCase):
    def test_gold_shape_is_frozen(self) -> None:
        rows = generate_gold_rows()
        self.assertEqual(len(rows), 304)
        self.assertEqual(len({row["group_id"] for row in rows}), 32)
        self.assertEqual(len({row["intent_id"] for row in rows}), 76)
        self.assertEqual(Counter(row["language"] for row in rows), Counter({"pt-BR": 152, "en": 152}))

    def test_each_query_has_one_canonical_target(self) -> None:
        for row in generate_gold_rows():
            self.assertEqual(len(row["relevant_doc_ids"]), 1)
            self.assertTrue(row["relevant_doc_ids"][0])


if __name__ == "__main__":
    unittest.main()
