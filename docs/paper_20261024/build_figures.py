#!/usr/bin/env python3
"""Build the manuscript's vector figures from preserved experiment artifacts.

Run from the repository root with ``.venv/bin/python
docs/paper_20261024/build_figures.py``. No training or application mutation is
performed. Numerical figures read their values from frozen JSON rather than
from manually transcribed manuscript tables. CSV data and source hashes are
exported beside the figures.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mai-paper-matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "figures"
TRAINING = ROOT / "outputs" / "training"
BLUE = "#175b87"
PALE_BLUE = "#edf4fa"
ORANGE = "#b65d17"
PALE_ORANGE = "#fff4e8"
INK = "#202b33"
GRAY = "#737d85"
LIGHT = "#e5e9ec"
SOURCE_RECORDS: dict[str, str] = {}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "svg.fonttype": "none",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": GRAY,
    "text.color": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "savefig.facecolor": "white",
})


def read(relative: str):
    path = TRAINING / relative
    SOURCE_RECORDS[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text())


def save(fig, name: str) -> None:
    for suffix in ("pdf", "svg", "png"):
        fig.savefig(OUT / f"{name}.{suffix}", dpi=260, bbox_inches="tight", pad_inches=0.025)
    plt.close(fig)


def write_csv(name: str, rows: list[dict]) -> None:
    with (OUT / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def box(ax, x, y, w, h, label, *, color=BLUE, fill=PALE_BLUE,
        fontsize=8, dashed=False, weight="normal"):
    patch = FancyBboxPatch((x, y), w, h,
                          boxstyle="round,pad=0.045,rounding_size=0.065",
                          edgecolor=color, facecolor=fill, linewidth=0.85,
                          linestyle=(0, (4, 3)) if dashed else "solid")
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=fontsize, linespacing=1.35, fontweight=weight)
    return patch


def arrow(ax, start, end, *, color=BLUE, dashed=False, rad=0):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>",
                                mutation_scale=9, linewidth=0.9,
                                color=color,
                                connectionstyle=f"arc3,rad={rad}",
                                linestyle=(0, (4, 3)) if dashed else "solid"))


def architecture() -> None:
    # Coordinates are inch-like to make layout readable at IEEE two-column width.
    fig, ax = plt.subplots(figsize=(7.16, 5.1))
    fig.subplots_adjust(left=0.005, right=0.995, bottom=0.005, top=0.995)
    ax.set(xlim=(0, 7.25), ylim=(0, 5.12))
    ax.axis("off")

    ax.text(0.08, 4.98, "A. IMPLEMENTED INPUT PROCESSING", fontsize=8,
            fontweight="bold", va="top", color=GRAY)
    ax.text(7.17, 4.98, "Not tested end-to-end in GAP", fontsize=7.2,
            va="top", ha="right", color=GRAY)
    box(ax, 0.15, 4.12, 1.28, .51, "Meeting audio", color=GRAY, fill="#f6f7f8")
    box(ax, 2.02, 4.12, 2.04, .51, "Offline ASR + diarization", color=GRAY, fill="#f6f7f8")
    box(ax, 4.68, 4.12, 2.32, .51, "Timed, speaker-labelled\nsource passages", color=GRAY, fill="#f6f7f8", fontsize=7.8)
    arrow(ax, (1.5, 4.375), (1.94, 4.375), color=GRAY)
    arrow(ax, (4.13, 4.375), (4.59, 4.375), color=GRAY)
    box(ax, 0.15, 3.37, 1.28, .48, "Optional slides", color=GRAY, fill="#f6f7f8", dashed=True)
    box(ax, 2.02, 3.37, 2.04, .48, "Slide text + semantic /\ntemporal association", color=GRAY, fill="#f6f7f8", fontsize=7.5, dashed=True)
    box(ax, 4.68, 3.37, 2.32, .48, "Optional passage-to-slide\nsource references", color=GRAY, fill="#f6f7f8", fontsize=7.6, dashed=True)
    arrow(ax, (1.5, 3.61), (1.94, 3.61), color=GRAY, dashed=True)
    arrow(ax, (4.13, 3.61), (4.59, 3.61), color=GRAY, dashed=True)
    # Inputs enter the common passage representation through explicit ports.
    ax.plot([7.1, 7.16, 7.16, .1, .1], [4.37, 4.37, 3.09, 3.09, 2.53],
            color=GRAY, lw=.75)
    arrow(ax, (.1, 2.53), (.28, 2.53), color=GRAY)
    ax.plot([5.84, 5.84], [3.32, 3.09], color=GRAY, lw=.75, ls=(0, (4, 3)))

    # Benchmark boundary marks which supplied input conditions support the claims.
    boundary = FancyBboxPatch((.04, .38), 7.16, 2.57,
                             boxstyle="round,pad=0.02,rounding_size=.05",
                             facecolor="#fbfdff", edgecolor=BLUE,
                             lw=1.0, linestyle=(0, (5, 3)))
    ax.add_patch(boundary)
    ax.text(.17, 2.87, "B. CONTRIBUTION ANALYSIS", fontsize=8, fontweight="bold", color=BLUE)
    ax.text(7.06, 2.87, "GAP: supplied English transcript + speaker IDs; no slides",
            fontsize=7.1, ha="right", color=BLUE)
    # Three columns are traversed left to right, then right to left.
    box(ax, .32, 2.1, 1.92, .54, "Source passages\n(text, speaker, time, IDs)", fontsize=7.6)
    box(ax, 2.70, 2.1, 1.88, .54, "Contribution events\n(proposal, evidence, objection, …)", fontsize=7.2)
    box(ax, 5.05, 2.1, 1.88, .54, "Candidate evidence\nrelationships", fontsize=7.8)
    arrow(ax, (2.3, 2.37), (2.62, 2.37))
    arrow(ax, (4.64, 2.37), (4.97, 2.37))
    box(ax, 5.05, 1.24, 1.88, .54, "Decision reconstruction\n+ source-linked lineage", fontsize=7.6)
    arrow(ax, (5.99, 2.03), (5.99, 1.86))
    box(ax, 2.70, 1.24, 1.88, .54, "Participant interactions\nfrom events, relations, decisions", fontsize=7.2)
    box(ax, .32, 1.24, 1.92, .54, "Seven contribution features\nwithin-meeting normalization", fontsize=7.3)
    arrow(ax, (4.97, 1.51), (4.64, 1.51))
    arrow(ax, (2.62, 1.51), (2.3, 1.51))
    box(ax, .32, .53, 1.92, .43, "Weighted contribution estimate", fontsize=7.3)
    box(ax, 2.70, .53, 1.88, .43, "Per-person scores / rankings", fontsize=7.3)
    box(ax, 5.05, .53, 1.88, .43, "Source review + feature rationale", fontsize=7.1)
    arrow(ax, (1.28, 1.17), (1.28, 1.04))
    arrow(ax, (2.3, .745), (2.62, .745))
    arrow(ax, (4.64, .745), (4.97, .745))
    ax.text(3.62, .12,
            "Source references support inspection; inferred links and scores do not establish causal influence.",
            fontsize=7.2, ha="center", va="center")
    save(fig, "architecture")


def gap_results(initial: dict) -> None:
    order = [
        ("structure__extra_trees", "Structure Extra Trees\n(selected primary)", BLUE),
        ("word_count", "Word count", ORANGE),
        ("speaking_time", "Speaking time", GRAY),
        ("prototype_influence", "Prototype contribution\nscore", GRAY),
    ]
    rows = []
    fig, ax = plt.subplots(figsize=(3.5, 2.80))
    fig.subplots_adjust(left=.36, right=.98, top=.88, bottom=.36)
    jitters = np.linspace(-.12, .12, 6)
    for i, (name, label, color) in enumerate(order):
        result = initial["results"][name]
        scores = np.array([m["pairwise_accuracy"] for m in result["meetings"]])
        mean = result["meeting_macro_pairwise_accuracy"]
        assert np.isclose(scores.mean(), mean)
        y = 3 - i
        ax.scatter(scores * 100, y + jitters, s=13, color=color, alpha=.42,
                   linewidths=0, zorder=3)
        ax.scatter([mean * 100], [y], marker="D", s=32, color=color,
                   edgecolors="white", linewidths=.6, zorder=4)
        ax.text(118, y, f"{mean * 100:.1f}", ha="right", va="center",
                fontsize=7.5, fontweight="bold", color=color)
        for meeting in result["meetings"]:
            rows.append({"method": name, "meeting_id": meeting["meeting_id"],
                         "pairwise_accuracy": meeting["pairwise_accuracy"],
                         "meeting_macro_pairwise_accuracy": mean,
                         "comparable_pairs": meeting["comparable_pairs"],
                         "predicted_ties": "half credit",
                         "reference_ties": "excluded"})
    ax.set(xlim=(-3, 120), ylim=(-.45, 3.45),
           xticks=[0, 25, 50, 75, 100], yticks=[3, 2, 1, 0],
           yticklabels=[x[1] for x in order], xlabel="Pairwise accuracy (%)")
    ax.set_axisbelow(True)
    ax.grid(axis="x", color=LIGHT, lw=.6)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=5)
    ax.text(.5, 1.1, "Six historical GAP meetings", transform=ax.transAxes,
            ha="center", fontsize=8.2, fontweight="bold")
    fig.legend(handles=[
        Line2D([0], [0], marker="o", ls="none", markerfacecolor=GRAY,
               alpha=.45, markeredgecolor="none", markersize=4, label="Individual meeting"),
        Line2D([0], [0], marker="D", ls="none", color=GRAY,
               markersize=4.5, label="Equal-meeting mean"),
    ], loc="lower center", bbox_to_anchor=(.58, .035), ncol=1,
       frameon=False, handletextpad=.4, labelspacing=.25)
    save(fig, "gap_results")
    write_csv("gap_results_data.csv", rows)


def best_development(trials: list[dict], name: str) -> float:
    candidates = [t for t in trials if t["name"] == name]
    assert candidates, name
    return max(t["development"]["meeting_macro_pairwise_accuracy"] for t in candidates)


def exploration(initial: dict) -> None:
    init_sel = read("gap_influence_20261024/selection.json")
    init_dev = read("gap_influence_20261024/development_search.json")
    sem = read("gap_influence_semantic_20261024/historical_results.json")
    sem_dev = read("gap_influence_semantic_20261024/development_search.json")
    xgb = read("xgb_influence_20261024_v2/historical_evaluation.json")
    xgb_sel = read("xgb_influence_20261024_v2/ranker.json")
    roles = read("contextual_roles_balanced_20261024/fixed_influence_evaluation.json")
    metric = "meeting_macro_pairwise_accuracy"
    records = [
        ("Structure Extra Trees\n(initial primary)", "initial snapshot",
         init_sel["primary"]["development"][metric],
         initial["results"]["structure__extra_trees"][metric],
         "gap_influence_20261024"),
        ("Word-count baseline", "participation baseline",
         best_development(init_dev, "word_count"),
         initial["results"]["word_count"][metric], "gap_influence_20261024"),
        ("Semantic uptake\n(ridge)", "pre-correction snapshot",
         best_development(sem_dev, "semantic__ridge"),
         sem["results"]["semantic__ridge"][metric], "gap_influence_semantic_20261024"),
        ("Learned role summaries\n(ridge)", "pre-correction snapshot",
         best_development(sem_dev, "learned_roles__ridge"),
         sem["results"]["learned_roles__ridge"][metric], "gap_influence_semantic_20261024"),
        ("XGBoost ranker", "corrected snapshot",
         xgb_sel["development"][metric], xgb["candidate"][metric],
         "xgb_influence_20261024_v2"),
        ("Balanced contextual roles\n(fixed contribution score)", "corrected snapshot",
         roles["cohorts"]["dev"]["contextual_roles_fixed_influence"][metric],
         roles["cohorts"]["test"]["contextual_roles_fixed_influence"][metric],
         "contextual_roles_balanced_20261024"),
    ]
    expected = [(83.333333, 61.111111), (82.777778, 63.888889),
                (74.444444, 30.555556), (74.444444, 36.111111),
                (86.111111, 50.), (71.111111, 38.888889)]
    for row, target in zip(records, expected):
        assert np.allclose(np.array(row[2:4]) * 100, target, atol=1e-5)
    fig, ax = plt.subplots(figsize=(7.16, 3.6))
    fig.subplots_adjust(left=.27, right=.78, top=.92, bottom=.23)
    rows = []
    for index, (label, version, dev, hist, artifact) in enumerate(records):
        y = 5 - index
        ax.plot([hist * 100, dev * 100], [y, y], color="#bac3c9", lw=1.1, zorder=1)
        ax.scatter([dev * 100], [y], marker="o", s=31, facecolor="white",
                   edgecolor=GRAY, lw=1.15, zorder=3)
        ax.scatter([hist * 100], [y], marker="s", s=30, color=BLUE, zorder=3)
        ax.text(hist * 100, y - .27, f"{hist * 100:.1f}", fontsize=7,
                color=BLUE, ha="center", va="center")
        ax.text(dev * 100, y + .27, f"{dev * 100:.1f}", fontsize=7,
                color=GRAY, ha="center", va="center")
        ax.text(103, y, version, fontsize=6.8, va="center", color=GRAY)
        rows.append({"method": label.replace("\n", " "), "feature_version": version,
                     "development_pairwise_accuracy": dev,
                     "historical_pairwise_accuracy": hist,
                     "artifact_directory": f"outputs/training/{artifact}",
                     "historical_status": "initial frozen scoring" if index < 2
                     else "exploratory reuse of historical cohort"})
    for y in [3.5, 1.5]:
        ax.axhline(y, color=LIGHT, lw=.7, ls=(0, (3, 3)))
    ax.set(xlim=(0, 100), ylim=(-.6, 5.6), xticks=np.arange(0, 101, 20),
           yticks=np.arange(5, -1, -1), yticklabels=[r[0] for r in records],
           xlabel="Meeting-average pairwise accuracy (%)")
    ax.set_axisbelow(True)
    ax.grid(axis="x", color=LIGHT, lw=.55)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.legend(handles=[
        Line2D([0], [0], marker="o", markerfacecolor="white", markeredgecolor=GRAY,
               color="none", markersize=5, label="Development"),
        Line2D([0], [0], marker="s", color=BLUE, ls="none", markersize=5,
               label="Historical evaluation"),
    ], loc="upper center", bbox_to_anchor=(.45, 1.14), ncol=2, frameon=False)
    fig.text(.51, .055,
             "Later experiments reuse the six historical groups; feature versions differ.\n"
             "Lines connect cohort scores and do not represent confidence intervals.",
             ha="center", fontsize=7.2, color=GRAY, linespacing=1.4)
    save(fig, "exploration")
    write_csv("exploration_data.csv", rows)


def evaluation_design() -> None:
    # Split counts and IDs are read, rather than transcribed, from the protocol.
    protocol = read("gap_influence_20261024/protocol.json")
    splits = protocol.get("splits", protocol.get("group_split"))
    if splits is None:
        # The exact original protocol uses group IDs under the `split` key.
        splits = protocol.get("split")
    assert splits is not None, list(protocol)
    development = splits.get("development", splits.get("dev"))
    train, test = splits["train"], splits["test"]
    assert (len(train), len(development), len(test)) == (16, 6, 6)
    assert not (set(train) & set(development) or set(train) & set(test) or set(development) & set(test))
    fig, ax = plt.subplots(figsize=(7.16, 2.25))
    fig.subplots_adjust(left=.005, right=.995, bottom=.005, top=.995)
    ax.set(xlim=(0, 7.2), ylim=(0, 2.25))
    ax.axis("off")
    box(ax, .15, 1.30, 1.65, .62, "GAP group-decision corpus\n28 meetings / 84 participants\nReference text + speaker IDs", fontsize=7.5)
    box(ax, 2.27, 1.42, 1.28, .46, f"Training\n{len(train)} complete groups", fontsize=7.7)
    box(ax, 3.93, 1.42, 1.28, .46, f"Development\n{len(development)} complete groups", fontsize=7.7)
    box(ax, 5.60, 1.42, 1.40, .46, f"Historical evaluation\n{len(test)} complete groups", fontsize=7.3)
    arrow(ax, (1.87, 1.65), (2.19, 1.65))
    arrow(ax, (3.62, 1.65), (3.85, 1.65))
    arrow(ax, (5.28, 1.65), (5.52, 1.65))
    ax.text(2.91, 1.15, "Fit features and models", fontsize=7, ha="center")
    ax.text(4.57, 1.15, "Select primary", fontsize=7, ha="center")
    ax.text(6.3, 1.15, "Initial frozen comparison", fontsize=7, ha="center")
    ax.text(.15, .80, "TARGET", fontsize=7.8, fontweight="bold", color=BLUE)
    ax.text(1.0, .80,
            "Individual-to-group ranking distance (AII): outcome alignment, not causal attribution.",
            fontsize=7.6, va="center")
    ax.text(.15, .43, "METRIC", fontsize=7.8, fontweight="bold", color=BLUE)
    ax.text(1.0, .43,
            "Pairwise ordering within each meeting; reference ties excluded; prediction ties = ½ credit.",
            fontsize=7.5, va="center")
    ax.text(3.6, .09,
            "Splits are disjoint by meeting. Later studies reuse the historical groups and remain exploratory.",
            fontsize=7.2, ha="center", color=GRAY)
    save(fig, "evaluation_design")
    write_csv("gap_split_data.csv", [
        {"split": label, "meeting_id": identifier}
        for label, values in [("train", train), ("development", development), ("historical", test)]
        for identifier in values
    ])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    initial = read("gap_influence_20261024/test_results.json")
    assert initial["test_meetings"] == 6
    assert initial["primary_selected_on_development"] == "structure__extra_trees"
    assert np.isclose(initial["results"]["structure__extra_trees"]["meeting_macro_pairwise_accuracy"], 11 / 18)
    assert np.isclose(initial["results"]["word_count"]["meeting_macro_pairwise_accuracy"], 23 / 36)
    architecture()
    gap_results(initial)
    exploration(initial)
    evaluation_design()
    (OUT / "source_manifest.json").write_text(json.dumps({
        "sources_sha256": SOURCE_RECORDS,
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "notes": [
            "All numerical plotting inputs are loaded from the listed frozen JSON artifacts.",
            "Individual GAP points are meetings; displayed means weight meetings equally.",
            "No confidence interval is implied by lines between development and historical scores.",
            "Architecture documents implementation and input conditions, not end-to-end validity.",
        ],
    }, indent=2) + "\n")
    print(f"Wrote 4 figures in PDF/SVG/PNG and 3 data CSVs to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
