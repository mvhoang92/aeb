# Paper v5.1 — Camera-Gated AEB Failure Analysis

## Status

English submission draft and Vietnamese author-reading copy. This is a new
paper generation; `paper/paper_v5/` is unchanged. The scientific campaign is
the frozen v4 CUDA campaign, with v5-derived severity/statistics reused without
adding or removing a CARLA run.

## Positioning

The paper is an empirical, mechanism- and severity-aware comparison of three
late brake-permission policies:

1. radar-only;
2. hard camera gate;
3. camera gate with radar emergency fallback.

It does not claim a new fusion detector, calibrated probabilistic tracker,
road-population prevalence, real-time ECU performance, vehicle validation,
Euro NCAP compliance or functional-safety certification.

## Files

- `aeb_ieee_6page.tex/.pdf`: English submission draft, exactly six pages.
- `aeb_ieee_6page_vi.tex/.pdf`: Vietnamese copy for author review.
- `references.bib`: bibliography including the closest verification, ghost,
  corner-case and probabilistic-threat studies.
- `figures/scenario_level_tradeoff.png`: copied unchanged from v5-derived
  evidence.
- `CLAIM_EVIDENCE_MATRIX.md`: claim-to-source mapping.
- `SOURCE_MAP.md`: frozen campaign and derivation paths.
- `SELF_REVIEW.md`: scope and reviewer-risk review.
- `CHANGELOG.md`: differences from v5.
- `SHA256SUMS.txt`: hashes of the manuscript package.

## Rebuild and validate

```bash
cd /home/mvhoang/CARLA_0.9.11/aeb/paper/paper_v5_1
./build.sh
cd ../..
/home/mvhoang/CARLA_0.9.11/venv/bin/python scripts/analysis/validate_v51_manuscript_claims.py
```

The validator checks all primary, paired, extended and severity tables against
frozen CSV files, citation coverage, bilingual equations/table numerics, PDF
text and page budget. A successful build is not a substitute for final author,
venue and plagiarism review.
