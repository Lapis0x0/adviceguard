"""AdviceGuard review queue for a compliance officer.

    streamlit run app/app.py

Offline replay is the default: decisions come from the committed results, so
the app opens and demonstrates without an API key. If OPENROUTER_API_KEY is
set, the "Check a sentence" tab can call the model live.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from adviceguard.pipeline import TAU, guard, live_available  # noqa: E402

st.set_page_config(page_title="AdviceGuard review queue", layout="wide")

DECISION_ORDER = {"HOLD": 0, "FLAG": 1, "PASS": 2}
BADGE = {"HOLD": "🟠 HOLD", "FLAG": "🔴 FLAG", "PASS": "🟢 PASS"}


@st.cache_data
def load_queue() -> pd.DataFrame:
    rows = [json.loads(l) for l in (REPO / "results" / "queue.jsonl").read_text().splitlines()]
    q = pd.DataFrame(rows)
    # risk score for ordering: HOLD first (a message is waiting), then FLAG, then PASS by p_flag
    q["p_sort"] = q.p_flag.fillna(1.0)
    q["order"] = q.decision.map(DECISION_ORDER)
    return q.sort_values(["order", "p_sort"], ascending=[True, False]).reset_index(drop=True)


def show_item(r: dict, key: str) -> None:
    if r.get("p_flag") is not None:
        p = f"p(advice) = {r['p_flag']:.3f}"
    else:
        p = "rule match" if str(r.get("source", "")).startswith("rule") else "no model score"
    with st.container(border=True):
        c1, c2 = st.columns([1, 5])
        c1.markdown(f"**{BADGE[r['decision']]}**")
        c1.caption(p)
        c2.markdown(f"> {r['sentence'] if 'sentence' in r else r['text']}")
        c2.caption(f"Why: {r.get('reason') or ''}  ·  decided by {r.get('source')}")
        cit = r.get("citation")
        if isinstance(cit, dict) and cit.get("card_id"):
            c2.caption(f"Nearest rule: **{cit['title']}** ({cit['source']}) [{cit['card_id']}]({cit['url']})")


mode = "Live (API key found)" if live_available() else "Offline replay (no API key)"
st.title("AdviceGuard")
st.caption(f"Outbound chatbot sentences checked for financial-advice language before sending. Mode: **{mode}**. "
           f"HOLD threshold: confidence below {TAU}.")

tab_q, tab_c, tab_e = st.tabs(["Review queue", "Check a sentence", "How well it works"])

with tab_q:
    q = load_queue()
    c1, c2, c3 = st.columns(3)
    sets = c1.multiselect("Source", sorted(q.set.unique()), default=["synthetic-test", "real-copy"])
    decs = c2.multiselect("Decision", ["HOLD", "FLAG", "PASS"], default=["HOLD", "FLAG"])
    show_ref = c3.toggle("Show reference label (evaluation only)", value=False)
    v = q[q.set.isin(sets) & q.decision.isin(decs)]
    m1, m2, m3 = st.columns(3)
    m1.metric("Held, waiting for you", int((v.decision == "HOLD").sum()))
    m2.metric("Blocked (FLAG)", int((v.decision == "FLAG").sum()))
    m3.metric("Sent (PASS)", int((v.decision == "PASS").sum()))
    for i, r in v.head(60).iterrows():
        show_item(r.to_dict(), f"q{i}")
        if show_ref:
            st.caption(f"reference label: {r.reference_label} ({r.reference_rule})")
    if len(v) > 60:
        st.caption(f"Showing the 60 highest-risk of {len(v)}.")

with tab_c:
    st.write("Type or paste one chatbot sentence.")
    examples = ["Now is the time to buy the PureGold ETF.",
                "Your questionnaire flagged income priority; this fund pays monthly distributions.",
                "The fund's total expense ratio is 0.45% a year."]
    ex = st.selectbox("or pick an example", [""] + examples)
    s = st.text_area("Sentence", value=ex, height=80)
    live = st.toggle("Allow a live model call", value=live_available(), disabled=not live_available(),
                     help="Needs OPENROUTER_API_KEY. Without it, uncached sentences that no rule catches are held.")
    if st.button("Check", type="primary") and s.strip():
        r = guard(s, allow_live=live)
        show_item(r, "check")
        if r["source"] == "no model available":
            st.info("No model in offline mode, so the guard fails closed: this sentence is held for a person to review, not passed.")

with tab_e:
    img = REPO / "results" / "abstention_curve.png"
    if img.exists():
        st.image(str(img), width=560)
    st.markdown((REPO / "results" / "tables.md").read_text())
