# Evals explainer

This file explains every evaluation in the repository: what it asks, how it is computed, where the code and outputs are, and how to read the result. Every number can be recomputed without an API key:

```bash
python scripts/evaluate.py      # rebuilds results/metrics.json, results/tables.md, results/abstention_curve.png
python -m pytest -q tests       # 8 offline checks, including that committed results re-score to the same numbers
```

## Ground rules

- **Dev and test are separate.** All tuning (prompt v1 → v2, rule patterns, TF-IDF training, the HOLD threshold) used the 120 dev sentences. The 120 test sentences were run once, with the final prompt.
- **Labels came first.** Reference labels were committed before any model ran (see `data/README.md`).
- **Model outputs are cached.** Every gpt-4o-mini response is stored in `results/*.jsonl`, so results do not depend on a live API.
- **FLAG and HOLD both count as "stopped".** For recall, a held sentence is not sent, so it counts as caught. Precision of the system is precision of everything it stopped.

## The evals

| # | question | how | code | output |
|---|---|---|---|---|
| 1 | Does it beat simple baselines? | majority class, keyword filter, TF-IDF + logistic regression vs rule layer, gpt-4o-mini alone, full system, on the same test split | `scripts/evaluate.py` | `tables.md` "Headline" |
| 2 | Does it work on the grey zone, not just the easy cases? | recall on the flag class broken out by band and zone | `scripts/evaluate.py` | `tables.md` "Recall by band" |
| 3 | Where does it false-flag? | false flags on PASS sentences by band | `scripts/evaluate.py` | `tables.md` "False flags" |
| 4 | Is the model layer itself accurate? | gpt-4o-mini alone against reference labels (the model is a component, not ground truth) | `scripts/run_llm.py`, `evaluate.py` | `tables.md` "LLM layer alone" |
| 5 | Does HOLD catch the model's mistakes? | sweep the confidence threshold; report HOLD rate and how many held sentences the model would have got wrong | `scripts/evaluate.py` | `tables.md` "Abstention", `abstention_curve.png` |
| 6 | Is the model reading template tells instead of meaning? | strip generator habits, re-score, compare before and after | `adviceguard/detemplate.py`, `evaluate.py` | `tables.md` "De-templating" |
| 7 | Does it hold up on real text? | 40 real sentences from Endowus, StashAway, Syfe | `evaluate.py` | `tables.md` "Held-out real copy" |
| 8 | Are the labels stable? | two blind passes on 60 sentences, Cohen's kappa, disagreements adjudicated | `labeling/stability_check.py` | `results/label_stability.json` |
| 9 | Do citations point to the right clause? | top-1 hit rate against a rule-to-card mapping; TF-IDF vs a dense retriever | `scripts/build_queue.py`, `scripts/compare_retrievers.py` | `retrieval_eval.json`, `retrieval_compare.json` |
| 10 | What does it cost and how fast is it? | measured tokens, cost and latency on 240 real calls | `scripts/run_llm.py`, `evaluate.py` | `tables.md` "Cost and latency", `api_spend.jsonl` |

## Headline results (test split)

| | precision | flag recall | grey-zone recall |
|---|---|---|---|
| majority class | n/a | 0.00 | 0/23 |
| keyword filter | 0.77 | 0.58 | 10/23 |
| TF-IDF + LR | 0.94 | 0.78 | 14/23 |
| rule layer alone | 1.00 | 0.37 | 0/23 |
| gpt-4o-mini alone | 0.98 | 0.90 | 17/23 |
| **full system** | **0.97** | **0.98** | **22/23** |

## How to read them, and what I would not claim

- **The rules catch 0/23 grey sentences by design.** They exist for explicit advice (22/24 on that band, no false flags). The grey zone is the model's job, and the jump from 14/23 (TF-IDF) to 22/23 is the case for using a model at all.
- **Small denominators.** The grey zone has 23 FLAG sentences on test, so one sentence moves recall by 4 points. Tables show k/n for this reason.
- **The synthetic scores are probably optimistic.** On real copy, precision falls to 0.69, just under the 0.70 release condition. Most false flags are product-page lines naming a target customer, which is genuinely close to the line.
- **HOLD catches uncertain errors, not confident ones.** 6 of the 9 sentences held on test were ones the model got wrong. The one remaining miss had p(advice) = 0.0006, so no threshold would have caught it. A weekly random audit of PASS decisions is the control for that.
- **The HOLD budget does not transfer.** Chosen at 5% on dev, it held 7.5% on test and 17.5% on real copy. In production the threshold should be set from the reviewer's daily capacity (`tables.md`, "Operating points").
- **De-templating moved scores by under 2 points**, so I found no evidence of template leakage. That does not rule out subtler shared habits between generator and classifier.
