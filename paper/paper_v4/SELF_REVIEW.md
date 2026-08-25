# Structured Self-Review — Paper v4

## Overall verdict

**Recommended as a final engineering-simulation manuscript after the fixes listed below.** The paper is strongest as a reproducible trade-off and failure-analysis study. It must not be presented as road-safety validation or as proof that fallback is universally fail-safe.

## Review round 1 — Technical correctness

### Critical issues found and fixed

1. **Core-only dominance risk.** Core fallback combined hard-gate precision and radar recall, which could support an overclaim. The frozen hold-out contradicted dominance (fallback 35/70 vs hard gate 55/70). The title, abstract, discussion and conclusion now foreground this contradiction.
2. **Brake TP confused with safe stop.** Some hold-out/degradation runs brake but still collide. Tables now report collision and system PASS separately from TP/FN.
3. **CPU/GPU evidence mixing.** Earlier CPU runs are explicitly diagnostic only. Final headline evidence requires and logs CUDA in 474 sessions; zero inference errors were recorded.
4. **Unseen-prop failure attribution.** The text no longer attributes every physical failure to camera gating. Cart has no confirmed track; bench fallback is late; warning behavior includes apparent camera confirmation/dynamics.
5. **Synthetic radar wording.** All injected returns are labelled synthetic fault injection, not native CARLA radar evidence.

### Checks

- 67 unit tests pass at the frozen evaluation commit.
- Final manifest contains 2,461/2,461 technically complete runs.
- Model/config/commit/provider metadata is present in the raw archive.
- All headline numbers are generated from checked-in CSV, not retyped from console output.

## Review round 2 — Experimental design/statistics

### Major issues found and fixed

1. **Pseudo-replication.** x3/x5 repetitions are now described as consistency checks. Named scenarios are the interpretation unit; Wilson intervals remain run-level descriptive intervals.
2. **Designed sample prior.** Precision/F1 are explicitly benchmark-composition dependent and are not road-prevalence estimates.
3. **Threshold arbitrariness.** Ablation and one-factor sensitivity were added. Central-path, point-count and latch effects are supported; stability/risk-conjunction non-effects on the focused suite are disclosed.
4. **Tuning leakage.** Protocol and threshold values were committed/tagged before hold-out. Hold-out outcomes were retained without changes.
5. **External validity.** A dedicated limitations section covers one map/ego, synthetic imagery, point-level radar, no HIL/real vehicle and no NCAP compliance.

### Residual statistical limitations accepted

- Hold-out has 14 named conditions and is deliberately balanced, not population-sampled.
- Repeats under fixed setup remain correlated.
- No hierarchical confidence interval is claimed from the small number of named conditions.
- The perturbation grid is local, not a global robustness envelope.

## Review round 3 — Safety/claims

### Claim audit fixes

- Replaced “fusion is better” with conditional trade-off language.
- Avoided “perfect precision” outside the exact sample; the table gives 1.000 with Wilson lower bounds.
- Avoided “real-time automotive” language; CUDA timing is host processing evidence under synchronous simulation.
- Avoided “deterministic physics”; wording is synchronous fixed-step simulation.
- Standardized AEB expansion to **Automatic Emergency Braking**.
- Described CCR scenarios as inspired by testing practice, not Euro NCAP certification.
- Described fallback as an emergency policy/safety-oriented candidate, not a functional-safety guarantee.

## Review round 4 — Reproducibility and format

- English IEEE master: exactly 6 pages including references.
- Vietnamese review PDF: builds without missing Vietnamese glyphs.
- References/citations resolve; only minor underfull boxes and a ~1.6-pt table overfull warning remain.
- Report v3 builds from `report/chapters_v3/`, not from a manually edited DOCX.
- Report DOCX/PDF preserve the established Times New Roman style, A4 page and thesis margins.
- All report image links resolve; 32 figures are embedded in the DOCX.
- Raw archive has a SHA-256 sidecar.

## Reviewer-style scores

| Dimension | Score / 10 | Comment |
|---|---:|---|
| Technical traceability | 9.5 | Sensor-to-brake code/config/log map is explicit |
| Experimental transparency | 9.0 | Failures and hold-out reversal are retained |
| Statistical restraint | 8.5 | Correct caveats; named-condition sample remains small |
| Reproducibility | 9.5 | Frozen tag, manifests, raw archive, generation scripts |
| Novelty | 6.5 | Integration/evaluation contribution, not a new fusion primitive |
| External validity | 5.0 | CARLA-only, one map, no signal-level radar/real vehicle |
| Writing/claim discipline | 9.0 | Core and adverse hold-out are both headline results |

## Remaining non-blocking work

- Instructor/department approval of the final Vietnamese project title.
- Manual visual inspection of the DOCX in Microsoft Word and field update for TOC/captions.
- Representative videos after manuscript lock; videos are illustrative, not quantitative evidence.
- Optional future real-data/HIL validation, outside the present project scope.

No unresolved Critical or Major issue is intentionally hidden. Remaining limitations are scientific scope constraints and are stated in the manuscripts.
