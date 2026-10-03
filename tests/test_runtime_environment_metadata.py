"""Tests for GPU runtime evidence recorded in run_metadata.json."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from ci_support import probe_carla_import, skip_if
from infrastructure import cuda_runtime


AEB_ROOT = Path(__file__).resolve().parents[1]
LEGACY_METADATA_KEYS = {
    "created_at",
    "command",
    "python_executable",
    "python_version",
    "platform",
    "carla_client_version",
    "carla_server_version",
    "carla_map",
    "fixed_delta_seconds",
    "seed",
    "sensor_config",
    "sensor_config_sha256",
    "scenario_config",
    "scenario_config_sha256",
    "model_path",
    "model_providers_configured",
    "model_inference_interval_s",
    "model_sha256",
    "config_snapshot_directory",
    "git_commit",
    "git_dirty",
    "completed_scenario_runs",
    "repeat",
    "control_mode",
    "resume_enabled",
    "record_evidence",
    "passed",
    "failed",
}
RUNTIME_KEYS = {
    "onnxruntime_version",
    "onnxruntime_available_providers",
    "cuda_library_dirs",
    "cuda_library_dirs_source",
    "cuda_reexec_applied",
    "ld_library_path_at_start",
    "ld_library_path_effective",
    "cuda_preflight",
    "loaded_cuda_libraries",
    "cudnn_version",
    "cuda_runtime_version",
    "nvidia_driver_version",
    "gpu_name",
}


class RuntimeEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.saved_state = dict(cuda_runtime._STATE)
        cuda_runtime._STATE.clear()
        cuda_runtime._STATE.update({"bootstrap": None, "probes": {}})

    def tearDown(self):
        cuda_runtime._STATE.clear()
        cuda_runtime._STATE.update(self.saved_state)

    def test_loaded_cuda_libraries_parses_proc_maps(self):
        with tempfile.NamedTemporaryFile("w", suffix=".maps") as maps:
            maps.write(
                "7f00-7f01 r-xp 00000000 08:02 1 /usr/lib/x86_64-linux-gnu/libcudnn.so.8.9.7\n"
                "7f01-7f02 r--p 00000000 08:02 1 /usr/lib/x86_64-linux-gnu/libcudnn.so.8.9.7\n"
                "7f02-7f03 r-xp 00000000 08:02 2 /usr/local/cuda-11.7/lib64/libcublasLt.so.11.10.3.66\n"
                "7f03-7f04 r-xp 00000000 08:02 3 /usr/lib/x86_64-linux-gnu/libc.so.6\n"
                "7f04-7f05 rw-p 00000000 00:00 0\n"
            )
            maps.flush()
            libraries = cuda_runtime.loaded_cuda_libraries(maps.name)
        self.assertEqual(
            [
                "/usr/lib/x86_64-linux-gnu/libcudnn.so.8.9.7",
                "/usr/local/cuda-11.7/lib64/libcublasLt.so.11.10.3.66",
            ],
            libraries,
        )
        self.assertEqual([], cuda_runtime.loaded_cuda_libraries("/nonexistent/maps"))

    def test_process_start_ld_library_path_reads_exec_environment(self):
        with tempfile.NamedTemporaryFile("wb") as environ_file:
            environ_file.write(b"HOME=/h\0LD_LIBRARY_PATH=/usr/local/cuda-11.7/lib64\0")
            environ_file.flush()
            self.assertEqual(
                "/usr/local/cuda-11.7/lib64",
                cuda_runtime.process_start_ld_library_path(environ_file.name),
            )
        with tempfile.NamedTemporaryFile("wb") as environ_file:
            environ_file.write(b"HOME=/h\0")
            environ_file.flush()
            self.assertEqual("", cuda_runtime.process_start_ld_library_path(environ_file.name))
        self.assertIsNone(cuda_runtime.process_start_ld_library_path("/nonexistent"))

    def test_version_decoding(self):
        self.assertEqual("8.9.7", cuda_runtime._decode_cudnn_version(8907))
        self.assertEqual("9.1.0", cuda_runtime._decode_cudnn_version(90100))
        self.assertEqual("11.7", cuda_runtime._decode_cuda_version(11070))
        self.assertEqual("12.2", cuda_runtime._decode_cuda_version(12020))

    def test_nvidia_smi_absence_is_tolerated(self):
        info = cuda_runtime.nvidia_driver_info(
            runner=mock.Mock(side_effect=FileNotFoundError("nvidia-smi"))
        )
        self.assertEqual({"nvidia_driver_version": None, "gpu_name": None}, info)

    def test_nvidia_smi_output_is_parsed_and_cached(self):
        runner = mock.Mock(
            return_value=subprocess.CompletedProcess(
                ["nvidia-smi"], 0, "550.120, NVIDIA GeForce RTX 3060\n", ""
            )
        )
        first = cuda_runtime.nvidia_driver_info(runner=runner)
        second = cuda_runtime.nvidia_driver_info(runner=runner)
        self.assertEqual("550.120", first["nvidia_driver_version"])
        self.assertEqual("NVIDIA GeForce RTX 3060", first["gpu_name"])
        self.assertIs(first, second)
        self.assertEqual(1, runner.call_count)

    def test_onnxruntime_details_use_already_imported_module(self):
        fake = types.ModuleType("onnxruntime")
        fake.__version__ = "1.14.1"
        fake.get_available_providers = lambda: ["CUDAExecutionProvider"]
        with mock.patch.dict(sys.modules, {"onnxruntime": fake}):
            self.assertEqual(
                ("1.14.1", ["CUDAExecutionProvider"]),
                cuda_runtime.onnxruntime_details(),
            )

    def test_runtime_environment_without_bootstrap_records_start_path(self):
        cuda_runtime._STATE["nvidia_smi"] = {
            "nvidia_driver_version": None,
            "gpu_name": None,
        }
        info = cuda_runtime.runtime_environment(
            environ={
                "AEB_CUDA_REEXEC": "1",
                "AEB_CUDA_ORIGINAL_LD_LIBRARY_PATH": "",
                "LD_LIBRARY_PATH": "/usr/local/cuda-11.7/lib64",
            }
        )
        self.assertTrue(RUNTIME_KEYS.issubset(info))
        self.assertTrue(info["cuda_reexec_applied"])
        self.assertEqual("", info["ld_library_path_at_start"])
        self.assertEqual("/usr/local/cuda-11.7/lib64", info["ld_library_path_effective"])
        self.assertEqual("not_bootstrapped", info["cuda_library_dirs_source"])
        json.dumps(info)

    def test_runtime_environment_includes_bootstrap_and_preflight(self):
        cuda_runtime._STATE["nvidia_smi"] = {
            "nvidia_driver_version": "550.1",
            "gpu_name": "GPU",
        }
        cuda_runtime._STATE["bootstrap"] = {
            "cuda_requested": True,
            "cuda_library_dirs": ["/usr/local/cuda-11.7/lib64"],
            "cuda_library_dirs_source": "default:system_cuda",
            "cuda_library_dirs_ignored": [],
            "cuda_reexec_applied": True,
            "cuda_reexec_skipped_reason": None,
            "ld_library_path_at_start": "",
        }
        cuda_runtime._STATE["probes"][("m", "", "{}")] = {
            "ok": True,
            "returncode": 0,
            "missing_library": None,
            "providers": ["CUDAExecutionProvider"],
            "duration_s": 2.5,
            "error": None,
        }
        info = cuda_runtime.runtime_environment(environ={})
        self.assertEqual("default:system_cuda", info["cuda_library_dirs_source"])
        self.assertEqual(["/usr/local/cuda-11.7/lib64"], info["cuda_library_dirs"])
        self.assertTrue(info["cuda_preflight"]["ok"])
        self.assertNotIn("error", info["cuda_preflight"])
        self.assertEqual("550.1", info["nvidia_driver_version"])


@skip_if(probe_carla_import("scripts.run_radar_aeb_scenarios"))
class RunMetadataTests(unittest.TestCase):
    def test_metadata_keeps_legacy_keys_and_adds_runtime_environment(self):
        from scripts.run_radar_aeb_scenarios import ScenarioRunner

        runner = ScenarioRunner.__new__(ScenarioRunner)
        runner.args = argparse.Namespace(
            sensor_config=AEB_ROOT / "configs" / "sensors.yaml",
            scenario_config=AEB_ROOT / "configs" / "scenarios" / "suites" / "smoke_basic.yaml",
            repeat=1,
            control_mode="physics",
            resume=False,
            record_evidence=False,
        )
        runner.sensor_config = {"model": {"providers": ["CPUExecutionProvider"]}}
        runner.runner_config = {}
        runner.seed = 2026
        runner.client = mock.Mock()
        runner.client.get_client_version.return_value = "0.9.11"
        runner.client.get_server_version.return_value = "0.9.11"
        runner.world = mock.Mock()
        runner.world.get_map.return_value.name = "Town04"
        environment = {"onnxruntime_version": "x", "cudnn_version": None}
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            cuda_runtime, "runtime_environment", return_value=environment
        ):
            runner._write_metadata(Path(directory), [])
            with open(str(Path(directory) / "run_metadata.json")) as stream:
                metadata = json.load(stream)
        self.assertTrue(LEGACY_METADATA_KEYS.issubset(metadata))
        self.assertEqual(environment, metadata["runtime_environment"])


if __name__ == "__main__":
    unittest.main()
