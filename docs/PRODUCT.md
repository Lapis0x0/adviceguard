# AdviceGuard: product documentation

## Persona

**Aisha** is the only compliance officer at a 40-person robo-advisory firm in Singapore. The firm's chatbot answers several hundred customer sessions a day. Today she spot-checks last week's transcripts at random, late at night, after the messages have already gone out. She knows the Financial Advisers Act well. She has never read a model confidence score, so every decision she sees needs a plain reason and a rule she can look up.

What changes for her: instead of sampling old transcripts, she works a ranked queue. Sentences the system is unsure about are held before they are sent, and every stopped sentence comes with a one-line reason and the nearest MAS/FAA clause.

## Input and output

| | |
|---|---|
| **Input** | One outbound chatbot sentence, in English, before it is sent to a customer. |
| **Output** | A decision: **PASS** (send), **FLAG** (stop, looks like regulated advice) or **HOLD** (stop, the model is not confident; a person decides). Plus: which layer decided, the model's probability that the sentence is advice, a one-line reason, and for FLAG and HOLD the nearest MAS/FAA clause card. |
| **Where it shows up** | The Streamlit review queue (`app/app.py`): HOLD first, then FLAG, ordered by risk. A second tab checks one sentence on demand. |

Example:

| input sentence | decision | decided by | reason |
|---|---|---|---|
| "Now is the time to buy the PureGold ETF." | FLAG | rule layer | explicit call to action |
| "Given your ten-year horizon, the growth portfolio is a sensible match for you." | FLAG | gpt-4o-mini, p = 1.00 | links a product to the customer's own horizon |
| "The fund's total expense ratio is 0.45% a year." | PASS | gpt-4o-mini, p = 0.00 | an objective, checkable fact |

## Architecture

```
                         ┌───────────────────────────────────────────────┐
  chatbot sentence ────► │ 1. RULE LAYER            adviceguard/rules.py │
                         │    8 regex patterns for explicit advice       │
                         └──────────────┬───────────────────┬────────────┘
                                 match  │                   │ no match
                                        ▼                   ▼
                                     FLAG   ┌──────────────────────────────────────────────┐
                                            │ 2. LLM LAYER          adviceguard/classifier │
                                            │    gpt-4o-mini via OpenRouter (rented)       │
                                            │    temperature 0, JSON out, label-token      │
                                            │    logprobs → p(advice)                      │
                                            └──────────────────┬───────────────────────────┘
                                                               ▼
                                            ┌──────────────────────────────────────────────┐
                                            │ 3. HOLD THRESHOLD     adviceguard/pipeline   │
                                            │    confidence < 0.995 → HOLD                 │
                                            │    else FLAG if p ≥ 0.5, PASS otherwise      │
                                            └──────────────────┬───────────────────────────┘
                                                               ▼  FLAG / HOLD only
                                            ┌──────────────────────────────────────────────┐
                                            │ 4. CITATION           adviceguard/retrieval  │
                                            │    TF-IDF over 20 MAS/FAA clause cards       │
                                            └──────────────────┬───────────────────────────┘
                                                               ▼
                                            ┌──────────────────────────────────────────────┐
                                            │ 5. REVIEW QUEUE       app/app.py (Streamlit) │
                                            │    HOLD first, then FLAG, by risk            │
                                            └──────────────────────────────────────────────┘
```

What is mine and what is rented:

| part | own or rent | why |
|---|---|---|
| rules, threshold, orchestration (~70 lines) | own | specific to this problem; a framework would cost more to learn than to write |
| gpt-4o-mini | rent (OpenRouter) | commodity capability; the cheapest model that read grey-zone sentences well in my A1 tests |
| clause cards and retriever | own (scikit-learn TF-IDF) | 20 short documents do not need a vector database |
| dataset, labels, evaluation | own | the part nobody else can supply for this problem |
| review queue UI | own (Streamlit) | ordering and wording are specific to Aisha |

**Offline mode** is the default: with no API key, the app replays committed model outputs, and a new sentence that no rule catches is held (the system fails closed, never open).

## Metrics: targeted and reached

Targets were set in the problem statement. Results are on the 120-sentence test half, which was not used for any tuning, unless marked otherwise.

| metric | target | reached | met? |
|---|---|---|---|
| Grey-zone recall (FLAG or HOLD counts as stopped) | ≥ 0.80 | 22/23 = 0.96 | yes |
| Overall recall on the flag class | ≥ 0.85 | 58/59 = 0.98 | yes |
| Precision of stopped sentences (release condition) | ≥ 0.70 | 0.97 | yes |
| Precision on 40 real sentences from Endowus, StashAway, Syfe | ≥ 0.70 | 0.69 (model alone) | **no, just under** |
| Recall on the 11 advice-like real sentences | n/a | 11/11 | |
| HOLD rate (budget set on dev) | ≤ 5% on dev | 7.5% on test, 17.5% on real copy | over budget off-dev |
| Share of held sentences the model would have got wrong | report | 6 of 9 on test | |
| Cost per 1,000 sentences | report | $0.092 with the rule layer | |
| Latency per model call | report | p50 1.9 s, p95 2.5 s | |
| Label stability (two blind passes, 60 sentences) | report | 59/60 agree, kappa 0.967 | |

The unmet real-copy target is why the recommended deployment is a review queue, not an automatic block. Full tables are in `results/tables.md`; how each number is computed is in `EVALS.md`.
