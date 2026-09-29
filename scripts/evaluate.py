"""Score every model and the full system from committed files. No API key needed.

    python scripts/evaluate.py

Reads data/, labels and the cached LLM outputs in results/llm_*_v2.jsonl.
Writes results/metrics.json, results/tables.md, results/abstention_curve.png,
results/system_predictions.csv.

Split: the dev half (120) was used to write the rule patterns, iterate the
prompt (v1 -> v2), train TF-IDF and pick the HOLD threshold. Every headline
number below is on the test half (120), which none of those steps touched.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from adviceguard.detemplate import detemplate  # noqa: E402
from adviceguard.rules import keyword_baseline, rule_layer  # noqa: E402

RES = REPO / "results"
PV = "v2"
HOLD_BUDGET = 0.05  # at most 5% of dev traffic may be held for review
PRICE_IN, PRICE_OUT = 0.15 / 1e6, 0.60 / 1e6  # openai/gpt-4o-mini on OpenRouter, USD per token
BAND_ORDER = ["plain_fact", "fact_comparison", "implied_suitability", "soft_recommendation", "explicit_recommendation"]


def load() -> pd.DataFrame:
    d = pd.read_csv(REPO / "data" / "advice_boundary_v1.csv").merge(
        pd.read_csv(REPO / "data" / "labels.csv")[["id", "label", "rule"]].rename(columns={"rule": "ref_rule"}), on="id")
    d["y"] = (d.label == "FLAG").astype(int)
    d["text_dt"] = d.text.map(detemplate)
    llm = pd.read_json(RES / f"llm_all_{PV}.jsonl", lines=True)[["id", "llm_label", "p_flag", "rule", "reason", "prompt_tokens", "completion_tokens", "cost_usd", "latency_ms"]]
    llm_dt = pd.read_json(RES / f"llm_detemplated_{PV}.jsonl", lines=True)[["id", "llm_label", "p_flag"]].rename(
        columns={"llm_label": "llm_label_dt", "p_flag": "p_flag_dt"})
    return d.merge(llm, on="id").merge(llm_dt, on="id")


def prf(y, pred) -> dict:
    y, pred = np.asarray(y), np.asarray(pred)
    tp = int(((pred == 1) & (y == 1)).sum()); fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum()); tn = int(((pred == 0) & (y == 0)).sum())
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"n": len(y), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "accuracy": round((tp + tn) / len(y), 4), "precision": round(p, 4), "recall": round(r, 4),
            "f1": round(2 * p * r / (p + r), 4) if p + r else 0.0, "block_rate": round((tp + fp) / len(y), 4)}


def by_band(df: pd.DataFrame, col: str) -> dict:
    """Recall on FLAG items per band and per zone; false-positive rate on PASS items per band."""
    out = {}
    for b in BAND_ORDER:
        s = df[df.band == b]
        f, p = s[s.y == 1], s[s.y == 0]
        out[b] = {"n_flag": len(f), "caught": int(f[col].sum()), "recall": round(f[col].mean(), 4) if len(f) else None,
                  "n_pass": len(p), "false_flags": int(p[col].sum())}
    for z in ["clear_flag", "grey"]:
        f = df[(df.zone == z) & (df.y == 1)]
        out[f"zone:{z}"] = {"n_flag": len(f), "caught": int(f[col].sum()), "recall": round(f[col].mean(), 4)}
    g = df[(df.zone == "grey") & (df.y == 0)]
    out["zone:grey_pass"] = {"n_pass": len(g), "false_flags": int(g[col].sum())}
    return out


def tfidf_model(train_text, train_y):
    best = None
    for c in [0.3, 1, 3, 10, 30]:
        pipe = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1), LogisticRegression(C=c, max_iter=5000))
        s = cross_val_score(pipe, train_text, train_y, cv=StratifiedKFold(5, shuffle=True, random_state=0), scoring="f1").mean()
        if best is None or s > best[0]:
            best = (s, c)
    pipe = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1), LogisticRegression(C=best[1], max_iter=5000))
    return pipe.fit(train_text, train_y), best[1]


def system_decisions(df: pd.DataFrame, tau: float, pcol="p_flag", textcol="text") -> pd.Series:
    rule = df[textcol].map(rule_layer)
    conf = np.maximum(df[pcol], 1 - df[pcol])
    llm_dec = np.where(conf < tau, "HOLD", np.where(df[pcol] >= 0.5, "FLAG", "PASS"))
    return pd.Series(np.where(rule.notna(), "FLAG", llm_dec), index=df.index)


def system_metrics(df: pd.DataFrame, dec: pd.Series) -> dict:
    y = df.y.values
    stopped = dec.isin(["FLAG", "HOLD"]).values
    flag = (dec == "FLAG").values
    hold = (dec == "HOLD").values
    return {
        "n": len(df),
        "recall_stopped_before_send": round(stopped[y == 1].mean(), 4),
        "auto_flag_precision": round(y[flag].mean(), 4) if flag.any() else None,
        "stopped_precision": round(y[stopped].mean(), 4),
        "flag_rate": round(flag.mean(), 4),
        "hold_rate": round(hold.mean(), 4),
        "block_rate": round(stopped.mean(), 4),
        "missed_flags": df.id[(y == 1) & ~stopped].tolist(),
        "clear_pass_stopped": df.id[(df.zone == "clear_pass").values & stopped].tolist(),
        "held_ids": df.id[hold].tolist(),
        "held_would_be_wrong": int(((dec == "HOLD").values & ((df.p_flag >= 0.5).astype(int).values != y)).sum()),
    }


def abstention_curve(df: pd.DataFrame, taus) -> list[dict]:
    conf = np.maximum(df.p_flag, 1 - df.p_flag).values
    wrong = ((df.p_flag >= 0.5).astype(int).values != df.y.values)
    rows = []
    for t in taus:
        ab = conf < t
        rows.append({"tau": float(t), "abstain_rate": round(ab.mean(), 4),
                     "abstained": int(ab.sum()),
                     "abstained_wrong": int((ab & wrong).sum()),
                     "share_abstained_wrong": round((ab & wrong).sum() / ab.sum(), 4) if ab.any() else None,
                     "errors_left_unabstained": int((~ab & wrong).sum()),
                     "total_errors": int(wrong.sum())})
    return rows


def main() -> None:
    d = load()
    dev, test = d[d.split == "dev"].copy(), d[d.split == "test"].copy()
    M: dict = {"n_all": len(d), "n_dev": len(dev), "n_test": len(test),
               "label_counts_all": d.label.value_counts().to_dict(), "label_counts_test": test.label.value_counts().to_dict()}
    M["majority_baseline_accuracy_all"] = round((d.y == 0).mean(), 4)
    M["majority_baseline_accuracy_test"] = round((test.y == 0).mean(), 4)

    # ---- models on the test split
    tf, c = tfidf_model(dev.text, dev.y)
    tf_dt, c_dt = tfidf_model(dev.text_dt, dev.y)
    test["pred_majority"] = 0
    test["pred_keyword"] = (test.text.map(keyword_baseline) == "FLAG").astype(int)
    test["pred_tfidf"] = tf.predict(test.text)
    test["pred_rule"] = test.text.map(rule_layer).notna().astype(int)
    test["pred_llm"] = (test.p_flag >= 0.5).astype(int)
    models = {"majority": "pred_majority", "keyword": "pred_keyword", "tfidf_lr": "pred_tfidf",
              "rule_layer_only": "pred_rule", "llm_only": "pred_llm"}
    M["tfidf_C"] = c
    M["test"] = {k: {**prf(test.y, test[v]), "by_band": by_band(test, v)} for k, v in models.items()}
    M["dev_rule_layer"] = prf(dev.y, dev.text.map(rule_layer).notna().astype(int))
    M["all_rule_layer"] = prf(d.y, d.text.map(rule_layer).notna().astype(int))
    M["all_llm_only"] = {**prf(d.y, (d.p_flag >= 0.5).astype(int)), "by_band": by_band(d.assign(pl=(d.p_flag >= 0.5).astype(int)), "pl")}
    M["dev_llm_only"] = prf(dev.y, (dev.p_flag >= 0.5).astype(int))

    # ---- abstention: choose tau on dev under a HOLD budget, report on test
    taus = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 0.99, 0.995, 0.999, 0.9999, 0.99999]
    dev_curve = abstention_curve(dev.assign(), taus)
    dev_sys_hold = {t: system_metrics(dev, system_decisions(dev, t))["hold_rate"] for t in taus}
    tau = max(t for t in taus if dev_sys_hold[t] <= HOLD_BUDGET)
    M["abstention"] = {"hold_budget": HOLD_BUDGET, "tau_selected_on_dev": tau, "dev_system_hold_rate_by_tau": dev_sys_hold,
                       "dev_curve": dev_curve, "test_curve": abstention_curve(test, taus), "all_curve": abstention_curve(d, taus)}

    # ---- full system on test
    test["decision"] = system_decisions(test, tau)
    M["test_system"] = system_metrics(test, test.decision)
    test["pred_sys_stopped"] = test.decision.isin(["FLAG", "HOLD"]).astype(int)
    M["test_system"]["by_band"] = by_band(test, "pred_sys_stopped")
    M["test_system_no_hold"] = system_metrics(test, system_decisions(test, 0.0))
    M["release_condition_precision_0.70"] = {
        "llm_only": M["test"]["llm_only"]["precision"] >= 0.70,
        "system_stopped": M["test_system"]["stopped_precision"] >= 0.70,
    }

    # ---- de-templating: before / after on test
    test["pred_keyword_dt"] = (test.text_dt.map(keyword_baseline) == "FLAG").astype(int)
    test["pred_tfidf_dt"] = tf_dt.predict(test.text_dt)
    test["pred_llm_dt"] = (test.p_flag_dt >= 0.5).astype(int)
    test["pred_tfidf_cross"] = tf.predict(test.text_dt)  # trained on templated, tested on de-templated
    M["detemplating"] = {
        "sentences_changed_all": int((d.text != d.text_dt).sum()),
        "keyword": {"before": prf(test.y, test.pred_keyword), "after": prf(test.y, test.pred_keyword_dt)},
        "tfidf_lr": {"before": prf(test.y, test.pred_tfidf), "after": prf(test.y, test.pred_tfidf_dt),
                     "trained_templated_tested_detemplated": prf(test.y, test.pred_tfidf_cross), "C_after": c_dt},
        "llm_only": {"before": prf(test.y, test.pred_llm), "after": prf(test.y, test.pred_llm_dt)},
        "llm_grey_recall": {"before": by_band(test, "pred_llm")["zone:grey"], "after": by_band(test, "pred_llm_dt")["zone:grey"]},
        "tfidf_grey_recall": {"before": by_band(test, "pred_tfidf")["zone:grey"], "after": by_band(test, "pred_tfidf_dt")["zone:grey"]},
    }

    # ---- held-out real copy
    h = pd.read_csv(REPO / "data" / "heldout_real_copy.csv").merge(pd.read_csv(REPO / "data" / "heldout_labels.csv"), on="id")
    h["y"] = (h.label == "FLAG").astype(int)
    hl = pd.read_json(RES / f"llm_heldout_{PV}.jsonl", lines=True)[["id", "llm_label", "p_flag", "reason"]]
    h = h.merge(hl, on="id")
    h["pred_keyword"] = (h.text.map(keyword_baseline) == "FLAG").astype(int)
    h["pred_tfidf"] = tf.predict(h.text)
    h["pred_llm"] = (h.p_flag >= 0.5).astype(int)
    h["decision"] = system_decisions(h, tau)
    M["heldout"] = {"n": len(h), "labels": h.label.value_counts().to_dict(),
                    "keyword": prf(h.y, h.pred_keyword), "tfidf_lr": prf(h.y, h.pred_tfidf), "llm_only": prf(h.y, h.pred_llm),
                    "system": system_metrics(h.assign(zone="real"), h.decision),
                    "llm_false_flags": h[(h.pred_llm == 1) & (h.y == 0)][["id", "text", "p_flag"]].to_dict("records"),
                    "llm_misses": h[(h.pred_llm == 0) & (h.y == 1)][["id", "text", "p_flag"]].to_dict("records")}

    # ---- operating points: what each tau costs the reviewer and what it misses
    ops = []
    for t in taus:
        st_, sh_ = system_metrics(test, system_decisions(test, t)), system_metrics(h.assign(zone="real"), system_decisions(h, t))
        ops.append({"tau": t, "test_hold_rate": st_["hold_rate"], "test_recall_stopped": st_["recall_stopped_before_send"],
                    "test_missed": len(st_["missed_flags"]), "test_grey_missed": int(sum(test.set_index("id").loc[i, "zone"] == "grey" for i in st_["missed_flags"])),
                    "heldout_hold_rate": sh_["hold_rate"], "heldout_stopped_precision": sh_["stopped_precision"]})
    M["operating_points"] = ops

    # ---- cost and latency (measured)
    n = len(d)
    rule_rate_all = d.text.map(rule_layer).notna().mean()
    per_call = d.cost_usd.mean()
    M["cost"] = {
        "calls_measured": n,
        "mean_prompt_tokens": round(d.prompt_tokens.mean(), 1),
        "mean_completion_tokens": round(d.completion_tokens.mean(), 1),
        "measured_cost_per_call_usd": round(per_call, 8),
        "llm_cost_per_1000_sentences_usd": round(per_call * 1000, 4),
        "list_price_check_per_1000_usd": round((d.prompt_tokens.mean() * PRICE_IN + d.completion_tokens.mean() * PRICE_OUT) * 1000, 4),
        "rule_layer_share_all": round(rule_rate_all, 4),
        "system_cost_per_1000_sentences_usd": round(per_call * 1000 * (1 - rule_rate_all), 4),
        "latency_ms_p50": round(d.latency_ms.median(), 1),
        "latency_ms_p95": round(d.latency_ms.quantile(0.95), 1),
    }
    spend = pd.read_json(RES / "api_spend.jsonl", lines=True)
    gen = pd.read_json(REPO / "data" / "generation" / "generation_spend.jsonl", lines=True)
    M["api_spend_total_usd"] = {"classification_runs": round(spend.cost_usd.sum(), 4), "dataset_generation": round(gen.cost_usd.sum(), 4),
                                "total": round(spend.cost_usd.sum() + gen.cost_usd.sum(), 4)}

    # ---- outputs
    RES.mkdir(exist_ok=True)
    (RES / "metrics.json").write_text(json.dumps(M, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    test[["id", "text", "band", "zone", "label", "pred_keyword", "pred_tfidf", "pred_rule", "pred_llm", "p_flag", "decision"]].to_csv(
        RES / "system_predictions_test.csv", index=False)
    h[["id", "text", "platform", "label", "pred_keyword", "pred_tfidf", "pred_llm", "p_flag", "decision"]].to_csv(
        RES / "system_predictions_heldout.csv", index=False)
    plot_curve(M["abstention"]["test_curve"], M["abstention"]["all_curve"], tau)
    write_tables(M)
    print((RES / "tables.md").read_text())


def plot_curve(test_curve, all_curve, tau) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=150)
    for curve, name, style in [(all_curve, "all 240", "o-"), (test_curve, "test 120", "s--")]:
        xs = [c["abstain_rate"] for c in curve if c["abstained"]]
        ys = [c["share_abstained_wrong"] for c in curve if c["abstained"]]
        ax.plot(xs, ys, style, label=name, ms=4)
    sel = [c for c in all_curve if c["tau"] == tau][0]
    ax.axvline(sel["abstain_rate"], color="grey", lw=0.8, ls=":")
    base = all_curve[0]["total_errors"] / 240
    ax.axhline(base, color="red", lw=0.8, ls="--")
    ax.annotate(f"LLM error rate on all 240: {base:.1%}", (0.06, base + 0.02), fontsize=8, color="red")
    ax.annotate(f"chosen tau={tau}", (sel["abstain_rate"], 0.95), fontsize=8, ha="left")
    ax.set_xlabel("abstention rate (share of LLM-scored sentences held)")
    ax.set_ylabel("share of held sentences the LLM\nwould have got wrong")
    ax.set_ylim(0, 1.02)
    ax.set_title("Abstention curve, gpt-4o-mini label-token confidence", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(RES / "abstention_curve.png")


def write_tables(M: dict) -> None:
    L = ["# Results tables (generated by scripts/evaluate.py)", ""]
    L.append(f"Test split: {M['n_test']} sentences, {M['label_counts_test']}. Majority-class accuracy on test {M['majority_baseline_accuracy_test']}, on all 240 {M['majority_baseline_accuracy_all']}.")
    L += ["", "## Headline, test split", "", "| model | accuracy | precision | recall (flag) | F1 | block rate |", "|---|---|---|---|---|---|"]
    for k, v in M["test"].items():
        L.append(f"| {k} | {v['accuracy']} | {v['precision']} | {v['recall']} | {v['f1']} | {v['block_rate']} |")
    s = M["test_system"]
    L.append(f"| **system (rules + LLM + HOLD, tau={M['abstention']['tau_selected_on_dev']})** | | auto-FLAG {s['auto_flag_precision']}, stopped {s['stopped_precision']} | {s['recall_stopped_before_send']} (FLAG or HOLD) | | {s['block_rate']} (FLAG {s['flag_rate']}, HOLD {s['hold_rate']}) |")
    L += ["", "## Recall on the flag class by band, test split (caught / flag items)", "",
          "| band | n flag | majority | keyword | TF-IDF LR | rule layer | LLM only | system |", "|---|---|---|---|---|---|---|---|"]
    keys = ["fact_comparison", "implied_suitability", "soft_recommendation", "explicit_recommendation", "zone:clear_flag", "zone:grey"]
    for b in keys:
        row = [b.replace("zone:", "zone: "), str(M["test"]["llm_only"]["by_band"][b]["n_flag"])]
        for k in ["majority", "keyword", "tfidf_lr", "rule_layer_only", "llm_only"]:
            x = M["test"][k]["by_band"][b]
            row.append(f"{x['caught']}/{x['n_flag']}")
        x = M["test_system"]["by_band"][b]
        row.append(f"{x['caught']}/{x['n_flag']}")
        L.append("| " + " | ".join(row) + " |")
    L += ["", "## False flags on PASS items by band, test split", "", "| band | n pass | keyword | TF-IDF LR | LLM only | system (FLAG or HOLD) |", "|---|---|---|---|---|---|"]
    for b in ["plain_fact", "fact_comparison", "implied_suitability", "soft_recommendation", "zone:grey_pass"]:
        row = [b, str(M["test"]["keyword"]["by_band"][b]["n_pass"])]
        for k in ["keyword", "tfidf_lr", "llm_only"]:
            row.append(str(M["test"][k]["by_band"][b]["false_flags"]))
        row.append(str(M["test_system"]["by_band"][b]["false_flags"]))
        L.append("| " + " | ".join(row) + " |")
    L += ["", "## LLM layer alone against reference labels", "",
          f"- test: precision {M['test']['llm_only']['precision']}, recall {M['test']['llm_only']['recall']}, accuracy {M['test']['llm_only']['accuracy']}",
          f"- dev (prompt was iterated here): precision {M['dev_llm_only']['precision']}, recall {M['dev_llm_only']['recall']}",
          f"- all 240: precision {M['all_llm_only']['precision']}, recall {M['all_llm_only']['recall']}, grey recall {M['all_llm_only']['by_band']['zone:grey']['caught']}/{M['all_llm_only']['by_band']['zone:grey']['n_flag']}",
          f"- rule layer alone, all 240: precision {M['all_rule_layer']['precision']}, recall {M['all_rule_layer']['recall']} ({M['all_rule_layer']['tp']} sentences)"]
    L += ["", "## Abstention (tau chosen on dev with HOLD budget " + str(M["abstention"]["hold_budget"]) + ")", "",
          "| tau | abstain rate (all 240) | held | held and LLM wrong | share wrong | LLM errors left |", "|---|---|---|---|---|---|"]
    for c in M["abstention"]["all_curve"]:
        L.append(f"| {c['tau']} | {c['abstain_rate']} | {c['abstained']} | {c['abstained_wrong']} | {c['share_abstained_wrong']} | {c['errors_left_unabstained']}/{c['total_errors']} |")
    dt = M["detemplating"]
    L += ["", f"## De-templating, test split ({dt['sentences_changed_all']} of 240 sentences changed)", "",
          "| model | accuracy before | accuracy after | recall before | recall after | precision before | precision after |", "|---|---|---|---|---|---|---|"]
    for k in ["keyword", "tfidf_lr", "llm_only"]:
        b, a = dt[k]["before"], dt[k]["after"]
        L.append(f"| {k} | {b['accuracy']} | {a['accuracy']} | {b['recall']} | {a['recall']} | {b['precision']} | {a['precision']} |")
    x = dt["tfidf_lr"]["trained_templated_tested_detemplated"]
    L.append(f"| tfidf_lr trained on templated, tested on de-templated | {dt['tfidf_lr']['before']['accuracy']} | {x['accuracy']} | {dt['tfidf_lr']['before']['recall']} | {x['recall']} | {dt['tfidf_lr']['before']['precision']} | {x['precision']} |")
    H = M["heldout"]
    L += ["", f"## Held-out real copy ({H['n']} sentences, {H['labels']})", "", "| model | accuracy | precision | recall | false flags | misses |", "|---|---|---|---|---|---|"]
    for k in ["keyword", "tfidf_lr", "llm_only"]:
        v = H[k]
        L.append(f"| {k} | {v['accuracy']} | {v['precision']} | {v['recall']} | {v['fp']} | {v['fn']} |")
    s = H["system"]
    L.append(f"| system | | stopped precision {s['stopped_precision']} | {s['recall_stopped_before_send']} | stopped {round(s['block_rate']*H['n'])} of {H['n']} | {len(s['missed_flags'])} |")
    C = M["cost"]
    L += ["", "## Cost and latency (measured on 240 calls)", "",
          f"- mean tokens per call: {C['mean_prompt_tokens']} in, {C['mean_completion_tokens']} out",
          f"- LLM cost per 1,000 sentences: ${C['llm_cost_per_1000_sentences_usd']} (list-price check ${C['list_price_check_per_1000_usd']})",
          f"- system cost per 1,000 sentences after the rule layer handles {C['rule_layer_share_all']:.1%}: ${C['system_cost_per_1000_sentences_usd']}",
          f"- latency per call: p50 {C['latency_ms_p50']} ms, p95 {C['latency_ms_p95']} ms",
          f"- total API spend for this project: ${M['api_spend_total_usd']['total']} (generation ${M['api_spend_total_usd']['dataset_generation']}, classification ${M['api_spend_total_usd']['classification_runs']})"]
    L += ["", "## Operating points by HOLD threshold", "", "| tau | test HOLD rate | test recall (stopped) | test misses | of which grey | real-copy HOLD rate | real-copy stopped precision |", "|---|---|---|---|---|---|---|"]
    for o in M["operating_points"]:
        L.append(f"| {o['tau']} | {o['test_hold_rate']} | {o['test_recall_stopped']} | {o['test_missed']} | {o['test_grey_missed']} | {o['heldout_hold_rate']} | {o['heldout_stopped_precision']} |")
    (RES / "tables.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
