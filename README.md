# AdviceGuard

AdviceGuard checks each outbound sentence from a retail investment chatbot and returns PASS, FLAG or HOLD before it is sent, so a compliance officer reviews a ranked queue instead of sampling transcripts after the fact.

Work in progress. This README is completed at the end of the build.

## Data so far

- `data/advice_boundary_v1.csv`: 240 synthetic chatbot sentences across five bands. Rebuild with `python scripts/make_dataset.py` (no API key needed; it reads the committed raw generations). The generation prompt is `data/generation/generation_prompt.md`.
- `data/labels.csv`: reference labels, written against `labeling/guideline.md` and committed before any classifier was run.
