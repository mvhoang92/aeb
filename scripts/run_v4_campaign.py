#!/usr/bin/env python3
"""Run the resumable paper-v4 three-way AEB evaluation campaign.

The campaign intentionally separates a small fail-safe smoke gate from the full
radar-only vs hard-camera-gate vs safe-fallback evaluation.  A runner exit code
of 1 can represent an expected algorithmic FAIL; a job is considered technically
complete when its summary contains every requested scenario-run.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import yaml


AEB_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_ROOT = AEB_ROOT / "logs"
DEFAULT_OUTPUT_ROOT = AEB_ROOT / "outputs" / "paper_v4_campaign"
FUSION_RUNNER = AEB_ROOT / "scripts" / "run_fusion_aeb_scenarios.py"
RADAR_RUNNER = AEB_ROOT / "scripts" / "run_radar_aeb_scenarios.py"
SUMMARIZER = AEB_ROOT / "scripts" / "summarize_repeatability.py"
SENSORS_HARD = AEB_ROOT / "configs" / "sensors.yaml"
SENSORS_SAFE = AEB_ROOT / "configs" / "sensors_fusion_safe_fallback.yaml"
SUITE_ROOT = AEB_ROOT / "configs" / "scenarios" / "suites"


@dataclass(frozen=True)
class CampaignJob:
    name: str
    runner: str
    sensor_config: str
    scenario_config: str
    repeat: int
    scenarios: Tuple[str, ...] = tuple()
    require_all_pass: bool = False


SMOKE_REGRESSION_SCENARIOS = (
    "clear_road_65",
    "ccrs_65",
    "adjacent_stationary_65",
    "curve_ccrs_65",
    "cut_in_65_45",
    "multi_adjacent_decoy_65",
)

FULL_SUITES = (
    "system_limit_extended_sweep.yaml",
    "radar_only_regression.yaml",
    "fusion_physical_false_positive_v2.yaml",
    "fusion_nonvehicle_hazard_limitation.yaml",
    "fusion_benefit_stress.yaml",
)

CONFIGURATIONS = {
    "radar_only": (RADAR_RUNNER, SENSORS_HARD),
    "hard_gate": (FUSION_RUNNER, SENSORS_HARD),
    "safe_fallback": (FUSION_RUNNER, SENSORS_SAFE),
}


def build_smoke_jobs(repeat):
    jobs = []
    for suite_name, scenarios in (
        ("fusion_nonvehicle_hazard_limitation.yaml", tuple()),
        ("fusion_physical_false_positive_v2.yaml", tuple()),
        ("fusion_benefit_stress.yaml", tuple()),
        ("radar_only_regression.yaml", SMOKE_REGRESSION_SCENARIOS),
    ):
        suite = SUITE_ROOT / suite_name
        jobs.append(
            CampaignJob(
                name="smoke_safe_{}".format(suite.stem),
                runner=str(FUSION_RUNNER),
                sensor_config=str(SENSORS_SAFE),
                scenario_config=str(suite),
                repeat=repeat,
                scenarios=tuple(scenarios),
                require_all_pass=True,
            )
        )
    return jobs


def build_full_jobs(repeat, selected_configs=None, selected_suites=None):
    configs = selected_configs or tuple(CONFIGURATIONS)
    suites = selected_suites or FULL_SUITES
    jobs = []
    for config_name in configs:
        runner, sensors = CONFIGURATIONS[config_name]
        for suite_name in suites:
            suite = SUITE_ROOT / suite_name
            jobs.append(
                CampaignJob(
                    name="{}_{}".format(config_name, suite.stem),
                    runner=str(runner),
                    sensor_config=str(sensors),
                    scenario_config=str(suite),
                    repeat=repeat,
                )
            )
    return jobs


def scenario_count(job):
    with open(job.scenario_config) as stream:
        data = yaml.safe_load(stream) or {}
    configured = [str(item["id"]) for item in data.get("scenarios", [])]
    if job.scenarios:
        missing = set(job.scenarios) - set(configured)
        if missing:
            raise ValueError(
                "Job {} references missing scenarios: {}".format(
                    job.name,
                    ", ".join(sorted(missing)),
                )
            )
        configured = [name for name in configured if name in set(job.scenarios)]
    return len(configured) * int(job.repeat)


def read_summaries(run_directory):
    path = Path(run_directory) / "summary.json"
    if not path.exists():
        return []
    with open(str(path)) as stream:
        value = json.load(stream)
    return value if isinstance(value, list) else []


def job_command(args, job, run_id):
    command = [
        str(args.python),
        job.runner,
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--sensor-config",
        job.sensor_config,
        "--scenario-config",
        job.scenario_config,
        "--log-root",
        str(args.log_root),
        "--run-id",
        run_id,
        "--resume",
        "--seed",
        str(args.seed),
        "--control-mode",
        "physics",
        "--repeat",
        str(job.repeat),
        "--scenario-cooldown-s",
        str(args.scenario_cooldown_s),
        "--reload-world-every",
        str(args.reload_world_every),
        "--reload-world-wait-s",
        str(args.reload_world_wait_s),
        "--load-map",
    ]
    for scenario in job.scenarios:
        command.extend(("--scenario", scenario))
    return command


def summarize_run(args, run_directory, output_directory):
    output_directory.mkdir(parents=True, exist_ok=True)
    command = [
        str(args.python),
        str(SUMMARIZER),
        str(run_directory),
        "--output-dir",
        str(output_directory),
    ]
    subprocess.check_call(command, cwd=str(AEB_ROOT))


def ensure_clean_worktree():
    status = subprocess.check_output(
        ["git", "-C", str(AEB_ROOT), "status", "--porcelain"],
        universal_newlines=True,
    )
    if status.strip():
        raise RuntimeError(
            "Campaign evidence yêu cầu working tree sạch; hãy commit trước khi chạy."
        )


def write_manifest(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "w") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)


def run_campaign(args, jobs):
    campaign_id = args.campaign_id
    output_root = Path(args.output_root) / campaign_id
    manifest_path = output_root / "campaign_manifest.json"
    results = []
    payload = {
        "campaign_id": campaign_id,
        "created_at": datetime.now().isoformat(),
        "phase": args.phase,
        "seed": args.seed,
        "jobs": [asdict(job) for job in jobs],
        "results": results,
    }
    write_manifest(manifest_path, payload)

    for index, job in enumerate(jobs, 1):
        run_id = "{}_{}".format(campaign_id, job.name)
        run_directory = Path(args.log_root) / run_id
        expected = scenario_count(job)
        command = job_command(args, job, run_id)
        print("\n[{}/{}] {} ({} scenario-runs)".format(index, len(jobs), job.name, expected))
        print(" ".join(command))
        if args.dry_run:
            continue

        completed_before = len(read_summaries(run_directory))
        if completed_before == expected:
            return_code = 0
            print("  Đã hoàn thành trước đó; chỉ sinh lại summary.")
        else:
            completed = subprocess.run(command, cwd=str(AEB_ROOT), check=False)
            return_code = int(completed.returncode)

        summaries = read_summaries(run_directory)
        technically_complete = len(summaries) == expected
        pass_count = sum(1 for row in summaries if row.get("status") == "PASS")
        fail_count = len(summaries) - pass_count
        result = {
            "job": job.name,
            "run_id": run_id,
            "return_code": return_code,
            "expected_scenario_runs": expected,
            "completed_scenario_runs": len(summaries),
            "pass": pass_count,
            "fail": fail_count,
            "technically_complete": technically_complete,
        }
        results.append(result)
        payload["results"] = results
        write_manifest(manifest_path, payload)

        if not technically_complete:
            raise RuntimeError(
                "Job {} dừng kỹ thuật ở {}/{} runs; chạy lại cùng lệnh để resume.".format(
                    job.name,
                    len(summaries),
                    expected,
                )
            )
        summarize_run(args, run_directory, output_root / job.name)
        if job.require_all_pass and fail_count:
            raise RuntimeError(
                "Smoke gate {} có {}/{} FAIL; dừng trước full campaign.".format(
                    job.name,
                    fail_count,
                    expected,
                )
            )

    payload["completed_at"] = datetime.now().isoformat()
    write_manifest(manifest_path, payload)
    return results


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("smoke", "full", "all"), default="smoke")
    parser.add_argument(
        "--campaign-id",
        default="paper_v4_safe_fusion_{}".format(datetime.now().strftime("%Y%m%d")),
    )
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--smoke-repeat", type=int, default=1)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--log-root", type=Path, default=DEFAULT_LOG_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--scenario-cooldown-s", type=float, default=0.5)
    parser.add_argument("--reload-world-every", type=int, default=0)
    parser.add_argument("--reload-world-wait-s", type=float, default=2.0)
    parser.add_argument(
        "--config",
        action="append",
        choices=tuple(CONFIGURATIONS),
        help="Giới hạn full phase vào cấu hình này; có thể lặp cờ.",
    )
    parser.add_argument(
        "--suite",
        action="append",
        choices=FULL_SUITES,
        help="Giới hạn full phase vào suite này; có thể lặp cờ.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.repeat < 1 or args.smoke_repeat < 1:
        parser.error("repeat phải >= 1")
    return args


def main():
    args = parse_args()
    if not args.dry_run:
        ensure_clean_worktree()
    jobs: List[CampaignJob] = []
    if args.phase in ("smoke", "all"):
        jobs.extend(build_smoke_jobs(args.smoke_repeat))
    if args.phase in ("full", "all"):
        jobs.extend(
            build_full_jobs(
                args.repeat,
                tuple(args.config) if args.config else None,
                tuple(args.suite) if args.suite else None,
            )
        )
    run_campaign(args, jobs)


if __name__ == "__main__":
    main()
