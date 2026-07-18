import re
import string
from itertools import zip_longest as iterzip

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

MODEL_ID = "/home/alpha/Playstoria/models/audio/voz/dominguesm-bert-restore-punctuation-ptbr"


class RestorePuncts:
    def __init__(self, words_per_pred=250, overlap=20, use_cuda=False) -> None:
        self.words_per_pred = words_per_pred
        self.overlap = overlap
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        self.model = AutoModelForTokenClassification.from_pretrained(MODEL_ID)
        self.model.eval()
        self.device = "cuda" if (use_cuda and torch.cuda.is_available()) else "cpu"
        self.model.to(self.device)
        self.id2label = self.model.config.id2label

    def restore_puncts(self, text: str):
        text = self.prepare_text(text)
        splits = [
            " ".join(s)
            for s in self.split_text(text, self.words_per_pred, self.overlap)
        ]
        predictions = self._predict(splits)
        return self.make_results(predictions)

    def _predict(self, splits):
        results = []
        for s in splits:
            words = s.split(" ")
            enc = self.tokenizer(
                words,
                is_split_into_words=True,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )
            word_ids = enc.word_ids(batch_index=0)
            enc = {k: v.to(self.device) for k, v in enc.items()}
            with torch.no_grad():
                logits = self.model(**enc).logits
            preds = logits.argmax(dim=-1)[0].tolist()
            word_preds = []
            last = None
            for wid, pid in zip(word_ids, preds):
                if wid is None:
                    continue
                if wid != last:
                    word_preds.append((words[wid], self.id2label[pid]))
                    last = wid
            results.append([{w: l} for w, l in word_preds])
        return results

    @staticmethod
    def prepare_text(text: str):
        text = text.strip()
        text = text.replace("\n", " ").lower()
        text = text.translate(str.maketrans(" ", " ", string.punctuation))
        text = re.sub(" +", " ", text)
        return text

    @staticmethod
    def split_text(text, words_per_pred, overlap):
        seq = text.replace("\n", " ").split(" ")
        for x in iterzip(
            *[seq[i :: words_per_pred - overlap] for i in range(words_per_pred)]
        ):
            yield tuple(i for i in x if i is not None) if x[-1] is None else x

    def make_results(self, predictions):
        text_restored = []
        total_predictions = len(predictions)
        for i, preds in enumerate(predictions):
            if i != (total_predictions - 1):
                preds = preds[0 : -self.overlap]
            for pred in preds:
                text, value = list(pred.items())[0]
                if value[1] == "U":
                    text = text.capitalize()
                if value[0] != "O":
                    text += value[0]
                text_restored.append(text)
        return " ".join(text_restored)
