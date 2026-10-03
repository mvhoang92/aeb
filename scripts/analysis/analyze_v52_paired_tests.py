#!/usr/bin/env python3
"""Exact paired (McNemar) comparisons of the three brake-permission policies.

Paper v5.2 derivation. Reads only frozen, git-tracked evidence:

* ``paper_v4_gpu_final/scenario_consistency.csv`` -- per named condition and
  policy, the repeated-run outcome (every condition is all-PASS or all-FAIL);
* ``paper_v5_derived/named_paired_outcomes.csv`` -- the frozen paired table
  used by paper v5/v5.1, against which the recomputed counts are cross-checked.

For each policy pair and scope (core benchmark without synthetic-fault rows;
frozen adverse hold-out) it reports the 2x2 paired table of named-condition
system PASS and the exact two-sided McNemar test, i.e. the conditional
binomial test of the discordant pairs against Binomial(b + c, 1/2).

Interpretation is descriptive: the named conditions form a constructed,
non-random grid, so the p-values quantify how lopsided the discordant pairs
are on that grid; they are not inference about a road-traffic population.
Repeated runs are never treated as independent pairs. No CARLA run is added,
removed or re-executed.
"""

from __future__ import annotations

import csv
import hashlib
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPEATABILITY = ROOT / "docs" / "log" / "repeatability"
CONSISTENCY = REPEATABILITY / "paper_v4_gpu_final" / "scenario_consistency.csv"
FROZEN_PAIRS = REPEATABILITY / "paper_v5_derived" / "named_paired_outcomes.csv"
OUT = REPEATABILITY / "paper_v5_2_derived"
CSV_NAME = "paired_exact_mcnemar.csv"
JSON_NAME = "paired_exact_mcnemar.json"

POLICIES = ("radar_only", "hard_gate", "safe_fallback")
PAIRS = (("radar_only", "hard_gate"), ("radar_only", "safe_fallback"), ("hard_gate", "safe_fallback"))
SCOPES = {
    "core_without_synthetic_fault": (
        "system_limit_extended_sweep",
        "radar_only_regression",
        "fusion_physical_false_positive_v2",
        "fusion_nonvehicle_hazard_limitation",
    ),
    "frozen_adverse_holdout": ("holdout",),
}
FIELDS = (
    "scope", "policy_a", "policy_b", "paired_named_conditions", "both_pass",
    "a_only_pass", "b_only_pass", "both_fail", "discordant", "exact_p_two_sided",
)


def binomial(n, k):
    """n choose k for Python 3.7 (no math.comb)."""
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    value = 1
    for i in range(1, k + 1):
        value = value * (n - k + i) // i
    return value


def exact_mcnemar_p(b, c):
    """Exact two-sided McNemar p-value (conditional binomial, doubled tail).

    Returns a :class:`fractions.Fraction`; p = 1 when there is no discordant pair.
    """
    if b < 0 or c < 0:
        raise ValueError("discordant counts must be non-negative")
    n = b + c
    if n == 0:
        return Fraction(1)
    tail = sum(binomial(n, k) for k in range(min(b, c) + 1))
    return min(Fraction(1), Fraction(2 * tail, 2 ** n))


def paired_table(status_a, status_b):
    """2x2 paired counts from two {condition: passed} maps on common keys."""
    common = sorted(set(status_a) & set(status_b))
    if set(status_a) != set(status_b):
        raise ValueError("policies do not share the same named conditions")
    return {
        "paired_named_conditions": len(common),
        "both_pass": sum(status_a[k] and status_b[k] for k in common),
        "a_only_pass": sum(status_a[k] and not status_b[k] for k in common),
        "b_only_pass": sum(not status_a[k] and status_b[k] for k in common),
        "both_fail": sum(not status_a[k] and not status_b[k] for k in common),
    }


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def status_maps(rows):
    """{(scope, policy): {(suite, scenario): passed}} from scenario_consistency."""
    maps = {(scope, policy): {} for scope in SCOPES for policy in POLICIES}
    for row in rows:
        if row["outcome"] not in ("all_pass", "all_fail"):
            raise ValueError("mixed repeated outcome: {}".format(row))
        for scope, suites in SCOPES.items():
            if row["suite"] in suites and row["config"] in POLICIES:
                maps[(scope, row["config"])][(row["suite"], row["scenario_id"])] = row["outcome"] == "all_pass"
    return maps


def derive():
    maps = status_maps(read_csv(CONSISTENCY))
    frozen = {(r["scope"], r["policy_a"], r["policy_b"]): r for r in read_csv(FROZEN_PAIRS)}
    results = []
    for scope in SCOPES:
        for policy_a, policy_b in PAIRS:
            table = paired_table(maps[(scope, policy_a)], maps[(scope, policy_b)])
            reference = frozen[(scope, policy_a, policy_b)]
            for key, value in table.items():
                if int(reference[key]) != value:
                    raise AssertionError("{} {}/{} {}: {} != frozen {}".format(
                        scope, policy_a, policy_b, key, value, reference[key]))
            p = exact_mcnemar_p(table["a_only_pass"], table["b_only_pass"])
            row = {"scope": scope, "policy_a": policy_a, "policy_b": policy_b}
            row.update(table)
            row["discordant"] = table["a_only_pass"] + table["b_only_pass"]
            row["exact_p_two_sided"] = "{:.4f}".format(float(p))
            row["exact_p_fraction"] = "{}/{}".format(p.numerator, p.denominator)
            results.append(row)
    return results


def main():
    results = derive()
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / CSV_NAME).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)
    document = {
        "description": "Exact two-sided McNemar tests on named-condition system PASS, paper v5.2.",
        "test": "Conditional binomial test of discordant pairs, p = min(1, 2*P[X <= min(b, c)]), X ~ Binomial(b + c, 1/2).",
        "unit": "named condition (repeats are all-PASS or all-FAIL and are not counted as pairs)",
        "framing": ("Descriptive on a constructed, non-random condition grid: no road-population "
                    "inference, no multiplicity correction claimed, discordant counts reported alongside p."),
        "inputs": {
            str(CONSISTENCY.relative_to(ROOT)): sha256(CONSISTENCY),
            str(FROZEN_PAIRS.relative_to(ROOT)): sha256(FROZEN_PAIRS),
        },
        "cross_check": "2x2 counts recomputed from scenario_consistency.csv equal named_paired_outcomes.csv",
        "results": results,
    }
    (OUT / JSON_NAME).write_text(json.dumps(document, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    write_checksums()
    for row in results:
        print("{scope:30s} {policy_a:>10s}/{policy_b:<13s} b={a_only_pass} c={b_only_pass} p={exact_p_two_sided}".format(**row))


def write_checksums():
    """SHA256SUMS.txt over every derived file in the output directory."""
    files = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    lines = ["{}  {}".format(sha256(p), p.relative_to(ROOT)) for p in files]
    (OUT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
