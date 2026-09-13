#!/usr/bin/env python3
"""Read-only checks for v5.1 tables, evidence, bilingual structure and PDFs.

These are consistency checks, not a substitute for scientific/translation review.
No CARLA run, archived CSV or frozen manuscript is rewritten.
"""
from __future__ import annotations

import csv
import hashlib
import re
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / 'paper' / 'paper_v5_1'
EVIDENCE = ROOT / 'docs/log/repeatability/paper_v5_derived'
NUMBER = re.compile(r'(?<![A-Za-z])[-+]?\d*\.\d+|(?<![A-Za-z])[-+]?\d+')
POLICIES = ('radar_only', 'hard_gate', 'safe_fallback')
SCOPES = ('core_without_synthetic_fault', 'frozen_adverse_holdout')
LABELS = ('tab:setup', 'tab:primary', 'tab:paired', 'tab:severity', 'tab:extended')


def read_rows(name):
    with (EVIDENCE / name).open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def select(rows, **criteria):
    found = [row for row in rows if all(row.get(k) == str(v) for k, v in criteria.items())]
    if len(found) != 1:
        raise AssertionError('Non-unique evidence selection: {}'.format(criteria))
    return found[0]


def table(text, label):
    blocks = re.findall(r'\\begin\{table\*?\}.*?\\end\{table\*?\}', text, re.S)
    matches = [block for block in blocks if '\\label{' + label + '}' in block]
    if len(matches) != 1:
        raise AssertionError('Expected one table {}'.format(label))
    return re.search(r'\\begin\{tabular\}.*?\n(.*?)\\end\{tabular\}', matches[0], re.S).group(1)


def data_rows(text, label):
    """Numeric table rows; declarations/headers/labels are not counted."""
    return [line.strip() for line in table(text, label).splitlines()
            if '&' in line and re.search(r'\d', line)]


def numbers(text):
    return [float(value) for value in NUMBER.findall(text)]


def equal(actual, expected, context):
    if actual != expected:
        raise AssertionError('{}: {} != {}'.format(context, actual, expected))


def primary_numbers(row):
    counts = [float(row[k]) for k in ('named_conditions', 'TP', 'FP', 'TN', 'FN')]
    rates = [round(float(row[k]), 3) for k in
             ('precision', 'precision_ci95_low', 'precision_ci95_high',
              'recall', 'recall_ci95_low', 'recall_ci95_high')]
    return counts + rates + [float(row['pass_conditions']), float(row['collision_conditions'])]


def validate_texts(english, vietnamese, bibliography):
    metrics = read_rows('named_scenario_metrics.csv')
    primary = [primary_numbers(select(metrics, scope=scope, config=policy))
               for scope in SCOPES for policy in POLICIES]
    paired = read_rows('named_paired_outcomes.csv')
    expected_pairs = [[float(row[k]) for k in ('both_pass', 'a_only_pass', 'b_only_pass', 'both_fail')]
                      for row in paired]
    extended = []
    for scope, policies in [('perturbation', POLICIES), ('camera_disabled', POLICIES[1:])]:
        for policy in policies:
            row = select(metrics, scope=scope, config=policy)
            extended.append([float(row[k]) for k in ('pass_conditions', 'named_conditions',
                                                    'TP', 'FP', 'TN', 'FN', 'collision_conditions')])
    collisions = read_rows('collision_severity_summary.csv')
    expected_severity = []
    for scenario, policies in [('holdout_cart_center_v50_g18', ('radar_only',)),
                              ('holdout_bench_center_v60_g22', POLICIES),
                              ('holdout_warning_center_v70_g25', ('radar_only',))]:
        for policy in policies:
            row = select(collisions, scope=SCOPES[1], config=policy, scenario_id=scenario)
            # Three-place onset gaps avoid the ambiguous 4.295 -> 4.29/4.30 rounding.
            gap = [float(row['first_brake_gap_m_median'])] if row['first_brake_gap_m_median'] else []
            # Frozen v5 headline uses decimal half-up rounding (59.945 -> 59.95).
            from decimal import Decimal, ROUND_HALF_UP
            speed = float(Decimal(row['preimpact_speed_kph_median']).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
            expected_severity.append(gap + [speed])
    false = read_rows('false_brake_severity_runs.csv')
    for policy, count in [('radar_only', 25), ('safe_fallback', 20)]:
        selected = [row for row in false if row['config'] == policy]
        equal(len(selected), count, 'ghost run count')
        equal(sum(row['stopped_below_1kph'] == 'True' for row in selected), count, 'ghost stops')
        values = [statistics.median(float(row[field]) for row in selected)
                  for field in ('onset_speed_kph', 'brake_duration_s', 'peak_deceleration_mps2')]
        expected_severity.append([float(count), round(values[0], 1), round(values[1], 2), round(values[2], 2), 2.0])
        # Final 2 is the exponent in m/s^2 in both source tables.

    bibkeys = set(re.findall(r'@\w+\{([^,]+),', bibliography))
    cited_sets = []
    for lang, text in [('EN', english), ('VI', vietnamese)]:
        equal([numbers(line) for line in data_rows(text, 'tab:primary')], primary, lang + ' primary')
        equal([numbers(line) for line in data_rows(text, 'tab:paired')], expected_pairs, lang + ' paired')
        equal([numbers(line) for line in data_rows(text, 'tab:extended')], extended, lang + ' extended')
        equal([numbers(line) for line in data_rows(text, 'tab:severity')], expected_severity, lang + ' severity')
        cited = set(key.strip() for group in re.findall(r'\\cite\{([^}]+)\}', text) for key in group.split(','))
        equal(cited, bibkeys, lang + ' bibliography coverage')
        cited_sets.append(cited)
        labels = re.findall(r'\\label\{([^}]+)\}', text)
        equal(len(labels), len(set(labels)), lang + ' duplicate labels')
        missing = set(re.findall(r'\\ref\{([^}]+)\}', text)) - set(labels)
        equal(missing, set(), lang + ' references')
        for token in ('2,461', '74,928', '474', '639', '0.353', '32.57', '54.93', '59.95',
                      '78.4', '3.60', '9.02', '1.10', '-2.0', '0.65', '0.70', '0.35', '0.15',
                      'CUDAExecutionProvider', 'safe-fallback-eval-v1', 'RQ1', 'RQ2', 'RQ3'):
            if token not in text:
                raise AssertionError('{} missing headline/protocol token {}'.format(lang, token))
    equal(cited_sets[0], cited_sets[1], 'bilingual citations')
    for label in LABELS:
        equal(numbers(table(english, label)), numbers(table(vietnamese, label)), 'bilingual table ' + label)
    for kind in ('section', 'subsection'):
        equal(len(re.findall(r'\\' + kind + r'\{', english)),
              len(re.findall(r'\\' + kind + r'\{', vietnamese)), 'bilingual ' + kind)
    equal(re.findall(r'\\begin\{(?:equation|align)\}(.*?)\\end\{(?:equation|align)\}', english, re.S),
          re.findall(r'\\begin\{(?:equation|align)\}(.*?)\\end\{(?:equation|align)\}', vietnamese, re.S),
          'bilingual equations')
    for text, phrases in [(english, ['post-hoc', 'knowledge of the rule', 'not a calibrated',
                                     'not an impossibility theorem', 'road-population inference']),
                          (vietnamese, ['hậu nghiệm', 'đã biết luật', 'không phải', 'không phải định lý bất khả'])]:
        flat = ' '.join(text.split())
        for phrase in phrases:
            if phrase not in flat:
                raise AssertionError('Missing interpretation safeguard: ' + phrase)


def pdf_pages(path):
    output = subprocess.check_output(['pdfinfo', str(path)], universal_newlines=True)
    return int(re.search(r'^Pages:\s+(\d+)', output, re.M).group(1))


def validate_package():
    english = (PAPER / 'aeb_ieee_6page.tex').read_text(encoding='utf-8')
    vietnamese = (PAPER / 'aeb_ieee_6page_vi.tex').read_text(encoding='utf-8')
    validate_texts(english, vietnamese, (PAPER / 'references.bib').read_text(encoding='utf-8'))
    equal(pdf_pages(PAPER / 'aeb_ieee_6page.pdf'), 6, 'English page budget')
    if pdf_pages(PAPER / 'aeb_ieee_6page_vi.pdf') < 1:
        raise AssertionError('Empty Vietnamese review PDF')
    for stem in ('aeb_ieee_6page', 'aeb_ieee_6page_vi'):
        text = subprocess.check_output(['pdftotext', str(PAPER / (stem + '.pdf')), '-'], universal_newlines=True)
        if '\ufffd' in text or not all(token in text for token in ('32.57', '54.93', '59.95', '0.353')):
            raise AssertionError('PDF text extraction failed: ' + stem)
        log = PAPER / (stem + '.log')
        if log.exists() and re.search(r'Citation .* undefined|Reference .* undefined|Missing character:|Overfull \\hbox', log.read_text()):
            raise AssertionError('Unresolved glyph/reference or horizontal overflow: ' + stem)
    frozen_figure = EVIDENCE / 'figures/scenario_level_tradeoff.png'
    equal(hashlib.sha256((PAPER / 'figures/scenario_level_tradeoff.png').read_bytes()).hexdigest(),
          hashlib.sha256(frozen_figure.read_bytes()).hexdigest(), 'unchanged evidence figure')


def main():
    validate_package()
    print('PASS: v5.1 primary/paired/extended/severity tables match frozen CSV; bilingual equations, citations and PDFs checked.')


if __name__ == '__main__':
    main()
