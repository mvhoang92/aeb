#!/usr/bin/env python3
"""Validate paper-v5 claims, bilingual parity and PDF page gates."""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "paper_v5"
EVIDENCE = ROOT / "docs" / "log" / "repeatability" / "paper_v5_derived"


def rows(name):
    with (EVIDENCE / name).open(newline="") as stream:
        return list(csv.DictReader(stream))


def one(items, **criteria):
    found = [row for row in items if all(row.get(key) == str(value) for key, value in criteria.items())]
    if len(found) != 1:
        raise AssertionError("Expected one row for {}, got {}".format(criteria, len(found)))
    return found[0]


def pages(path):
    text = subprocess.check_output(["pdfinfo", str(path)], universal_newlines=True)
    return int(next(line.split(":", 1)[1] for line in text.splitlines() if line.startswith("Pages:")))


def main():
    metrics = rows("named_scenario_metrics.csv")
    expected = {
        ("core_without_synthetic_fault", "radar_only"): ("105", "84", "8", "12", "1", "93", "3"),
        ("core_without_synthetic_fault", "hard_gate"): ("105", "82", "0", "20", "3", "99", "5"),
        ("core_without_synthetic_fault", "safe_fallback"): ("105", "84", "0", "20", "1", "101", "3"),
        ("frozen_adverse_holdout", "radar_only"): ("14", "6", "5", "2", "1", "6", "3"),
        ("frozen_adverse_holdout", "hard_gate"): ("14", "5", "0", "7", "2", "11", "3"),
        ("frozen_adverse_holdout", "safe_fallback"): ("14", "6", "4", "3", "1", "7", "3"),
        ("perturbation", "safe_fallback"): ("20", "20", "0", "0", "0", "18", "1"),
    }
    fields = ("named_conditions", "TP", "FP", "TN", "FN", "pass_conditions", "collision_conditions")
    for (scope, config), wanted in expected.items():
        row = one(metrics, scope=scope, config=config)
        actual = tuple(row[field] for field in fields)
        if actual != wanted:
            raise AssertionError("Metric mismatch {} {}: {} != {}".format(scope, config, actual, wanted))

    false_summary = rows("false_brake_severity_summary.csv")
    fallback = one(false_summary, config="safe_fallback", scenario_id="holdout_ghost_6pt_center")
    if (fallback["onset_speed_kph_median"], fallback["brake_duration_s_median"], fallback["stopped_runs"]) != ("78.368", "3.6", "5"):
        raise AssertionError("Six-point fallback severity mismatch")
    all_false = rows("false_brake_severity_runs.csv")
    fallback_runs = [row for row in all_false if row["config"] == "safe_fallback"]
    if len(fallback_runs) != 20 or sum(row["stopped_below_1kph"] == "True" for row in fallback_runs) != 20:
        raise AssertionError("Fallback ghost-stop count mismatch")

    collisions = rows("collision_severity_summary.csv")
    bench_expected = {"radar_only": "32.574", "hard_gate": "59.945", "safe_fallback": "54.932"}
    for config, speed in bench_expected.items():
        row = one(collisions, scope="frozen_adverse_holdout", config=config, scenario_id="holdout_bench_center_v60_g22")
        if row["preimpact_speed_kph_median"] != speed:
            raise AssertionError("Bench severity mismatch for {}".format(config))

    english = (PAPER / "aeb_ieee_6page.tex").read_text(encoding="utf-8")
    vietnamese = (PAPER / "aeb_ieee_6page_vi.tex").read_text(encoding="utf-8")
    required_en = ["105", "14-condition", "named condition", "78.4", "3.60", "9.02", "32.57", "54.93", "59.95", "0.353"]
    required_vi = ["105", "14 điều kiện", "named condition", "78,4", "3,60", "9,02", "32,57", "54,93", "59,95", "0,353"]
    for label, text, tokens in (("English", english, required_en), ("Vietnamese", vietnamese, required_vi)):
        missing = [token for token in tokens if token not in text]
        if missing:
            raise AssertionError("{} source missing {}".format(label, missing))

    def structure(text):
        sections = len(re.findall(r"^\\(?:section|subsection)\{", text, re.MULTILINE))
        tables = len(re.findall(r"^\\begin\{table\*?\}", text, re.MULTILINE))
        figures = len(re.findall(r"^\\begin\{figure\*?\}", text, re.MULTILINE))
        cited = set()
        for group in re.findall(r"\\cite\{([^}]+)\}", text):
            cited.update(item.strip() for item in group.split(","))
        return sections, tables, figures, cited

    en_structure = structure(english)
    vi_structure = structure(vietnamese)
    if en_structure[:3] != (16, 4, 1) or vi_structure[:3] != (16, 4, 1):
        raise AssertionError("Bilingual structural count mismatch: {} {}".format(en_structure[:3], vi_structure[:3]))
    if en_structure[3] != vi_structure[3] or len(en_structure[3]) != 15:
        raise AssertionError("Bilingual citations are not equivalent")

    if pages(PAPER / "aeb_ieee_6page.pdf") != 6:
        raise AssertionError("English PDF is not six pages")
    if pages(PAPER / "aeb_ieee_6page_vi.pdf") != 5:
        raise AssertionError("Vietnamese review PDF is not five pages")

    forbidden = ["collisions remain at 19- and 21-m gaps", "collisions remain at 19 and 21"]
    if any(phrase in english for phrase in forbidden):
        raise AssertionError("Paper retains corrected perturbation wording")

    print("PASS: paper v5 claims, named-condition evidence, severity and bilingual parity are consistent.")


if __name__ == "__main__":
    main()
