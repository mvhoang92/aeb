"""Make ONNX Runtime CUDA sessions robust in non-interactive shells.

Background (measured on the home workstation): the system cuDNN
``libcudnn8 8.9.7+cuda12.2`` dlopens ``libcublasLt.so.12``.  That name only
exists as a symlink in ``/usr/local/cuda-11.7/lib64`` and is not indexed by
``ld.so.cache`` (the target's SONAME is ``libcublasLt.so.11``).  Interactive
shells add the directory through ``~/.bashrc``; ssh/nohup/desktop launches do
not, and creating the CUDA session then aborts the whole interpreter with
SIGABRT.

Mechanism: glibc reads ``LD_LIBRARY_PATH`` only at process start, and
preloading the library with ``ctypes.CDLL(..., RTLD_GLOBAL)`` does not help
because the loader matches already-loaded objects by SONAME (``.so.11``), not
by the requested ``.so.12`` name (verified: preload still aborts).  The entry
point therefore re-executes the interpreter once with the resolved CUDA
library directories prepended to ``LD_LIBRARY_PATH``.  Before a run that
requires ``CUDAExecutionProvider`` the session is probed in a subprocess, so a
native abort becomes a readable technical hard-stop instead of killing the
runner.
"""

from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys
import time
from collections import namedtuple
from pathlib import Path


AEB_ROOT = Path(__file__).resolve().parents[1]
CUDA_PROVIDER = "CUDAExecutionProvider"
LIBRARY_PATH_ENV = "AEB_CUDA_LIBRARY_PATH"
REEXEC_MARKER_ENV = "AEB_CUDA_REEXEC"
ORIGINAL_LD_PATH_ENV = "AEB_CUDA_ORIGINAL_LD_LIBRARY_PATH"
NO_REEXEC_ENV = "AEB_CUDA_NO_REEXEC"
CONFIG_KEY = "cuda_library_path"
DEFAULT_SYSTEM_CUDA_DIRS = ("/usr/local/cuda-11.7/lib64",)
TECHNICAL_HARD_STOP_EXIT_CODE = 3
DEFAULT_PROBE_TIMEOUT_S = 180.0

CudaLibraryResolution = namedtuple(
    "CudaLibraryResolution",
    ("dirs", "source", "ignored"),
)

_STATE = {"bootstrap": None, "probes": {}}

_MISSING_LIBRARY_PATTERNS = (
    re.compile(r"(lib[\w.+-]+?\.so(?:\.\d+)*): cannot open shared object file"),
    re.compile(r"Could not load library (lib[\w.+-]+?\.so(?:\.\d+)*)"),
)

_PROBE_CODE = """
import json, sys
import numpy as np
import onnxruntime as ort
model_path, options = sys.argv[1], json.loads(sys.argv[2])
provider = ("CUDAExecutionProvider", options) if options else "CUDAExecutionProvider"
session = ort.InferenceSession(model_path, providers=[provider])
model_input = session.get_inputs()[0]
shape = [dim if isinstance(dim, int) and dim > 0 else 1 for dim in model_input.shape]
dtype = np.float16 if "float16" in str(model_input.type) else np.float32
session.run(None, {model_input.name: np.zeros(shape, dtype=dtype)})
print("AEB_CUDA_PROBE " + json.dumps({
    "providers": session.get_providers(),
    "onnxruntime_version": ort.__version__,
}))
"""


def cuda_requested(model_config):
    """Return True when a model config would create a CUDA ORT session."""

    config = model_config or {}
    if not bool(config.get("enabled", True)):
        return False
    backend = str(config.get("backend", "auto")).lower()
    path = str(config.get("path") or "")
    if backend == "ultralytics":
        return False
    if backend == "auto" and path and not path.lower().endswith(".onnx"):
        return False
    providers = config.get("providers", [CUDA_PROVIDER, "CPUExecutionProvider"])
    names = [str(provider) for provider in (providers or [])]
    return CUDA_PROVIDER in names or config.get("require_provider") == CUDA_PROVIDER


def cuda_required(model_config):
    """Return True when CUDA is mandatory (CPU fallback is a hard-stop)."""

    config = model_config or {}
    return (
        cuda_requested(config)
        and str(config.get("require_provider") or "") == CUDA_PROVIDER
    )


def split_path_list(value):
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        items = [str(item) for item in value]
    else:
        items = str(value).split(os.pathsep)
    return [item.strip() for item in items if item and item.strip()]


def _normalize_dirs(values, base=None):
    normalized = []
    for value in values:
        path = os.path.expanduser(str(value))
        if base is not None and not os.path.isabs(path):
            path = os.path.join(str(base), path)
        path = os.path.normpath(path)
        if path not in normalized:
            normalized.append(path)
    return normalized


def _partition_existing(paths):
    existing = [path for path in paths if os.path.isdir(path)]
    ignored = [path for path in paths if not os.path.isdir(path)]
    return existing, ignored


def site_packages_dirs():
    candidates = []
    try:
        import site  # pylint: disable=import-outside-toplevel

        candidates.extend(site.getsitepackages())
    except AttributeError:
        pass
    candidates.extend(
        path for path in sys.path if path and path.rstrip("/").endswith("site-packages")
    )
    unique = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def pip_nvidia_library_dirs(site_dirs=None):
    dirs = []
    for site_dir in site_packages_dirs() if site_dirs is None else site_dirs:
        for path in sorted(glob.glob(os.path.join(str(site_dir), "nvidia", "*", "lib"))):
            if os.path.isdir(path) and path not in dirs:
                dirs.append(path)
    return dirs


def resolve_cuda_library_dirs(
    model_config=None,
    environ=None,
    system_dirs=DEFAULT_SYSTEM_CUDA_DIRS,
    site_dirs=None,
):
    """Resolve CUDA library dirs: env, then model config, then defaults.

    The pip ``nvidia/*/lib`` directories are only a fallback when no system
    CUDA directory exists, because putting them first would silently replace
    the validated system cuDNN with the pip wheel's cuDNN.
    """

    environ = os.environ if environ is None else environ
    env_value = environ.get(LIBRARY_PATH_ENV, "")
    if env_value.strip():
        existing, ignored = _partition_existing(
            _normalize_dirs(split_path_list(env_value))
        )
        return CudaLibraryResolution(existing, "env:" + LIBRARY_PATH_ENV, ignored)

    config_value = (model_config or {}).get(CONFIG_KEY)
    if config_value:
        existing, ignored = _partition_existing(
            _normalize_dirs(split_path_list(config_value), base=AEB_ROOT)
        )
        return CudaLibraryResolution(existing, "config:model." + CONFIG_KEY, ignored)

    system, _ = _partition_existing(_normalize_dirs(system_dirs or ()))
    if system:
        return CudaLibraryResolution(system, "default:system_cuda", [])
    pip_dirs = pip_nvidia_library_dirs(site_dirs)
    if pip_dirs:
        return CudaLibraryResolution(pip_dirs, "default:pip_nvidia", [])
    return CudaLibraryResolution([], "none", [])


def _reexec_argv(argv):
    if not argv or not argv[0] or argv[0] in ("-c", "-m", "-"):
        return None
    if not os.path.exists(argv[0]):
        return None
    return list(argv)


def ensure_cuda_library_path(
    model_config=None,
    argv=None,
    environ=None,
    executable=None,
    execve=None,
    system_dirs=DEFAULT_SYSTEM_CUDA_DIRS,
    site_dirs=None,
):
    """Re-exec the interpreter once so CUDA libraries are on LD_LIBRARY_PATH.

    Must be called by an entry point before any CARLA/pygame resource exists.
    It is a no-op for configs that do not request CUDAExecutionProvider and
    when every resolved directory is already on ``LD_LIBRARY_PATH``.
    """

    environ = os.environ if environ is None else environ
    reexeced = environ.get(REEXEC_MARKER_ENV) == "1"
    current_ld = environ.get("LD_LIBRARY_PATH", "")
    info = {
        "cuda_requested": cuda_requested(model_config),
        "cuda_library_dirs": [],
        "cuda_library_dirs_source": None,
        "cuda_library_dirs_ignored": [],
        "cuda_reexec_applied": reexeced,
        "cuda_reexec_skipped_reason": None,
        "ld_library_path_at_start": (
            environ.get(ORIGINAL_LD_PATH_ENV, "") if reexeced else current_ld
        ),
    }
    if info["cuda_requested"]:
        resolution = resolve_cuda_library_dirs(
            model_config,
            environ=environ,
            system_dirs=system_dirs,
            site_dirs=site_dirs,
        )
        info["cuda_library_dirs"] = list(resolution.dirs)
        info["cuda_library_dirs_source"] = resolution.source
        info["cuda_library_dirs_ignored"] = list(resolution.ignored)
        current = split_path_list(current_ld)
        missing = [path for path in resolution.dirs if path not in current]
        reexec_argv = _reexec_argv(sys.argv if argv is None else argv)
        if missing:
            if reexeced:
                info["cuda_reexec_skipped_reason"] = "already re-executed"
            elif environ.get(NO_REEXEC_ENV) == "1":
                info["cuda_reexec_skipped_reason"] = NO_REEXEC_ENV + "=1"
            elif reexec_argv is None:
                info["cuda_reexec_skipped_reason"] = "argv is not a script path"
            else:
                new_env = dict(environ)
                new_env["LD_LIBRARY_PATH"] = os.pathsep.join(missing + current)
                new_env[REEXEC_MARKER_ENV] = "1"
                new_env[ORIGINAL_LD_PATH_ENV] = current_ld
                executable = executable or sys.executable
                print(
                    "[cuda_runtime] re-exec with CUDA library dirs {} ({})".format(
                        os.pathsep.join(missing),
                        resolution.source,
                    ),
                    file=sys.stderr,
                )
                sys.stdout.flush()
                sys.stderr.flush()
                (execve or os.execve)(executable, [executable] + reexec_argv, new_env)
                return info  # only reached when execve is mocked
    _STATE["bootstrap"] = info
    return info


def bootstrap_info():
    return _STATE["bootstrap"]


def parse_missing_library(text):
    for pattern in _MISSING_LIBRARY_PATTERNS:
        match = pattern.search(text or "")
        if match:
            return match.group(1)
    return None


def _excerpt(text, limit=800):
    text = (text or "").strip()
    return text if len(text) <= limit else "..." + text[-limit:]


def probe_cuda_session(
    model_path,
    provider_options=None,
    environ=None,
    timeout_s=DEFAULT_PROBE_TIMEOUT_S,
    runner=None,
    executable=None,
    use_cache=True,
):
    """Create a CUDA ORT session in a subprocess and run one inference.

    A native abort (SIGABRT) only kills the child; the caller receives a
    result dict with ``ok`` False, the return code and the missing library.
    """

    environ = dict(os.environ if environ is None else environ)
    options = {
        str(key): str(value) for key, value in (provider_options or {}).items()
    }
    cache_key = (
        str(model_path),
        environ.get("LD_LIBRARY_PATH", ""),
        json.dumps(options, sort_keys=True),
    )
    if use_cache and cache_key in _STATE["probes"]:
        return _STATE["probes"][cache_key]

    command = [
        executable or sys.executable,
        "-c",
        _PROBE_CODE,
        str(model_path),
        json.dumps(options, sort_keys=True),
    ]
    started = time.monotonic()
    result = {
        "ok": False,
        "model_path": str(model_path),
        "returncode": None,
        "signal": None,
        "missing_library": None,
        "providers": [],
        "onnxruntime_version": None,
        "error": None,
        "duration_s": None,
        "ld_library_path": environ.get("LD_LIBRARY_PATH", ""),
    }
    try:
        completed = (runner or subprocess.run)(
            command,
            cwd=str(AEB_ROOT),
            env=environ,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        result["error"] = "CUDA probe timed out after {:.0f}s".format(timeout_s)
    except OSError as exc:
        result["error"] = "CUDA probe could not start: {}".format(exc)
    else:
        output = "{}\n{}".format(completed.stdout or "", completed.stderr or "")
        result["returncode"] = completed.returncode
        if completed.returncode is not None and completed.returncode < 0:
            result["signal"] = -completed.returncode
        for line in (completed.stdout or "").splitlines():
            if line.startswith("AEB_CUDA_PROBE "):
                try:
                    payload = json.loads(line[len("AEB_CUDA_PROBE "):])
                except ValueError:
                    payload = {}
                result["providers"] = list(payload.get("providers") or [])
                result["onnxruntime_version"] = payload.get("onnxruntime_version")
        result["missing_library"] = parse_missing_library(output)
        result["ok"] = (
            completed.returncode == 0 and CUDA_PROVIDER in result["providers"]
        )
        if not result["ok"]:
            result["error"] = _excerpt(completed.stderr or completed.stdout) or (
                "CUDAExecutionProvider is not active in the probe session"
            )
    result["duration_s"] = round(time.monotonic() - started, 3)
    if use_cache:
        _STATE["probes"][cache_key] = result
    return result


def last_probe_result():
    probes = list(_STATE["probes"].values())
    return probes[-1] if probes else None


def candidate_dirs_for_library(library_name, site_dirs=None):
    """Return directories on this machine that contain ``library_name``."""

    if not library_name:
        return []
    candidates = sorted(glob.glob("/usr/local/cuda*/lib64")) + pip_nvidia_library_dirs(
        site_dirs
    )
    found = []
    for directory in candidates:
        if os.path.exists(os.path.join(directory, library_name)):
            real = os.path.realpath(directory)
            if directory not in found and real not in found:
                found.append(directory)
    return found


def format_probe_failure(result, resolution_info=None, hard_stop=True):
    if resolution_info is None:
        resolution_info = bootstrap_info()
    if not resolution_info or not resolution_info.get("cuda_library_dirs_source"):
        resolution = resolve_cuda_library_dirs()
        resolution_info = {
            "cuda_library_dirs": resolution.dirs,
            "cuda_library_dirs_source": resolution.source,
        }
    status = "exit code {}".format(result.get("returncode"))
    if result.get("signal"):
        status += " (signal {}{})".format(
            result["signal"],
            ", SIGABRT" if result["signal"] == 6 else "",
        )
    lines = [
        "{}: CUDAExecutionProvider preflight failed ({}).{}".format(
            "TECHNICAL HARD-STOP" if hard_stop else "WARNING",
            status if result.get("returncode") is not None else result.get("error"),
            "" if hard_stop else " Falling back to CPUExecutionProvider.",
        ),
    ]
    missing = result.get("missing_library")
    if missing:
        lines.append("  Missing CUDA library: {}".format(missing))
    lines.append(
        "  CUDA library dirs: {} (source: {})".format(
            os.pathsep.join(resolution_info.get("cuda_library_dirs") or []) or "<none>",
            resolution_info.get("cuda_library_dirs_source") or "unresolved",
        )
    )
    lines.append(
        "  LD_LIBRARY_PATH seen by probe: {}".format(
            result.get("ld_library_path") or "<empty>"
        )
    )
    if result.get("error") and result.get("returncode") is not None:
        lines.append("  Probe output: {}".format(result["error"].replace("\n", " | ")))
    suggestions = candidate_dirs_for_library(missing)
    example = suggestions[0] if suggestions else "/usr/local/cuda-11.7/lib64"
    lines.append(
        "  Fix: export {}=<dir containing {}> (colon-separated list), e.g. "
        "{}={}, then rerun.".format(
            LIBRARY_PATH_ENV,
            missing or "the CUDA/cuDNN libraries",
            LIBRARY_PATH_ENV,
            example,
        )
    )
    if hard_stop:
        lines.append(
            "  This is a runtime-environment hard-stop, not an algorithm FAIL; "
            "no scenario was run."
        )
    return "\n".join(lines)


def preflight_or_exit(model_config, model_path, stream=None, prober=None):
    """Probe CUDA when the config requires it; exit cleanly on failure."""

    stream = sys.stderr if stream is None else stream
    if not cuda_required(model_config):
        return None
    options = ((model_config or {}).get("provider_options") or {}).get(
        CUDA_PROVIDER
    )
    result = (prober or probe_cuda_session)(str(model_path), options)
    if result.get("ok"):
        print(
            "[cuda_runtime] CUDA preflight OK: providers={} ({}s)".format(
                ",".join(result.get("providers") or []),
                result.get("duration_s"),
            ),
            file=stream,
        )
        return result
    print(format_probe_failure(result), file=stream)
    stream.flush()
    raise SystemExit(TECHNICAL_HARD_STOP_EXIT_CODE)


_CUDA_LIBRARY_MAP_PATTERN = re.compile(
    r"lib(?:cudnn|cublas|cublasLt|cudart|cufft|curand|nvrtc|onnxruntime_providers_cuda)"
    r"[\w.-]*\.so"
)


def loaded_cuda_libraries(maps_path="/proc/self/maps"):
    """Return the CUDA-related shared objects mapped into this process."""

    try:
        with open(maps_path) as stream:
            lines = stream.read().splitlines()
    except (IOError, OSError):
        return []
    found = []
    for line in lines:
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        path = parts[5].strip()
        name = os.path.basename(path)
        if _CUDA_LIBRARY_MAP_PATTERN.match(name) and path not in found:
            found.append(path)
    return sorted(found)


def _decode_cudnn_version(value):
    value = int(value)
    if value >= 90000:  # cuDNN 9 encodes major*10000 + minor*100 + patch
        return "{}.{}.{}".format(value // 10000, (value % 10000) // 100, value % 100)
    return "{}.{}.{}".format(value // 1000, (value % 1000) // 100, value % 100)


def _decode_cuda_version(value):
    value = int(value)
    return "{}.{}".format(value // 1000, (value % 1000) // 10)


def _library_version(libraries, prefix, symbol, decoder, pointer_arg):
    """Query a version from a library that is *already* mapped in-process."""

    import ctypes  # pylint: disable=import-outside-toplevel

    for path in libraries:
        if not os.path.basename(path).startswith(prefix):
            continue
        try:
            library = ctypes.CDLL(path)
            function = getattr(library, symbol)
            if pointer_arg:
                value = ctypes.c_int(0)
                if function(ctypes.byref(value)) != 0:
                    return None
                return decoder(value.value)
            function.restype = ctypes.c_size_t
            return decoder(function())
        except (OSError, AttributeError, ValueError):
            return None
    return None


def onnxruntime_details():
    """Return ORT version/providers without importing ORT into a CPU-only run."""

    module = sys.modules.get("onnxruntime")
    if module is not None:
        try:
            providers = list(module.get_available_providers())
        except Exception:  # pylint: disable=broad-except
            providers = None
        return getattr(module, "__version__", None), providers
    try:
        import pkg_resources  # pylint: disable=import-outside-toplevel
    except ImportError:
        return None, None
    for distribution in ("onnxruntime-gpu", "onnxruntime"):
        try:
            return pkg_resources.get_distribution(distribution).version, None
        except Exception:  # pylint: disable=broad-except
            continue
    return None, None


def nvidia_driver_info(runner=None):
    """Query nvidia-smi once; tolerate a missing binary or driver."""

    if "nvidia_smi" in _STATE:
        return _STATE["nvidia_smi"]
    info = {"nvidia_driver_version": None, "gpu_name": None}
    try:
        completed = (runner or subprocess.run)(
            [
                "nvidia-smi",
                "--query-gpu=driver_version,name",
                "--format=csv,noheader",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        completed = None
    if completed is not None and completed.returncode == 0:
        first = (completed.stdout or "").strip().splitlines()
        if first:
            fields = [field.strip() for field in first[0].split(",", 1)]
            info["nvidia_driver_version"] = fields[0] or None
            info["gpu_name"] = fields[1] if len(fields) > 1 else None
    _STATE["nvidia_smi"] = info
    return info


def process_start_ld_library_path(environ_path="/proc/self/environ"):
    """Return LD_LIBRARY_PATH as the dynamic loader saw it at exec time.

    ``os.environ`` is not authoritative: e.g. importing cv2 prepends its own
    lib dir there, which the loader never reads.
    """

    try:
        with open(environ_path, "rb") as stream:
            entries = stream.read().split(b"\0")
    except (IOError, OSError):
        return None
    for entry in entries:
        if entry.startswith(b"LD_LIBRARY_PATH="):
            return entry[len(b"LD_LIBRARY_PATH="):].decode("utf-8", "replace")
    return ""


def runtime_environment(environ=None):
    """Return additive ``run_metadata.json`` evidence about the GPU runtime."""

    effective_ld = process_start_ld_library_path() if environ is None else None
    environ = os.environ if environ is None else environ
    bootstrap = bootstrap_info()
    if bootstrap is None:
        reexeced = environ.get(REEXEC_MARKER_ENV) == "1"
        bootstrap = {
            "cuda_requested": None,
            "cuda_library_dirs": [],
            "cuda_library_dirs_source": "not_bootstrapped",
            "cuda_library_dirs_ignored": [],
            "cuda_reexec_applied": reexeced,
            "cuda_reexec_skipped_reason": None,
            "ld_library_path_at_start": (
                environ.get(ORIGINAL_LD_PATH_ENV, "")
                if reexeced
                else environ.get("LD_LIBRARY_PATH", "")
            ),
        }
    libraries = loaded_cuda_libraries()
    ort_version, ort_providers = onnxruntime_details()
    probe = last_probe_result()
    info = dict(bootstrap)
    info.update(
        {
            "ld_library_path_effective": (
                environ.get("LD_LIBRARY_PATH", "")
                if effective_ld is None
                else effective_ld
            ),
            "onnxruntime_version": ort_version,
            "onnxruntime_available_providers": ort_providers,
            "cuda_preflight": (
                None
                if probe is None
                else {
                    key: probe.get(key)
                    for key in (
                        "ok",
                        "returncode",
                        "missing_library",
                        "providers",
                        "duration_s",
                    )
                }
            ),
            "loaded_cuda_libraries": libraries,
            "cudnn_version": _library_version(
                libraries, "libcudnn.so", "cudnnGetVersion", _decode_cudnn_version, False
            ),
            "cuda_runtime_version": _library_version(
                libraries,
                "libcudart.so",
                "cudaRuntimeGetVersion",
                _decode_cuda_version,
                True,
            ),
        }
    )
    info.update(nvidia_driver_info())
    return info


def main(argv=None):
    """CLI: ``python -m infrastructure.cuda_runtime MODEL.onnx`` probes CUDA."""

    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python -m infrastructure.cuda_runtime MODEL.onnx", file=sys.stderr)
        return 2
    result = probe_cuda_session(argv[0], use_cache=False)
    if result["ok"]:
        print("CUDA probe OK: providers={}".format(",".join(result["providers"])))
        return 0
    print(format_probe_failure(result), file=sys.stderr)
    return TECHNICAL_HARD_STOP_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
