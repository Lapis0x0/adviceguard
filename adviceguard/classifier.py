"""LLM layer: gpt-4o-mini via OpenRouter, temperature 0, JSON output.

The label is the first field of the JSON object, so the first content token
after `{"label":"` carries the decision. Confidence is read from that token's
log-probabilities (top 5 alternatives): p_flag = P(FLAG) / (P(FLAG) + P(PASS)).
If the provider returns no logprobs, p_flag falls back to 1.0 or 0.0 from the
parsed label and the result is marked `conf_source = "none"`, so a missing
confidence can never silently look like a confident one.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from . import llm

MODEL = "openai/gpt-4o-mini"
PROMPT_VERSION = "v2"

SYSTEM_PROMPT = """You are a compliance filter for a Singapore retail investment platform. You read ONE sentence that the platform's chatbot is about to send to a retail customer and decide whether it gives financial advice.

FLAG the sentence if a reasonable retail customer could read it as the platform telling them what to do with their money, or that something fits them:
F1 An opinion on the merits of a specific product (good or bad idea to buy, sell, hold, switch, avoid), including a favourable forward-looking claim about it.
F2 Personal suitability: links a product, class of products or allocation to the customer's own circumstances (profile, age, horizon, goal, tax, something they said) in a way that implies fit or misfit. Includes placing the customer's profile next to a matching product feature, and "investors like you / your age" framing.
F3 Points the customer at a class of investment products to consider or look into, usually conditioned on their priorities.
F4 An action or allocation instruction (buy, sell, top up, trim, switch, hold, avoid, percentages), firm or hedged.
F5 Suitability language about a named product for a type of investor ("suits investors who", "better matched to").
F6 A disclaimer such as "not financial advice" does not change any of the above.

PASS the sentence if it gives information:
P1 Objective, checkable facts: fees, rates, limits, past returns, how a process works, eligibility, risks, what a regulation requires. Advice words used factually stay PASS.
P2 Factual comparisons, including checkable comparative words (cheaper, more liquid, higher past return), unless they add a forward-looking merit claim or suitability language.
P3 Neutral design-target statements ("designed for investors seeking income") not tied to the reader.
P4 Generic education not tied to the reader and not pointing them at a product or class.
P5 Referral to tools or a licensed representative, prompts to reflect on their own needs, or saying suitability depends on circumstances without concluding.

Two common mistakes to avoid:
- Mentioning the customer ("you", "your profile") is not enough for F2. It is F2 only if the sentence implies that a product or allocation fits or does not fit them. A question asking them to check their own needs, or a statement that suitability depends on their circumstances, is P5.
- Stating a product's trade-off, or which checkable feature matters to which kind of investor (liquidity, lock-in, certainty), is P2. It becomes F5 only with fit words such as "suits", "right for", "better matched".

Return only JSON: {"label": "FLAG" or "PASS", "rule": "<rule code>", "reason": "<one short sentence>"}"""


def build_messages(sentence: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Sentence: {sentence}"},
    ]


def _label_probs(logprobs: list[dict] | None) -> tuple[float | None, str]:
    """Find the token that starts the label value and turn its top-k
    alternatives into P(FLAG) normalised over FLAG and PASS."""
    if not logprobs:
        return None, "none"
    for tok in logprobs:
        t = tok.get("token", "").strip().strip('"').upper()
        if t.startswith(("FL", "PA")):
            p_f = p_p = 0.0
            for alt in tok.get("top_logprobs") or [{"token": tok["token"], "logprob": tok["logprob"]}]:
                a = alt["token"].strip().strip('"').upper()
                if a.startswith("FL"):
                    p_f += math.exp(alt["logprob"])
                elif a.startswith("PA"):
                    p_p += math.exp(alt["logprob"])
            if p_f + p_p == 0:
                return None, "none"
            return p_f / (p_f + p_p), "logprobs"
    return None, "none"


def classify(sentence: str, ledger: Path | None = None, tag: str = "") -> dict:
    res = llm.chat(
        MODEL,
        build_messages(sentence),
        temperature=0.0,
        max_tokens=120,
        response_format={"type": "json_object"},
        logprobs=True,
        top_logprobs=5,
        seed=6201,
        ledger=ledger,
        tag=tag,
    )
    try:
        parsed = json.loads(res["content"])
        label = str(parsed.get("label", "")).upper()
    except json.JSONDecodeError:
        parsed, label = {}, ""
    if label not in ("FLAG", "PASS"):
        label = "PARSE_ERROR"
    p_flag, conf_source = _label_probs(res["logprobs"])
    if p_flag is None:
        p_flag = 1.0 if label == "FLAG" else 0.0 if label == "PASS" else 0.5
    return {
        "llm_label": label,
        "p_flag": round(p_flag, 6),
        "conf_source": conf_source,
        "rule": parsed.get("rule", ""),
        "reason": parsed.get("reason", ""),
        "model": res["model"],
        "provider": res["provider"],
        "prompt_tokens": res["prompt_tokens"],
        "completion_tokens": res["completion_tokens"],
        "cost_usd": res["cost_usd"],
        "latency_ms": res["latency_ms"],
        "prompt_version": PROMPT_VERSION,
    }
