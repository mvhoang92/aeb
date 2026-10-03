"""Tests for the paper-v5.2 exact paired McNemar derivation."""

from __future__ import annotations

import csv
import unittest
from fractions import Fraction

from scripts.analysis import analyze_v52_paired_tests as paired


class ExactMcNemarTest(unittest.TestCase):
    def test_no_discordant_pairs_gives_one(self):
        self.assertEqual(paired.exact_mcnemar_p(0, 0), Fraction(1))

    def test_one_sided_discordance_is_doubled_tail(self):
        # 0 vs 8: 2 * (1/2)^8
        self.assertEqual(paired.exact_mcnemar_p(0, 8), Fraction(2, 256))
        self.assertEqual(paired.exact_mcnemar_p(4, 0), Fraction(2, 16))
        self.assertEqual(paired.exact_mcnemar_p(0, 5), Fraction(2, 32))

    def test_mixed_discordance(self):
        # 2 vs 8: 2 * (C(10,0) + C(10,1) + C(10,2)) / 2^10 = 112/1024
        self.assertEqual(paired.exact_mcnemar_p(2, 8), Fraction(112, 1024))

    def test_symmetric_and_capped_at_one(self):
        self.assertEqual(paired.exact_mcnemar_p(3, 7), paired.exact_mcnemar_p(7, 3))
        self.assertEqual(paired.exact_mcnemar_p(0, 1), Fraction(1))
        self.assertEqual(paired.exact_mcnemar_p(5, 5), Fraction(1))

    def test_rejects_negative_counts(self):
        with self.assertRaises(ValueError):
            paired.exact_mcnemar_p(-1, 2)

    def test_binomial_matches_pascal(self):
        for n in range(12):
            row = [paired.binomial(n, k) for k in range(n + 1)]
            self.assertEqual(sum(row), 2 ** n)
            self.assertEqual(row, row[::-1])

    def test_paired_table_counts(self):
        a = {"x": True, "y": True, "z": False, "w": False}
        b = {"x": True, "y": False, "z": True, "w": False}
        self.assertEqual(paired.paired_table(a, b), {
            "paired_named_conditions": 4, "both_pass": 1, "a_only_pass": 1,
            "b_only_pass": 1, "both_fail": 1,
        })

    def test_paired_table_requires_same_conditions(self):
        with self.assertRaises(ValueError):
            paired.paired_table({"x": True}, {"y": True})


class FrozenEvidenceTest(unittest.TestCase):
    def test_derivation_reproduces_frozen_pairs_and_committed_csv(self):
        results = paired.derive()  # raises if counts differ from v5 frozen pairs
        with (paired.OUT / paired.CSV_NAME).open(newline="", encoding="utf-8") as stream:
            committed = list(csv.DictReader(stream))
        self.assertEqual(len(committed), 6)
        for row, frozen in zip(results, committed):
            for field in paired.FIELDS:
                self.assertEqual(str(row[field]), frozen[field], field)
        by_pair = {(r["scope"], r["policy_a"], r["policy_b"]): r for r in results}
        core = by_pair[("core_without_synthetic_fault", "radar_only", "safe_fallback")]
        self.assertEqual((core["a_only_pass"], core["b_only_pass"], core["exact_p_two_sided"]), (0, 8, "0.0078"))
        hold = by_pair[("frozen_adverse_holdout", "hard_gate", "safe_fallback")]
        self.assertEqual((hold["a_only_pass"], hold["b_only_pass"], hold["exact_p_two_sided"]), (4, 0, "0.1250"))


class ManuscriptValidatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.analysis import validate_v52_manuscript_claims as validator

        cls.validator = validator
        cls.english = (validator.PAPER / "aeb_ieee_6page.tex").read_text(encoding="utf-8")
        cls.vietnamese = (validator.PAPER / "aeb_ieee_6page_vi.tex").read_text(encoding="utf-8")
        cls.bibliography = (validator.PAPER / "references.bib").read_text(encoding="utf-8")

    def test_committed_sources_pass(self):
        self.validator.validate_texts(self.english, self.vietnamese, self.bibliography)

    def test_altered_mcnemar_value_is_rejected(self):
        altered = self.english.replace("& 0.0078", "& 0.0080", 1)
        self.assertNotEqual(altered, self.english)
        with self.assertRaises(AssertionError):
            self.validator.validate_texts(altered, self.vietnamese, self.bibliography)

    def test_number_removed_from_body_is_rejected(self):
        altered = self.english.replace("median onset speed of 78.4 km/h", "median onset speed", 1)
        self.assertNotEqual(altered, self.english)
        with self.assertRaises(AssertionError):
            self.validator.validate_texts(altered, self.vietnamese, self.bibliography)

    def test_story_number_removed_from_abstract_is_rejected(self):
        abstract, _ = self.validator.split_abstract(self.english)
        altered = self.english.replace(abstract, abstract.replace("11/14", "most", 1), 1)
        with self.assertRaises(AssertionError):
            self.validator.validate_texts(altered, self.vietnamese, self.bibliography)

    def test_unbalanced_citation_is_rejected(self):
        altered = self.vietnamese.replace("\\cite{mcnemar1947}", "", 1)
        with self.assertRaises(AssertionError):
            self.validator.validate_texts(self.english, altered, self.bibliography)


if __name__ == "__main__":
    unittest.main()
