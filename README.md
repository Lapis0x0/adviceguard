# AdviceGuard

AdviceGuard reads each sentence a retail investment chatbot is about to send and returns **PASS**, **FLAG** or **HOLD**. It is built for the compliance officer at a small Singapore robo-advisory firm. She stops sampling transcripts after the fact and instead works a ranked queue of sentences that may have crossed the line between financial information and financial advice under the Financial Advisers Act.

```
sentence ──► rule layer ── explicit advice construction? ──► FLAG (no model call)
                 │ no
                 ▼
            gpt-4o-mini (OpenRouter, temperature 0, JSON, logprobs)
                 │ p_flag from the label token
                 ▼
            confidence max(p, 1-p) < 0.995 ? ──► HOLD for review
                 │ no
                 ▼
            FLAG if p_flag >= 0.5, else PASS
FLAG and HOLD get the nearest MAS/FAA clause card (TF-IDF over 20 cards) as a citation.
```

Orchestration is about 70 lines of plain Python (`adviceguard/pipeline.py`). No agent framework.

## Results (test half, 120 sentences, never used for tuning)

| | precision | recall on flag class | grey-zone recall | block rate |
|---|---|---|---|---|
| majority class (always PASS) | n/a | 0.00 | 0/23 | 0.00 |
| keyword filter | 0.77 | 0.58 | 10/23 | 0.37 |
| TF-IDF + logistic regression | 0.94 | 0.78 | 14/23 | 0.41 |
| rule layer alone | 1.00 | 0.37 | 0/23 | 0.18 |
| gpt-4o-mini alone | 0.98 | 0.90 | 17/23 | 0.45 |
| **full system (FLAG or HOLD)** | 0.97 | **0.98** | **22/23** | 0.50 (HOLD 0.075) |

- Majority-class accuracy is 0.55 on all 240 sentences (0.51 on the test half).
- On 40 sentences quoted verbatim from Endowus, StashAway and Syfe web pages, gpt-4o-mini flagged all 11 advice-like sentences but also 5 of 29 informational ones: precision 0.69, just under the 0.70 release floor. The keyword filter and TF-IDF reached 0.33 and 0.40.
- Measured cost: $0.113 per 1,000 sentences for the model, $0.092 per 1,000 once the rule layer takes its 19%. Latency p50 1.9 s, p95 2.5 s per call.
- Label stability check on 60 sentences: Cohen's kappa 0.967, one disagreement, adjudicated in `labeling/adjudication.csv`.

All tables: `results/tables.md`. Every number is recomputed from committed files by `scripts/evaluate.py`.

## Run it

Tested with Python 3.12 on macOS. Python 3.11 to 3.13 should work.

### Without an API key (default)

```bash
git clone https://github.com/Lapis0x0/adviceguard.git
cd adviceguard
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m pytest -q tests          # 8 offline checks, including re-scoring every result
python -m streamlit run app/app.py # review queue at http://localhost:8501
```

or `make setup && make check && make app`.

Offline mode replays the model outputs committed in `results/`. The queue, the evaluation tab and the example sentences work fully. If you type a new sentence that no rule catches, the guard **holds** it, because with no model available it fails closed rather than passing it.

### With an OpenRouter key

```bash
cp .env.example .env               # then put your key in .env (git-ignored)
python -m streamlit run app/app.py # "Check a sentence" now calls gpt-4o-mini live
python scripts/run_llm.py --set heldout   # re-run a set; results are cached per id
```

The key is read from the `OPENROUTER_API_KEY` environment variable or `.env`. It is never written anywhere else.

## Repository layout

| path | what it is |
|---|---|
| `adviceguard/rules.py` | rule layer (part of the system) and the keyword baseline (for comparison only) |
| `adviceguard/classifier.py` | gpt-4o-mini prompt (v2), JSON parsing, confidence from label-token logprobs |
| `adviceguard/pipeline.py` | `guard(sentence)`: rules, model, HOLD threshold, citation; offline and live modes |
| `adviceguard/retrieval.py`, `clause_cards.py` | 20 MAS/FAA clause cards and the TF-IDF citation retriever |
| `adviceguard/detemplate.py` | strips generator habits (particles, openers, disclaimers, invented brand names) |
| `app/app.py` | Streamlit review queue |
| `data/advice_boundary_v1.csv` | 240 synthetic sentences with band, zone and dev/test split |
| `data/labels.csv` | reference labels with the guideline rule that decided each one |
| `data/heldout_real_copy.csv`, `heldout_labels.csv` | 40 real sentences with source URL and retrieval date |
| `data/generation/` | generation prompt, raw generator output, generation spend |
| `labeling/` | guideline, blind 60-item sample, second pass, adjudication, stability script |
| `scripts/make_dataset.py` | rebuilds the dataset from the cached raw generations (`--regenerate` draws a new set) |
| `scripts/run_llm.py` | runs the model over a set and caches every response |
| `scripts/evaluate.py` | all baselines, per-band recall, abstention curve, de-templating, held-out, cost |
| `scripts/build_queue.py` | precomputes the queue and scores the citation layer |
| `results/` | every model output (jsonl), metrics, tables, figure, API spend ledger |

## How the data was made and checked

- **advice_boundary_v1**: 240 sentences written by `anthropic/claude-sonnet-4.6`, a different model family from the classifier, from a grid of 5 bands (plain fact, fact plus comparison, implied suitability, soft recommendation, explicit recommendation) by 3 zones (96 clear-pass, 72 clear-flag, 72 grey). Each cell fixes length, tone, product type and an awkward twist, such as advice wrapped in a disclaimer or information containing the word "recommend". Ids are shuffled so they carry no band information.
- **Reference labels** follow `labeling/guideline.md` (FAA Second Schedule and MAS 2019 guidelines turned into 11 rules). They were committed before any classifier ran; the git history shows the order.
- **Label stability check**: 60 sentences, stratified and weighted towards the grey zone, were labelled a second time in a pass blind to the first one (`labeling/blind_60.csv` has id and text only). Agreement was 59/60, kappa 0.967. The one disagreement (ab171) was adjudicated to FLAG before any classifier ran. Both passes applied the same written guideline, so this measures how well the guideline pins down the label. It does not measure how far two compliance lawyers would agree.
- **Held-out real copy**: 40 sentences quoted verbatim from public Endowus, StashAway and Syfe pages on 2026-09-29, with their URLs. They were not generated, and they are only used for testing.
- **De-templating**: 146 of 240 sentences change when generator habits are stripped. Test scores moved by at most 1.7 points (TF-IDF accuracy 0.867 to 0.875, LLM 0.942 to 0.950), so I found no sign that the models were reading template tells.

## Intended use and non-use

**Intended use**: an internal review aid that holds and ranks outbound chatbot sentences for a qualified compliance reviewer at a Singapore retail investment platform, with a clause citation for each stopped sentence.

**Not for**:
- compliance sign-off, or a legal opinion on whether something is advice;
- judging whether advice is good or suitable;
- replacing a licensed representative;
- sending messages with no human able to review what was stopped;
- other jurisdictions, languages or multi-turn context, which it was not tested on.

## Known limitations

- The benchmark is synthetic. Sentences skew long (131 long, 84 medium, 25 short), and a generator's idea of chatbot language is not a production transcript.
- On real marketing copy, precision is 0.69, below the 0.70 release floor. Most false flags are product-page lines that name a target customer ("Suitable for immediate and near-term cash needs") or make favourable claims about past results. For this reason FLAG goes to the reviewer's queue rather than silently blocking.
- Confidence is poorly calibrated at the top end. Three of the model's nine errors on all 240 sentences had confidence above 0.99, and one missed advice sentence had p_flag of 0.0006. Abstention catches uncertain errors, not confident ones. A weekly random audit of PASS decisions is the control for those.
- Both labelling passes follow one written guideline, and the grey-zone rules (F3, F5) are my reading of MAS guidance, not settled law.
- Single sentences only. Advice split across two sentences, or implied by an earlier turn, is out of scope.
- The HOLD threshold (0.995) was chosen on 120 dev sentences under a 5% hold budget. On the real copy it held 17.5% of sentences. In production the threshold has to be set from the reviewer's daily capacity (see `results/tables.md`, operating points).
- Citation top-1 hit rate is 0.59 against a rule-to-card mapping I wrote myself. Treat the citation as a pointer, not an authority.

## Reproducibility notes

- `scripts/make_dataset.py --regenerate` produces a new draw at temperature 0.9, which would need new reference labels. Without the flag it rebuilds the committed CSV exactly.
- Model outputs are cached. Re-running `run_llm.py` on OpenRouter may route to a different provider, and gpt-4o-mini logprobs can shift slightly between runs.
- Prompt v1 and v2 dev results are both kept (`results/llm_dev_v1.jsonl`, `llm_dev_v2.jsonl`). v2 added two sentences on common mistakes after reading the v1 dev errors; the test half was run once, with v2.
- Total API spend for the project: see `api_spend_total_usd` in `results/metrics.json`.

## Sources

Clause cards summarise public MAS and FAA documents: Financial Advisers Act 2001; MAS Guidelines on Provision of Financial Advisory Service (2019); MAS Notices FAA-N16 and FAA-N03; MAS Guidelines on Provision of Digital Advisory Services (2018); MAS Guidelines on Fair Dealing. The URLs are in `adviceguard/clause_cards.py`. Held-out sentences are short quotations from public web pages, used for evaluation, with sources listed per sentence.
