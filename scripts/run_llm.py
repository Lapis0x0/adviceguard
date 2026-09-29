"""Run the LLM layer over a sentence set and cache every response.

    python scripts/run_llm.py --set dev          # 120 dev sentences (prompt iteration)
    python scripts/run_llm.py --set all          # all 240 sentences
    python scripts/run_llm.py --set detemplated  # all 240, de-templated text
    python scripts/run_llm.py --set heldout      # 40 real-copy sentences

Results go to results/llm_<set>_<prompt_version>.jsonl, one line per id. Ids
already in the file are skipped, so a crashed run resumes where it stopped.
Every call is also appended to results/api_spend.jsonl.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from adviceguard import classifier  # noqa: E402
from adviceguard.detemplate import detemplate  # noqa: E402

LEDGER = REPO / "results" / "api_spend.jsonl"


def load(set_name: str) -> list[tuple[str, str]]:
    if set_name == "heldout":
        return [(r["id"], r["text"]) for r in csv.DictReader(open(REPO / "data" / "heldout_real_copy.csv"))]
    rows = list(csv.DictReader(open(REPO / "data" / "advice_boundary_v1.csv")))
    if set_name == "dev":
        rows = [r for r in rows if r["split"] == "dev"]
    if set_name == "detemplated":
        return [(r["id"], detemplate(r["text"])) for r in rows]
    return [(r["id"], r["text"]) for r in rows]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", required=True, choices=["dev", "all", "detemplated", "heldout"])
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    out = REPO / "results" / f"llm_{a.set}_{classifier.PROMPT_VERSION}.jsonl"
    out.parent.mkdir(exist_ok=True)
    done = {json.loads(l)["id"] for l in out.read_text().splitlines()} if out.exists() else set()
    todo = [(i, t) for i, t in load(a.set) if i not in done]
    print(f"{a.set}: {len(todo)} to run, {len(done)} cached")

    def one(item):
        i, t = item
        r = classifier.classify(t, ledger=LEDGER, tag=f"{a.set}:{classifier.PROMPT_VERSION}")
        return {"id": i, "text": t, **r}

    cost = 0.0
    with ThreadPoolExecutor(a.workers) as ex, out.open("a") as f:
        for r in ex.map(one, todo):
            f.write(json.dumps(r) + "\n")
            f.flush()
            cost += r["cost_usd"] or 0
    print(f"done, cost this run ${cost:.4f}")


if __name__ == "__main__":
    main()
