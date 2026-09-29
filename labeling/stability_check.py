"""Label stability check: compare two independent, mutually blind labelling
passes on the same 60 sentences and report agreement.

Pass 1 is the reference pass (data/labels.csv as first committed, recovered
from labeling/adjudication.csv for any row changed afterwards). Pass 2 is
labeling/pass2_60.csv, produced from labeling/guideline.md and
labeling/blind_60.csv only.

    python labeling/stability_check.py
"""
import csv
import json
from collections import Counter
from pathlib import Path

from sklearn.metrics import cohen_kappa_score

REPO = Path(__file__).resolve().parent.parent
ref = {r["id"]: r for r in csv.DictReader(open(REPO / "data" / "labels.csv"))}
adj = {r["id"]: r for r in csv.DictReader(open(REPO / "labeling" / "adjudication.csv"))}
p2 = {r["id"]: r for r in csv.DictReader(open(REPO / "labeling" / "pass2_60.csv"))}
data = {r["id"]: r for r in csv.DictReader(open(REPO / "data" / "advice_boundary_v1.csv"))}

ids = sorted(p2)
p1_lab = [adj[i]["reference_label"] if i in adj else ref[i]["label"] for i in ids]
p2_lab = [p2[i]["label"] for i in ids]
agree = sum(a == b for a, b in zip(p1_lab, p2_lab))
kappa = cohen_kappa_score(p1_lab, p2_lab)
by_zone = {}
for z in ["clear_pass", "clear_flag", "grey"]:
    zi = [k for k, i in enumerate(ids) if data[i]["zone"] == z]
    by_zone[z] = {"n": len(zi), "agree": sum(p1_lab[k] == p2_lab[k] for k in zi)}
low1 = {i for i in ids if ref[i]["confidence"] == "low"}
low2 = {i for i in ids if p2[i]["confidence"] == "low"}
out = {
    "n": len(ids),
    "agree": agree,
    "percent_agreement": round(agree / len(ids), 4),
    "cohen_kappa": round(kappa, 4),
    "pass1_counts": dict(Counter(p1_lab)),
    "pass2_counts": dict(Counter(p2_lab)),
    "agreement_by_zone": by_zone,
    "low_confidence_pass1": len(low1),
    "low_confidence_pass2": len(low2),
    "low_confidence_both": len(low1 & low2),
    "disagreements": [
        {"id": i, "text": data[i]["text"], "pass1": adj[i]["reference_label"], "pass2": p2[i]["label"],
         "final": adj[i]["final_label"], "reason": adj[i]["reason"]}
        for i in ids if (adj[i]["reference_label"] if i in adj else ref[i]["label"]) != p2[i]["label"]
    ],
}
(REPO / "results").mkdir(exist_ok=True)
(REPO / "results" / "label_stability.json").write_text(json.dumps(out, indent=2))
print(json.dumps({k: v for k, v in out.items() if k != "disagreements"}, indent=2))
for d in out["disagreements"]:
    print(f"{d['id']}: pass1 {d['pass1']} / pass2 {d['pass2']} -> {d['final']}")
