# Data explainer

Everything the evaluation uses is in this folder or in `../labeling/`. No customer data and no personal data are used anywhere.

## Files

| file | rows | columns | what it is |
|---|---|---|---|
| `advice_boundary_v1.csv` | 240 | `id, text, band, zone, split, length_bucket, tone, product, twist, cell` | the synthetic benchmark |
| `labels.csv` | 240 | `id, label, rule, confidence, note` | reference labels for the benchmark |
| `heldout_real_copy.csv` | 40 | `id, text, platform, source_url, retrieved` | real sentences quoted from public web pages |
| `heldout_labels.csv` | 40 | `id, label, rule, confidence, note` | reference labels for the real sentences |
| `generation/generation_prompt.md` | | | the exact prompt that wrote the synthetic sentences |
| `generation/raw_generations.jsonl` | | | raw generator output, so the CSV can be rebuilt without an API key |
| `generation/generation_spend.jsonl` | | | cost of every generation call |

## The synthetic benchmark: advice_boundary_v1

**Why synthetic.** There is no public dataset of robo-advisor chatbot sentences labelled against Singapore's information/advice line, and real transcripts contain customer data. Generating the set lets me control exactly which kinds of sentences appear and publish everything.

**How it was made.** `scripts/make_dataset.py` asks `anthropic/claude-sonnet-4.6` (a different model family from the classifier, on purpose) to write sentences for a grid:

- **5 bands**, from clearly safe to clearly advice: `plain_fact`, `fact_comparison`, `implied_suitability`, `soft_recommendation`, `explicit_recommendation`.
- **3 zones**: `clear_pass` (96), `clear_flag` (72), `grey` (72). The grey zone is where the project is decided.
- **Each cell** also fixes a length, a tone, a product type and a `twist`: an awkward case such as advice wrapped in a disclaimer, or information that contains the word "recommend".

Ids are shuffled so they carry no band information. `split` divides the set in half by band and zone: **dev** (120) was used for prompt iteration, rule writing, TF-IDF training and threshold choice; **test** (120) was scored once.

**Cleaning, all scripted.** Three real brand names were replaced with invented ones, and the generator's em dashes were normalised. `adviceguard/detemplate.py` can additionally strip generator habits (openers, particles like "lah", disclaimers) to test for leakage.

**Label balance.** PASS 132, FLAG 108 on all 240, so the majority-class baseline is 0.55 accuracy. The grey zone is split exactly 36 FLAG / 36 PASS.

## Reference labels

Labels follow `../labeling/guideline.md`, which turns the Financial Advisers Act Second Schedule and MAS 2019 guidance into 6 FLAG rules (F1 to F6) and 5 PASS rules (P1 to P5), plus a tie-breaker. Each label records the rule that decided it and a high or low confidence. `labels.csv` was committed before any classifier ran; `git log --reverse` shows the order.

**Label stability check.** 60 sentences, weighted towards the grey zone, were labelled a second time in a pass that saw only id and text (`../labeling/blind_60.csv` → `../labeling/pass2_60.csv`). The two passes agreed on 59/60 (Cohen's kappa 0.967). The one disagreement is adjudicated in `../labeling/adjudication.csv`. Both passes use the same guideline, so this shows the guideline pins labels down; it does not show that two compliance lawyers would agree.

## The held-out real copy

40 sentences quoted word for word from public Endowus, StashAway and Syfe web pages on 2026-09-29, with the URL of each. They were fetched as raw pages and checked to be exact substrings. They were never generated and never used for tuning. Most are informational (29 PASS, 11 FLAG), so their main job is to catch false flags on real marketing language.

## What this data cannot tell you

- Sentences skew long (131 long, 84 medium, 25 short). Real chatbot replies are often shorter.
- A language model wrote the benchmark and a language model classifies it. They may share a sense of what advice sounds like, which would make the synthetic scores optimistic. The real copy is the check on this, and precision does drop there (0.97 → 0.69).
- Single sentences only. Advice spread across turns is not covered.
- The grey-zone rules are one written reading of MAS guidance, not settled law.

## Rebuild

```bash
python scripts/make_dataset.py              # rebuilds advice_boundary_v1.csv exactly from raw_generations.jsonl
python scripts/make_dataset.py --regenerate # draws a new set (needs a key; would need new labels)
```
