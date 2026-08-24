#!/usr/bin/env python3
"""Run the final paper-v4 campaign with checkpointed CARLA process isolation.

One master invocation manages many short CARLA sessions.  Each named scenario
runs all requested repetitions on a fresh server; the server is then terminated
before the next scenario.  Algorithmic FAIL outcomes are retained, while
technical incompleteness or loss of the required CUDA provider stops the gate.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[1]
CARLA_ROOT = AEB_ROOT.parent
if str(AEB_ROOT) not in sys.path:
    sys.path.insert(0, str(AEB_ROOT))

from scripts.run_v4_campaign import (  # noqa: E402
    CONFIGURATIONS,
    CampaignJob,
    build_full_jobs,
    build_smoke_jobs,
    ensure_clean_worktree,
    job_command,
    read_summaries,
    scenario_count,
    scenario_ids,
    summarize_run,
)


DEFAULT_OUTPUT_ROOT = AEB_ROOT / "outputs" / "paper_v4_final_pipeline"
DEFAULT_LOG_ROOT = AEB_ROOT / "logs"


def utc_now():
    return datetime.now().astimezone().isoformat()


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with open(str(temporary), "w") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
    temporary.replace(path)


def gpu_snapshot():
    command = [
        "nvidia-smi",
        "--query-gpu=name,memory.used,memory.total,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        output = subprocess.check_output(command, universal_newlines=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return output


class CarlaServerManager(object):
    """Start, health-check and fully terminate one local CARLA server."""

    def __init__(self, host, port, startup_timeout_s, log_root):
        self.host = str(host)
        self.port = int(port)
        self.startup_timeout_s = float(startup_timeout_s)
        self.log_root = Path(log_root)
        self.process = None
        self.log_stream = None

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass
        self._terminate_shipping_processes(signal.SIGTERM)
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline and self._port_open():
            time.sleep(0.2)
        if self._port_open():
            if self.process is not None and self.process.poll() is None:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    pass
            self._terminate_shipping_processes(signal.SIGKILL)
            time.sleep(1.0)
        if self.log_stream is not None:
            self.log_stream.close()
        self.process = None
        self.log_stream = None

    def start(self, label):
        self.stop()
        self.log_root.mkdir(parents=True, exist_ok=True)
        log_path = self.log_root / "{}.log".format(label)
        self.log_stream = open(str(log_path), "a")
        command = [
            str(CARLA_ROOT / "CarlaUE4.sh"),
            "/Game/Carla/Maps/Town04",
            "-quality-level=Low",
            "-windowed",
            "-ResX=640",
            "-ResY=360",
            "-carla-port={}".format(self.port),
        ]
        self.process = subprocess.Popen(
            command,
            cwd=str(CARLA_ROOT),
            stdout=self.log_stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self._wait_until_healthy()
        return {
            "pid": self.process.pid,
            "command": command,
            "log": str(log_path),
            "started_at": utc_now(),
            "gpu": gpu_snapshot(),
        }

    def _wait_until_healthy(self):
        deadline = time.monotonic() + self.startup_timeout_s
        last_error = None
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(
                    "CARLA exited during startup with code {}".format(
                        self.process.returncode
                    )
                )
            try:
                carla = self._import_carla()
                client = carla.Client(self.host, self.port)
                client.set_timeout(2.0)
                client.get_server_version()
                client.get_world().get_map().name
                return
            except Exception as exc:  # pylint: disable=broad-except
                last_error = exc
                time.sleep(1.0)
        raise RuntimeError("CARLA health check timed out: {}".format(last_error))

    def _import_carla(self):
        try:
            import carla  # pylint: disable=import-outside-toplevel

            return carla
        except ImportError:
            eggs = glob.glob(
                str(
                    CARLA_ROOT
                    / "PythonAPI"
                    / "carla"
                    / "dist"
                    / "carla-*{}.*-linux-x86_64.egg".format(sys.version_info.major)
                )
            )
            if not eggs:
                raise
            sys.path.append(eggs[0])
            import carla  # pylint: disable=import-outside-toplevel,reimported

            return carla

    def _port_open(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.2)
        try:
            return sock.connect_ex((self.host, self.port)) == 0
        finally:
            sock.close()

    @staticmethod
    def _terminate_shipping_processes(sig):
        try:
            output = subprocess.check_output(
                ["pgrep", "-f", "CarlaUE4-Linux-Shipping"],
                universal_newlines=True,
            )
        except subprocess.CalledProcessError:
            return
        for raw_pid in output.split():
            try:
                pid = int(raw_pid)
                if pid != os.getpid():
                    os.kill(pid, sig)
            except (ValueError, OSError, ProcessLookupError):
                continue


def summary_count_for_scenario(run_directory, scenario_id):
    return sum(
        1
        for row in read_summaries(run_directory)
        if str(row.get("scenario_id")) == str(scenario_id)
    )


def read_runtime_metadata(run_directory):
    path = Path(run_directory) / "run_metadata.json"
    if not path.exists():
        return {}
    with open(str(path)) as stream:
        return json.load(stream)


def validate_cuda_runtime(job, metadata):
    if Path(job.runner).name != "run_fusion_aeb_scenarios.py":
        return
    runtime = metadata.get("model_runtime", {}) or {}
    active = runtime.get("active_providers", []) or []
    if "CUDAExecutionProvider" not in active:
        raise RuntimeError(
            "HARD STOP: {} did not use CUDAExecutionProvider (active={})".format(
                job.name,
                active,
            )
        )
    if int(runtime.get("inference_error_count", 0)) != 0:
        raise RuntimeError(
            "HARD STOP: {} recorded {} inference errors".format(
                job.name,
                runtime.get("inference_error_count"),
            )
        )


def selected_jobs(args):
    jobs = []
    if args.phase in ("smoke", "all"):
        jobs.extend(build_smoke_jobs(args.smoke_repeat))
    if args.phase in ("core", "all"):
        jobs.extend(
            build_full_jobs(
                args.repeat,
                tuple(args.config) if args.config else None,
                tuple(args.suite) if args.suite else None,
            )
        )
    return jobs


def run_preflight(args):
    ensure_clean_worktree()
    if args.skip_tests:
        return
    subprocess.check_call(
        [str(args.python), "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=str(AEB_ROOT),
    )


def run_pipeline(args):
    run_preflight(args)
    jobs = selected_jobs(args)
    output_root = Path(args.output_root) / args.campaign_id
    manifest_path = output_root / "campaign_manifest.json"
    session_path = output_root / "runtime_sessions.json"
    sessions = []
    if args.resume and session_path.exists():
        with open(str(session_path)) as stream:
            sessions = json.load(stream)
    session_keys = {
        "{}|{}".format(row["job"], row["scenario_id"]) for row in sessions
    }
    manifest = {
        "campaign_id": args.campaign_id,
        "created_at": utc_now(),
        "phase": args.phase,
        "restart_policy": "after_each_named_scenario_all_repetitions",
        "seed": args.seed,
        "repeat": args.repeat,
        "gpu_at_start": gpu_snapshot(),
        "jobs": [asdict(job) for job in jobs],
        "results": [],
        "status": "running",
    }
    write_json(manifest_path, manifest)
    server = CarlaServerManager(
        args.host,
        args.port,
        args.server_startup_timeout_s,
        output_root / "carla_server_logs",
    )

    try:
        for job_index, job in enumerate(jobs, 1):
            run_id = "{}_{}".format(args.campaign_id, job.name)
            run_directory = Path(args.log_root) / run_id
            ids = scenario_ids(job)
            print(
                "\n=== [{}/{}] {}: {} scenarios × {} ===".format(
                    job_index,
                    len(jobs),
                    job.name,
                    len(ids),
                    job.repeat,
                )
            )
            for scenario_index, scenario_id in enumerate(ids, 1):
                completed = summary_count_for_scenario(run_directory, scenario_id)
                session_key = "{}|{}".format(job.name, scenario_id)
                if completed == job.repeat and session_key in session_keys:
                    print(
                        "[{}/{}] {}: resume skip {}/{}".format(
                            scenario_index,
                            len(ids),
                            scenario_id,
                            completed,
                            job.repeat,
                        )
                    )
                    continue

                scenario_job = replace(job, scenarios=(scenario_id,))
                command = job_command(args, scenario_job, run_id)
                if args.dry_run:
                    print(" ".join(command))
                    continue

                last_error = None
                for attempt in range(1, args.technical_retries + 2):
                    label = "{:02d}_{}_{}_attempt{}".format(
                        job_index,
                        job.name,
                        scenario_id,
                        attempt,
                    )
                    label = label.replace("/", "_")
                    server_info = None
                    try:
                        server_info = server.start(label)
                        result = subprocess.run(
                            command,
                            cwd=str(AEB_ROOT),
                            check=False,
                        )
                        completed = summary_count_for_scenario(
                            run_directory,
                            scenario_id,
                        )
                        if completed != job.repeat:
                            raise RuntimeError(
                                "technical incompleteness: {}/{} runs; child rc={}".format(
                                    completed,
                                    job.repeat,
                                    result.returncode,
                                )
                            )
                        metadata = read_runtime_metadata(run_directory)
                        validate_cuda_runtime(job, metadata)
                        record = {
                            "job": job.name,
                            "scenario_id": scenario_id,
                            "repeat": job.repeat,
                            "completed_at": utc_now(),
                            "child_return_code": result.returncode,
                            "server": server_info,
                            "gpu_after": gpu_snapshot(),
                            "model_runtime": metadata.get("model_runtime"),
                            "git_commit": metadata.get("git_commit"),
                            "sensor_config_sha256": metadata.get(
                                "sensor_config_sha256"
                            ),
                            "scenario_config_sha256": metadata.get(
                                "scenario_config_sha256"
                            ),
                        }
                        sessions = [
                            row
                            for row in sessions
                            if "{}|{}".format(row["job"], row["scenario_id"])
                            != session_key
                        ]
                        sessions.append(record)
                        session_keys.add(session_key)
                        write_json(session_path, sessions)
                        last_error = None
                        break
                    except Exception as exc:  # pylint: disable=broad-except
                        last_error = exc
                        print(
                            "  Technical attempt {}/{} failed: {}".format(
                                attempt,
                                args.technical_retries + 1,
                                exc,
                            )
                        )
                    finally:
                        server.stop()
                if last_error is not None:
                    raise RuntimeError(
                        "Scenario {} failed technically after retries: {}".format(
                            scenario_id,
                            last_error,
                        )
                    )

            if args.dry_run:
                continue
            expected = scenario_count(job)
            summaries = read_summaries(run_directory)
            technically_complete = len(summaries) == expected
            passes = sum(1 for row in summaries if row.get("status") == "PASS")
            result = {
                "job": job.name,
                "run_id": run_id,
                "expected_scenario_runs": expected,
                "completed_scenario_runs": len(summaries),
                "pass": passes,
                "fail": len(summaries) - passes,
                "technically_complete": technically_complete,
            }
            manifest["results"].append(result)
            write_json(manifest_path, manifest)
            if not technically_complete:
                raise RuntimeError(
                    "Job {} incomplete: {}/{}".format(
                        job.name,
                        len(summaries),
                        expected,
                    )
                )
            summarize_run(args, run_directory, output_root / job.name)
            if job.require_all_pass and passes != expected:
                raise RuntimeError(
                    "Smoke gate {} has {}/{} algorithmic FAIL".format(
                        job.name,
                        expected - passes,
                        expected,
                    )
                )
    except Exception as exc:
        manifest["status"] = "failed_technical_or_gate"
        manifest["error"] = str(exc)
        manifest["stopped_at"] = utc_now()
        write_json(manifest_path, manifest)
        raise
    finally:
        server.stop()

    manifest["status"] = "completed"
    manifest["completed_at"] = utc_now()
    manifest["gpu_at_end"] = gpu_snapshot()
    write_json(manifest_path, manifest)
    return manifest


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("smoke", "core", "all"), default="smoke")
    parser.add_argument(
        "--campaign-id",
        default="paper_v4_gpu_final_{}".format(datetime.now().strftime("%Y%m%d")),
    )
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--server-startup-timeout-s", type=float, default=90.0)
    parser.add_argument("--technical-retries", type=int, default=2)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--smoke-repeat", type=int, default=1)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--log-root", type=Path, default=DEFAULT_LOG_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--scenario-cooldown-s", type=float, default=0.5)
    parser.add_argument("--reload-world-every", type=int, default=0)
    parser.add_argument("--reload-world-wait-s", type=float, default=2.0)
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--config",
        action="append",
        choices=tuple(CONFIGURATIONS),
    )
    parser.add_argument("--suite", action="append")
    args = parser.parse_args()
    if args.repeat < 1 or args.smoke_repeat < 1:
        parser.error("repeat must be >= 1")
    if args.technical_retries < 0:
        parser.error("technical retries must be >= 0")
    return args


def main():
    args = parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
