"""Citation layer: attach the most relevant MAS/FAA clause card to a FLAG or
HOLD sentence so the reviewer sees why it was stopped.

20 clause cards (adviceguard/clause_cards.py) indexed with TF-IDF from
scikit-learn, which the project already depends on. The query is the sentence
plus the LLM's one-line reason, because the reason names the legal pattern
("links the product to the customer's profile") while the sentence mostly
names products.

I also measured a dense retriever (BAAI/bge-small-en-v1.5 via fastembed) on
the same queries: scripts/compare_retrievers.py. It was right on 3 more of 109
sentences, which did not pay for an ONNX runtime and a 70 MB model download on
every machine that clones the repo. Numbers: results/retrieval_eval.json and
results/retrieval_compare.json.
"""
from __future__ import annotations

from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer

from .clause_cards import DOCS

RULE_HIT_REASON = "The sentence tells the customer directly what to buy, sell or allocate: a call to action."


@lru_cache(maxsize=1)
def _index():
    cards = [d["title"] + ". " + d["text"] for d in DOCS]
    vec = TfidfVectorizer(stop_words="english", sublinear_tf=True).fit(cards)
    return vec, vec.transform(cards)


def _card(i: int, score: float) -> dict:
    d = DOCS[i]
    return {"card_id": d["id"], "title": d["title"], "source": d["source"], "url": d["url"], "score": round(score, 4)}


def cite_many(pairs: list[tuple[str, str]]) -> list[dict]:
    vec, C = _index()
    S = (vec.transform([f"{s} {r}".strip() for s, r in pairs]) @ C.T).toarray()
    return [_card(int(row.argmax()), float(row.max())) for row in S]


def cite(sentence: str, reason: str = "") -> dict:
    return cite_many([(sentence, reason)])[0]
