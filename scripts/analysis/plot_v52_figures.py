#!/usr/bin/env python3
"""Paper v5.2 figures: permission pipeline diagram and failure time series.

Reads only frozen evidence and never re-runs CARLA:

* the locked raw-log archive
  ``artifacts/paper_v4_gpu_final_locked_20260825_raw_logs.tar.gz`` (SHA256
  verified against its ``.sha256`` sidecar before use; tick CSVs are read
  directly from the archive, nothing is extracted into the repository);
* the frozen v5 severity tables, used only to apply the run-selection rule.

Selection rule (stated in the figure caption):

* fallback synthetic-ghost false brake: among the 20 fallback ghost runs in
  ``false_brake_severity_runs.csv``, the runs whose onset speed, brake
  duration and peak deceleration all equal the per-policy medians; ties are
  broken by the lexicographically smallest (scenario_id, run_index);
* hard-gate hold-out bench: among the five hard-gate bench runs in
  ``collision_severity_runs.csv``, the runs whose last-tick pre-impact speed
  equals the median; ties broken by the smallest run index.

Outputs (vector PDF + traced data) go to
``docs/log/repeatability/paper_v5_2_derived/figures/`` and the two PDFs are
copied into ``paper/paper_v5_2/figures/``.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import shutil
import statistics
import sys
import tarfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analysis.analyze_v52_paired_tests import write_checksums  # noqa: E402

REPEATABILITY = ROOT / "docs" / "log" / "repeatability"
ARCHIVE = REPEATABILITY / "artifacts" / "paper_v4_gpu_final_locked_20260825_raw_logs.tar.gz"
ARCHIVE_SHA = ARCHIVE.with_name(ARCHIVE.name + ".sha256")
CAMPAIGN = "paper_v4_gpu_final_locked_20260825"
V5 = REPEATABILITY / "paper_v5_derived"
OUT = REPEATABILITY / "paper_v5_2_derived"
FIGURES = OUT / "figures"
PAPER_FIGURES = ROOT / "paper" / "paper_v5_2" / "figures"
PIPELINE_PDF = "pipeline_permission_policies.pdf"
TIMESERIES_PDF = "timeseries_ghost_vs_bench.pdf"
TRACE_CSV = "timeseries_selected_runs.csv"
SELECTION_JSON = "timeseries_selection.json"

# Categorical slots (fixed order): radar-only, hard gate, fallback.
COLORS = {"radar_only": "#2a78d6", "hard_gate": "#eb6834", "safe_fallback": "#1baf7a"}
INK = "#0b0b0b"
MUTED = "#52514e"
GRID = "#d9d8d4"
REQUEST_FILL = "#e4e3df"
RADAR_REQUEST_ACTIONS = {
    "camera_confirmed", "confirmation_hold", "fusion_blocked_brake",
    "radar_emergency_fallback", "radar_emergency_fallback_hold",
}
TRACE_FIELDS = ("elapsed_s", "ego_speed_kph", "ttc_s", "bumper_gap_m", "brake_cmd",
                "aeb_override", "fusion_gate_action", "collision_count")


def style():
    matplotlib.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Nimbus Roman", "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 7,
        "axes.labelsize": 7,
        "axes.titlesize": 7,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5,
        "axes.edgecolor": MUTED,
        "axes.linewidth": 0.6,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.major.width": 0.5,
        "ytick.major.width": 0.5,
        "pdf.fonttype": 42,
        "svg.hashsalt": "aeb-v52",
    })


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_archive():
    expected = ARCHIVE_SHA.read_text(encoding="utf-8").split()[0]
    actual = sha256(ARCHIVE)
    if actual != expected:
        raise AssertionError("raw archive SHA256 mismatch: {} != {}".format(actual, expected))
    return actual


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def select_runs():
    ghosts = [r for r in read_csv(V5 / "false_brake_severity_runs.csv") if r["config"] == "safe_fallback"]
    fields = ("onset_speed_kph", "brake_duration_s", "peak_deceleration_mps2")
    medians = {f: statistics.median(float(r[f]) for r in ghosts) for f in fields}
    tied = [r for r in ghosts if all(float(r[f]) == medians[f] for f in fields)]
    ghost = min(tied, key=lambda r: (r["scenario_id"], int(r["run_index"])))
    bench_rows = [r for r in read_csv(V5 / "collision_severity_runs.csv")
                  if r["config"] == "hard_gate" and r["scenario_id"] == "holdout_bench_center_v60_g22"]
    bench_median = statistics.median(float(r["preimpact_speed_kph"]) for r in bench_rows)
    bench = min((r for r in bench_rows if float(r["preimpact_speed_kph"]) == bench_median),
                key=lambda r: int(r["run_index"]))
    return [
        {"panel": "ghost", "config": "safe_fallback", "job": "holdout_safe_fallback",
         "scenario_id": ghost["scenario_id"], "run_index": int(ghost["run_index"]),
         "rule": "median onset/duration/peak deceleration over 20 fallback ghost runs; smallest (scenario, run) on ties",
         "tied_runs": len(tied), "medians": medians},
        {"panel": "bench", "config": "hard_gate", "job": "holdout_hard_gate",
         "scenario_id": bench["scenario_id"], "run_index": int(bench["run_index"]),
         "rule": "median last-tick pre-impact speed over 5 hard-gate bench runs; smallest run on ties",
         "tied_runs": sum(float(r["preimpact_speed_kph"]) == bench_median for r in bench_rows),
         "medians": {"preimpact_speed_kph": bench_median}},
    ]


def load_traces(selection):
    wanted = {
        "logs/{}_{}/{}_run_{:02d}.csv".format(CAMPAIGN, s["job"], s["scenario_id"], s["run_index"]): s
        for s in selection
    }
    traces = {}
    with tarfile.open(str(ARCHIVE), "r:gz") as archive:
        for member in archive:
            if member.name in wanted:
                text = archive.extractfile(member).read().decode("utf-8")
                traces[wanted[member.name]["panel"]] = list(csv.DictReader(io.StringIO(text)))
    missing = {s["panel"] for s in selection} - set(traces)
    if missing:
        raise AssertionError("runs missing from archive: {}".format(sorted(missing)))
    return traces


def num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def series(rows, field):
    return [num(row[field]) for row in rows]


def spans(times, flags, step=0.05):
    """Contiguous [start, end) intervals where flags are true."""
    out, start = [], None
    for t, flag in zip(times, flags):
        if flag and start is None:
            start = t - step / 2
        if not flag and start is not None:
            out.append((start, t - step / 2))
            start = None
    if start is not None:
        out.append((start, times[-1] + step / 2))
    return out


def plot_timeseries(traces, selection, path):
    fig, axes = plt.subplots(3, 2, figsize=(3.5, 2.55), sharex="col",
                             gridspec_kw={"hspace": 0.18, "wspace": 0.30})
    titles = {"ghost": "(a) Fallback: synthetic ghost (no hazard)",
              "bench": "(b) Hard gate: bench (hazard)"}
    for col, sel in enumerate(selection):
        rows = traces[sel["panel"]]
        color = COLORS[sel["config"]]
        t = series(rows, "elapsed_s")
        request = [row["fusion_gate_action"] in RADAR_REQUEST_ACTIONS for row in rows]
        collided = [num(row["collision_count"]) > 0 for row in rows]
        for ax in axes[:, col]:
            for a, b in spans(t, request):
                ax.axvspan(a, b, color=REQUEST_FILL, lw=0, zorder=0)
            ax.grid(axis="y", color=GRID, lw=0.4)
            ax.set_axisbelow(True)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            if any(collided):
                ax.axvline(t[collided.index(True)], color=INK, lw=0.7, ls=(0, (2, 1.5)))
        axes[0, col].plot(t, series(rows, "ego_speed_kph"), color=color, lw=1.2)
        axes[0, col].set_ylim(0, 90)
        axes[0, col].set_title(titles[sel["panel"]], loc="left", fontsize=6.5, color=INK, pad=2)
        axes[1, col].plot(t, series(rows, "ttc_s"), color=color, lw=1.2, marker="o", ms=1.1)
        axes[1, col].set_ylim(0, 1.25)
        axes[1, col].axhline(1.10, color=MUTED, lw=0.5, ls=":")
        axes[1, col].text(t[0], 1.12, "fallback TTC limit 1.10 s", fontsize=5.5, ha="left",
                          va="bottom", color=MUTED)
        axes[2, col].step(t, series(rows, "brake_cmd"), where="mid", color=color, lw=1.2)
        axes[2, col].set_ylim(-0.05, 1.1)
        axes[2, col].set_xlabel("Time since start [s]", labelpad=1)
        if sel["panel"] == "ghost":
            stop = next(x for x, v in zip(t, series(rows, "ego_speed_kph")) if v < 1.0)
            axes[0, col].text(0.25, 6, "full stop (<1 km/h) at {:.2f} s".format(stop),
                              fontsize=5.8, color=INK)
            axes[2, col].text(0.30, 0.40, "permission granted\n(emergency fallback)",
                              fontsize=5.8, color=INK)
        else:
            hit = collided.index(True)
            pre = series(rows, "ego_speed_kph")[hit - 1]
            axes[0, col].text(t[hit] - 0.04, 18, "impact; last tick\n{:.2f} km/h".format(pre),
                              fontsize=5.8, ha="right", va="bottom", color=INK)
            axes[2, col].text(0.06, 0.40, "radar request\nvetoed (no car box)", fontsize=5.8, color=INK)
    axes[0, 0].set_ylabel("Speed\n[km/h]", labelpad=1)
    axes[1, 0].set_ylabel("Radar\nTTC [s]", labelpad=1)
    axes[2, 0].set_ylabel("Brake\ncmd", labelpad=1)
    fig.subplots_adjust(left=0.125, right=0.99, top=0.93, bottom=0.12)
    fig.savefig(str(path), metadata={"CreationDate": None, "Creator": None, "Producer": None})
    plt.close(fig)


def box(ax, x, y, w, h, text, edge=MUTED, fill="#ffffff", size=6.2, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=0.8",
                                lw=0.7, edgecolor=edge, facecolor=fill))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size,
            color=INK, weight=weight, linespacing=1.15)


def arrow(ax, start, end, color=MUTED, style="-|>", lw=0.7, ls="-"):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle=style, mutation_scale=6,
                                 lw=lw, color=color, linestyle=ls, shrinkA=0, shrinkB=0))


def plot_pipeline(path):
    fig = plt.figure(figsize=(3.5, 1.78))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 51)
    ax.axis("off")
    # Shared radar chain (top) and car-only camera chain (bottom).
    box(ax, 1, 37, 12, 10, "Radar\n0.05 s")
    box(ax, 17, 37, 18, 10, "Path filter,\ncluster, track,\ntarget select")
    box(ax, 39, 37, 17, 10, "Risk: TTC,\nmargin $m$\n$\\rightarrow$ request $B_r$")
    box(ax, 1, 4, 12, 10, "RGB\ncamera")
    box(ax, 17, 4, 18, 10, "YOLO26n\ncar-only\n(0.15 s)")
    box(ax, 39, 4, 17, 10, "Target in\ncar box: $C$;\nhold $H$ 0.35 s")
    arrow(ax, (13.6, 42), (16.4, 42))
    arrow(ax, (35.6, 42), (38.4, 42))
    arrow(ax, (13.6, 9), (16.4, 9))
    arrow(ax, (35.6, 9), (38.4, 9))
    arrow(ax, (30, 36.4), (44, 14.6), ls=(0, (2, 1.5)))
    ax.text(38.6, 26, "projected\ntarget", fontsize=5.6, color=MUTED, va="center")
    # Three late permission policies; colours follow the fixed policy order.
    policies = [
        (33, "radar_only", "Radar-only: $B_r$"),
        (22, "hard_gate", "Hard: $B_r\\wedge(C\\vee H)$"),
        (11, "safe_fallback", "Fallback: $B_r\\wedge(C\\vee H\\vee E_r)$"),
    ]
    for y, key, label in policies:
        box(ax, 61, y, 25, 8, label, edge=COLORS[key], size=5.6)
        arrow(ax, (86.6, y + 4), (89.4, 26 + (y - 22) * 0.3), color=COLORS[key])
    ax.add_patch(FancyBboxPatch((90, 15), 8.5, 22, boxstyle="round,pad=0.3,rounding_size=0.8",
                                lw=0.7, edgecolor=MUTED, facecolor="#ffffff"))
    ax.text(94.25, 26, "Staged PID brake", rotation=90, ha="center", va="center",
            fontsize=6.0, color=INK)
    # Request from risk (solid) and confirmation from camera (dashed) into the policies.
    arrow(ax, (56.6, 42), (60.4, 37))
    arrow(ax, (56.6, 41), (60.4, 26))
    arrow(ax, (56.6, 40), (60.4, 15))
    arrow(ax, (56.6, 10), (60.4, 24.5), ls=(0, (2, 1.5)))
    arrow(ax, (56.6, 8.5), (60.4, 13.5), ls=(0, (2, 1.5)))
    ax.text(61, 0.6, "$E_r$: age, hits $\\geq3$; $\\geq6$ points;\n"
                     "conf. $\\geq0.70$; $|$offset$|\\leq0.65$ m;\n"
                     "TTC $\\leq1.10$ s $\\wedge$ $m\\leq-2.0$ m",
            fontsize=5.0, color=INK, va="bottom", linespacing=1.1)
    ax.text(61, 45.5, "Late brake permission\n(deny $\\Rightarrow$ no brake)", fontsize=5.8,
            color=INK, va="center", linespacing=1.1)
    fig.savefig(str(path), metadata={"CreationDate": None, "Creator": None, "Producer": None})
    plt.close(fig)


def write_traces(traces, selection, path):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("panel", "config", "scenario_id", "run_index") + TRACE_FIELDS)
        for sel in selection:
            for row in traces[sel["panel"]]:
                writer.writerow((sel["panel"], sel["config"], sel["scenario_id"], sel["run_index"])
                                + tuple(row[f] for f in TRACE_FIELDS))


def main():
    archive_sha = verify_archive()
    style()
    FIGURES.mkdir(parents=True, exist_ok=True)
    selection = select_runs()
    traces = load_traces(selection)
    plot_pipeline(FIGURES / PIPELINE_PDF)
    plot_timeseries(traces, selection, FIGURES / TIMESERIES_PDF)
    write_traces(traces, selection, FIGURES / TRACE_CSV)
    (FIGURES / SELECTION_JSON).write_text(json.dumps({
        "archive": str(ARCHIVE.relative_to(ROOT)),
        "archive_sha256": archive_sha,
        "selection": selection,
        "shading": "grey = radar request B_r present (gate action in {})".format(sorted(RADAR_REQUEST_ACTIONS)),
    }, indent=2) + "\n", encoding="utf-8")
    PAPER_FIGURES.mkdir(parents=True, exist_ok=True)
    for name in (PIPELINE_PDF, TIMESERIES_PDF):
        shutil.copyfile(str(FIGURES / name), str(PAPER_FIGURES / name))
    write_checksums()
    for sel in selection:
        print("{panel}: {config} {scenario_id} run {run_index} (tied runs: {tied_runs})".format(**sel))


if __name__ == "__main__":
    main()
