#!/usr/bin/env python3
"""Read-only checks for the paper v5.2 package.

Modeled on the v5.1 validator: all manuscript tables must match frozen CSV
files, the new McNemar column must match the committed v5.2 derivation (which
is itself recomputed here), both languages must share equations, citations,
labels, figures and table numbers, the derived-evidence checksums must hold,
and the PDFs must exist with an English page budget of at most six pages.
These are consistency checks, not a substitute for scientific/translation
review. Nothing is written.
"""
from __future__ import annotations

import csv
import hashlib
import re
import statistics
import subprocess
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.analysis import analyze_v52_paired_tests as paired  # noqa: E402

PAPER = ROOT / 'paper' / 'paper_v5_2'
EVIDENCE = ROOT / 'docs/log/repeatability/paper_v5_derived'
DERIVED = ROOT / 'docs/log/repeatability/paper_v5_2_derived'
NUMBER = re.compile(r'(?<![A-Za-z])[-+]?\d*\.\d+|(?<![A-Za-z])[-+]?\d+')
POLICIES = ('radar_only', 'hard_gate', 'safe_fallback')
SCOPES = ('core_without_synthetic_fault', 'frozen_adverse_holdout')
LABELS = ('tab:setup', 'tab:primary', 'tab:paired', 'tab:severity', 'tab:extended')
FIGURES = ('pipeline_permission_policies.pdf', 'timeseries_ghost_vs_bench.pdf')
FIGURE_LABELS = ('fig:pipeline', 'fig:timeseries')
MIN_REFERENCES = 30
ARTIFACT_MACRO = r'\newcommand{\artifactdoi}'


def read_rows(path):
    with path.open(newline='', encoding='utf-8') as stream:
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
    return [line.strip() for line in table(text, label).splitlines()
            if '&' in line and re.search(r'\d', line)]


def numbers(text):
    return [float(value) for value in NUMBER.findall(text)]


def equal(actual, expected, context):
    if actual != expected:
        raise AssertionError('{}: {} != {}'.format(context, actual, expected))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def primary_numbers(row):
    counts = [float(row[k]) for k in ('named_conditions', 'TP', 'FP', 'TN', 'FN')]
    rates = [round(float(row[k]), 3) for k in
             ('precision', 'precision_ci95_low', 'precision_ci95_high',
              'recall', 'recall_ci95_low', 'recall_ci95_high')]
    return counts + rates + [float(row['pass_conditions']), float(row['collision_conditions'])]


def expected_tables():
    metrics = read_rows(EVIDENCE / 'named_scenario_metrics.csv')
    primary = [primary_numbers(select(metrics, scope=scope, config=policy))
               for scope in SCOPES for policy in POLICIES]
    frozen_pairs = read_rows(EVIDENCE / 'named_paired_outcomes.csv')
    mcnemar = read_rows(DERIVED / paired.CSV_NAME)
    recomputed = paired.derive()
    equal(len(mcnemar), len(frozen_pairs), 'McNemar rows')
    paired_rows = []
    for frozen, derived, fresh in zip(frozen_pairs, mcnemar, recomputed):
        for key in ('scope', 'policy_a', 'policy_b', 'both_pass', 'a_only_pass', 'b_only_pass', 'both_fail'):
            equal(derived[key], frozen[key], 'McNemar CSV vs frozen pairs ' + key)
        for key in paired.FIELDS:
            equal(str(fresh[key]), derived[key], 'McNemar recomputation ' + key)
        paired_rows.append([float(frozen[k]) for k in ('both_pass', 'a_only_pass', 'b_only_pass', 'both_fail')]
                           + [float(derived['exact_p_two_sided'])])
    extended = []
    for scope, policies in [('perturbation', POLICIES), ('camera_disabled', POLICIES[1:])]:
        for policy in policies:
            row = select(metrics, scope=scope, config=policy)
            extended.append([float(row[k]) for k in ('pass_conditions', 'named_conditions',
                                                    'TP', 'FP', 'TN', 'FN', 'collision_conditions')])
    collisions = read_rows(EVIDENCE / 'collision_severity_summary.csv')
    severity = []
    for scenario, policies in [('holdout_cart_center_v50_g18', ('radar_only',)),
                               ('holdout_bench_center_v60_g22', POLICIES),
                               ('holdout_warning_center_v70_g25', ('radar_only',))]:
        for policy in policies:
            row = select(collisions, scope=SCOPES[1], config=policy, scenario_id=scenario)
            gap = [float(row['first_brake_gap_m_median'])] if row['first_brake_gap_m_median'] else []
            speed = float(Decimal(row['preimpact_speed_kph_median']).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
            severity.append(gap + [speed])
    false = read_rows(EVIDENCE / 'false_brake_severity_runs.csv')
    for policy, count in [('radar_only', 25), ('safe_fallback', 20)]:
        selected = [row for row in false if row['config'] == policy]
        equal(len(selected), count, 'ghost run count')
        equal(sum(row['stopped_below_1kph'] == 'True' for row in selected), count, 'ghost stops')
        values = [statistics.median(float(row[field]) for row in selected)
                  for field in ('onset_speed_kph', 'brake_duration_s', 'peak_deceleration_mps2')]
        severity.append([float(count), round(values[0], 1), round(values[1], 2), round(values[2], 2), 2.0])
    return {'tab:primary': primary, 'tab:paired': paired_rows,
            'tab:extended': extended, 'tab:severity': severity}


def cited_keys(text):
    return set(key.strip() for group in re.findall(r'\\cite\{([^}]+)\}', text) for key in group.split(','))


def validate_texts(english, vietnamese, bibliography):
    expected = expected_tables()
    bibkeys = set(re.findall(r'@\w+\{([^,]+),', bibliography))
    if len(bibkeys) < MIN_REFERENCES:
        raise AssertionError('Expected at least {} references, found {}'.format(MIN_REFERENCES, len(bibkeys)))
    for lang, text in [('EN', english), ('VI', vietnamese)]:
        for label, rows in expected.items():
            equal([numbers(line) for line in data_rows(text, label)], rows, '{} {}'.format(lang, label))
        equal(cited_keys(text), bibkeys, lang + ' bibliography coverage')
        labels = re.findall(r'\\label\{([^}]+)\}', text)
        equal(len(labels), len(set(labels)), lang + ' duplicate labels')
        equal(set(re.findall(r'\\ref\{([^}]+)\}', text)) - set(labels), set(), lang + ' references')
        for label in FIGURE_LABELS:
            if label not in labels or '\\ref{' + label + '}' not in text:
                raise AssertionError('{} figure {} missing or never referenced'.format(lang, label))
        equal(sorted(re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', text)), sorted(FIGURES),
              lang + ' figures')
        if ARTIFACT_MACRO not in text or text.count('\\artifactdoi') < 2:
            raise AssertionError(lang + ' artifact DOI macro missing or unused')
        for token in ('2,461', '74,928', '474', '639', '0.353', '32.57', '54.93', '59.95',
                      '78.4', '3.60', '9.02', '1.10', '-2.0', '0.65', '0.70', '0.35', '0.15',
                      'CUDAExecutionProvider', 'safe-fallback-eval-v1', 'RQ1', 'RQ2', 'RQ3'):
            if token not in text:
                raise AssertionError('{} missing headline/protocol token {}'.format(lang, token))
    for label in LABELS:
        equal(numbers(table(english, label)), numbers(table(vietnamese, label)), 'bilingual table ' + label)
    for kind in ('section', 'subsection'):
        equal(len(re.findall(r'\\' + kind + r'\{', english)),
              len(re.findall(r'\\' + kind + r'\{', vietnamese)), 'bilingual ' + kind)
    equation = r'\\begin\{(?:equation|align)\}(.*?)\\end\{(?:equation|align)\}'
    equal(re.findall(equation, english, re.S), re.findall(equation, vietnamese, re.S), 'bilingual equations')
    if re.search(r'[^\x00-\x7f]', english):
        raise AssertionError('English pdfLaTeX source must be ASCII')
    for text, phrases in [(english, ['post-hoc', 'knowledge of the rule', 'not a calibrated',
                                     'not an impossibility theorem', 'road-population inference',
                                     'exact two-sided McNemar', 'without multiplicity adjustment',
                                     'not a new fusion primitive']),
                          (vietnamese, ['hậu nghiệm', 'đã biết luật', 'không phải', 'không phải kết luận về mọi',
                                        'McNemar chính xác hai phía', 'không hiệu chỉnh đa so sánh'])]:
        flat = ' '.join(text.split())
        for phrase in phrases:
            if phrase not in flat:
                raise AssertionError('Missing interpretation safeguard: ' + phrase)


def validate_checksums():
    manifest = (DERIVED / 'SHA256SUMS.txt').read_text(encoding='utf-8').split('\n')
    entries = [line.split('  ', 1) for line in manifest if line.strip()]
    if not entries:
        raise AssertionError('Empty v5.2 derived checksum manifest')
    for digest, relative in entries:
        equal(sha256(ROOT / relative), digest, 'derived checksum ' + relative)
    listed = {relative for _, relative in entries}
    present = {str(p.relative_to(ROOT)) for p in DERIVED.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.txt'}
    equal(present, listed, 'derived checksum coverage')
    for name in FIGURES:
        equal(sha256(PAPER / 'figures' / name), sha256(DERIVED / 'figures' / name), 'paper figure ' + name)


def pdf_pages(path):
    output = subprocess.check_output(['pdfinfo', str(path)], universal_newlines=True)
    return int(re.search(r'^Pages:\s+(\d+)', output, re.M).group(1))


def validate_package():
    english = (PAPER / 'aeb_ieee_6page.tex').read_text(encoding='utf-8')
    vietnamese = (PAPER / 'aeb_ieee_6page_vi.tex').read_text(encoding='utf-8')
    validate_texts(english, vietnamese, (PAPER / 'references.bib').read_text(encoding='utf-8'))
    validate_checksums()
    pages = pdf_pages(PAPER / 'aeb_ieee_6page.pdf')
    if pages > 6:
        raise AssertionError('English page budget exceeded: {} pages'.format(pages))
    if pdf_pages(PAPER / 'aeb_ieee_6page_vi.pdf') < 1:
        raise AssertionError('Empty Vietnamese review PDF')
    for stem in ('aeb_ieee_6page', 'aeb_ieee_6page_vi'):
        text = subprocess.check_output(['pdftotext', str(PAPER / (stem + '.pdf')), '-'], universal_newlines=True)
        if '\ufffd' in text or not all(token in text for token in ('32.57', '54.93', '59.95', '0.353', '0.0078')):
            raise AssertionError('PDF text extraction failed: ' + stem)
        log = PAPER / (stem + '.log')
        if log.exists() and re.search(r'Citation .* undefined|Reference .* undefined|Missing character:',
                                      log.read_text(errors='replace')):
            raise AssertionError('Unresolved glyph/reference: ' + stem)
    return pages


def main():
    pages = validate_package()
    print('PASS: v5.2 tables match frozen CSV and McNemar derivation; bilingual equations, citations, '
          'figures and checksums checked; English PDF {} pages.'.format(pages))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
