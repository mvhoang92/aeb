# Paper v4 frozen evaluation protocol

Date prepared: 2026-08-25  
Evaluation branch: `feature/fail-safe-fusion-v4`  
Algorithm tag: `safe-fallback-eval-v1` (created after this protocol and suite commit)

## Research question

Can a camera-gated AEB retain the false-brake suppression observed for a hard
camera veto while a conservative radar emergency fallback recovers genuine
non-vehicle obstacles that the car-only camera class does not confirm?

The study compares three fixed policies:

1. radar-only;
2. hard camera gate;
3. camera gate with radar emergency fallback.

## Locked safe-fallback rule

Camera confirmation remains preferred. In the absence of confirmation, radar
may override only when the selected track is confirmed and non-stale, has age
and hit streak of at least 3 frames, has at least 6 points and confidence at
least 0.70, lies within 0.65 m of the predicted path, and simultaneously has
TTC <= 1.10 s and stopping-distance margin <= -2.0 m. Once triggered, fallback
is latched until the radar AEB leaves BRAKE. These values must not be changed in
response to frozen hold-out outcomes.

## Execution controls

- CARLA 0.9.11, Town04, synchronous fixed-step simulation, 0.05 s/tick.
- Seed recorded as 2026; repeated deterministic runs assess consistency rather
  than independent traffic prevalence.
- Hard-gate and safe-fallback model inference must report active
  `CUDAExecutionProvider`; CPU fallback is a technical hard stop.
- Model SHA-256, config SHA-256, Git commit and provider diagnostics are stored.
- One fresh CARLA server is started for each named scenario; all repetitions of
  that scenario run before the next server restart.
- Checkpoint/resume skips completed `(scenario_id, run_index)` pairs.
- Algorithmic FAIL outcomes do not terminate final evaluation. Technical
  incompleteness, provider mismatch or inference errors do.

## Development analyses

The development suite contains conditions represented in prior evidence. It is
used for component ablation and one-factor sensitivity only. Ablations remove:

- camera fallback entirely (hard gate);
- central-path constraint;
- minimum point constraint;
- stability/confidence constraint;
- conjunction of TTC and stopping-margin conditions;
- fallback latch.

One-factor sensitivity varies point count, path width, stability, TTC, stopping
margin and confidence around the locked nominal values. These results describe
robustness; they do not automatically retune the frozen policy.

## Final suites

### Core paired suites

The existing full66, regression, physical edge-prop, in-path non-vehicle and
labelled synthetic fault-injection suites are run x5 for all three policies.

### Perturbation robustness

Twenty named conditions perturb speed, initial gap, cut-in timing and physical
prop position. Each condition is a distinct scenario; repeats are reported
separately from scenario-level consistency.

### Camera degradation

The detector-disabled suite evaluates hard gate and safe fallback with no
camera detections. It is a controlled fault/degradation test, not an estimate
of natural camera failure prevalence.

### Frozen hold-out

`fusion_fallback_holdout.yaml` contains physical prop types, vehicle
appearances and high-support synthetic radar ghosts not used by the v1 fallback
threshold selection. Hold-out outcomes are run last and must be reported
without threshold changes. In particular, 6--10-point persistent central
synthetic ghosts test the expected limitation that rule-based radar evidence
cannot always distinguish a convincing ghost from a genuine obstacle.

## Outcome and statistical reporting

Primary system outcomes are brake/no-brake relative to the scenario label,
collision, minimum bumper gap and first-brake simulation time. Processing
metrics include inference count, errors and p50/p95/p99/max wall-clock inference
latency, explicitly separating computation latency from simulation response.

Results are reported at two levels:

- run level: descriptive counts and Wilson intervals;
- named-scenario level: all-PASS, all-FAIL and mixed consistency plus paired
  policy outcomes.

Repeated runs of one scenario are not treated as independent samples for broad
population inference. Aggregate precision/recall depends on the deliberately
constructed suite composition and is not an on-road prevalence estimate.

## Claim policy

No result constitutes Euro NCAP compliance, real-vehicle validation, functional
safety certification or proof of real-time automotive deployment. Synthetic
radar returns remain explicitly labelled fault injection. Any unsuccessful
hold-out, degradation or system-limit condition is retained as a limitation.
