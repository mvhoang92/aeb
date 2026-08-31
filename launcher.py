#!/usr/bin/env python3
"""Desktop launcher for the CARLA AEB project."""

from __future__ import annotations

import argparse
import os
import queue
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Dict, List, Optional

import yaml

from infrastructure.workspace import environments_root


AEB_ROOT = Path(__file__).resolve().parent
CARLA_ROOT = AEB_ROOT.parent
CARLA_PYTHON = CARLA_ROOT / "venv" / "bin" / "python"
YOLO_PYTHON = Path(
    os.environ.get(
        "AEB_YOLO_PYTHON",
        str(environments_root() / "yolo310" / "bin" / "python"),
    )
)
CARLA_SCRIPT = CARLA_ROOT / "CarlaUE4.sh"
SENSOR_CONFIG = AEB_ROOT / "configs" / "sensors.yaml"
DEFAULT_SCENARIO_CONFIG = (
    AEB_ROOT / "configs" / "scenarios" / "suites" / "system_limit_extended_sweep.yaml"
)
SCENARIO_CONFIGS = {
    "Suite / report demo": AEB_ROOT / "configs" / "scenarios" / "suites" / "report_demo.yaml",
    "Suite / smoke basic": AEB_ROOT / "configs" / "scenarios" / "suites" / "smoke_basic.yaml",
    "Suite / radar-only regression": AEB_ROOT / "configs" / "scenarios" / "suites" / "radar_only_regression.yaml",
    "Suite / fusion regression": AEB_ROOT / "configs" / "scenarios" / "suites" / "fusion_regression.yaml",
    "Suite / CCRs system limit": AEB_ROOT / "configs" / "scenarios" / "suites" / "system_limit_ccrs_sweep.yaml",
    "Suite / extended system limit": AEB_ROOT / "configs" / "scenarios" / "suites" / "system_limit_extended_sweep.yaml",
    "Car-to-car / clear road": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "clear_road.yaml",
    "Car-to-car / CCRs stationary lead": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "ccrs_stationary_lead.yaml",
    "Car-to-car / CCRm moving lead": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "ccrm_moving_lead.yaml",
    "Car-to-car / CCRb braking lead": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "ccrb_braking_lead.yaml",
    "Car-to-car / cut-in": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "cut_in.yaml",
    "Car-to-car / cut-out": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "cut_out.yaml",
    "Car-to-car / adjacent vehicle": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "adjacent_vehicle.yaml",
    "Car-to-car / curve cases": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "curve_cases.yaml",
    "Car-to-car / multi actor": AEB_ROOT / "configs" / "scenarios" / "car_to_car" / "multi_actor.yaml",
}
ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

UI_APPLICATIONS = {
    "Final demo 3 màn": AEB_ROOT / "ui" / "aeb_demo_view.py",
    "Radar AEB": AEB_ROOT / "ui" / "radar_aeb_view.py",
    "Camera": AEB_ROOT / "ui" / "camera_view.py",
    "Radar": AEB_ROOT / "ui" / "radar_view.py",
    "YOLO": AEB_ROOT / "ui" / "yolo_view.py",
    "Fusion": AEB_ROOT / "ui" / "fusion_view.py",
}

TEST_SCRIPTS = {
    "Radar scenario batch": AEB_ROOT / "scripts" / "run_radar_aeb_scenarios.py",
    "Fusion scenario batch": AEB_ROOT / "scripts" / "run_fusion_aeb_scenarios.py",
}

BRAKE_MODES = (
    "config default",
    "binary",
    "staged",
    "pid",
    "pid_v1",
    "pid_v2",
    "pid_v2_comfort",
    "staged_pid",
)


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}


def scenario_ids(path: Path) -> List[str]:
    return [
        str(item["id"])
        for item in load_yaml(path).get("scenarios", [])
        if isinstance(item, dict) and item.get("id")
    ]


def command_text(command: List[str]) -> str:
    return " ".join(
        "'{}'".format(part.replace("'", "'\\''"))
        if any(character.isspace() for character in part)
        else part
        for part in command
    )


def port_open(host: str, port: int, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def carla_process_rows() -> List[tuple]:
    try:
        output = subprocess.check_output(
            ["pgrep", "-af", "CarlaUE4"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    rows = []
    for line in output.splitlines():
        parts = line.split(maxsplit=1)
        if not parts:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        command = parts[1] if len(parts) > 1 else ""
        if "CarlaUE4-Linux-Shipping" in command or "CarlaUE4.sh" in command:
            rows.append((pid, command))
    return rows


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


@dataclass
class ProcessSpec:
    name: str
    command: List[str]
    cwd: Path
    environment: Optional[dict] = None


class ManagedProcess:
    def __init__(self, spec: ProcessSpec, output_queue: queue.Queue):
        self.spec = spec
        self.output_queue = output_queue
        self.process: Optional[subprocess.Popen] = None
        self.reader: Optional[threading.Thread] = None

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self) -> None:
        if self.running:
            raise RuntimeError("{} đang chạy".format(self.spec.name))
        environment = os.environ.copy()
        environment["PYTHONUNBUFFERED"] = "1"
        if self.spec.environment:
            environment.update(self.spec.environment)
        self.process = subprocess.Popen(
            self.spec.command,
            cwd=str(self.spec.cwd),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            bufsize=1,
            start_new_session=True,
        )
        self.output_queue.put(
            (
                self.spec.name,
                "START pid={} | {}\n".format(
                    self.process.pid,
                    command_text(self.spec.command),
                ),
            )
        )
        self.reader = threading.Thread(target=self._read_output, daemon=True)
        self.reader.start()

    def _read_output(self) -> None:
        assert self.process is not None
        assert self.process.stdout is not None
        for line in iter(self.process.stdout.readline, ""):
            self.output_queue.put((self.spec.name, ANSI_ESCAPE.sub("", line)))
        return_code = self.process.wait()
        self.output_queue.put(
            (
                self.spec.name,
                "EXIT code={}\n".format(return_code),
            )
        )

    def stop(self, timeout: float = 5.0) -> None:
        if not self.running or self.process is None:
            return
        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGINT)
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass


class AebLauncher:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CARLA AEB Project Launcher")
        self.root.geometry("1180x820")
        self.root.minsize(980, 680)
        self.output_queue: queue.Queue = queue.Queue()
        self.processes: Dict[str, ManagedProcess] = {}
        self.scenario_config_name = tk.StringVar(value="Suite / report demo")
        self.scenario_config_path = SCENARIO_CONFIGS[self.scenario_config_name.get()]
        self.scenarios = scenario_ids(self.scenario_config_path)

        self.host = tk.StringVar(value="127.0.0.1")
        self.port = tk.IntVar(value=2000)
        self.server_status = tk.StringVar(value="Đang kiểm tra...")
        self.server_quality = tk.StringVar(value="Low")
        self.nvidia_offload = tk.BooleanVar(value=True)
        self.server_stable_mode = tk.BooleanVar(value=False)

        self.ui_name = tk.StringVar(value="Final demo 3 màn")
        self.ui_map = tk.StringVar(value="Town04")
        self.ui_resolution = tk.StringVar(value="1500x850")
        self.ui_autopilot = tk.BooleanVar(value=False)
        self.ui_behavior = tk.StringVar(value="Validation: phanh rồi dừng để đo")
        self.ui_brake_mode = tk.StringVar(value="config default")
        self.ui_clean_overlay = tk.BooleanVar(value=True)
        self.ui_sync = tk.BooleanVar(value=True)
        self.ui_reload_world = tk.BooleanVar(value=True)
        self.ui_restart_carla = tk.BooleanVar(value=False)
        self.live_scenario = tk.StringVar(
            value="cutin_80_50_gap_25"
            if "cutin_80_50_gap_25" in self.scenarios
            else (self.scenarios[0] if self.scenarios else "")
        )
        self.live_control_mode = tk.StringVar(value="physics")
        self.live_camera = tk.StringVar(value="wide_chase")
        self.live_warmup = tk.DoubleVar(value=2.0)

        self.test_type = tk.StringVar(value="Radar scenario batch")
        self.test_scenario = tk.StringVar(value="Tất cả")
        self.test_control_mode = tk.StringVar(value="physics")
        self.test_repeat = tk.IntVar(value=1)
        self.test_load_map = tk.BooleanVar(value=True)
        self.test_record_evidence = tk.BooleanVar(value=False)
        self.test_run_id = tk.StringVar(value="")
        self.test_cooldown = tk.DoubleVar(value=1.0)
        self.test_reload_every = tk.IntVar(value=1)

        self.video_scenario = tk.StringVar(value=self.live_scenario.get())
        self.video_run_id = tk.StringVar(value="final_demo_manual")
        self.video_resolution = tk.StringVar(value="1500x850")
        self.video_encoder = tk.StringVar(value="h264_nvenc")
        self.video_brake_mode = tk.StringVar(value="config default")
        self.video_cooldown = tk.DoubleVar(value=2.0)
        self.video_reload_every = tk.IntVar(value=1)
        self.video_linger = tk.DoubleVar(value=4.0)
        self.video_max_seconds = tk.DoubleVar(value=90.0)
        self.video_realistic = tk.BooleanVar(value=False)

        self._configure_style()
        self._build_layout()
        self.host.trace_add("write", lambda *_args: self._refresh_command_preview())
        self.port.trace_add("write", lambda *_args: self._refresh_command_preview())
        self._refresh_command_preview()
        self.root.after(100, self._drain_output)
        self.root.after(500, self._poll_processes)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", padding=(10, 6))
        style.configure("Primary.TButton", padding=(12, 7))
        style.configure("Status.TLabel", font=("TkDefaultFont", 10, "bold"))
        style.configure("Title.TLabel", font=("TkDefaultFont", 17, "bold"))

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(outer)
        header.pack(fill=tk.X)
        ttk.Label(header, text="CARLA AEB Project Launcher", style="Title.TLabel").pack(
            side=tk.LEFT
        )
        ttk.Label(header, textvariable=self.server_status, style="Status.TLabel").pack(
            side=tk.RIGHT, padx=(8, 0)
        )
        ttk.Button(header, text="Kiểm tra server", command=self._check_server_now).pack(
            side=tk.RIGHT
        )

        notebook = ttk.Notebook(outer)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(12, 8))
        self.server_tab = ttk.Frame(notebook, padding=14)
        self.ui_tab = ttk.Frame(notebook, padding=14)
        self.test_tab = ttk.Frame(notebook, padding=14)
        self.video_tab = ttk.Frame(notebook, padding=14)
        notebook.add(self.server_tab, text="CARLA Server")
        notebook.add(self.ui_tab, text="Ứng dụng UI")
        notebook.add(self.test_tab, text="Kiểm thử")
        notebook.add(self.video_tab, text="Quay video")

        self._build_server_tab()
        self._build_ui_tab()
        self._build_test_tab()
        self._build_video_tab()

        process_bar = ttk.Frame(outer)
        process_bar.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(process_bar, text="Tiến trình đang quản lý:").pack(side=tk.LEFT)
        self.process_label = ttk.Label(process_bar, text="Không có")
        self.process_label.pack(side=tk.LEFT, padx=6)
        ttk.Button(
            process_bar,
            text="Dừng tiến trình...",
            command=self._stop_selected_process,
        ).pack(side=tk.RIGHT)

        log_header = ttk.Frame(outer)
        log_header.pack(fill=tk.X)
        ttk.Label(log_header, text="Log").pack(side=tk.LEFT)
        ttk.Button(log_header, text="Xóa log", command=self._clear_log).pack(
            side=tk.RIGHT
        )
        self.log = ScrolledText(
            outer,
            height=15,
            wrap=tk.WORD,
            font=("DejaVu Sans Mono", 10),
            state=tk.DISABLED,
        )
        self.log.pack(fill=tk.BOTH, expand=True)

    def _build_server_tab(self) -> None:
        form = ttk.Frame(self.server_tab)
        form.pack(anchor=tk.NW, fill=tk.X)
        ttk.Label(form, text="Host").grid(row=0, column=0, sticky=tk.W, pady=6)
        ttk.Entry(form, textvariable=self.host, width=18).grid(
            row=0, column=1, sticky=tk.W, padx=(8, 24)
        )
        ttk.Label(form, text="Port").grid(row=0, column=2, sticky=tk.W)
        ttk.Spinbox(form, from_=1, to=65535, textvariable=self.port, width=8).grid(
            row=0, column=3, sticky=tk.W, padx=8
        )

        ttk.Label(form, text="Quality").grid(row=1, column=0, sticky=tk.W, pady=6)
        quality = ttk.Combobox(
            form,
            textvariable=self.server_quality,
            values=("Low", "Epic"),
            state="readonly",
            width=15,
        )
        quality.grid(row=1, column=1, sticky=tk.W, padx=(8, 24))
        quality.bind("<<ComboboxSelected>>", lambda _event: self._refresh_command_preview())
        ttk.Checkbutton(
            form,
            text="NVIDIA PRIME render offload",
            variable=self.nvidia_offload,
            command=self._refresh_command_preview,
        ).grid(row=1, column=2, columnspan=2, sticky=tk.W)
        ttk.Checkbutton(
            form,
            text="Stable mode: port rõ ràng, tắt sound, window 1280x720",
            variable=self.server_stable_mode,
            command=self._refresh_command_preview,
        ).grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=(6, 0))

        actions = ttk.Frame(self.server_tab)
        actions.pack(anchor=tk.W, pady=(16, 10))
        ttk.Button(
            actions,
            text="Bật CARLA",
            style="Primary.TButton",
            command=self._start_server,
        ).pack(side=tk.LEFT)
        ttk.Button(actions, text="Dừng CARLA đã bật từ launcher", command=self._stop_server).pack(
            side=tk.LEFT, padx=8
        )
        ttk.Button(actions, text="Dọn CARLA treo", command=self._cleanup_carla_processes).pack(
            side=tk.LEFT
        )

        ttk.Label(
            self.server_tab,
            text=(
                "Launcher không thêm -opengl. Stable mode giảm tải UE4 và khóa đúng "
                "RPC port. Nút dọn CARLA treo chỉ dùng khi port offline nhưng process "
                "CarlaUE4 vẫn còn chạy ngầm."
            ),
            wraplength=900,
        ).pack(anchor=tk.W, pady=(4, 10))
        self.server_command = self._command_preview(self.server_tab)

    def _build_ui_tab(self) -> None:
        form = ttk.Frame(self.ui_tab)
        form.pack(anchor=tk.NW, fill=tk.X)

        ttk.Label(form, text="Ứng dụng").grid(row=0, column=0, sticky=tk.W, pady=6)
        app_combo = ttk.Combobox(
            form,
            textvariable=self.ui_name,
            values=tuple(UI_APPLICATIONS.keys()),
            state="readonly",
            width=20,
        )
        app_combo.grid(row=0, column=1, sticky=tk.W, padx=(8, 24))
        app_combo.bind("<<ComboboxSelected>>", self._on_ui_selection)

        ttk.Label(form, text="Map").grid(row=0, column=2, sticky=tk.W)
        ttk.Combobox(
            form,
            textvariable=self.ui_map,
            values=("Town04", "Town06"),
            width=14,
        ).grid(row=0, column=3, sticky=tk.W, padx=8)

        ttk.Label(form, text="Độ phân giải mỗi panel").grid(
            row=1, column=0, sticky=tk.W, pady=6
        )
        ttk.Combobox(
            form,
            textvariable=self.ui_resolution,
            values=("1500x850", "1600x900", "1280x720", "960x540", "800x450"),
            width=20,
        ).grid(row=1, column=1, sticky=tk.W, padx=(8, 24))
        ttk.Checkbutton(
            form,
            text="Autopilot",
            variable=self.ui_autopilot,
            command=self._refresh_command_preview,
        ).grid(row=1, column=2, sticky=tk.W)

        scenario_frame = ttk.LabelFrame(form, text="Radar AEB live scenario", padding=10)
        scenario_frame.grid(
            row=2,
            column=0,
            columnspan=4,
            sticky=tk.EW,
            pady=(12, 0),
        )
        ttk.Label(scenario_frame, text="Config").grid(row=0, column=0, sticky=tk.W)
        config_combo = ttk.Combobox(
            scenario_frame,
            textvariable=self.scenario_config_name,
            values=tuple(SCENARIO_CONFIGS.keys()),
            state="readonly",
            width=26,
        )
        config_combo.grid(row=0, column=1, sticky=tk.W, padx=8)
        config_combo.bind("<<ComboboxSelected>>", self._on_scenario_config_selection)

        ttk.Label(scenario_frame, text="Scenario").grid(row=0, column=2, sticky=tk.W)
        self.live_scenario_combo = ttk.Combobox(
            scenario_frame,
            textvariable=self.live_scenario,
            values=self.scenarios,
            state="readonly",
            width=30,
        )
        self.live_scenario_combo.grid(row=0, column=3, sticky=tk.W, padx=8)
        ttk.Label(scenario_frame, text="Control").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Combobox(
            scenario_frame,
            textvariable=self.live_control_mode,
            values=("physics", "deterministic"),
            state="readonly",
            width=14,
        ).grid(row=1, column=1, sticky=tk.W, padx=8, pady=(8, 0))
        ttk.Label(scenario_frame, text="Camera").grid(row=1, column=2, sticky=tk.W, pady=(8, 0))
        ttk.Combobox(
            scenario_frame,
            textvariable=self.live_camera,
            values=("wide_chase", "high_chase", "manual"),
            state="readonly",
            width=14,
        ).grid(row=1, column=3, sticky=tk.W, padx=8, pady=(8, 0))
        ttk.Label(scenario_frame, text="Warm-up").grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Spinbox(
            scenario_frame,
            from_=0.0,
            to=10.0,
            increment=0.5,
            textvariable=self.live_warmup,
            width=8,
        ).grid(row=2, column=1, sticky=tk.W, padx=8, pady=(8, 0))
        ttk.Label(scenario_frame, text="Hành vi AEB").grid(row=2, column=2, sticky=tk.W, pady=(8, 0))
        ttk.Combobox(
            scenario_frame,
            textvariable=self.ui_behavior,
            values=(
                "Validation: phanh rồi dừng để đo",
                "Realistic: hết nguy hiểm thì nhả phanh chạy tiếp",
            ),
            state="readonly",
            width=42,
        ).grid(row=2, column=3, sticky=tk.W, padx=8, pady=(8, 0))
        ttk.Label(scenario_frame, text="Loại phanh").grid(row=3, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Combobox(
            scenario_frame,
            textvariable=self.ui_brake_mode,
            values=BRAKE_MODES,
            state="readonly",
            width=24,
        ).grid(row=3, column=1, sticky=tk.W, padx=8, pady=(8, 0))

        option_frame = ttk.Frame(form)
        option_frame.grid(row=3, column=0, columnspan=4, sticky=tk.W, pady=(12, 0))
        ttk.Checkbutton(
            option_frame,
            text="Clean radar overlay",
            variable=self.ui_clean_overlay,
            command=self._refresh_command_preview,
        ).pack(side=tk.LEFT)
        ttk.Checkbutton(
            option_frame,
            text="Synchronous 20 FPS",
            variable=self.ui_sync,
            command=self._refresh_command_preview,
        ).pack(side=tk.LEFT, padx=18)
        ttk.Checkbutton(
            option_frame,
            text="Reload world khi mở scenario",
            variable=self.ui_reload_world,
            command=self._refresh_command_preview,
        ).pack(side=tk.LEFT)
        ttk.Checkbutton(
            option_frame,
            text="Restart CARLA trước scenario",
            variable=self.ui_restart_carla,
            command=self._refresh_command_preview,
        ).pack(side=tk.LEFT, padx=18)

        for variable in (
            self.ui_map,
            self.ui_resolution,
            self.ui_behavior,
            self.ui_brake_mode,
            self.ui_reload_world,
            self.ui_restart_carla,
            self.live_scenario,
            self.live_control_mode,
            self.live_camera,
            self.live_warmup,
        ):
            variable.trace_add("write", lambda *_args: self._refresh_command_preview())

        actions = ttk.Frame(self.ui_tab)
        actions.pack(anchor=tk.W, pady=(16, 10))
        ttk.Button(
            actions,
            text="Chạy ứng dụng",
            style="Primary.TButton",
            command=self._start_ui,
        ).pack(side=tk.LEFT)
        ttk.Button(actions, text="Dừng ứng dụng", command=self._stop_ui).pack(
            side=tk.LEFT, padx=8
        )
        self.ui_command_preview = self._command_preview(self.ui_tab)

    def _build_test_tab(self) -> None:
        form = ttk.Frame(self.test_tab)
        form.pack(anchor=tk.NW, fill=tk.X)
        ttk.Label(form, text="Loại kiểm thử").grid(row=0, column=0, sticky=tk.W, pady=6)
        test_combo = ttk.Combobox(
            form,
            textvariable=self.test_type,
            values=(
                "Radar scenario batch",
                "Fusion scenario batch",
                "Unit test",
                "Kiểm tra dataset YOLO",
            ),
            state="readonly",
            width=28,
        )
        test_combo.grid(row=0, column=1, sticky=tk.W, padx=(8, 24))
        test_combo.bind("<<ComboboxSelected>>", self._on_test_selection)

        ttk.Label(form, text="Scenario").grid(row=0, column=2, sticky=tk.W)
        self.test_scenario_combo = ttk.Combobox(
            form,
            textvariable=self.test_scenario,
            values=["Tất cả"] + self.scenarios,
            state="readonly",
            width=30,
        )
        self.test_scenario_combo.grid(row=0, column=3, sticky=tk.W, padx=8)

        ttk.Label(form, text="Control mode").grid(row=1, column=0, sticky=tk.W, pady=6)
        self.test_control_combo = ttk.Combobox(
            form,
            textvariable=self.test_control_mode,
            values=("physics", "deterministic"),
            state="readonly",
            width=20,
        )
        self.test_control_combo.grid(row=1, column=1, sticky=tk.W, padx=(8, 24))
        ttk.Label(form, text="Số lần lặp").grid(row=1, column=2, sticky=tk.W)
        self.test_repeat_spin = ttk.Spinbox(
            form,
            from_=1,
            to=20,
            textvariable=self.test_repeat,
            width=8,
        )
        self.test_repeat_spin.grid(row=1, column=3, sticky=tk.W, padx=8)

        ttk.Label(form, text="Run ID").grid(row=2, column=0, sticky=tk.W, pady=6)
        ttk.Entry(form, textvariable=self.test_run_id, width=28).grid(
            row=2,
            column=1,
            sticky=tk.W,
            padx=(8, 24),
        )
        ttk.Label(form, text="Cooldown").grid(row=2, column=2, sticky=tk.W)
        ttk.Spinbox(
            form,
            from_=0.0,
            to=10.0,
            increment=0.5,
            textvariable=self.test_cooldown,
            width=8,
        ).grid(row=2, column=3, sticky=tk.W, padx=8)

        ttk.Label(form, text="Reload world mỗi N bài").grid(
            row=3,
            column=0,
            sticky=tk.W,
            pady=6,
        )
        ttk.Spinbox(
            form,
            from_=0,
            to=20,
            textvariable=self.test_reload_every,
            width=8,
        ).grid(row=3, column=1, sticky=tk.W, padx=(8, 24))

        options = ttk.Frame(form)
        options.grid(row=4, column=0, columnspan=4, sticky=tk.W, pady=(8, 0))
        self.load_map_check = ttk.Checkbutton(
            options,
            text="Load map",
            variable=self.test_load_map,
            command=self._refresh_command_preview,
        )
        self.load_map_check.pack(side=tk.LEFT)
        self.evidence_check = ttk.Checkbutton(
            options,
            text="Ghi evidence",
            variable=self.test_record_evidence,
            command=self._refresh_command_preview,
        )
        self.evidence_check.pack(side=tk.LEFT, padx=18)

        for variable in (
            self.test_type,
            self.test_scenario,
            self.test_control_mode,
            self.test_repeat,
            self.test_run_id,
            self.test_cooldown,
            self.test_reload_every,
        ):
            variable.trace_add("write", lambda *_args: self._refresh_command_preview())

        actions = ttk.Frame(self.test_tab)
        actions.pack(anchor=tk.W, pady=(16, 10))
        ttk.Button(
            actions,
            text="Chạy kiểm thử",
            style="Primary.TButton",
            command=self._start_test,
        ).pack(side=tk.LEFT)
        ttk.Button(actions, text="Dừng kiểm thử", command=self._stop_test).pack(
            side=tk.LEFT, padx=8
        )
        self.test_command_preview = self._command_preview(self.test_tab)
        self._on_test_selection()

    def _build_video_tab(self) -> None:
        form = ttk.Frame(self.video_tab)
        form.pack(anchor=tk.NW, fill=tk.X)

        ttk.Label(form, text="Scenario").grid(row=0, column=0, sticky=tk.W, pady=6)
        self.video_scenario_combo = ttk.Combobox(
            form,
            textvariable=self.video_scenario,
            values=["Tất cả"] + self.scenarios,
            state="readonly",
            width=34,
        )
        self.video_scenario_combo.grid(row=0, column=1, sticky=tk.W, padx=(8, 24))

        ttk.Label(form, text="Run ID").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(form, textvariable=self.video_run_id, width=28).grid(
            row=0,
            column=3,
            sticky=tk.W,
            padx=8,
        )

        ttk.Label(form, text="Độ phân giải").grid(row=1, column=0, sticky=tk.W, pady=6)
        ttk.Combobox(
            form,
            textvariable=self.video_resolution,
            values=("1500x850", "1600x900", "1280x720", "1920x1080"),
            width=18,
        ).grid(row=1, column=1, sticky=tk.W, padx=(8, 24))

        ttk.Label(form, text="Encoder").grid(row=1, column=2, sticky=tk.W)
        ttk.Combobox(
            form,
            textvariable=self.video_encoder,
            values=("h264_nvenc", "libx264"),
            state="readonly",
            width=16,
        ).grid(row=1, column=3, sticky=tk.W, padx=8)

        ttk.Label(form, text="Loại phanh").grid(row=2, column=0, sticky=tk.W, pady=6)
        ttk.Combobox(
            form,
            textvariable=self.video_brake_mode,
            values=BRAKE_MODES,
            state="readonly",
            width=18,
        ).grid(row=2, column=1, sticky=tk.W, padx=(8, 24))

        ttk.Label(form, text="Nán sau test").grid(row=2, column=2, sticky=tk.W, pady=6)
        ttk.Spinbox(
            form,
            from_=0.0,
            to=20.0,
            increment=0.5,
            textvariable=self.video_linger,
            width=8,
        ).grid(row=2, column=3, sticky=tk.W, padx=8)

        ttk.Label(form, text="Max seconds").grid(row=3, column=0, sticky=tk.W)
        ttk.Spinbox(
            form,
            from_=10.0,
            to=300.0,
            increment=5.0,
            textvariable=self.video_max_seconds,
            width=8,
        ).grid(row=3, column=1, sticky=tk.W, padx=(8, 24))

        ttk.Label(form, text="Cooldown").grid(row=3, column=2, sticky=tk.W)
        ttk.Spinbox(
            form,
            from_=0.0,
            to=20.0,
            increment=0.5,
            textvariable=self.video_cooldown,
            width=8,
        ).grid(row=3, column=3, sticky=tk.W, padx=8)

        ttk.Label(form, text="Reload world mỗi N video").grid(
            row=4,
            column=0,
            sticky=tk.W,
            pady=6,
        )
        ttk.Spinbox(
            form,
            from_=0,
            to=20,
            textvariable=self.video_reload_every,
            width=8,
        ).grid(row=4, column=1, sticky=tk.W, padx=(8, 24))

        ttk.Checkbutton(
            form,
            text="Realistic mode: hết nguy hiểm thì nhả phanh/chạy tiếp",
            variable=self.video_realistic,
            command=self._refresh_command_preview,
        ).grid(row=5, column=0, columnspan=4, sticky=tk.W, pady=(8, 0))

        for variable in (
            self.video_scenario,
            self.video_run_id,
            self.video_resolution,
            self.video_encoder,
            self.video_brake_mode,
            self.video_cooldown,
            self.video_reload_every,
            self.video_linger,
            self.video_max_seconds,
        ):
            variable.trace_add("write", lambda *_args: self._refresh_command_preview())

        actions = ttk.Frame(self.video_tab)
        actions.pack(anchor=tk.W, pady=(16, 10))
        ttk.Button(
            actions,
            text="Quay video",
            style="Primary.TButton",
            command=self._start_video,
        ).pack(side=tk.LEFT)
        ttk.Button(actions, text="Dừng quay", command=self._stop_video).pack(
            side=tk.LEFT, padx=8
        )
        self.video_command_preview = self._command_preview(self.video_tab)

    @staticmethod
    def _command_preview(parent: ttk.Frame) -> tk.Text:
        ttk.Label(parent, text="Lệnh sẽ chạy:").pack(anchor=tk.W, pady=(10, 4))
        widget = tk.Text(
            parent,
            height=3,
            wrap=tk.WORD,
            font=("DejaVu Sans Mono", 10),
            state=tk.DISABLED,
        )
        widget.pack(fill=tk.X)
        return widget

    @staticmethod
    def _set_preview(widget: tk.Text, command: List[str]) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", command_text(command))
        widget.configure(state=tk.DISABLED)

    @staticmethod
    def _int_value(variable: tk.IntVar, default: int) -> int:
        try:
            return int(variable.get())
        except (tk.TclError, ValueError):
            return default

    @staticmethod
    def _float_value(variable: tk.Variable, default: float) -> float:
        try:
            return float(variable.get())
        except (tk.TclError, ValueError):
            return default

    def _current_scenario_config(self) -> Path:
        return SCENARIO_CONFIGS.get(
            self.scenario_config_name.get(),
            DEFAULT_SCENARIO_CONFIG,
        )

    def _server_spec(self) -> ProcessSpec:
        port = self._int_value(self.port, 2000)
        command = [
            str(CARLA_SCRIPT),
            "-quality-level={}".format(self.server_quality.get()),
        ]
        if port != 2000 or self.server_stable_mode.get():
            command.append("-carla-rpc-port={}".format(port))
        if self.server_stable_mode.get():
            command.extend(["-nosound", "-windowed", "-ResX=1280", "-ResY=720"])
        environment = {}
        if self.nvidia_offload.get():
            environment.update(
                {
                    "__NV_PRIME_RENDER_OFFLOAD": "1",
                    "__GLX_VENDOR_LIBRARY_NAME": "nvidia",
                }
            )
        return ProcessSpec("CARLA Server", command, CARLA_ROOT, environment)

    def _server_preview_command(self) -> List[str]:
        command = list(self._server_spec().command)
        if self.nvidia_offload.get():
            command = [
                "__NV_PRIME_RENDER_OFFLOAD=1",
                "__GLX_VENDOR_LIBRARY_NAME=nvidia",
            ] + command
        return command

    def _ui_command(self) -> List[str]:
        name = self.ui_name.get()
        command = [
            str(CARLA_PYTHON),
            str(UI_APPLICATIONS[name]),
            "--map-name",
            self.ui_map.get(),
            "--res",
            self.ui_resolution.get(),
            "--host",
            self.host.get(),
            "--port",
            str(self._int_value(self.port, 2000)),
        ]
        if self.ui_autopilot.get():
            command.append("-a")
        if self.ui_brake_mode.get() != "config default":
            command.extend(["--brake-mode", self.ui_brake_mode.get()])
        if name in ("Radar AEB", "Final demo 3 màn") and self.live_scenario.get():
            command.extend(
                [
                    "--scenario-config",
                    str(self._current_scenario_config()),
                    "--scenario",
                    self.live_scenario.get(),
                    "--control-mode",
                    self.live_control_mode.get(),
                    "--scenario-camera",
                    self.live_camera.get(),
                    "--scenario-warmup-s",
                    str(self._float_value(self.live_warmup, 2.0)),
                ]
            )
            if self.ui_reload_world.get():
                command.append("--reload-world-on-start")
            if "Realistic" in self.ui_behavior.get():
                command.append("--keep-driving-after-aeb")
        if name == "Final demo 3 màn":
            command.append("--clean-radar-overlay" if self.ui_clean_overlay.get() else "--debug-radar-overlay")
            command.append("--sync" if self.ui_sync.get() else "--no-sync")
        return command

    def _test_command(self) -> List[str]:
        test_type = self.test_type.get()
        if test_type == "Unit test":
            return [
                str(CARLA_PYTHON),
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                "test_*.py",
            ]
        if test_type == "Kiểm tra dataset YOLO":
            return [str(YOLO_PYTHON), str(AEB_ROOT / "scripts" / "check_yolo_dataset.py")]

        command = [
            str(CARLA_PYTHON),
            str(TEST_SCRIPTS[test_type]),
            "--scenario-config",
            str(self._current_scenario_config()),
            "--control-mode",
            self.test_control_mode.get(),
            "--repeat",
            str(self._int_value(self.test_repeat, 1)),
            "--scenario-cooldown-s",
            str(self._float_value(self.test_cooldown, 1.0)),
            "--reload-world-wait-s",
            "2.0",
        ]
        reload_every = self._int_value(self.test_reload_every, 0)
        if reload_every > 0:
            command.extend(["--reload-world-every", str(reload_every)])
        if self.test_scenario.get() != "Tất cả":
            command.extend(["--scenario", self.test_scenario.get()])
        if self.test_load_map.get():
            command.append("--load-map")
        if self.test_record_evidence.get():
            command.append("--record-evidence")
        if self.test_run_id.get().strip():
            command.extend(["--run-id", self.test_run_id.get().strip()])
        return command

    def _video_command(self) -> List[str]:
        command = [
            str(CARLA_PYTHON),
            str(AEB_ROOT / "scripts" / "record_scenario_videos.py"),
            "--scenario-config",
            str(self._current_scenario_config()),
            "--run-id",
            self.video_run_id.get().strip() or "final_demo_manual",
            "--capture-size",
            self.video_resolution.get(),
            "--screen-size",
            self.video_resolution.get(),
            "--encoder",
            self.video_encoder.get(),
            "--linger",
            str(self._float_value(self.video_linger, 4.0)),
            "--max-seconds",
            str(self._float_value(self.video_max_seconds, 90.0)),
            "--scenario-cooldown-s",
            str(self._float_value(self.video_cooldown, 2.0)),
            "--reload-world-wait-s",
            "2.0",
            "--control-mode",
            "physics",
        ]
        reload_every = self._int_value(self.video_reload_every, 0)
        if reload_every > 0:
            command.extend(["--reload-world-every", str(reload_every)])
        if self.video_scenario.get() != "Tất cả":
            command.extend(["--scenario", self.video_scenario.get()])
        if self.video_brake_mode.get() != "config default":
            command.extend(["--brake-mode", self.video_brake_mode.get()])
        if self.video_realistic.get():
            command.append("--keep-driving-after-aeb")
        return command

    def _refresh_command_preview(self) -> None:
        if hasattr(self, "server_command"):
            self._set_preview(self.server_command, self._server_preview_command())
        if hasattr(self, "ui_command_preview"):
            self._set_preview(self.ui_command_preview, self._ui_command())
        if hasattr(self, "test_command_preview"):
            self._set_preview(self.test_command_preview, self._test_command())
        if hasattr(self, "video_command_preview"):
            self._set_preview(self.video_command_preview, self._video_command())

    def _on_ui_selection(self, _event=None) -> None:
        self._refresh_command_preview()

    def _on_scenario_config_selection(self, _event=None) -> None:
        self.scenario_config_path = self._current_scenario_config()
        self.scenarios = scenario_ids(self.scenario_config_path)
        values = self.scenarios
        if hasattr(self, "live_scenario_combo"):
            self.live_scenario_combo.configure(values=values)
        if hasattr(self, "test_scenario_combo"):
            self.test_scenario_combo.configure(values=["Tất cả"] + values)
        if hasattr(self, "video_scenario_combo"):
            self.video_scenario_combo.configure(values=["Tất cả"] + values)
        if self.live_scenario.get() not in values:
            self.live_scenario.set(values[0] if values else "")
        if self.test_scenario.get() != "Tất cả" and self.test_scenario.get() not in values:
            self.test_scenario.set("Tất cả")
        if self.video_scenario.get() != "Tất cả" and self.video_scenario.get() not in values:
            self.video_scenario.set(self.live_scenario.get() or "Tất cả")
        self._refresh_command_preview()

    def _on_test_selection(self, _event=None) -> None:
        radar_test = self.test_type.get() in TEST_SCRIPTS
        state = "readonly" if radar_test else "disabled"
        self.test_scenario_combo.configure(state=state)
        self.test_control_combo.configure(state=state)
        self.test_repeat_spin.configure(state="normal" if radar_test else "disabled")
        self.load_map_check.configure(state="normal" if radar_test else "disabled")
        self.evidence_check.configure(state="normal" if radar_test else "disabled")
        self._refresh_command_preview()

    def _start_process(self, key: str, spec: ProcessSpec) -> None:
        current = self.processes.get(key)
        if current is not None and current.running:
            messagebox.showinfo("Đang chạy", "{} đang chạy.".format(spec.name))
            return
        try:
            process = ManagedProcess(spec, self.output_queue)
            process.start()
            self.processes[key] = process
            self._update_process_label()
        except (OSError, RuntimeError) as exc:
            messagebox.showerror("Không chạy được", str(exc))

    def _start_server(self) -> None:
        if not CARLA_SCRIPT.is_file():
            messagebox.showerror("Thiếu CARLA", "Không thấy {}".format(CARLA_SCRIPT))
            return
        port = self._int_value(self.port, 2000)
        if port_open(self.host.get(), port):
            messagebox.showinfo(
                "Server đã bật",
                "Port {} đã mở. Có thể CARLA đang được bật bên ngoài launcher.".format(
                    port
                ),
            )
            return
        rows = carla_process_rows()
        if rows and not messagebox.askyesno(
            "Có CARLA process treo",
            (
                "Port {} chưa mở nhưng vẫn thấy {} process CarlaUE4.\n"
                "Dọn các process này rồi bật lại CARLA?"
            ).format(port, len(rows)),
        ):
            return
        if rows:
            self._cleanup_carla_processes(confirm=False)
        self._start_process("server", self._server_spec())

    def _stop_server(self) -> None:
        self._stop_process("server")

    def _cleanup_carla_processes(self, confirm: bool = True) -> None:
        rows = carla_process_rows()
        if not rows:
            messagebox.showinfo("CARLA", "Không thấy process CarlaUE4 đang treo.")
            return
        if confirm:
            preview = "\n".join(
                "pid={} {}".format(pid, command[:120])
                for pid, command in rows[:4]
            )
            if len(rows) > 4:
                preview += "\n..."
            if not messagebox.askyesno(
                "Dọn CARLA treo",
                "Sẽ gửi tín hiệu dừng tới các process sau:\n\n{}".format(preview),
            ):
                return

        pids = [pid for pid, _command in rows]
        self._append_log(
            "CARLA Server",
            "Cleanup requested for pids: {}\n".format(
                ", ".join(str(pid) for pid in pids)
            ),
        )
        for pid in pids:
            try:
                os.kill(pid, signal.SIGINT)
            except OSError:
                pass
        time.sleep(1.5)
        for pid in pids:
            if process_alive(pid):
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    pass
        time.sleep(0.5)
        still_alive = [pid for pid in pids if process_alive(pid)]
        if still_alive:
            for pid in still_alive:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
            self._append_log(
                "CARLA Server",
                "Force killed pids: {}\n".format(
                    ", ".join(str(pid) for pid in still_alive)
                ),
            )
        self._check_server_now()

    def _restart_carla_blocking(self) -> bool:
        port = self._int_value(self.port, 2000)
        self._append_log(
            "CARLA Server",
            "Restart requested before launching scenario\n",
        )
        managed = self.processes.get("server")
        if managed is not None and managed.running:
            self._append_log("CARLA Server", "Stopping launcher-managed CARLA\n")
            managed.stop(timeout=8.0)

        rows = carla_process_rows()
        if rows:
            self._append_log(
                "CARLA Server",
                "Stopping external CarlaUE4 pids: {}\n".format(
                    ", ".join(str(pid) for pid, _command in rows)
                ),
            )
            for pid, _command in rows:
                try:
                    os.kill(pid, signal.SIGINT)
                except OSError:
                    pass
            deadline = time.time() + 8.0
            while time.time() < deadline and carla_process_rows():
                self.root.update()
                time.sleep(0.25)
            for pid, _command in carla_process_rows():
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    pass
            time.sleep(1.0)
            for pid, _command in carla_process_rows():
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass

        spec = self._server_spec()
        try:
            process = ManagedProcess(spec, self.output_queue)
            process.start()
            self.processes["server"] = process
            self._update_process_label()
        except (OSError, RuntimeError) as exc:
            messagebox.showerror("Không bật được CARLA", str(exc))
            return False

        deadline = time.time() + 90.0
        while time.time() < deadline:
            self.root.update()
            if port_open(self.host.get(), port, timeout=0.5):
                self._append_log(
                    "CARLA Server",
                    "Port {} online after restart\n".format(port),
                )
                return True
            time.sleep(0.5)
        messagebox.showerror(
            "CARLA chưa sẵn sàng",
            "Đã restart nhưng port {} chưa online sau 90 giây.".format(port),
        )
        return False

    def _start_ui(self) -> None:
        port = self._int_value(self.port, 2000)
        if self.ui_restart_carla.get() and self.ui_name.get() in (
            "Radar AEB",
            "Final demo 3 màn",
        ):
            if not self._restart_carla_blocking():
                return
        if not port_open(self.host.get(), port):
            if not messagebox.askyesno(
                "CARLA chưa sẵn sàng",
                "Không kết nối được CARLA port {}. Vẫn chạy ứng dụng?".format(
                    port
                ),
            ):
                return
        spec = ProcessSpec(
            "UI {}".format(self.ui_name.get()),
            self._ui_command(),
            AEB_ROOT,
        )
        self._start_process("ui", spec)

    def _stop_ui(self) -> None:
        self._stop_process("ui")

    def _start_test(self) -> None:
        needs_carla = self.test_type.get() in TEST_SCRIPTS
        if needs_carla and not port_open(
            self.host.get(),
            self._int_value(self.port, 2000),
        ):
            messagebox.showerror(
                "CARLA chưa sẵn sàng",
                "Hãy bật CARLA server trước khi chạy radar scenario.",
            )
            return
        spec = ProcessSpec(
            self.test_type.get(),
            self._test_command(),
            AEB_ROOT,
        )
        self._start_process("test", spec)

    def _stop_test(self) -> None:
        self._stop_process("test")

    def _start_video(self) -> None:
        if not port_open(self.host.get(), self._int_value(self.port, 2000)):
            messagebox.showerror(
                "CARLA chưa sẵn sàng",
                "Hãy bật CARLA server trước khi quay video.",
            )
            return
        spec = ProcessSpec(
            "Record video",
            self._video_command(),
            AEB_ROOT,
        )
        self._start_process("video", spec)

    def _stop_video(self) -> None:
        self._stop_process("video")

    def _stop_selected_process(self) -> None:
        running = [key for key, process in self.processes.items() if process.running]
        if not running:
            return
        if len(running) == 1:
            self._stop_process(running[0])
            return
        menu = tk.Menu(self.root, tearoff=False)
        for key in running:
            process = self.processes[key]
            menu.add_command(
                label=process.spec.name,
                command=lambda selected=key: self._stop_process(selected),
            )
        menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def _stop_process(self, key: str) -> None:
        process = self.processes.get(key)
        if process is None or not process.running:
            return
        self._append_log(process.spec.name, "STOP requested\n")
        threading.Thread(target=process.stop, daemon=True).start()

    def _check_server_now(self) -> None:
        port = self._int_value(self.port, 2000)
        opened = port_open(self.host.get(), port, timeout=0.5)
        if opened:
            status = "CARLA: ONLINE {}:{}".format(self.host.get(), port)
        else:
            rows = carla_process_rows()
            if rows:
                status = "CARLA: PROCESS TREO, PORT OFFLINE {}:{} ({})".format(
                    self.host.get(),
                    port,
                    len(rows),
                )
            else:
                status = "CARLA: OFFLINE {}:{}".format(self.host.get(), port)
        self.server_status.set(status)

    def _poll_processes(self) -> None:
        self._check_server_now()
        self._update_process_label()
        self.root.after(1000, self._poll_processes)

    def _update_process_label(self) -> None:
        names = [
            process.spec.name
            for process in self.processes.values()
            if process.running
        ]
        self.process_label.configure(text=", ".join(names) if names else "Không có")

    def _drain_output(self) -> None:
        while True:
            try:
                source, text = self.output_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(source, text)
        self.root.after(100, self._drain_output)

    def _append_log(self, source: str, text: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log.configure(state=tk.NORMAL)
        for line in text.splitlines(True):
            self.log.insert(tk.END, "[{}] [{}] {}".format(timestamp, source, line))
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _clear_log(self) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.configure(state=tk.DISABLED)

    def _on_close(self) -> None:
        running = [process for process in self.processes.values() if process.running]
        if running and not messagebox.askyesno(
            "Đóng launcher",
            "Có {} tiến trình đang chạy. Dừng tất cả và thoát?".format(len(running)),
        ):
            return
        for process in running:
            process.stop(timeout=2.0)
        self.root.destroy()


def check_prerequisites() -> int:
    checks = {
        "CARLA script": CARLA_SCRIPT.is_file(),
        "CARLA Python": CARLA_PYTHON.is_file(),
        "YOLO Python": YOLO_PYTHON.is_file(),
        "Sensor config": SENSOR_CONFIG.is_file(),
        "Scenario config": DEFAULT_SCENARIO_CONFIG.is_file(),
        "Final demo UI": UI_APPLICATIONS["Final demo 3 màn"].is_file(),
        "Video recorder": (AEB_ROOT / "scripts" / "record_scenario_videos.py").is_file(),
    }
    for name, passed in checks.items():
        print("{:<18} {}".format(name, "OK" if passed else "MISSING"))
    print("Scenarios          {}".format(len(scenario_ids(DEFAULT_SCENARIO_CONFIG))))
    return 0 if all(checks.values()) else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check launcher prerequisites without opening the window.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.check:
        return check_prerequisites()
    root = tk.Tk()
    AebLauncher(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
