# v5.1 Review Response Outline

This outline is for supervisor/venue review. It does not claim that all
reviewer objections are experimentally solved.

| Likely concern | Response in v5.1 | Remaining boundary |
|---|---|---|
| Camera/radar fusion is established | Agreed; the paper explicitly disclaims a new fusion primitive and isolates late brake permission | Contribution is empirical comparison |
| Why is fallback not radar-only? | Equations and text show fallback requires camera confirmation or a stricter emergency condition | Same radar track can still be a ghost |
| Why not report only precision/recall? | Paired conditions, collision status, braking onset and severity are added | Severity remains kinematic, not injury risk |
| Are repeated runs independent samples? | Named condition is the primary unit; repeats assess consistency | Grid is constructed and not prevalence representative |
| Is the hold-out truly blind? | It is labelled a frozen adverse mechanism hold-out; rule knowledge and post-hoc derivation are disclosed | It is not an unbiased deployment test |
| Does fallback dominate hard gating? | No. Core and hold-out produce different orderings; the manuscript reports both | No universal policy recommendation |
| Is a synthetic ghost a real radar ghost? | No. It is explicitly synthetic fault injection, motivated by ghost failure mechanisms | Real multipath prevalence is not estimated |
| Is this a new probabilistic AEB? | No. Existing probabilistic threat/existence work is cited; current fallback is deterministic | A probabilistic method would need a new protocol and hold-out |
| Does CUDA prove real-time operation? | No. Host ONNX timing is reported with its scope and exclusions | No ECU, HIL or actuator deadline claim |
