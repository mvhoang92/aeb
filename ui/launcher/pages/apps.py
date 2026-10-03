"""Visual applications page (pygame UIs and live AEB scenarios)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import List

from ui.launcher.commands import AppSettings, app_command
from ui.launcher.config import AEB_ROOT, BRAKE_MODES, SCENARIO_CONFIGS, UI_APPLICATIONS
from ui.launcher.processes import ProcessSpec, port_open


class AppsPageMixin:
    """Mixed into ``AebLauncher``; uses its Tk variables and helpers."""

    def _build_ui_tab(self) -> None:
        self._section_intro(
            self.ui_tab,
            "Ứng dụng trực quan",
            "Chọn màn hình quan sát và scenario. Các tùy chọn AEB chỉ xuất hiện trong lệnh khi phù hợp.",
        )
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

        scenario_frame = ttk.LabelFrame(
            form,
            text="Scenario AEB trực tiếp",
            style="Panel.TLabelframe",
            padding=10,
        )
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
        ttk.Label(scenario_frame, text="Điều khiển").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
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
        ttk.Label(scenario_frame, text="Warm-up (s)").grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
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
        ttk.Button(
            actions,
            text="Dừng ứng dụng",
            style="Danger.TButton",
            command=self._stop_ui,
        ).pack(side=tk.LEFT, padx=8)
        self.ui_command_preview = self._command_preview(self.ui_tab)

    def _app_settings(self) -> AppSettings:
        return AppSettings(
            name=self.ui_name.get(),
            map_name=self.ui_map.get(),
            resolution=self.ui_resolution.get(),
            host=self.host.get(),
            port=self._int_value(self.port, 2000),
            autopilot=self.ui_autopilot.get(),
            brake_mode=self.ui_brake_mode.get(),
            scenario_config=self._current_scenario_config(),
            scenario=self.live_scenario.get(),
            control_mode=self.live_control_mode.get(),
            camera=self.live_camera.get(),
            warmup_s=self._float_value(self.live_warmup, 2.0),
            reload_world=self.ui_reload_world.get(),
            behavior=self.ui_behavior.get(),
            clean_overlay=self.ui_clean_overlay.get(),
            sync=self.ui_sync.get(),
        )

    def _ui_command(self) -> List[str]:
        return app_command(self._app_settings())

    def _on_ui_selection(self, _event=None) -> None:
        self._refresh_command_preview()

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
