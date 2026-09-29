"""Precompute the review queue the Streamlit app replays in offline mode, and
score the citation layer.

    python scripts/build_queue.py

Writes results/queue.jsonl (all 240 dataset sentences and 40 real-copy
sentences with system decision and citation) and results/retrieval_eval.json.
Uses only cached LLM results. No API key and no network needed.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from adviceguard.pipeline import TAU, guard  # noqa: E402
from adviceguard.retrieval import RULE_HIT_REASON, cite_many  # noqa: E402

# Which clause cards count as a correct citation for each guideline rule.
GOLD = {"F1": {"doc_03", "doc_04"}, "F2": {"doc_06", "doc_07", "doc_19"}, "F3": {"doc_02", "doc_12"},
        "F4": {"doc_08", "doc_12"}, "F5": {"doc_03", "doc_07"}, "F6": {"doc_05"}}

rows = []
for r in csv.DictReader(open(REPO / "data" / "advice_boundary_v1.csv")):
    rows.append({"id": r["id"], "text": r["text"], "set": f"synthetic-{r['split']}", "band": r["band"], "zone": r["zone"]})
for r in csv.DictReader(open(REPO / "data" / "heldout_real_copy.csv")):
    rows.append({"id": r["id"], "text": r["text"], "set": "real-copy", "band": "", "zone": "", "platform": r["platform"], "source_url": r["source_url"]})
labels = {r["id"]: r for f in ["labels.csv", "heldout_labels.csv"] for r in csv.DictReader(open(REPO / "data" / f))}

out = []
for r in rows:
    g = guard(r["text"], allow_live=False, with_citation=False)
    out.append({**r, **{k: g.get(k) for k in ["decision", "source", "p_flag", "reason"]},
                "reference_label": labels[r["id"]]["label"], "reference_rule": labels[r["id"]]["rule"]})

need = [o for o in out if o["decision"] in ("FLAG", "HOLD")]
cites = cite_many([(o["text"], RULE_HIT_REASON if o["source"].startswith("rule") else (o["reason"] or "")) for o in need])
for o, c in zip(need, cites):
    o["citation"] = c
with open(REPO / "results" / "queue.jsonl", "w") as f:
    for o in out:
        f.write(json.dumps(o) + "\n")

# retrieval eval: FLAG reference items in the synthetic set, production query path
ev = []
syn = [o for o in out if o["set"].startswith("synthetic") and o["reference_label"] == "FLAG"]
qs = [(o["text"], RULE_HIT_REASON if o["source"].startswith("rule") else (o["reason"] or "")) for o in syn]
for o, c in zip(syn, cite_many(qs)):
    gold = set().union(*[GOLD.get(x.strip(), set()) for x in o["reference_rule"].split(",")])
    ev.append({"id": o["id"], "rule": o["reference_rule"], "cited": c["card_id"], "hit": c["card_id"] in gold})
sent_only = cite_many([(o["text"], "") for o in syn])
hit_sent = sum(c["card_id"] in set().union(*[GOLD.get(x.strip(), set()) for x in o["reference_rule"].split(",")]) for o, c in zip(syn, sent_only))
res = {"n_flag_items": len(ev), "top1_hit_rate": round(sum(e["hit"] for e in ev) / len(ev), 4),
       "top1_hit_rate_sentence_only_query": round(hit_sent / len(ev), 4),
       "cited_card_counts": {k: sum(e["cited"] == k for e in ev) for k in sorted({e["cited"] for e in ev})},
       "gold_mapping": {k: sorted(v) for k, v in GOLD.items()}, "tau": TAU, "items": ev}
(REPO / "results" / "retrieval_eval.json").write_text(json.dumps(res, indent=2))
print({k: v for k, v in res.items() if k != "items"})
print("queue:", len(out), {d: sum(o["decision"] == d for o in out) for d in ["PASS", "FLAG", "HOLD"]})
