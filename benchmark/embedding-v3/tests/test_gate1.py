from __future__ import annotations

import unittest

from holo_benchmark.corpus import (
    build_corpus,
    build_queries,
    build_review_checklist,
    validate_corpus,
)


class Gate1CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.chunks, cls.id_map, cls.quote_map = build_corpus()
        cls.queries = build_queries(cls.id_map, cls.quote_map)
        cls.validation = validate_corpus(cls.chunks, cls.queries)

    def test_counts_and_distribution(self) -> None:
        self.assertEqual(len(self.chunks), 600)
        self.assertEqual(len(self.queries), 150)
        self.assertEqual(self.validation["counts"]["works"], 30)
        self.assertTrue(self.validation["all_automated_checks_passed"], self.validation["errors"])

    def test_unique_queries_and_chunks(self) -> None:
        self.assertEqual(len({c["chunk_id"] for c in self.chunks}), 600)
        self.assertEqual(len({c["text"] for c in self.chunks}), 600)
        self.assertEqual(len({q["query_id"] for q in self.queries}), 150)
        self.assertEqual(len({q["query"] for q in self.queries}), 150)

    def test_token_and_template_limits(self) -> None:
        dist = self.validation["token_distribution"]
        self.assertGreaterEqual(dist["min"], 180)
        self.assertLessEqual(dist["max"], 420)
        self.assertLess(self.validation["template_overlap"]["max_jaccard_5gram"], 0.55)

    def test_review_checklist(self) -> None:
        checklist = build_review_checklist(self.chunks, self.queries)
        self.assertGreaterEqual(checklist["sample_count"], 30)
        self.assertEqual({i["query_type"] for i in checklist["items"]}, {
            "semantic_event", "context_dependency", "emotion_intention", "indirect_dialogue",
            "character_name", "exact_phrase", "similar_scene",
        })


if __name__ == "__main__":
    unittest.main()
