"""De-templating: strip surface habits of the generator that correlate with
band but do not change the label under the guideline.

What is stripped (all label-preserving by the guideline):
- Singapore colloquial particles and interjections (lah, leh, lor, eh, wah).
  The generator used them more often in recommendation bands.
- Reassurance openers ("Just so you know,", "We want to make sure you have
  the full picture:", "It is important to note that", "Good news is that").
  The generator used them only in fact bands.
- Disclaimers ("Not financial advice, but", "This isn't advice, but", ...).
  Rule F6 says a disclaimer never changes the label, and the generator only
  attached them to advice sentences, so for a bag-of-words model they are an
  answer key.
- Invented fund brand names ("the Meridian Global Bond Trust" becomes
  "the global bond trust"), which the generator reused unevenly across bands.

What is not stripped: pronouns, verbs, numbers. Those carry the meaning the
guideline tests.
"""
from __future__ import annotations

import re

_PARTICLES = re.compile(r"(?:,\s*)?\b(?:lah|leh|lor)\b(?:\s*,)?", re.I)
_INTERJ = re.compile(r"^(?:eh|wah|honestly)[,!]?\s+", re.I)
_OPENERS = re.compile(
    r"^(?:just so you (?:know|have the full picture),?\s*|we want to make sure you have (?:all the facts|the full picture):\s*"
    r"|it is important to note that\s+|good news is that\s+)", re.I)
_DISCLAIMERS = re.compile(
    r"^(?:just to be clear,\s*)?(?:this is not|this isn'?t|not|please note this does not constitute)\s+"
    r"(?:personalised\s+)?(?:financial\s+)?advice,?\s*but,?\s*", re.I)
_PRODUCT_NOUNS = r"(?:ETF|Fund|Portfolio|Trust|REIT|Account|Plan|Unit Trust|Note|Basket)"
_BRAND = re.compile(
    r"\b(?:the\s+)?((?:[A-Z][A-Za-z+]*[a-z][A-Za-z+]*\s+){1,4})(" + _PRODUCT_NOUNS + r")\b")
_KEEP = {"Singapore", "Global", "Gold", "Technology", "Tech", "Equity", "Bond", "Income", "Dividend",
         "Monthly", "Balanced", "Growth", "Cash", "Management", "Managed", "Stock", "Savings",
         "Endowment", "Robo", "Robo-Advisory", "Short-Duration", "Retail", "Conservative", "Core",
         "Select", "Sector", "Commodities", "Fixed", "World", "Blue", "Chip", "Local", "Supplementary",
         "Retirement", "Scheme", "Ordinary", "Special", "CPF", "SRS", "Capital", "Stable", "Reserve",
         "Tracker", "Flexi", "Plus", "Government", "Singapore-listed", "Thematic", "Deposit"}


def _debrand(m: re.Match) -> str:
    words = m.group(1).split()
    kept = [w for w in words if w in _KEEP]
    if len(kept) == len(words):
        return m.group(0)
    noun = m.group(2) if m.group(2) in ("ETF", "REIT") else m.group(2).lower()
    return "the " + " ".join(kept + [noun])


def detemplate(text: str) -> str:
    t = text.strip()
    for _ in range(2):
        t = _INTERJ.sub("", t)
        t = _OPENERS.sub("", t)
        t = _DISCLAIMERS.sub("", t)
    t = _PARTICLES.sub("", t)
    t = _BRAND.sub(_debrand, t)
    t = re.sub(r"\bthe the\b", "the", t, flags=re.I)
    t = re.sub(r"\s+([,.;!?])", r"\1", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" ,")
    return t[:1].upper() + t[1:] if t else t
