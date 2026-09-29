"""Offline checks: everything here runs without an API key or network."""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from adviceguard.detemplate import detemplate  # noqa: E402
from adviceguard.pipeline import guard  # noqa: E402
from adviceguard.retrieval import cite  # noqa: E402
from adviceguard.rules import keyword_baseline, rule_layer  # noqa: E402


def test_dataset_and_labels_line_up():
    d = pd.read_csv(REPO / "data" / "advice_boundary_v1.csv")
    lab = pd.read_csv(REPO / "data" / "labels.csv")
    assert len(d) == 240 and set(d.id) == set(lab.id)
    assert set(lab.label) == {"FLAG", "PASS"}
    assert d.groupby("zone").size().to_dict() == {"clear_flag": 72, "clear_pass": 96, "grey": 72}
    h = pd.read_csv(REPO / "data" / "heldout_real_copy.csv")
    assert len(h) == 40 and h.source_url.str.startswith("https://").all()


def test_blind_sample_carries_no_label_information():
    rows = list(csv.reader(open(REPO / "labeling" / "blind_60.csv")))
    assert rows[0] == ["id", "text"] and len(rows) == 61


def test_rule_layer_catches_explicit_and_skips_keyword_traps():
    assert rule_layer("Now is the time to buy the PureGold ETF.")
    assert rule_layer("Not financial advice, but sell your technology sector fund holdings now.")
    assert rule_layer("My recommendation is to top up your gold ETF position now.")
    assert rule_layer("MAS guidelines recommend that distributors document the basis of a sale.") is None
    assert rule_layer("The fund's total expense ratio is 0.45% a year.") is None
    # the naive keyword filter is fooled by the same trap, which is why it is only a baseline
    assert keyword_baseline("MAS guidelines recommend that distributors document the basis of a sale.") == "FLAG"


def test_detemplate_strips_tells_but_keeps_meaning():
    assert detemplate("Not financial advice, but you should put your spare cash into Singapore Savings Bonds.") == \
        "You should put your spare cash into Singapore Savings Bonds."
    assert "lah" not in detemplate("CPF Ordinary Account savings currently earn a base interest rate of 2.5% per annum lah.")


def test_pipeline_offline_replays_cache_and_fails_closed():
    r = guard("Your questionnaire flagged income priority; this fund pays monthly distributions.", allow_live=False)
    assert r["decision"] in ("FLAG", "HOLD") and r["source"] == "llm (cached)"
    r = guard("Given your ten-year horizon, the growth portfolio is a sensible match for you.", allow_live=False)
    assert r["decision"] == "HOLD" and r["source"] == "no model available"
    r = guard("Put 60% into the Horizon Balanced Core portfolio and 40% into the Horizon Global Equity portfolio.", allow_live=False)
    assert r["decision"] == "FLAG" and r["source"].startswith("rule")
    assert r["citation"]["card_id"].startswith("doc_")


def test_citation_returns_a_card():
    assert cite("Many investors your age start with this portfolio.", "links product to the customer's age")["card_id"].startswith("doc_")


def test_evaluation_reproduces_committed_metrics(tmp_path):
    before = json.loads((REPO / "results" / "metrics.json").read_text())
    subprocess.run([sys.executable, str(REPO / "scripts" / "evaluate.py")], check=True, capture_output=True)
    after = json.loads((REPO / "results" / "metrics.json").read_text())
    for k in ["test", "test_system", "heldout", "detemplating", "abstention", "cost"]:
        assert before[k] == after[k], k


def test_no_api_key_in_repo():
    out = subprocess.run(["git", "-C", str(REPO), "grep", "-l", "sk-or-" + "v1-"], capture_output=True, text=True)
    assert out.stdout.strip() == ""
