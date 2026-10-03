"""Unit tests for scripts/maintenance/doctor.py (all external effects mocked)."""

from __future__ import annotations

import contextlib
import hashlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts.maintenance import doctor
from scripts.maintenance.doctor import FAIL, OK, WARN


def completed(stdout="", returncode=0, stderr=""):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def git_runner(branch="main", head="abc1234", status=""):
    def run(command, **kwargs):
        if command[-1] == "--porcelain":
            return completed(status)
        if command[-1] == "HEAD" and "--short" in command:
            return completed(head + "\n")
        return completed(branch + "\n")

    return run


class RepositoryTests(unittest.TestCase):
    def test_clean_tree_is_ok(self):
        [check] = doctor.check_repository(runner=git_runner())
        self.assertEqual(OK, check.status)
        self.assertEqual("main @ abc1234, clean", check.detail)

    def test_dirty_tree_counts_modified_and_untracked(self):
        status = " M a.py\nA  b.py\n?? c.txt\n"
        [check] = doctor.check_repository(runner=git_runner(status=status))
        self.assertEqual(WARN, check.status)
        self.assertIn("2 modified/staged, 1 untracked", check.detail)

    def test_missing_git_is_warn(self):
        def run(command, **kwargs):
            raise OSError("git not found")

        [check] = doctor.check_repository(runner=run)
        self.assertEqual(WARN, check.status)
        self.assertIn("git not found", check.detail)


def workspace_status(dataset_ok=True, env_ok=True, dir_ok=True):
    return {
        "directories": {
            "workspace": {"path": "/ws", "exists": True},
            "logs": {"path": "/ws/runs/logs", "exists": dir_ok},
        },
        "datasets": {
            "dataset_v6": {"path": "/a", "exists": True, "dataset_yaml": True},
            "dataset_v7_same_lane": {"path": "/b", "exists": True, "dataset_yaml": dataset_ok},
        },
        "environment": {"yolo_python": "/ws/environments/yolo310/bin/python", "exists": env_ok},
    }


class WorkspaceTests(unittest.TestCase):
    def test_complete_workspace_is_ok(self):
        checks = doctor.check_workspace_status(collect=workspace_status)
        self.assertEqual([OK, OK, OK], [check.status for check in checks])
        self.assertEqual("2/2 generations with dataset.yaml", checks[1].detail)

    def test_missing_items_fail_like_check_workspace(self):
        checks = doctor.check_workspace_status(
            collect=lambda: workspace_status(dataset_ok=False, env_ok=False, dir_ok=False)
        )
        self.assertEqual([FAIL, FAIL, FAIL], [check.status for check in checks])
        self.assertIn("missing: logs", checks[0].detail)
        self.assertIn("missing: dataset_v7_same_lane", checks[1].detail)


class LauncherTests(unittest.TestCase):
    def test_reuses_prerequisite_function_output(self):
        def prerequisites():
            print("CARLA script       OK")
            print("Scenarios          66")
            return 0

        [check] = doctor.check_launcher(prerequisites=prerequisites)
        self.assertEqual(OK, check.status)
        self.assertIn("66 scenarios", check.detail)

    def test_missing_prerequisites_fail(self):
        def prerequisites():
            print("CARLA script       MISSING")
            print("YOLO Python        OK")
            print("Scenarios          66")
            return 2

        [check] = doctor.check_launcher(prerequisites=prerequisites)
        self.assertEqual(FAIL, check.status)
        self.assertIn("missing: CARLA script", check.detail)

    def test_exception_in_prerequisites_is_reported(self):
        def prerequisites():
            raise ValueError("bad yaml")

        [check] = doctor.check_launcher(prerequisites=prerequisites)
        self.assertEqual(FAIL, check.status)
        self.assertIn("bad yaml", check.detail)


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.repo = root / "repo"
        self.main = root / "main"
        (self.main / "models").mkdir(parents=True)
        (self.repo / "models").mkdir(parents=True)
        self.onnx = self.main / "models" / "m.onnx"
        self.onnx.write_bytes(b"onnx-bytes")
        self.manifest = root / "model_sha256.txt"

    def write_manifest(self, onnx_digest=None):
        onnx_digest = onnx_digest or hashlib.sha256(b"onnx-bytes").hexdigest()
        self.manifest.write_text(
            "{}  models/m.onnx\n{}  models/m.pt\n".format(onnx_digest, "0" * 64)
        )

    def run_check(self, model_path=None):
        return doctor.check_models(
            model_path if model_path is not None else self.onnx,
            manifest_path=self.manifest,
            search_roots=(self.repo, self.main),
            hasher=lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        )

    def test_matching_onnx_ok_missing_pt_warn(self):
        self.write_manifest()
        checks = {check.name: check for check in self.run_check()}
        self.assertEqual(OK, checks["model m.onnx"].status)
        self.assertIn(str(self.onnx), checks["model m.onnx"].detail)
        self.assertEqual(WARN, checks["model m.pt"].status)
        self.assertEqual(OK, checks["runtime model"].status)

    def test_hash_mismatch_fails(self):
        self.write_manifest(onnx_digest="f" * 64)
        checks = {check.name: check for check in self.run_check()}
        self.assertEqual(FAIL, checks["model m.onnx"].status)
        self.assertIn("!= manifest ffffffffffff", checks["model m.onnx"].detail)
        self.assertEqual(FAIL, checks["runtime model"].status)

    def test_missing_onnx_and_runtime_model_fail(self):
        self.write_manifest()
        self.onnx.unlink()
        checks = {check.name: check for check in self.run_check()}
        self.assertEqual(FAIL, checks["model m.onnx"].status)
        self.assertEqual(FAIL, checks["runtime model"].status)

    def test_unreadable_manifest_fails(self):
        [check] = self.run_check()
        self.assertEqual(FAIL, check.status)
        self.assertEqual("model manifest", check.name)

    def test_runtime_model_path_resolves_from_carla_root(self):
        path = doctor.runtime_model_path({"path": "aeb/models/x.onnx"}, carla_root=Path("/c"))
        self.assertEqual(Path("/c/aeb/models/x.onnx"), path)
        self.assertIsNone(doctor.runtime_model_path({"enabled": False, "path": "x.onnx"}))


REQUIRED = {
    "backend": "onnx",
    "path": "m.onnx",
    "providers": ["CUDAExecutionProvider"],
    "require_provider": "CUDAExecutionProvider",
    "provider_options": {"CUDAExecutionProvider": {"gpu_mem_limit": 1}},
}
OPTIONAL = {"backend": "onnx", "path": "m.onnx", "providers": ["CUDAExecutionProvider", "CPUExecutionProvider"]}


class CudaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model = Path(self.tmp.name) / "m.onnx"
        self.model.write_bytes(b"")
        self.lib_dir = Path(self.tmp.name) / "cuda"
        self.lib_dir.mkdir()

    def run_check(self, config, result=None, error=None):
        calls = []

        def probe(model_path, options, **kwargs):
            calls.append((model_path, options, kwargs))
            if error:
                raise error
            return result

        environ = {"AEB_CUDA_LIBRARY_PATH": str(self.lib_dir), "LD_LIBRARY_PATH": "/x"}
        checks = doctor.check_cuda(
            config, self.model, probe=probe, executable="/py", environ=environ
        )
        return checks, calls

    def test_successful_probe_is_ok_and_uses_resolved_dirs(self):
        [check], calls = self.run_check(
            REQUIRED, {"ok": True, "providers": ["CUDAExecutionProvider"], "duration_s": 1.0}
        )
        self.assertEqual(OK, check.status)
        model_path, options, kwargs = calls[0]
        self.assertEqual({"gpu_mem_limit": 1}, options)
        self.assertEqual("/py", kwargs["executable"])
        self.assertFalse(kwargs["use_cache"])
        self.assertEqual(
            "{}:/x".format(self.lib_dir), kwargs["environ"]["LD_LIBRARY_PATH"]
        )

    def test_failed_probe_fails_when_cuda_required(self):
        result = {"ok": False, "returncode": -6, "signal": 6,
                  "missing_library": "libcublasLt.so.12", "error": "abort"}
        [check], _ = self.run_check(REQUIRED, result)
        self.assertEqual(FAIL, check.status)
        self.assertIn("signal 6", check.detail)
        self.assertIn("missing libcublasLt.so.12", check.detail)
        self.assertIn("AEB_CUDA_LIBRARY_PATH", check.detail)

    def test_failed_probe_only_warns_when_cuda_optional(self):
        [check], _ = self.run_check(OPTIONAL, {"ok": False, "returncode": 1, "error": "x"})
        self.assertEqual(WARN, check.status)

    def test_probe_exception_never_propagates(self):
        [check], _ = self.run_check(REQUIRED, error=RuntimeError("boom"))
        self.assertEqual(FAIL, check.status)
        self.assertIn("boom", check.detail)

    def test_cpu_config_skips_probe(self):
        [check], calls = self.run_check({"backend": "onnx", "providers": ["CPUExecutionProvider"]})
        self.assertEqual(WARN, check.status)
        self.assertEqual([], calls)


class PortAndGpuTests(unittest.TestCase):
    def test_listening_ports_parses_proc_table(self):
        with tempfile.NamedTemporaryFile("w", suffix="tcp", delete=False) as stream:
            stream.write(
                "  sl  local_address rem_address   st\n"
                "   0: 0100007F:07D0 00000000:0000 0A\n"
                "   1: 0100007F:07D1 0100007F:9C40 01\n"
            )
        self.addCleanup(Path(stream.name).unlink)
        self.assertEqual({2000}, doctor.listening_ports(paths=(stream.name,)))
        self.assertIsNone(doctor.listening_ports(paths=("/nonexistent/tcp",)))

    def test_local_port_uses_socket_table_without_connecting(self):
        connect = mock.Mock(return_value=True)
        [check] = doctor.check_carla_port("127.0.0.1", 2000, listening=lambda: {2000}, connect=connect)
        self.assertEqual(OK, check.status)
        connect.assert_not_called()
        [check] = doctor.check_carla_port("127.0.0.1", 2000, listening=lambda: set(), connect=connect)
        self.assertEqual(WARN, check.status)
        connect.assert_not_called()

    def test_remote_port_uses_tcp_connect(self):
        [check] = doctor.check_carla_port("10.0.0.5", 2000, listening=lambda: {2000}, connect=lambda h, p: False)
        self.assertEqual(WARN, check.status)
        self.assertIn("TCP connect", check.detail)

    def test_gpu_memory_threshold(self):
        def run(command, **kwargs):
            return completed("0, NVIDIA GeForce RTX 3050 Laptop GPU, 900, 4096, 580.173.02\n")

        [check] = doctor.check_gpu_memory(1024, runner=run)
        self.assertEqual(WARN, check.status)
        self.assertIn("900 MiB free / 4096 MiB", check.detail)
        [check] = doctor.check_gpu_memory(512, runner=run)
        self.assertEqual(OK, check.status)

    def test_missing_nvidia_smi_is_warn(self):
        def run(command, **kwargs):
            raise FileNotFoundError("nvidia-smi")

        [check] = doctor.check_gpu_memory(runner=run)
        self.assertEqual(WARN, check.status)

    def test_nvidia_smi_timeout_is_warn(self):
        def run(command, **kwargs):
            raise subprocess.TimeoutExpired(command, 15)

        [check] = doctor.check_gpu_memory(runner=run)
        self.assertEqual(WARN, check.status)


class ExitCodeTests(unittest.TestCase):
    def test_only_fail_changes_exit_code(self):
        self.assertEqual(0, doctor.exit_code([doctor.Check(OK, "a", ""), doctor.Check(WARN, "b", "")]))
        self.assertEqual(1, doctor.exit_code([doctor.Check(FAIL, "c", "")]))

    def test_main_prints_summary_and_returns_exit_code(self):
        checks = [doctor.Check(OK, "a", "x"), doctor.Check(WARN, "b", "y")]
        stdout = io.StringIO()
        with mock.patch.object(doctor, "run_checks", return_value=iter(checks)):
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(0, doctor.main([]))
        self.assertIn("WARN  b", stdout.getvalue())
        self.assertIn("Summary: 1 OK, 1 WARN, 0 FAIL", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
