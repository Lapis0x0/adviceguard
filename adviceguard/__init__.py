"""AdviceGuard: checks outbound robo-advisor chatbot sentences for financial-advice language.

Package map (read in this order):
    pipeline.py      guard(sentence) -> PASS / FLAG / HOLD; the only entry point the app needs
    rules.py         rule layer (explicit advice patterns) and the keyword baseline
    classifier.py    gpt-4o-mini prompt, JSON parsing, confidence from label-token logprobs
    llm.py           minimal OpenRouter client; reads OPENROUTER_API_KEY from the environment
    retrieval.py     TF-IDF citation layer over the clause cards
    clause_cards.py  20 MAS/FAA clause cards with sources
    detemplate.py    strips generator habits, used only for the leakage check

See README.md to run it, docs/PRODUCT.md for the product view, EVALS.md and data/README.md
for how the evaluation and data were built.
"""
