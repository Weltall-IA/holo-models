from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import voyage_benchmark as voyage


class FakeClient:
    def count_tokens(self, texts, model):
        return sum(len(text) for text in texts)


class VoyageBenchmarkTests(unittest.TestCase):
    def test_key_path_requires_mode_600(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".voyage4_token"
            path.write_text("secret", encoding="utf-8")
            path.chmod(0o600)
            resolved = voyage.configure_key(path)
            self.assertEqual(os.environ["VOYAGE_API_KEY_PATH"], str(resolved))
            path.chmod(0o644)
            with self.assertRaises(PermissionError):
                voyage.configure_key(path)

    def test_pack_texts_respects_token_limit_and_order(self) -> None:
        items = [("a", "a" * 5_000), ("b", "b" * 4_000), ("c", "c" * 2_000)]
        batches = voyage.pack_texts(FakeClient(), "voyage-4-large", items)
        self.assertEqual(
            [[item_id for item_id, _ in batch] for batch in batches],
            [["a", "b"], ["c"]],
        )

    def test_pack_texts_rejects_single_oversized_item(self) -> None:
        with self.assertRaises(RuntimeError):
            voyage.pack_texts(
                FakeClient(),
                "voyage-4-large",
                [("a", "a" * (voyage.MAX_REQUEST_TOKENS + 1))],
            )

    def test_group_by_work_preserves_order(self) -> None:
        chunks = [
            {"work_id": "w2", "chunk_id": "c1", "text": "one"},
            {"work_id": "w1", "chunk_id": "c2", "text": "two"},
            {"work_id": "w2", "chunk_id": "c3", "text": "three"},
        ]
        groups = voyage.group_by_work(chunks)
        self.assertEqual([group_id for group_id, _ in groups], ["w2", "w1"])
        self.assertEqual([item_id for item_id, _ in groups[0][1]], ["c1", "c3"])

    def test_context_batch_never_splits_a_work(self) -> None:
        groups = [
            ("w1", [("a", "a" * 8_000)]),
            ("w2", [("b", "b" * 1_500)]),
        ]
        batches = voyage.pack_context_groups(
            FakeClient(), "voyage-context-4", groups
        )
        self.assertEqual(len(batches), 2)
        self.assertEqual(batches[0][0][0], "w1")

    def test_only_current_voyage_models_are_accepted(self) -> None:
        self.assertEqual(
            voyage.parse_models("voyage-4-large,voyage-context-4"),
            ["voyage-4-large", "voyage-context-4"],
        )
        with self.assertRaises(ValueError):
            voyage.parse_models("voyage-3-large")


if __name__ == "__main__":
    unittest.main()
