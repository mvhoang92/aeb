#!/usr/bin/env python3
"""Environment doctor: one OK/WARN/FAIL line per prerequisite.

Checks the repository state, the external workspace (``check_workspace``),
the launcher prerequisites (``launcher.py --check`` logic), the model files
against the tracked SHA-256 manifest, a CUDA ONNX Runtime session probe (in a
subprocess, so a native abort cannot kill the doctor), CARLA port
reachability and free GPU memory.

It never talks to the CARLA RPC API: for a local host the port is looked up
in the kernel's listening-socket table, so no connection is made.  Exit code
0 when no check FAILs, 1 otherwise; WARN never changes the exit code.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import socket
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

from evaluation.artifact_io import sha256_file
from infrastructure import cuda_runtime
from infrastructure.workspace import AEB_ROOT, CARLA_ROOT
from scripts.maintenance import check_workspace


OK = "OK"
WARN = "WARN"
FAIL = "FAIL"

Check = namedtuple("Check", ("status", "name", "detail"))

MODEL_MANIFEST = (
    AEB_ROOT / "docs" / "log" / "repeatability" / "environment_20260818" / "model_sha256.txt"
)
# Sensor configs reference models as ``aeb/models/...`` relative to the CARLA
# root, i.e. the main checkout; a linked worktree has an empty ``models/``.
MODEL_SEARCH_ROOTS = (AEB_ROOT, CARLA_ROOT / "aeb")
DEFAULT_SENSOR_CONFIG = AEB_ROOT / "configs" / "sensors_fusion_safe_fallback_batch_gpu.yaml"
CARLA_PYTHON = CARLA_ROOT / "venv" / "bin" / "python"
LAUNCHER_GUI_PYTHON = Path("/usr/bin/python3")
DEFAULT_CARLA_HOST = "127.0.0.1"
DEFAULT_CARLA_PORT = 2000
DEFAULT_MIN_FREE_GPU_MIB = 1024
DEFAULT_PROBE_TIMEOUT_S = 120.0
LOCAL_HOSTS = frozenset(("127.0.0.1", "localhost", "::1", "0.0.0.0", ""))
TCP_LISTEN_STATE = "0A"


def _run(runner, command, timeout):
    return runner(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=timeout,
    )


def _last_line(text, limit=160):
    lines = [line.strip() for line in (text or "").strip().splitlines() if line.strip()]
    line = lines[-1] if lines else ""
    return line if len(line) <= limit else line[: limit - 3] + "..."


# --------------------------------------------------------------------------
# Repository
# --------------------------------------------------------------------------


def check_repository(root=AEB_ROOT, runner=subprocess.run):
    def git(*args):
        completed = _run(runner, ["git", "-C", str(root)] + list(args), 20)
        if completed.returncode != 0:
            raise RuntimeError(_last_line(completed.stderr) or "git failed")
        return completed.stdout

    try:
        branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
        head = git("rev-parse", "--short", "HEAD").strip()
        status = git("status", "--porcelain")
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        return [Check(WARN, "repository", "git state unavailable: {}".format(exc))]
    entries = [line for line in status.splitlines() if line.strip()]
    if not entries:
        return [Check(OK, "repository", "{} @ {}, clean".format(branch, head))]
    untracked = sum(1 for line in entries if line.startswith("??"))
    return [
        Check(
            WARN,
            "repository",
            "{} @ {}, dirty: {} modified/staged, {} untracked".format(
                branch, head, len(entries) - untracked, untracked
            ),
        )
    ]


# --------------------------------------------------------------------------
# Workspace (reuses scripts/maintenance/check_workspace.py)
# --------------------------------------------------------------------------


def check_workspace_status(collect=check_workspace.collect_status):
    status = collect()
    root = status["directories"]["workspace"]["path"]
    missing_dirs = [
        name for name, item in status["directories"].items() if not item["exists"]
    ]
    datasets = status["datasets"]
    missing_datasets = [
        name
        for name, item in datasets.items()
        if not (item["exists"] and item["dataset_yaml"])
    ]
    environment = status["environment"]
    checks = [
        Check(
            FAIL if missing_dirs else OK,
            "workspace",
            root if not missing_dirs else "{} missing: {}".format(root, ", ".join(missing_dirs)),
        ),
        Check(
            FAIL if missing_datasets else OK,
            "datasets",
            "{}/{} generations with dataset.yaml{}".format(
                len(datasets) - len(missing_datasets),
                len(datasets),
                "; missing: " + ", ".join(missing_datasets) if missing_datasets else "",
            ),
        ),
        Check(
            OK if environment["exists"] else FAIL,
            "yolo python",
            environment["yolo_python"],
        ),
    ]
    return checks


# --------------------------------------------------------------------------
# Launcher prerequisites (reuses ui.launcher.config.check_prerequisites)
# --------------------------------------------------------------------------


def launcher_checks_from_output(text, returncode, source):
    missing = [
        line[:18].strip()
        for line in text.splitlines()
        if line.rstrip().endswith("MISSING")
    ]
    scenarios = "?"
    for line in text.splitlines():
        if line.startswith("Scenarios"):
            scenarios = line.split()[-1]
    if returncode == 0 and not missing:
        return [
            Check(
                OK,
                "launcher",
                "all prerequisites present, {} scenarios in default suite ({})".format(
                    scenarios, source
                ),
            )
        ]
    detail = "missing: " + ", ".join(missing) if missing else "exit code {}".format(returncode)
    return [Check(FAIL, "launcher", "{} ({})".format(detail, source))]


def _launcher_subprocess(runner=subprocess.run):
    python = LAUNCHER_GUI_PYTHON if LAUNCHER_GUI_PYTHON.is_file() else Path(sys.executable)
    try:
        completed = runner(
            [str(python), "launcher.py", "--check"],
            cwd=str(AEB_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return [Check(FAIL, "launcher", "launcher.py --check could not run: {}".format(exc))]
    return launcher_checks_from_output(
        completed.stdout, completed.returncode, "{} launcher.py --check".format(python)
    )


def check_launcher(prerequisites=None, runner=subprocess.run):
    if prerequisites is None:
        try:
            from ui.launcher.config import check_prerequisites as prerequisites
        except ImportError:
            return _launcher_subprocess(runner)
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            returncode = prerequisites()
    except Exception as exc:  # e.g. an unreadable scenario suite
        return [Check(FAIL, "launcher", "prerequisite check raised {}: {}".format(type(exc).__name__, exc))]
    return launcher_checks_from_output(
        buffer.getvalue(), returncode, "ui.launcher.config.check_prerequisites"
    )


# --------------------------------------------------------------------------
# Models and SHA-256 manifest
# --------------------------------------------------------------------------


def load_model_config(sensor_config):
    import yaml

    with open(str(sensor_config), "r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    return data.get("model") or {}


def runtime_model_path(model_config, carla_root=CARLA_ROOT):
    """Resolve like ``ui.manual_control_common.resolve_yolo_model_path``."""

    if not bool(model_config.get("enabled", True)) or not model_config.get("path"):
        return None
    path = Path(str(model_config["path"]))
    return path if path.is_absolute() else carla_root / path


def read_manifest(path):
    entries = {}
    with open(str(path), "r", encoding="utf-8") as stream:
        for line in stream:
            parts = line.split()
            if len(parts) == 2:
                entries[parts[1].lstrip("*")] = parts[0].lower()
    return entries


def check_models(
    model_path,
    manifest_path=MODEL_MANIFEST,
    search_roots=MODEL_SEARCH_ROOTS,
    hasher=sha256_file,
):
    try:
        manifest = read_manifest(manifest_path)
    except OSError as exc:
        return [Check(FAIL, "model manifest", "cannot read {}: {}".format(manifest_path, exc))]
    checks = []
    for relative, expected in sorted(manifest.items()):
        name = "model " + Path(relative).name
        candidates = [Path(root) / relative for root in search_roots]
        found = next((path for path in candidates if path.is_file()), None)
        if found is None:
            checks.append(
                Check(
                    FAIL if relative.endswith(".onnx") else WARN,
                    name,
                    "not found in {}".format(" or ".join(str(p.parent) for p in candidates)),
                )
            )
            continue
        actual = hasher(found)
        if actual == expected:
            checks.append(Check(OK, name, "sha256 {} matches manifest ({})".format(actual[:12], found)))
        else:
            checks.append(
                Check(
                    FAIL,
                    name,
                    "sha256 {} != manifest {} ({})".format(actual[:12], expected[:12], found),
                )
            )
    if model_path is None:
        checks.append(Check(WARN, "runtime model", "model disabled or no path in sensor config"))
    elif not Path(model_path).is_file():
        checks.append(Check(FAIL, "runtime model", "missing: {}".format(model_path)))
    elif hasher(Path(model_path)) in set(manifest.values()):
        checks.append(Check(OK, "runtime model", "{} is a manifest model".format(model_path)))
    else:
        checks.append(
            Check(FAIL, "runtime model", "{} sha256 not in {}".format(model_path, manifest_path.name))
        )
    return checks


# --------------------------------------------------------------------------
# CUDA ONNX Runtime probe (subprocess; never aborts the doctor)
# --------------------------------------------------------------------------


def check_cuda(
    model_config,
    model_path,
    probe=cuda_runtime.probe_cuda_session,
    executable=None,
    environ=None,
    timeout_s=DEFAULT_PROBE_TIMEOUT_S,
):
    name = "cuda probe"
    if not cuda_runtime.cuda_requested(model_config):
        return [Check(WARN, name, "sensor config does not request CUDAExecutionProvider; skipped")]
    severity = FAIL if cuda_runtime.cuda_required(model_config) else WARN
    if model_path is None or not Path(model_path).is_file():
        return [Check(severity, name, "model missing; probe skipped")]
    resolution = cuda_runtime.resolve_cuda_library_dirs(model_config, environ=environ)
    environment = dict(os.environ if environ is None else environ)
    current = cuda_runtime.split_path_list(environment.get("LD_LIBRARY_PATH", ""))
    environment["LD_LIBRARY_PATH"] = os.pathsep.join(
        [path for path in resolution.dirs if path not in current] + current
    )
    dirs = "{} from {}".format(os.pathsep.join(resolution.dirs) or "<none>", resolution.source)
    options = (model_config.get("provider_options") or {}).get(cuda_runtime.CUDA_PROVIDER)
    if executable is None:
        executable = str(CARLA_PYTHON) if CARLA_PYTHON.is_file() else sys.executable
    try:
        result = probe(
            str(model_path),
            options,
            environ=environment,
            timeout_s=timeout_s,
            executable=executable,
            use_cache=False,
        )
    except Exception as exc:  # the doctor must report, never crash
        return [Check(severity, name, "probe raised {}: {}".format(type(exc).__name__, exc))]
    if result.get("ok"):
        return [
            Check(
                OK,
                name,
                "{} active, onnxruntime {}, {}s; CUDA lib dirs {}".format(
                    ",".join(result.get("providers") or []),
                    result.get("onnxruntime_version"),
                    result.get("duration_s"),
                    dirs,
                ),
            )
        ]
    reasons = []
    if result.get("signal"):
        reasons.append("signal {}".format(result["signal"]))
    elif result.get("returncode") is not None:
        reasons.append("exit {}".format(result["returncode"]))
    if result.get("missing_library"):
        reasons.append("missing {}".format(result["missing_library"]))
    reasons.append(_last_line(result.get("error")) or "CUDAExecutionProvider not active")
    return [
        Check(
            severity,
            name,
            "{}; CUDA lib dirs {}; set {} to the dir holding the missing library".format(
                "; ".join(reasons), dirs, cuda_runtime.LIBRARY_PATH_ENV
            ),
        )
    ]


# --------------------------------------------------------------------------
# CARLA port and GPU memory (both non-fatal)
# --------------------------------------------------------------------------


def listening_ports(paths=("/proc/net/tcp", "/proc/net/tcp6")):
    """Return local TCP ports in LISTEN state, or None if unavailable."""

    ports = set()
    readable = False
    for path in paths:
        try:
            with open(path, "r") as stream:
                lines = stream.read().splitlines()[1:]
        except OSError:
            continue
        readable = True
        for line in lines:
            fields = line.split()
            if len(fields) > 3 and fields[3] == TCP_LISTEN_STATE:
                ports.add(int(fields[1].rsplit(":", 1)[1], 16))
    return ports if readable else None


def tcp_connect(host, port, timeout=1.0):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_carla_port(host, port, listening=listening_ports, connect=tcp_connect):
    ports = listening() if host in LOCAL_HOSTS else None
    if ports is not None:
        reachable = port in ports
        method = "listening-socket table, no connection made"
    else:
        reachable = connect(host, port)
        method = "TCP connect"
    if reachable:
        return [Check(OK, "carla port", "{}:{} is listening ({})".format(host, port, method))]
    return [
        Check(
            WARN,
            "carla port",
            "{}:{} not listening ({}); CARLA is offline, needed only for scenario runs".format(
                host, port, method
            ),
        )
    ]


def check_gpu_memory(min_free_mib=DEFAULT_MIN_FREE_GPU_MIB, runner=subprocess.run):
    command = [
        "nvidia-smi",
        "--query-gpu=index,name,memory.free,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = _run(runner, command, 15)
    except (OSError, subprocess.SubprocessError) as exc:
        return [Check(WARN, "gpu memory", "nvidia-smi unavailable: {}".format(exc))]
    if completed.returncode != 0:
        return [
            Check(
                WARN,
                "gpu memory",
                "nvidia-smi failed: {}".format(_last_line(completed.stderr or completed.stdout)),
            )
        ]
    checks = []
    for line in completed.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) < 5:
            continue
        try:
            free_mib = int(float(fields[-3]))
            total_mib = int(float(fields[-2]))
        except ValueError:
            continue
        checks.append(
            Check(
                OK if free_mib >= min_free_mib else WARN,
                "gpu{} memory".format(fields[0]),
                "{} MiB free / {} MiB (min {}); {}, driver {}".format(
                    free_mib, total_mib, min_free_mib, ", ".join(fields[1:-3]), fields[-1]
                ),
            )
        )
    return checks or [Check(WARN, "gpu memory", "nvidia-smi reported no GPU")]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def run_checks(args):
    """Yield checks in report order; each group is isolated from the others."""

    yield from check_repository()
    yield from check_workspace_status()
    yield from check_launcher()
    try:
        model_config = load_model_config(args.sensor_config)
    except Exception as exc:  # unreadable YAML must not hide the other checks
        yield Check(FAIL, "sensor config", "{}: {}".format(args.sensor_config, exc))
        model_config = {}
    model_path = runtime_model_path(model_config)
    yield from check_models(model_path)
    # Free memory first: the probe itself briefly allocates GPU memory.
    yield from check_gpu_memory(args.min_free_gpu_mib)
    if args.skip_cuda_probe:
        yield Check(WARN, "cuda probe", "skipped (--skip-cuda-probe)")
    else:
        yield from check_cuda(model_config, model_path, timeout_s=args.probe_timeout)
    yield from check_carla_port(args.carla_host, args.carla_port)


def format_check(check):
    return "{:<5} {:<26} {}".format(check.status, check.name, check.detail)


def exit_code(checks):
    return 1 if any(check.status == FAIL for check in checks) else 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--sensor-config",
        type=Path,
        default=DEFAULT_SENSOR_CONFIG,
        help="Sensor config whose model block drives the model/CUDA checks "
        "(default: %(default)s).",
    )
    parser.add_argument(
        "--skip-cuda-probe",
        action="store_true",
        help="Do not create a CUDA ONNX Runtime session.",
    )
    parser.add_argument("--probe-timeout", type=float, default=DEFAULT_PROBE_TIMEOUT_S)
    parser.add_argument("--carla-host", default=DEFAULT_CARLA_HOST)
    parser.add_argument("--carla-port", type=int, default=DEFAULT_CARLA_PORT)
    parser.add_argument(
        "--min-free-gpu-mib",
        type=int,
        default=DEFAULT_MIN_FREE_GPU_MIB,
        help="WARN below this much free GPU memory (default: %(default)s).",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    print("AEB doctor: {}".format(AEB_ROOT))
    checks = []
    for check in run_checks(args):
        checks.append(check)
        print(format_check(check), flush=True)
    counts = {status: sum(1 for c in checks if c.status == status) for status in (OK, WARN, FAIL)}
    print(
        "Summary: {} OK, {} WARN, {} FAIL".format(counts[OK], counts[WARN], counts[FAIL])
    )
    return exit_code(checks)


if __name__ == "__main__":
    raise SystemExit(main())
