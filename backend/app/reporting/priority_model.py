"""
The priority classifier: a small natural-language model that reads a report and suggests high, medium (shown as
"Moderate") or low.

How it works:
- The text becomes numbers with TF-IDF: which words and word pairs it uses (weighted so that rare, telling words
  count more than common ones), plus short pieces of words, so other forms of a word ("belittling", "belittled")
  still count as similar.
- Logistic regression, trained on labelled example reports (priority_examples.json), turns those numbers into a
  chance for each level. The level with the highest chance is the suggestion.
- It runs on this server and is trained the first time it's needed (in well under a second), so report text is
  never sent anywhere and nothing is downloaded.

Explaining it: for each word, the model is asked again without that word. The words whose removal lowers the
chance of the suggested level the most are the ones that drove it, and HR sees them.

The training examples are separate from the evaluation sets in backend/evaluation, and the settings below were
chosen by cross-validation on the training examples only (evaluation/choose_priority_model.py), so the
evaluation measures the model on reports it has never seen.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline, make_union
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

EXAMPLES = Path(__file__).with_name("priority_examples.json")
LEVELS = ["low", "medium", "high"]
# The anonymiser's tags ("[PERSON 1]", "[DATE 2]") say nothing about urgency, so they are removed before reading
TAG = re.compile(r"\[(?:PERSON|EMAIL|PHONE|DATE) \d+\]")
WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")
# Settings chosen by cross-validation on the training examples (see the module docstring)
SETTINGS = {"C": 3.0, "char": True}


def prepare(text: str) -> str:
    return TAG.sub(" ", text).lower()


def build(C: float = SETTINGS["C"], char: bool = SETTINGS["char"]):
    """The untrained model: TF-IDF features, then logistic regression."""
    words = TfidfVectorizer(preprocessor=prepare, ngram_range=(1, 2), sublinear_tf=True)
    features = make_union(words, TfidfVectorizer(preprocessor=prepare, analyzer="char_wb", ngram_range=(3, 5),
                                                 sublinear_tf=True)) if char else words
    return make_pipeline(features, LogisticRegression(C=C, class_weight="balanced", max_iter=5000))


def training_data() -> tuple[list[str], list[str]]:
    data = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    texts, labels = [], []
    for level in LEVELS:
        texts += data[level]
        labels += [level] * len(data[level])
    return texts, labels


@lru_cache(maxsize=1)
def model():
    """The trained model, trained once and then kept in memory."""
    texts, labels = training_data()
    return build().fit(texts, labels)


def chances(texts: list[str]) -> np.ndarray:
    """For each text, the chance of each level, in the order of LEVELS."""
    m = model()
    order = [list(m.classes_).index(level) for level in LEVELS]
    return m.predict_proba(texts)[:, order]


def predict(text: str, top: int = 5) -> dict:
    """
    The suggested level, how sure the model is (the chance of that level), the chance of every level, and the
    words that drove the suggestion most.
    """
    probabilities = chances([text])[0]
    best = int(np.argmax(probabilities))
    level = LEVELS[best]

    # Leave one word out at a time and see how much the chance of the suggested level drops. Filler words ("and",
    # "the") are read by the model but not listed, as they mean nothing to a person reading the explanation.
    words = list(dict.fromkeys(w.lower() for w in WORD.findall(TAG.sub(" ", text))
                               if len(w) > 2 and w.lower() not in ENGLISH_STOP_WORDS))
    drivers = []
    if words:
        without = [re.sub(rf"(?<![A-Za-z']){re.escape(w)}(?![A-Za-z'])", " ", text, flags=re.IGNORECASE) for w in words]
        drops = probabilities[best] - chances(without)[:, best]
        ranked = sorted(zip(words, drops), key=lambda pair: -pair[1])
        drivers = [{"word": w, "weight": round(float(d), 3)} for w, d in ranked[:top] if d > 0.01]
    return {"priority": level, "confidence": round(float(probabilities[best]), 3),
            "chances": {lvl: round(float(p), 3) for lvl, p in zip(LEVELS, probabilities)}, "words": drivers}
