"""Golden tests for the launcher command builders (Tk-free).

The launcher is an entry point for reproducible runs: these argument lists are
part of the experiment record and must not drift when the GUI changes.
"""

import subprocess
import unittest
from pathlib import Path

from ui.launcher.commands import (
    AppSettings,
    CheckSettings,
    VideoSettings,
    app_command,
    check_command,
    command_text,
    server_command,
    server_environment,
    server_preview_command,
    video_command,
)
from ui.launcher.config import AEB_ROOT, CARLA_PYTHON, CARLA_SCRIPT, YOLO_PYTHON


PY = str(CARLA_PYTHON)
SUITE = AEB_ROOT / "configs" / "scenarios" / "suites" / "report_demo.yaml"


def app_settings(**overrides):
    values = dict(
        name="Final demo 3 màn",
        map_name="Town04",
        resolution="1500x850",
        host="127.0.0.1",
        port=2000,
        autopilot=False,
        brake_mode="config default",
        scenario_config=SUITE,
        scenario="cutin_80_50_gap_25",
        control_mode="physics",
        camera="wide_chase",
        warmup_s=2.0,
        reload_world=True,
        behavior="Validation: phanh rồi dừng để đo",
        clean_overlay=True,
        sync=True,
    )
    values.update(overrides)
    return AppSettings(**values)


def check_settings(**overrides):
    values = dict(
        test_type="Radar scenario batch",
        scenario_config=SUITE,
        control_mode="physics",
        repeat=1,
        cooldown_s=1.0,
        reload_every=1,
        scenario="Tất cả",
        load_map=True,
        record_evidence=False,
        run_id="",
    )
    values.update(overrides)
    return CheckSettings(**values)


def video_settings(**overrides):
    values = dict(
        scenario_config=SUITE,
        run_id="final_demo_manual",
        resolution="1500x850",
        encoder="h264_nvenc",
        linger_s=4.0,
        max_seconds=90.0,
        cooldown_s=2.0,
        reload_every=1,
        scenario="cutin_80_50_gap_25",
        brake_mode="config default",
        realistic=False,
    )
    values.update(overrides)
    return VideoSettings(**values)


class CommandTextTests(unittest.TestCase):
    def test_quotes_only_parts_with_whitespace(self):
        self.assertEqual(
            command_text(["a", "b c", "it's ok", "--x=1"]),
            "a 'b c' 'it'\\''s ok' --x=1",
        )


class ServerCommandTests(unittest.TestCase):
    def test_default_server_command(self):
        self.assertEqual(
            server_command("Low", 2000, False),
            [str(CARLA_SCRIPT), "-quality-level=Low"],
        )

    def test_custom_port_and_stable_mode(self):
        self.assertEqual(
            server_command("Epic", 2005, False),
            [str(CARLA_SCRIPT), "-quality-level=Epic", "-carla-rpc-port=2005"],
        )
        self.assertEqual(
            server_command("Low", 2000, True),
            [
                str(CARLA_SCRIPT),
                "-quality-level=Low",
                "-carla-rpc-port=2000",
                "-nosound",
                "-windowed",
                "-ResX=1280",
                "-ResY=720",
            ],
        )

    def test_prime_offload_environment_and_preview(self):
        self.assertEqual(server_environment(False), {})
        self.assertEqual(
            server_environment(True),
            {"__NV_PRIME_RENDER_OFFLOAD": "1", "__GLX_VENDOR_LIBRARY_NAME": "nvidia"},
        )
        command = server_command("Low", 2000, False)
        self.assertEqual(
            command_text(server_preview_command(command, True)),
            "__NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia "
            "{} -quality-level=Low".format(CARLA_SCRIPT),
        )
        self.assertEqual(server_preview_command(command, False), command)


class AppCommandTests(unittest.TestCase):
    def test_final_demo_with_live_scenario(self):
        self.assertEqual(
            app_command(app_settings()),
            [
                PY,
                str(AEB_ROOT / "ui" / "aeb_demo_view.py"),
                "--map-name", "Town04",
                "--res", "1500x850",
                "--host", "127.0.0.1",
                "--port", "2000",
                "--scenario-config", str(SUITE),
                "--scenario", "cutin_80_50_gap_25",
                "--control-mode", "physics",
                "--scenario-camera", "wide_chase",
                "--scenario-warmup-s", "2.0",
                "--reload-world-on-start",
                "--clean-radar-overlay",
                "--sync",
            ],
        )

    def test_realistic_radar_aeb_with_brake_mode(self):
        command = app_command(
            app_settings(
                name="Radar AEB",
                autopilot=True,
                brake_mode="pid_v2_comfort",
                reload_world=False,
                behavior="Realistic: hết nguy hiểm thì nhả phanh chạy tiếp",
                clean_overlay=False,
                sync=False,
            )
        )
        self.assertEqual(command[1], str(AEB_ROOT / "ui" / "radar_aeb_view.py"))
        self.assertEqual(command[10:13], ["-a", "--brake-mode", "pid_v2_comfort"])
        self.assertEqual(command[-1], "--keep-driving-after-aeb")
        self.assertNotIn("--reload-world-on-start", command)
        self.assertNotIn("--no-sync", command)

    def test_viewer_apps_ignore_scenario_options(self):
        command = app_command(app_settings(name="Camera", clean_overlay=False, sync=False))
        self.assertEqual(
            command,
            [
                PY,
                str(AEB_ROOT / "ui" / "camera_view.py"),
                "--map-name", "Town04",
                "--res", "1500x850",
                "--host", "127.0.0.1",
                "--port", "2000",
            ],
        )

    def test_final_demo_debug_overlay_without_sync(self):
        command = app_command(app_settings(scenario="", clean_overlay=False, sync=False))
        self.assertEqual(command[-2:], ["--debug-radar-overlay", "--no-sync"])
        self.assertNotIn("--scenario", command)


class CheckCommandTests(unittest.TestCase):
    def test_radar_batch_defaults(self):
        self.assertEqual(
            check_command(check_settings()),
            [
                PY,
                str(AEB_ROOT / "scripts" / "run_radar_aeb_scenarios.py"),
                "--scenario-config", str(SUITE),
                "--control-mode", "physics",
                "--repeat", "1",
                "--scenario-cooldown-s", "1.0",
                "--reload-world-wait-s", "2.0",
                "--reload-world-every", "1",
                "--load-map",
            ],
        )

    def test_fusion_batch_with_all_options(self):
        command = check_command(
            check_settings(
                test_type="Fusion scenario batch",
                control_mode="deterministic",
                repeat=3,
                reload_every=0,
                scenario="cutin_80_50_gap_25",
                load_map=False,
                record_evidence=True,
                run_id="  run a  ",
            )
        )
        self.assertEqual(command[1], str(AEB_ROOT / "scripts" / "run_fusion_aeb_scenarios.py"))
        self.assertEqual(
            command[12:],
            ["--scenario", "cutin_80_50_gap_25", "--record-evidence", "--run-id", "run a"],
        )

    def test_unit_test_and_dataset_audit(self):
        self.assertEqual(
            check_command(check_settings(test_type="Unit test")),
            [PY, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        )
        self.assertEqual(
            check_command(check_settings(test_type="Kiểm tra dataset YOLO")),
            [str(YOLO_PYTHON), str(AEB_ROOT / "scripts" / "check_yolo_dataset.py")],
        )


class VideoCommandTests(unittest.TestCase):
    def test_video_defaults(self):
        self.assertEqual(
            video_command(video_settings()),
            [
                PY,
                str(AEB_ROOT / "scripts" / "record_scenario_videos.py"),
                "--scenario-config", str(SUITE),
                "--run-id", "final_demo_manual",
                "--capture-size", "1500x850",
                "--screen-size", "1500x850",
                "--encoder", "h264_nvenc",
                "--linger", "4.0",
                "--max-seconds", "90.0",
                "--scenario-cooldown-s", "2.0",
                "--reload-world-wait-s", "2.0",
                "--control-mode", "physics",
                "--reload-world-every", "1",
                "--scenario", "cutin_80_50_gap_25",
            ],
        )

    def test_video_blank_run_id_all_scenarios_realistic(self):
        command = video_command(
            video_settings(
                run_id="   ",
                reload_every=0,
                scenario="Tất cả",
                brake_mode="staged_pid",
                realistic=True,
            )
        )
        self.assertEqual(command[5], "final_demo_manual")
        self.assertNotIn("--scenario", command)
        self.assertNotIn("--reload-world-every", command)
        self.assertEqual(command[-3:], ["--brake-mode", "staged_pid", "--keep-driving-after-aeb"])


class LauncherReexportTests(unittest.TestCase):
    def test_entry_point_keeps_public_names(self):
        names = (
            "AebLauncher ManagedProcess ProcessSpec command_text port_open "
            "carla_process_rows process_alive scenario_ids load_yaml "
            "check_prerequisites SCENARIO_CONFIGS UI_APPLICATIONS TEST_SCRIPTS "
            "BRAKE_MODES COLORS AEB_ROOT CARLA_PYTHON YOLO_PYTHON main"
        ).split()
        result = subprocess.run(
            [
                "/usr/bin/python3",
                "-c",
                "import launcher; missing=[n for n in {!r} if not hasattr(launcher, n)]; "
                "print(missing); raise SystemExit(1 if missing else 0)".format(names),
            ],
            cwd=str(AEB_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
