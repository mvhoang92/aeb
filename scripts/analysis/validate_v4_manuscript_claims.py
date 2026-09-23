#!/usr/bin/env python3
"""Fail if headline report/paper claims diverge from generated final CSV."""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs" / "log" / "repeatability" / "paper_v4_gpu_final"


def read_rows(name):
    with open(str(EVIDENCE / name), newline="") as stream:
        return list(csv.DictReader(stream))


def row_by(rows, **criteria):
    matches = [
        row
        for row in rows
        if all(str(row.get(key)) == str(value) for key, value in criteria.items())
    ]
    if len(matches) != 1:
        raise AssertionError("Expected one row for {}, got {}".format(criteria, len(matches)))
    return matches[0]


def require(text, tokens, label):
    missing = [token for token in tokens if token not in text]
    if missing:
        raise AssertionError("{} is missing claims: {}".format(label, missing))


def main():
    core = read_rows("core_confusion_metrics.csv")
    section = read_rows("section_metrics.csv")
    latency = read_rows("gpu_latency.csv")[0]

    expected_core = {
        "radar_only": ("420", "40", "60", "5", "0.913", "0.9882", "15"),
        "hard_gate": ("410", "0", "100", "15", "1.0", "0.9647", "25"),
        "safe_fallback": ("420", "0", "100", "5", "1.0", "0.9882", "15"),
    }
    for config, expected in expected_core.items():
        row = row_by(core, config=config, scope="without_synthetic_fault")
        actual = (
            row["TP"], row["FP"], row["TN"], row["FN"],
            row["precision"], row["recall"], row["collision"],
        )
        if actual != expected:
            raise AssertionError("Core mismatch {}: {} != {}".format(config, actual, expected))

    expected_holdout = {
        "radar_only": ("30", "25", "10", "5", "30", "15"),
        "hard_gate": ("25", "0", "35", "10", "55", "15"),
        "safe_fallback": ("30", "20", "15", "5", "35", "15"),
    }
    for config, expected in expected_holdout.items():
        row = row_by(section, section="holdout", config=config)
        actual = (row["TP"], row["FP"], row["TN"], row["FN"], row["pass"], row["collision"])
        if actual != expected:
            raise AssertionError("Hold-out mismatch {}: {} != {}".format(config, actual, expected))

    if (latency["cuda_sessions"], latency["inference_count"], latency["inference_errors"]) != ("474", "74928", "0"):
        raise AssertionError("CUDA headline mismatch: {}".format(latency))

    report = (ROOT / "report" / "report_v3.md").read_text(encoding="utf-8")
    english = (ROOT / "paper" / "paper_v4" / "aeb_ieee_6page.tex").read_text(encoding="utf-8")
    vietnamese = (ROOT / "paper" / "paper_v4" / "aeb_ieee_6page_vi.tex").read_text(encoding="utf-8")
    require(report, ["2.461", "639", "0,913", "0,988", "35/70", "20/25", "74.928"], "report_v3")
    require(english, ["2,461", "639", "0.913", "0.988", "35/70", "74,928", "276.10"], "English paper")
    require(vietnamese, ["2.461", "639", "0,913", "0,988", "35/70", "74.928", "276,10"], "Vietnamese paper")

    forbidden = {
        "report_v3": (report, ["Autonomous Emergency Braking", "deterministic physics"]),
        "English paper": (english, ["perfect precision", "real-time automotive deployment"]),
        "Vietnamese paper": (vietnamese, ["precision hoàn hảo", "kiểm định xe thật thành công"]),
    }
    for label, (text, phrases) in forbidden.items():
        found = [phrase for phrase in phrases if phrase in text]
        if found:
            raise AssertionError("{} contains forbidden wording: {}".format(label, found))

    english_pdf = ROOT / "paper" / "paper_v4" / "aeb_ieee_6page.pdf"
    if english_pdf.exists():
        output = subprocess.check_output(["pdfinfo", str(english_pdf)], universal_newlines=True)
        pages = next(line.split(":", 1)[1].strip() for line in output.splitlines() if line.startswith("Pages:"))
        if pages != "6":
            raise AssertionError("English paper has {} pages, expected 6".format(pages))

    print("PASS: report v3 and paper v4 headline claims match generated evidence.")


if __name__ == "__main__":
    main()
