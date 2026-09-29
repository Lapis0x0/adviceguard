"""AdviceGuard: one outbound sentence in, PASS / FLAG / HOLD out.

    rule layer  -> explicit construction matched: FLAG, no model call
    LLM layer   -> gpt-4o-mini, label-token confidence p_flag
    threshold   -> confidence max(p, 1-p) below TAU: HOLD for human review
    citation    -> FLAG and HOLD get the top-1 MAS/FAA clause card

Modes
- offline (default without a key): LLM results are replayed from the cached
  runs in results/. A sentence that is not in the cache and does not hit a
  rule is HELD. The guard fails closed: no model means no automatic PASS.
- live (OPENROUTER_API_KEY set): uncached sentences are sent to the model.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from . import llm
from .rules import rule_layer

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results"
TAU = 0.995  # chosen on dev under a 5% HOLD budget, see scripts/evaluate.py


@lru_cache(maxsize=1)
def _cache() -> dict:
    c = {}
    for f in sorted(RESULTS.glob("llm_*_v2.jsonl")):
        for line in f.read_text().splitlines():
            r = json.loads(line)
            c.setdefault(r["text"].strip(), r)
    return c


def live_available() -> bool:
    return llm.has_key()


def guard(sentence: str, tau: float = TAU, allow_live: bool = True, with_citation: bool = True) -> dict:
    s = sentence.strip()
    out = {"sentence": s, "tau": tau}
    hit = rule_layer(s)
    if hit:
        out.update(decision="FLAG", source=f"rule:{hit}", p_flag=None, reason="Explicit advice construction matched by the rule layer.")
    else:
        r = _cache().get(s)
        src = "llm (cached)"
        if r is None and allow_live and live_available():
            from .classifier import classify
            r = classify(s, ledger=RESULTS / "api_spend_live.jsonl", tag="live")
            src = "llm (live)"
        if r is None:
            out.update(decision="HOLD", source="no model available", p_flag=None,
                       reason="Offline mode and no rule matched: held for review rather than passed.")
        else:
            p = r["p_flag"]
            conf = max(p, 1 - p)
            dec = "HOLD" if conf < tau else ("FLAG" if p >= 0.5 else "PASS")
            out.update(decision=dec, source=src, p_flag=p, reason=r.get("reason", ""), llm_rule=r.get("rule", ""))
    if with_citation and out["decision"] in ("FLAG", "HOLD"):
        try:
            from .retrieval import RULE_HIT_REASON, cite
            reason = RULE_HIT_REASON if out["source"].startswith("rule") else out.get("reason", "")
            out["citation"] = cite(s, reason)
        except Exception as e:  # embedding model not downloadable offline: keep the decision, drop the citation
            out["citation"] = {"error": f"citation unavailable: {type(e).__name__}"}
    return out
