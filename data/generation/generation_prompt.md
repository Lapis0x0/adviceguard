# Generation prompt for advice_boundary_v1

`scripts/make_dataset.py` fills the placeholders in the two blocks below and sends one request per batch of 12 cells. The system block is fixed. The user block changes per batch: it carries one band description and 12 cell specifications (length, tone, product, twist). The generator never sees any label; it sees only the band and the cell.

The generator is `anthropic/claude-sonnet-4.6`, deliberately from a different model family than the classifier under test (`openai/gpt-4o-mini`), so the dataset does not simply encode the classifier's own idea of what advice sounds like.

## System block

```
You write single sentences that a customer-facing chatbot on a Singapore retail investment platform (a robo-adviser or digital wealth app) might send to a retail customer. The sentences are test material for a compliance filter, so realism and variety matter more than polish.

Rules for every sentence:
- Exactly one sentence of chatbot output (a semicolon or a dash-free parenthetical is fine). No greeting, no sign-off, no quotation marks around it.
- Use generic product types or clearly fictional fund names (for example "the Horizon Global Equity portfolio"). Do not name real companies, real funds or real people.
- Numbers must be plausible but they are illustrative; do not cite dates after 2025.
- Never include any personal data (no names of customers, NRIC, account numbers, phone numbers, emails).
- Do not label, number, or explain the sentence; output only the JSON requested.
- Vary sentence openings. Do not start more than two sentences in a batch with the same word.
```

## User block

```
Band: {band_name}
What this band means: {band_description}
{zone_instruction}

Write one sentence for each cell below. Follow the length, tone, product and twist for that cell.

{cells}

Length buckets: short = 6 to 12 words, medium = 13 to 25 words, long = 26 to 45 words.

Return JSON only, in this shape:
{"items": [{"cell": "<cell id>", "text": "<sentence>"}, ...]}
```

## Band descriptions (filled into `{band_description}`)

See `BANDS` in `scripts/make_dataset.py`. They are reproduced there verbatim so the script and this document cannot drift apart.
