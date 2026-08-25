# Paper v5 — Response to Simulated Review Panel

Paper v5 is a new version; paper v4 and its frozen evidence remain unchanged.
No CARLA run was added or removed. New severity/statistical results are derived
reproducibly from the frozen tick logs by `scripts/analyze_v5_review_metrics.py`.

| Review item | v5 response | Status |
|---|---|---|
| M1: run-level repetition used as statistical unit | Core is now 105 named conditions and hold-out is 14. Confusion, Wilson descriptors, PASS/collision and paired outcomes use named conditions. Runs are consistency/coverage only. | Resolved |
| M2: PASS/label/brake definition incomplete | Section IV formally defines frozen labels, any-override brake prediction, collision event, 0.5-m minimum-gap rule and optional lane/target assertions. | Resolved |
| M3: binary AEB severity insufficient | Added last-tick pre-impact speed, first-brake gap, false-brake duration, peak deceleration and stop completion. Bench/ghost outcomes are headline results. | Resolved from existing logs |
| M4: detector/sensor setup under-specified | Added camera/radar geometry and rates, model thresholds/cadence/hash, dataset image/instance/session counts, empty-frame ratios and session-separated split statement. | Resolved |
| M5: hold-out could imply broad robustness | Renamed and repeatedly scoped as a **frozen adverse mechanism hold-out**. Ghosts are threshold-directed falsification, not measured multipath prevalence. A stochastic multi-map protocol is future work. | Scope corrected; broader experiment remains future work |
| M6: low algorithmic novelty/limited baselines | Title and contribution are explicitly empirical. The paper disclaims broad algorithmic novelty and lists probabilistic, confidence-matched, multi-class/free-space baselines as required future comparison. | Claim resolved; new baseline remains future work |
| M7: related work thin/direct references unused | Added CenterFusion; cited and positioned radar-guided verification and CARLA AEB work; all 15 bibliography entries are cited in both languages. | Resolved |
| M8: Vietnamese copy not equivalent | English/Vietnamese versions now have the same 16 section headings, four tables, one figure, 14 citation commands and 15 cited references. | Resolved |

## Additional correction discovered during revision

Paper v4 Table IV described all six fallback perturbation FAIL runs as
collisions. Raw summaries show one named 19-m condition collides (3 runs), while
the 21-m condition avoids collision but stops at 0.353 m, below the frozen
0.5-m PASS threshold (3 runs). Paper v5 reports one collision condition and
separates the minimum-gap failure.

## Deliberately unchanged boundaries

- CARLA-only, one map/ego, one fixed seed and point-level radar.
- No road prevalence, HIL, real vehicle, NCAP or functional-safety claim.
- No post-hold-out threshold tuning.
- Existing 2,461-run campaign remains the sole quantitative campaign.
