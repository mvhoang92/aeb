"""The ``AebLauncher`` main window."""

from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Dict

from ui.launcher.config import (
    DEFAULT_SCENARIO_CONFIG,
    SCENARIO_CONFIGS,
    scenario_ids,
)
from ui.launcher.pages.apps import AppsPageMixin
from ui.launcher.pages.server import ServerPageMixin
from ui.launcher.pages.testing import TestingPageMixin
from ui.launcher.pages.video import VideoPageMixin
from ui.launcher.processes import (
    ManagedProcess,
    ProcessSpec,
    carla_process_rows,
    port_open,
)
from ui.launcher.theme import COLORS, configure_style
from ui.launcher.widgets import command_preview, section_intro, set_preview


class AebLauncher(
    ServerPageMixin,
    AppsPageMixin,
    TestingPageMixin,
    VideoPageMixin,
):
    _section_intro = staticmethod(section_intro)
    _command_preview = staticmethod(command_preview)
    _set_preview = staticmethod(set_preview)

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AEB Control Center · CARLA 0.9.11")
        self.root.geometry("1240x900")
        self.root.minsize(1080, 760)
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

        configure_style(self.root)
        self._build_layout()
        self.root.bind("<F5>", lambda _event: self._check_server_now())
        self.root.bind("<Control-l>", lambda _event: self._clear_log())
        for index in range(4):
            self.root.bind(
                "<Control-{}>".format(index + 1),
                lambda _event, selected=index: self.notebook.select(selected),
            )
        self.host.trace_add("write", lambda *_args: self._refresh_command_preview())
        self.port.trace_add("write", lambda *_args: self._refresh_command_preview())
        self._refresh_command_preview()
        self.root.after(100, self._drain_output)
        self.root.after(500, self._poll_processes)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=(18, 16, 18, 12))
        outer.pack(fill=tk.BOTH, expand=True)

        hero = ttk.Frame(outer, style="Hero.TFrame", padding=(22, 16))
        hero.pack(fill=tk.X)
        identity = ttk.Frame(hero, style="Hero.TFrame")
        identity.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(
            identity,
            text="AEB Control Center",
            style="HeroTitle.TLabel",
        ).pack(anchor=tk.W)
        ttk.Label(
            identity,
            text="Khởi động CARLA, chạy demo, kiểm thử và ghi video tại một nơi.",
            style="HeroSubtitle.TLabel",
        ).pack(anchor=tk.W, pady=(3, 0))

        hero_actions = ttk.Frame(hero, style="Hero.TFrame")
        hero_actions.pack(side=tk.RIGHT)
        ttk.Button(
            hero_actions,
            text="Kiểm tra kết nối",
            style="Hero.TButton",
            command=self._check_server_now,
        ).pack(side=tk.LEFT, padx=(0, 10))
        self.server_status_label = ttk.Label(
            hero_actions,
            textvariable=self.server_status,
            style="Status.TLabel",
        )
        self.server_status_label.pack(side=tk.LEFT)

        guide = ttk.Frame(outer, style="Card.TFrame", padding=(16, 9))
        guide.pack(fill=tk.X, pady=(10, 8))
        ttk.Label(guide, text="QUY TRÌNH", style="CardTitle.TLabel").pack(side=tk.LEFT)
        ttk.Label(
            guide,
            text="  1  Bật CARLA   →   2  Chạy ứng dụng   →   3  Kiểm thử   →   4  Ghi video",
            style="Muted.TLabel",
        ).pack(side=tk.LEFT, padx=(10, 0))

        body = ttk.Panedwindow(outer, orient=tk.VERTICAL)
        body.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(body)
        self.notebook = notebook
        self.server_tab = ttk.Frame(notebook, padding=(18, 14))
        self.ui_tab = ttk.Frame(notebook, padding=(18, 14))
        self.test_tab = ttk.Frame(notebook, padding=(18, 14))
        self.video_tab = ttk.Frame(notebook, padding=(18, 14))
        notebook.add(self.server_tab, text="1   CARLA SERVER")
        notebook.add(self.ui_tab, text="2   ỨNG DỤNG")
        notebook.add(self.test_tab, text="3   KIỂM THỬ")
        notebook.add(self.video_tab, text="4   GHI VIDEO")

        self._build_server_tab()
        self._build_ui_tab()
        self._build_test_tab()
        self._build_video_tab()

        console = ttk.Frame(body, style="Card.TFrame", padding=(14, 10))
        console_header = ttk.Frame(console, style="Card.TFrame")
        console_header.pack(fill=tk.X, pady=(0, 7))
        ttk.Label(console_header, text="NHẬT KÝ TIẾN TRÌNH", style="CardTitle.TLabel").pack(
            side=tk.LEFT
        )
        ttk.Label(console_header, text="Đang chạy:", style="Muted.TLabel").pack(
            side=tk.LEFT, padx=(22, 5)
        )
        self.process_label = ttk.Label(
            console_header,
            text="Không có",
            style="CardTitle.TLabel",
        )
        self.process_label.pack(side=tk.LEFT)
        ttk.Button(
            console_header,
            text="Dừng tiến trình…",
            style="Danger.TButton",
            command=self._stop_selected_process,
        ).pack(side=tk.RIGHT)
        ttk.Button(
            console_header,
            text="Xóa nhật ký",
            command=self._clear_log,
        ).pack(side=tk.RIGHT, padx=(0, 8))

        self.log = ScrolledText(
            console,
            height=2,
            wrap=tk.WORD,
            font=("DejaVu Sans Mono", 9),
            background=COLORS["console"],
            foreground=COLORS["console_text"],
            insertbackground="#FFFFFF",
            selectbackground=COLORS["primary"],
            relief=tk.FLAT,
            padx=10,
            pady=8,
            state=tk.DISABLED,
        )
        self.log.pack(fill=tk.BOTH, expand=True)
        body.add(notebook, weight=7)
        body.add(console, weight=1)

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

    def _refresh_command_preview(self) -> None:
        if hasattr(self, "server_command"):
            self._set_preview(self.server_command, self._server_preview_command())
        if hasattr(self, "ui_command_preview"):
            self._set_preview(self.ui_command_preview, self._ui_command())
        if hasattr(self, "test_command_preview"):
            self._set_preview(self.test_command_preview, self._test_command())
        if hasattr(self, "video_command_preview"):
            self._set_preview(self.video_command_preview, self._video_command())

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
            status = "ONLINE  {}:{}".format(self.host.get(), port)
            status_style = "Online.Status.TLabel"
        else:
            rows = carla_process_rows()
            if rows:
                status = "CẦN DỌN  {}:{} · {} process".format(
                    self.host.get(),
                    port,
                    len(rows),
                )
                status_style = "Warning.Status.TLabel"
            else:
                status = "OFFLINE  {}:{}".format(self.host.get(), port)
                status_style = "Offline.Status.TLabel"
        self.server_status.set(status)
        if hasattr(self, "server_status_label"):
            self.server_status_label.configure(style=status_style)

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
