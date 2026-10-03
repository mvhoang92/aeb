"""Tests for CUDA library resolution, re-exec bootstrap and subprocess probe."""

from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from infrastructure import cuda_runtime


GPU_MODEL = {
    "enabled": True,
    "backend": "onnx",
    "path": "aeb/models/yolo26n_aeb_v7.onnx",
    "providers": ["CUDAExecutionProvider"],
    "require_provider": "CUDAExecutionProvider",
    "allow_provider_fallback": False,
    "provider_options": {"CUDAExecutionProvider": {"gpu_mem_limit": 536870912}},
}
CPU_MODEL = {
    "enabled": True,
    "backend": "onnx",
    "path": "aeb/models/yolo26n_aeb_v7.onnx",
    "providers": ["CPUExecutionProvider"],
}
ABORT_STDERR = (
    "Could not load library libcublasLt.so.12. Error: libcublasLt.so.12: "
    "cannot open shared object file: No such file or directory\n"
)


def completed(returncode, stdout="", stderr=""):
    return subprocess.CompletedProcess(["python"], returncode, stdout, stderr)


class CudaRuntimeTestCase(unittest.TestCase):
    def setUp(self):
        self.saved_state = dict(cuda_runtime._STATE)
        cuda_runtime._STATE["bootstrap"] = None
        cuda_runtime._STATE["probes"] = {}
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.system_dir = self.root / "cuda-11.7" / "lib64"
        self.env_dir = self.root / "custom"
        self.config_dir = self.root / "from_config"
        self.site_dir = self.root / "site-packages"
        for path in (self.system_dir, self.env_dir, self.config_dir):
            path.mkdir(parents=True)
        for package in ("cublas", "cudnn"):
            (self.site_dir / "nvidia" / package / "lib").mkdir(parents=True)

    def tearDown(self):
        cuda_runtime._STATE.clear()
        cuda_runtime._STATE.update(self.saved_state)
        self.temp.cleanup()


class ResolutionTests(CudaRuntimeTestCase):
    def resolve(self, model_config=None, environ=None, system_dirs=None):
        return cuda_runtime.resolve_cuda_library_dirs(
            model_config,
            environ=environ or {},
            system_dirs=(str(self.system_dir),) if system_dirs is None else system_dirs,
            site_dirs=[str(self.site_dir)],
        )

    def test_env_variable_has_highest_priority(self):
        missing = str(self.root / "missing")
        resolution = self.resolve(
            dict(GPU_MODEL, cuda_library_path=str(self.config_dir)),
            {"AEB_CUDA_LIBRARY_PATH": "{}:{}".format(self.env_dir, missing)},
        )
        self.assertEqual([str(self.env_dir)], resolution.dirs)
        self.assertEqual("env:AEB_CUDA_LIBRARY_PATH", resolution.source)
        self.assertEqual([missing], resolution.ignored)

    def test_config_key_used_when_env_is_unset_or_blank(self):
        resolution = self.resolve(
            dict(GPU_MODEL, cuda_library_path=[str(self.config_dir)]),
            {"AEB_CUDA_LIBRARY_PATH": "  "},
        )
        self.assertEqual([str(self.config_dir)], resolution.dirs)
        self.assertEqual("config:model.cuda_library_path", resolution.source)

    def test_system_default_preferred_over_pip_wheels(self):
        resolution = self.resolve(GPU_MODEL)
        self.assertEqual([str(self.system_dir)], resolution.dirs)
        self.assertEqual("default:system_cuda", resolution.source)

    def test_pip_nvidia_dirs_are_fallback_when_system_cuda_is_absent(self):
        resolution = self.resolve(GPU_MODEL, system_dirs=(str(self.root / "nope"),))
        self.assertEqual("default:pip_nvidia", resolution.source)
        self.assertEqual(
            [
                str(self.site_dir / "nvidia" / "cublas" / "lib"),
                str(self.site_dir / "nvidia" / "cudnn" / "lib"),
            ],
            resolution.dirs,
        )

    def test_nothing_found(self):
        resolution = cuda_runtime.resolve_cuda_library_dirs(
            GPU_MODEL,
            environ={},
            system_dirs=(str(self.root / "nope"),),
            site_dirs=[],
        )
        self.assertEqual(([], "none"), (resolution.dirs, resolution.source))

    def test_cuda_requested_and_required(self):
        self.assertTrue(cuda_runtime.cuda_requested(GPU_MODEL))
        self.assertTrue(cuda_runtime.cuda_required(GPU_MODEL))
        self.assertFalse(cuda_runtime.cuda_requested(CPU_MODEL))
        self.assertFalse(cuda_runtime.cuda_required(CPU_MODEL))
        self.assertFalse(cuda_runtime.cuda_requested(dict(GPU_MODEL, enabled=False)))
        self.assertFalse(
            cuda_runtime.cuda_requested(dict(GPU_MODEL, backend="ultralytics"))
        )
        self.assertTrue(cuda_runtime.cuda_requested({}))
        self.assertFalse(cuda_runtime.cuda_required({}))


class BootstrapTests(CudaRuntimeTestCase):
    def ensure(self, model_config, environ, execve):
        script = self.root / "runner.py"
        script.write_text("")
        with mock.patch("sys.stderr", new=io.StringIO()):
            return self._ensure(script, model_config, environ, execve)

    def _ensure(self, script, model_config, environ, execve):
        return cuda_runtime.ensure_cuda_library_path(
            model_config,
            argv=[str(script), "--flag"],
            environ=environ,
            executable="/venv/bin/python",
            execve=execve,
            system_dirs=(str(self.system_dir),),
            site_dirs=[],
        )

    def test_reexec_prepends_missing_dirs_and_marks_environment(self):
        execve = mock.Mock()
        self.ensure(GPU_MODEL, {"LD_LIBRARY_PATH": "/opt/x", "HOME": "/h"}, execve)
        executable, argv, env = execve.call_args[0]
        self.assertEqual("/venv/bin/python", executable)
        self.assertEqual(["/venv/bin/python", str(self.root / "runner.py"), "--flag"], argv)
        self.assertEqual("{}:/opt/x".format(self.system_dir), env["LD_LIBRARY_PATH"])
        self.assertEqual("1", env["AEB_CUDA_REEXEC"])
        self.assertEqual("/opt/x", env["AEB_CUDA_ORIGINAL_LD_LIBRARY_PATH"])
        self.assertEqual("/h", env["HOME"])

    def test_no_reexec_when_dirs_already_on_path(self):
        execve = mock.Mock()
        info = self.ensure(GPU_MODEL, {"LD_LIBRARY_PATH": str(self.system_dir)}, execve)
        execve.assert_not_called()
        self.assertFalse(info["cuda_reexec_applied"])
        self.assertEqual(str(self.system_dir), info["ld_library_path_at_start"])
        self.assertIs(info, cuda_runtime.bootstrap_info())

    def test_cpu_config_is_untouched(self):
        execve = mock.Mock()
        info = self.ensure(CPU_MODEL, {}, execve)
        execve.assert_not_called()
        self.assertFalse(info["cuda_requested"])
        self.assertEqual([], info["cuda_library_dirs"])

    def test_reexec_happens_at_most_once(self):
        execve = mock.Mock()
        info = self.ensure(
            GPU_MODEL,
            {
                "AEB_CUDA_REEXEC": "1",
                "AEB_CUDA_ORIGINAL_LD_LIBRARY_PATH": "",
                "LD_LIBRARY_PATH": "",
            },
            execve,
        )
        execve.assert_not_called()
        self.assertTrue(info["cuda_reexec_applied"])
        self.assertEqual("already re-executed", info["cuda_reexec_skipped_reason"])

    def test_opt_out_disables_reexec(self):
        execve = mock.Mock()
        info = self.ensure(GPU_MODEL, {"AEB_CUDA_NO_REEXEC": "1"}, execve)
        execve.assert_not_called()
        self.assertEqual("AEB_CUDA_NO_REEXEC=1", info["cuda_reexec_skipped_reason"])

    def test_interactive_argv_is_not_reexeced(self):
        execve = mock.Mock()
        info = cuda_runtime.ensure_cuda_library_path(
            GPU_MODEL,
            argv=["-c"],
            environ={},
            execve=execve,
            system_dirs=(str(self.system_dir),),
            site_dirs=[],
        )
        execve.assert_not_called()
        self.assertEqual("argv is not a script path", info["cuda_reexec_skipped_reason"])


class ProbeTests(CudaRuntimeTestCase):
    def test_native_abort_is_reported_with_missing_library(self):
        runner = mock.Mock(return_value=completed(-6, stderr=ABORT_STDERR))
        result = cuda_runtime.probe_cuda_session(
            "/m.onnx",
            {"gpu_mem_limit": 1},
            environ={"LD_LIBRARY_PATH": ""},
            runner=runner,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(-6, result["returncode"])
        self.assertEqual(6, result["signal"])
        self.assertEqual("libcublasLt.so.12", result["missing_library"])
        command = runner.call_args[0][0]
        self.assertEqual("-c", command[1])
        self.assertEqual("/m.onnx", command[3])
        self.assertEqual('{"gpu_mem_limit": "1"}', command[4])

    def test_success_requires_cuda_in_probe_providers(self):
        ok_stdout = (
            'AEB_CUDA_PROBE {"providers": ["CUDAExecutionProvider", '
            '"CPUExecutionProvider"], "onnxruntime_version": "1.14.1"}\n'
        )
        result = cuda_runtime.probe_cuda_session(
            "/m.onnx",
            environ={},
            runner=mock.Mock(return_value=completed(0, stdout=ok_stdout)),
        )
        self.assertTrue(result["ok"])
        self.assertEqual("1.14.1", result["onnxruntime_version"])

        cpu_stdout = 'AEB_CUDA_PROBE {"providers": ["CPUExecutionProvider"]}\n'
        result = cuda_runtime.probe_cuda_session(
            "/other.onnx",
            environ={},
            runner=mock.Mock(return_value=completed(0, stdout=cpu_stdout)),
        )
        self.assertFalse(result["ok"])

    def test_probe_result_is_cached_per_model_and_library_path(self):
        runner = mock.Mock(return_value=completed(-6, stderr=ABORT_STDERR))
        for _ in range(2):
            cuda_runtime.probe_cuda_session("/m.onnx", environ={}, runner=runner)
        self.assertEqual(1, runner.call_count)
        cuda_runtime.probe_cuda_session(
            "/m.onnx",
            environ={"LD_LIBRARY_PATH": "/x"},
            runner=runner,
        )
        self.assertEqual(2, runner.call_count)

    def test_timeout_is_a_failure_not_an_exception(self):
        runner = mock.Mock(side_effect=subprocess.TimeoutExpired("python", 5))
        result = cuda_runtime.probe_cuda_session(
            "/m.onnx", environ={}, runner=runner, timeout_s=5
        )
        self.assertFalse(result["ok"])
        self.assertIn("timed out", result["error"])

    def test_preflight_failure_exits_with_hard_stop_message(self):
        failure = cuda_runtime.probe_cuda_session(
            "/m.onnx",
            environ={},
            runner=mock.Mock(return_value=completed(-6, stderr=ABORT_STDERR)),
        )
        stream = io.StringIO()
        with self.assertRaises(SystemExit) as raised:
            cuda_runtime.preflight_or_exit(
                GPU_MODEL,
                "/m.onnx",
                stream=stream,
                prober=lambda path, options: failure,
            )
        self.assertEqual(cuda_runtime.TECHNICAL_HARD_STOP_EXIT_CODE, raised.exception.code)
        self.assertNotEqual(1, raised.exception.code)
        text = stream.getvalue()
        self.assertIn("TECHNICAL HARD-STOP", text)
        self.assertIn("libcublasLt.so.12", text)
        self.assertIn("AEB_CUDA_LIBRARY_PATH", text)
        self.assertIn("not an algorithm FAIL", text)

    def test_preflight_skipped_for_cpu_and_optional_cuda(self):
        prober = mock.Mock()
        self.assertIsNone(cuda_runtime.preflight_or_exit(CPU_MODEL, "/m", prober=prober))
        optional = dict(GPU_MODEL, require_provider=None)
        self.assertIsNone(cuda_runtime.preflight_or_exit(optional, "/m", prober=prober))
        prober.assert_not_called()

    def test_preflight_passes_provider_options(self):
        prober = mock.Mock(return_value={"ok": True, "providers": ["CUDAExecutionProvider"]})
        cuda_runtime.preflight_or_exit(GPU_MODEL, "/m.onnx", stream=io.StringIO(), prober=prober)
        prober.assert_called_once_with("/m.onnx", {"gpu_mem_limit": 536870912})


class YoloDetectorGuardTests(CudaRuntimeTestCase):
    """The shared detector must never create a CUDA session after a failed probe."""

    def make_fake_ort(self):
        fake = types.ModuleType("onnxruntime")
        fake.created = []

        class Session(object):
            def __init__(self, path, providers):
                fake.created.append(list(providers))
                self.providers = [
                    p if isinstance(p, str) else p[0] for p in providers
                ]

            def get_inputs(self):
                return [types.SimpleNamespace(name="images")]

            def get_outputs(self):
                return [types.SimpleNamespace(name="output0")]

            def get_modelmeta(self):
                return types.SimpleNamespace(custom_metadata_map={})

            def get_providers(self):
                return self.providers

        fake.InferenceSession = Session
        fake.get_available_providers = lambda: [
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]
        return fake

    def load(self, config, probe_result):
        from ui.manual_control_common import YoloDetector

        model = self.root / "m.onnx"
        model.write_bytes(b"")
        fake = self.make_fake_ort()
        with mock.patch.dict(sys.modules, {"onnxruntime": fake}), mock.patch.object(
            cuda_runtime, "probe_cuda_session", return_value=probe_result
        ), mock.patch("sys.stderr", new=io.StringIO()):
            detector = YoloDetector(dict(config, path=str(model)))
        return detector, fake

    def test_optional_cuda_falls_back_to_cpu_without_touching_cuda(self):
        failure = {"ok": False, "returncode": -6, "signal": 6,
                   "missing_library": "libcublasLt.so.12", "error": ABORT_STDERR}
        detector, fake = self.load(
            {"providers": ["CUDAExecutionProvider", "CPUExecutionProvider"]},
            failure,
        )
        self.assertEqual([["CPUExecutionProvider"]], fake.created)
        self.assertEqual(["CPUExecutionProvider"], detector.active_providers)
        self.assertIs(failure, detector.cuda_probe)

    def test_required_cuda_raises_clean_error(self):
        failure = {"ok": False, "returncode": -6, "signal": 6,
                   "missing_library": "libcublasLt.so.12", "error": ABORT_STDERR}
        with self.assertRaises(RuntimeError) as raised:
            self.load(GPU_MODEL, failure)
        self.assertIn("libcublasLt.so.12", str(raised.exception))
        self.assertIn("AEB_CUDA_LIBRARY_PATH", str(raised.exception))

    def test_successful_probe_keeps_cuda(self):
        detector, fake = self.load(
            GPU_MODEL,
            {"ok": True, "providers": ["CUDAExecutionProvider"]},
        )
        self.assertEqual("CUDAExecutionProvider", fake.created[0][0][0])
        self.assertIn("CUDAExecutionProvider", detector.active_providers)


if __name__ == "__main__":
    unittest.main()
