"""Optional: compare the TF-IDF citation retriever with a dense one.

Needs an extra package that the project does not otherwise install:
    pip install fastembed==0.8.1
    python scripts/compare_retrievers.py

Writes results/retrieval_compare.json. Run scripts/build_queue.py first.
"""
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from fastembed import TextEmbedding  # noqa: E402

from adviceguard.clause_cards import DOCS  # noqa: E402
from adviceguard.retrieval import RULE_HIT_REASON, cite_many  # noqa: E402

GOLD = json.loads((REPO / "results" / "retrieval_eval.json").read_text())["gold_mapping"]
q = [json.loads(l) for l in (REPO / "results" / "queue.jsonl").read_text().splitlines()]
syn = [o for o in q if o["set"].startswith("synthetic") and o["reference_label"] == "FLAG"]
queries = [f"{o['text']} {RULE_HIT_REASON if o['source'].startswith('rule') else (o['reason'] or '')}" for o in syn]
gold = [set().union(*[set(GOLD.get(x.strip(), [])) for x in o["reference_rule"].split(",")]) for o in syn]

m = TextEmbedding("BAAI/bge-small-en-v1.5")
E = np.array(list(m.embed([d["title"] + ". " + d["text"] for d in DOCS])))
Q = np.array(list(m.embed(queries)))
dense = [DOCS[i]["id"] for i in (Q @ E.T).argmax(1)]
tfidf = [c["card_id"] for c in cite_many([(s, "") for s in queries])]
out = {"n": len(syn), "tfidf_top1_hit": round(np.mean([a in g for a, g in zip(tfidf, gold)]), 4),
       "dense_bge_small_top1_hit": round(np.mean([a in g for a, g in zip(dense, gold)]), 4),
       "agree_same_card": round(np.mean([a == b for a, b in zip(tfidf, dense)]), 4)}
(REPO / "results" / "retrieval_compare.json").write_text(json.dumps(out, indent=2))
print(out)
