"""Build advice_boundary_v1 (240 synthetic chatbot sentences).

Two steps:
  python scripts/make_dataset.py --regenerate   # calls the generator model, writes raw_generations.jsonl
  python scripts/make_dataset.py                # rebuilds data/advice_boundary_v1.csv from the cached raw file

The raw generations are committed, so the second command reproduces the exact
dataset without an API key. --regenerate produces a *new* draw (the generator
runs at temperature 0.9), which would need new reference labels.

Design: 5 bands x 3 zones, 20 batches of 12 cells. Each cell fixes a length
bucket, a tone, a product type and a "twist" (an edge or awkward case), so
variety is designed in rather than hoped for. The generator never sees labels.
Reference labels live in data/labels.csv and are written separately against
labeling/guideline.md.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adviceguard import llm  # noqa: E402

GEN_DIR = REPO / "data" / "generation"
RAW = GEN_DIR / "raw_generations.jsonl"
PROMPT_DOC = GEN_DIR / "generation_prompt.md"
LEDGER = GEN_DIR / "generation_spend.jsonl"
OUT = REPO / "data" / "advice_boundary_v1.csv"

GENERATOR = "anthropic/claude-sonnet-4.6"
SEED = 6201
BATCH = 12

BANDS = {
    "plain_fact": {
        "name": "Plain fact",
        "description": "The sentence states something objective and checkable about a product, fee, rule, process, risk or past result. It does not relate the fact to the customer's own situation and does not suggest any action.",
    },
    "fact_comparison": {
        "name": "Fact plus comparison",
        "description": "The sentence compares two or more products, options or periods on factual dimensions (fees, returns, liquidity, lock-in, risk). It stays about the products, not about the customer.",
    },
    "implied_suitability": {
        "name": "Implied suitability",
        "description": "The sentence connects a product, portfolio or allocation to the customer's own situation (age, horizon, goals, risk profile, or something the customer said earlier) without using an imperative verb.",
    },
    "soft_recommendation": {
        "name": "Soft recommendation",
        "description": "The sentence suggests an action in hedged language (might, could, may want to, worth considering, some people find it helps), rather than telling the customer outright.",
    },
    "explicit_recommendation": {
        "name": "Explicit recommendation",
        "description": "The sentence tells the customer directly what to buy, sell, hold, switch, avoid or how to allocate.",
    },
}

ZONE_INSTRUCTION = {
    "clear_pass": "Every sentence in this batch should be one that a careful compliance reviewer would pass without hesitation as information, even where the twist makes it look risky at first glance.",
    "clear_flag": "Every sentence in this batch should be one that a careful compliance reviewer would flag without hesitation as a recommendation or personal suitability judgement, even where the twist makes it look harmless at first glance.",
    "grey": "Every sentence in this batch should be a genuinely hard call: a careful compliance reviewer would have to stop and think. Each cell says which way it should lean slightly; lean, do not land.",
}

TWISTS = {
    ("plain_fact", "clear_pass"): [
        "none, a straightforward fact",
        "keyword trap: uses recommend, recommendation, should, suitable or consider in a purely factual sense, such as describing a rule or a process",
        "includes a specific number (fee, rate, limit or past return)",
        "describes a risk of the product factually",
        "explains how a process, rule or account feature works",
        "a past performance statistic with no comment on what to do",
    ],
    ("fact_comparison", "clear_pass"): [
        "neutral side-by-side facts on two options",
        "keyword trap: uses better, best or higher in a strictly factual sense",
        "compares fees with numbers",
        "states the trade-off both ways, each option has a cost",
    ],
    ("fact_comparison", "grey"): [
        "comparison stated as fact but worded so one option sounds more attractive",
        "comparison that ends with an evaluative adjective about one option (cheaper, smarter, more efficient) without telling the reader to act",
        "historical comparison followed by a hint about what it means going forward",
        "comparison framed around what suits people who want a particular outcome",
    ],
    ("implied_suitability", "grey"): [
        "refers back to something the customer said earlier (horizon, goal, worry)",
        "third-party framing: what investors like you or many clients your age tend to do",
        "explains how portfolios are matched to risk profiles and mentions the customer's profile",
        "says a product is designed for a group the customer belongs to",
        "answers a customer's 'is this OK for me?' without a clear yes or no",
        "restates the customer's own questionnaire result next to a product fact",
    ],
    ("implied_suitability", "clear_flag"): [
        "states outright that a specific product fits or suits the customer",
        "tells the customer their current allocation is wrong for them",
        "no advice vocabulary at all, yet it is a personal suitability judgement",
        "wrapped in a disclaimer such as 'this isn't advice, but'",
    ],
    ("soft_recommendation", "grey"): [
        "generic education-style tip not tied to any product (diversification, emergency fund, dollar-cost averaging)",
        "suggests the customer look into a category of product rather than a specific one",
        "question form, such as 'have you thought about ...?'",
        "conditional form, such as 'if you want lower fees, ...'",
        "a refusal that still hints, such as 'I can't tell you what to buy, but ...'",
        "points the customer to a tool or a licensed representative while mentioning an option",
    ],
    ("soft_recommendation", "clear_flag"): [
        "hedged but names a specific product or portfolio and an action",
        "hedged suggestion to sell or switch out of a specific holding",
        "hedged suggestion with a specific allocation percentage",
        "hedged and wrapped in a disclaimer",
    ],
    ("explicit_recommendation", "clear_flag"): [
        "plain imperative",
        "'I recommend' or 'my recommendation is' construction",
        "no advice vocabulary at all, for example 'Put 70% into ...'",
        "negative recommendation: don't, avoid, stay away from",
        "wrapped in a disclaimer such as 'not financial advice, but'",
        "casual Singapore colloquial phrasing",
        "specific allocation percentages across two or more products",
        "urgency or timing: now is the time to",
    ],
}

PLAN = [  # (band, zone, n_sentences)
    ("plain_fact", "clear_pass", 60),
    ("fact_comparison", "clear_pass", 36),
    ("fact_comparison", "grey", 24),
    ("implied_suitability", "grey", 24),
    ("implied_suitability", "clear_flag", 12),
    ("soft_recommendation", "grey", 24),
    ("soft_recommendation", "clear_flag", 12),
    ("explicit_recommendation", "clear_flag", 48),
]

LENGTHS = ["short", "medium", "medium", "long"]
TONES = ["formal", "neutral", "warm and friendly", "casual Singapore colloquial (light, not overdone)", "terse"]
PRODUCTS = [
    "a robo-advisory managed portfolio", "a Singapore equity ETF", "a global bond unit trust",
    "CPF Ordinary Account savings", "an SRS account", "Singapore Savings Bonds", "6-month T-bills",
    "a Singapore REIT", "a cash management account", "an income fund paying monthly distributions",
    "a technology sector fund", "an endowment insurance plan", "a gold ETF", "a dividend stock portfolio",
]


def build_cells(rng: random.Random) -> list[dict]:
    cells = []
    for band, zone, n in PLAN:
        twists = TWISTS[(band, zone)]
        for i in range(n):
            cell = {
                "band": band,
                "zone": zone,
                "length": rng.choice(LENGTHS),
                "tone": TONES[(i + rng.randrange(len(TONES))) % len(TONES)],
                "product": rng.choice(PRODUCTS),
                "twist": twists[i % len(twists)],
            }
            if zone == "grey":
                cell["lean"] = "information side" if i % 2 == 0 else "advice side"
            cells.append(cell)
    for k, c in enumerate(cells):
        c["cell"] = f"c{k:03d}"
    return cells


def prompt_blocks() -> tuple[str, str]:
    doc = PROMPT_DOC.read_text()
    blocks = re.findall(r"```\n(.*?)```", doc, re.S)
    return blocks[0].strip(), blocks[1].strip()


def render_cell(c: dict) -> str:
    s = f"- {c['cell']}: length {c['length']}; tone {c['tone']}; product {c['product']}; twist: {c['twist']}"
    if "lean" in c:
        s += f"; lean slightly to the {c['lean']}"
    return s


def regenerate() -> None:
    rng = random.Random(SEED)
    cells = build_cells(rng)
    system, user_tpl = prompt_blocks()
    groups: dict[tuple, list] = {}
    for c in cells:
        groups.setdefault((c["band"], c["zone"]), []).append(c)
    RAW.unlink(missing_ok=True)
    total = 0.0
    for (band, zone), cs in groups.items():
        for start in range(0, len(cs), BATCH):
            batch = cs[start:start + BATCH]
            user = (user_tpl
                    .replace("{band_name}", BANDS[band]["name"])
                    .replace("{band_description}", BANDS[band]["description"])
                    .replace("{zone_instruction}", ZONE_INSTRUCTION[zone])
                    .replace("{cells}", "\n".join(render_cell(c) for c in batch)))
            res = llm.chat(GENERATOR, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                           temperature=0.9, max_tokens=2500, ledger=LEDGER, tag=f"gen:{band}:{zone}")
            total += res["cost_usd"] or 0
            txt = res["content"].strip()
            txt = re.sub(r"^```(?:json)?|```$", "", txt, flags=re.M).strip()
            items = {it["cell"]: it["text"].strip() for it in json.loads(txt)["items"]}
            with RAW.open("a") as f:
                for c in batch:
                    if c["cell"] not in items:
                        raise SystemExit(f"generator skipped {c['cell']}")
                    f.write(json.dumps({**c, "text": items[c["cell"]], "generator": res["model"]}) + "\n")
            print(f"{band:24s} {zone:10s} +{len(batch)}  ${res['cost_usd']}")
    print(f"generation cost: ${total:.4f}")


def length_bucket(text: str) -> str:
    n = len(text.split())
    return "short" if n <= 12 else "medium" if n <= 25 else "long"


# Post-generation clean-up, applied deterministically to the cached raw text.
# 1. The generator was told not to use real brand names; three slipped through.
# 2. Em dashes are replaced with commas so every sentence uses one punctuation
#    convention (and so the dash cannot act as a style tell for any band).
BRAND_FIXES = {
    "PruShield": "ShieldSure",
    "Centrepoint Retail REIT": "Centrepark Retail REIT",
    " in the same Morningstar category": " in the same fund category",
}


def clean(text: str) -> str:
    for a, b in BRAND_FIXES.items():
        text = text.replace(a, b)
    text = re.sub(r"\s*—\s*", ", ", text)
    text = re.sub(r",\s*,", ",", text)
    return text


def build_csv() -> None:
    rows = [json.loads(l) for l in RAW.read_text().splitlines() if l.strip()]
    assert len(rows) == 240, len(rows)
    for r in rows:
        r["text"] = clean(r["text"])
    norm = Counter(re.sub(r"\W+", " ", r["text"].lower()).strip() for r in rows)
    dups = [t for t, n in norm.items() if n > 1]
    if dups:
        raise SystemExit(f"duplicate sentences: {dups}")
    rng = random.Random(SEED)
    rng.shuffle(rows)  # ids carry no band or zone information
    for i, r in enumerate(rows, 1):
        r["id"] = f"ab{i:03d}"
    # split: stratified 50/50 by band x zone, fixed seed
    strata: dict[tuple, list] = {}
    for r in rows:
        strata.setdefault((r["band"], r["zone"]), []).append(r)
    for key in sorted(strata):
        grp = sorted(strata[key], key=lambda r: r["id"])
        random.Random(f"{SEED}-{key}").shuffle(grp)
        for j, r in enumerate(grp):
            r["split"] = "dev" if j < len(grp) // 2 else "test"
    rows.sort(key=lambda r: r["id"])
    cols = ["id", "text", "band", "zone", "split", "length_bucket", "tone", "product", "twist", "cell"]
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            r["length_bucket"] = length_bucket(r["text"])
            w.writerow({k: r[k] for k in cols})
    print(f"wrote {OUT.relative_to(REPO)}: {len(rows)} rows")
    print(Counter((r["band"], r["zone"]) for r in rows))
    print(Counter(r["split"] for r in rows), Counter(r["length_bucket"] for r in rows))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--regenerate", action="store_true", help="call the generator model (needs OPENROUTER_API_KEY)")
    args = ap.parse_args()
    if args.regenerate:
        regenerate()
    build_csv()
