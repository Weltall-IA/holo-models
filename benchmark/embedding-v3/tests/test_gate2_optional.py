from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from holo_benchmark.gate2 import Gate2ModelSpec
from holo_benchmark.gate2_worker_v2 import _log_tail, _sentence_transformer_kwargs


class Gate2OptionalModelTests(unittest.TestCase):
    def test_voyage_uses_configured_truncate_dimension(self) -> None:
        voyage = Gate2ModelSpec(
            "voyage4_nano",
            "voyageai/voyage-4-nano",
            "sentence-transformers",
            1024,
            trust_remote_code=True,
            required=False,
        )
        kwargs = _sentence_transformer_kwargs(voyage, "cuda")
        self.assertEqual(kwargs["truncate_dim"], 1024)
        self.assertTrue(kwargs["trust_remote_code"])
        self.assertEqual(kwargs["device"], "cuda")

    def test_other_sentence_transformer_does_not_receive_truncate_dimension(self) -> None:
        model = Gate2ModelSpec(
            "other",
            "org/other",
            "sentence-transformers",
            768,
        )
        self.assertNotIn(
            "truncate_dim",
            _sentence_transformer_kwargs(model, "cuda"),
        )

    def test_llama_server_log_tail_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "llama-server.log"
            path.write_text("prefixo\ncausa real do llama-server\n", encoding="utf-8")
            self.assertIn("causa real do llama-server", _log_tail(path))


if __name__ == "__main__":
    unittest.main()
