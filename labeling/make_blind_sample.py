"""Draw the 60-item stratified sample for the label stability check.

The sample over-weights the grey zone (24 of 60, against 72 of 240 in the full
set) because that is where a second, independent labelling pass is most
likely to disagree. Within each zone, items are drawn in proportion to band.
The output file holds only id and text: no band, zone, split or label.

    python labeling/make_blind_sample.py
"""
import csv
import random
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEED = 6201
QUOTA = {  # (band, zone): n
    ("plain_fact", "clear_pass"): 11,
    ("fact_comparison", "clear_pass"): 7,
    ("fact_comparison", "grey"): 8,
    ("implied_suitability", "grey"): 8,
    ("soft_recommendation", "grey"): 8,
    ("implied_suitability", "clear_flag"): 3,
    ("soft_recommendation", "clear_flag"): 3,
    ("explicit_recommendation", "clear_flag"): 12,
}

rows = list(csv.DictReader(open(REPO / "data" / "advice_boundary_v1.csv")))
rng = random.Random(SEED)
picked = []
for key, n in QUOTA.items():
    pool = sorted((r for r in rows if (r["band"], r["zone"]) == key), key=lambda r: r["id"])
    picked += rng.sample(pool, n)
rng.shuffle(picked)
assert len(picked) == 60
with open(REPO / "labeling" / "blind_60.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "text"])
    for r in picked:
        w.writerow([r["id"], r["text"]])
print("wrote labeling/blind_60.csv")
