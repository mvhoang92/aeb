# Source Map

| Claim or value | Primary source | Supporting source | Note |
|---|---|---|---|
| CARLA version, Town04, Tesla Model 3 | `configs/sensors.yaml` | `report/report.md` | Configuration used by the project. |
| Camera: 1280x720, 70 degrees, 20 Hz | `configs/sensors.yaml` | `report/report.md` | Runtime inference is throttled separately. |
| Radar: 100 m, 30/6 degrees, 2000 points/s, 20 Hz | `configs/sensors.yaml` | `report/report.md` | Values are simulator configuration, not commercial-sensor specifications. |
| Radar clustering and track confirmation | `perception/radar/radar_object_tracker.py` | `configs/sensors.yaml` | Cluster confirmation is 3 frames; target gate is 5 frames. |
| Camera gate behavior | `scripts/run_fusion_aeb_scenarios.py` | `configs/sensors.yaml` | A `BRAKE` decision is released unless the target is currently or recently camera-confirmed; hold time defaults to 0.35 s in code. |
| TTC and stopping-distance model | `control/brake.py` | `configs/sensors.yaml` | Negative relative velocity denotes a closing target. |
| YOLO training configuration | `configs/model_training.yaml` | `report/report.md` | 640 px, 100 epochs, AdamW, `lr0=0.001`; final metrics are reported from the project evidence summary. |
| Dataset split and YOLO metrics | `report/report.md`, Sec. 3.5 | `docs/official/08_DATASET_AND_TRAINING.md` | Local training artifacts are not present in this checkout. |
| 66-case final result and three collisions | `docs/log/FINAL_EVIDENCE_PACK_20260628.md` | `report/report.md`, Ch. 4 | Local CSV/JSON evidence artifacts are not present in this checkout. |

## Source discrepancies and decisions

- The final-evidence CSV/JSON paths documented in the evidence pack are absent
  from this checkout. The paper therefore cites the checked-in final-evidence
  summary and reports no confidence intervals or repeated-trial statistics.
- The current author-information instruction locks the contact email as
  `hoangmai04222@gmail.com`; no department, school, academic title, or
  corresponding-author marker is added.
- The Vietnamese review copy retains its original T5/Times typography and is
  built with pdfLaTeX; it is not subject to the six-page English-paper target.
