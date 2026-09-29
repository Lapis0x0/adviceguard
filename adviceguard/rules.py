"""Deterministic layers.

1. RULE LAYER (part of the system): a short list of explicit advice
   constructions. A match means FLAG with no model call. The patterns were
   written against the dev split only and are kept narrow on purpose: this
   layer must be close to 100% precise, because nothing downstream checks it.

2. KEYWORD BASELINE (not part of the system): the naive filter a team would
   write first, flagging any sentence containing an advice-sounding word.
   It exists to be measured against.
"""
from __future__ import annotations

import re

# Leading material that does not change meaning: interjections and
# disclaimers ("Not financial advice, but ..."). Stripped before the
# sentence-initial imperative patterns are tested.
_LEAD = re.compile(
    r"^(?:(?:eh|wah|lah|ok|okay|honestly|so)[,!]?\s+)*"
    r"(?:(?:this is |it'?s )?not (?:personalised )?(?:financial )?advice,?\s*but,?\s*)?",
    re.I,
)

EXPLICIT_PATTERNS = [
    ("i_recommend", r"\b(?:i|we)(?:'d| would)?\s+(?:strongly\s+|genuinely\s+|really\s+)?(?:recommend|suggest)\b"),
    ("my_recommendation", r"\bmy recommendation is\b"),
    ("now_is_the_time", r"\bnow is the (?:time|moment) to\b"),
    ("you_should_act", r"\byou should (?:definitely |really )?(?:buy|sell|put|move|allocate|invest|switch|increase|reduce|exit|hold|avoid)\b"),
    ("put_percent", r"\bput (?:\d{1,3}|at least half)%?\s*(?:of your [\w\s-]+?)?\s*(?:into|in)\b"),
    ("just_go_buy", r"\bjust (?:go (?:ahead )?and |go )?(?:buy|put|hold|go with)\b"),
    ("please_dont", r"^please don'?t (?:leave|buy|sell|put|touch)\b"),
    ("imperative_start", r"^(?:just\s+)?(?:go\s+(?:ahead\s+and\s+)?)?(?:buy|sell|put|move|switch|transfer|max out|top up|avoid|stay away from|don'?t (?:touch|open|buy|park))\b"),
]
_COMPILED = [(n, re.compile(p, re.I)) for n, p in EXPLICIT_PATTERNS]


def rule_layer(sentence: str) -> str | None:
    """Return the name of the first matching explicit pattern, or None."""
    s = sentence.strip()
    core = _LEAD.sub("", s)
    for name, pat in _COMPILED:
        if name == "imperative_start":
            if pat.search(core):
                return name
        elif pat.search(s):
            return name
    return None


KEYWORDS = ["recommend", "suggest", "should", "consider", "suit", "fit", "buy", "sell",
            "switch", "allocate", "advice", "best", "better", "worth"]
_KW = re.compile(r"\b(?:" + "|".join(KEYWORDS) + r")\w*", re.I)


def keyword_baseline(sentence: str) -> str:
    return "FLAG" if _KW.search(sentence) else "PASS"
