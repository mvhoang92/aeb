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
        page = self.ui_tab
        px = self.theme.px

        app_form = self._form(self._card(page, "Ứng dụng"))
        app_combo = ttk.Combobox(
            app_form,
            textvariable=self.ui_name,
            values=tuple(UI_APPLICATIONS.keys()),
            state="readonly",
            width=18,
        )
        self._field(app_form, "Ứng dụng", app_combo, row=0)
        app_combo.bind("<<ComboboxSelected>>", self._on_ui_selection)
        self._field(
            app_form,
            "Map",
            ttk.Combobox(
                app_form,
                textvariable=self.ui_map,
                values=("Town04", "Town06"),
                width=12,
            ),
            row=0,
            column=1,
        )
        self._field(
            app_form,
            "Độ phân giải mỗi panel",
            ttk.Combobox(
                app_form,
                textvariable=self.ui_resolution,
                values=("1500x850", "1600x900", "1280x720", "960x540", "800x450"),
                width=12,
            ),
            row=1,
        )
        ttk.Checkbutton(
            app_form,
            text="Autopilot",
            variable=self.ui_autopilot,
            command=self._refresh_command_preview,
        ).grid(row=1, column=2, columnspan=2, sticky=tk.W, padx=(px(20), 0))

        scenario_form = self._form(self._card(page, "Scenario AEB trực tiếp"))
        config_combo = ttk.Combobox(
            scenario_form,
            textvariable=self.scenario_config_name,
            values=tuple(SCENARIO_CONFIGS.keys()),
            state="readonly",
            width=22,
        )
        self._field(scenario_form, "Config", config_combo, row=0)
        config_combo.bind("<<ComboboxSelected>>", self._on_scenario_config_selection)
        self.live_scenario_combo = ttk.Combobox(
            scenario_form,
            textvariable=self.live_scenario,
            values=self.scenarios,
            state="readonly",
            width=22,
        )
        self._field(scenario_form, "Scenario", self.live_scenario_combo, row=0, column=1)
        self._field(
            scenario_form,
            "Điều khiển",
            ttk.Combobox(
                scenario_form,
                textvariable=self.live_control_mode,
                values=("physics", "deterministic"),
                state="readonly",
                width=14,
            ),
            row=1,
        )
        self._field(
            scenario_form,
            "Camera",
            ttk.Combobox(
                scenario_form,
                textvariable=self.live_camera,
                values=("wide_chase", "high_chase", "manual"),
                state="readonly",
                width=14,
            ),
            row=1,
            column=1,
        )
        self._field(
            scenario_form,
            "Warm-up (s)",
            ttk.Spinbox(
                scenario_form,
                from_=0.0,
                to=10.0,
                increment=0.5,
                textvariable=self.live_warmup,
                width=8,
            ),
            row=2,
        )
        self._field(
            scenario_form,
            "Loại phanh",
            ttk.Combobox(
                scenario_form,
                textvariable=self.ui_brake_mode,
                values=BRAKE_MODES,
                state="readonly",
                width=14,
            ),
            row=2,
            column=1,
        )
        self._field(
            scenario_form,
            "Hành vi AEB",
            ttk.Combobox(
                scenario_form,
                textvariable=self.ui_behavior,
                values=(
                    "Validation: phanh rồi dừng để đo",
                    "Realistic: hết nguy hiểm thì nhả phanh chạy tiếp",
                ),
                state="readonly",
                width=40,
            ),
            row=3,
            span=2,
        )

        option_frame = self._form(self._card(page, "Tùy chọn chạy"))
        for index, (text, variable) in enumerate(
            (
                ("Clean radar overlay", self.ui_clean_overlay),
                ("Synchronous 20 FPS", self.ui_sync),
                ("Reload world khi mở scenario", self.ui_reload_world),
                ("Restart CARLA trước scenario", self.ui_restart_carla),
            )
        ):
            ttk.Checkbutton(
                option_frame,
                text=text,
                variable=variable,
                command=self._refresh_command_preview,
            ).grid(
                row=index // 2,
                column=(index % 2) * 2,
                columnspan=2,
                sticky=tk.W,
                padx=(px(20) if index % 2 else 0, 0),
                pady=px(2),
            )

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

        self._action(page, "Chạy ứng dụng", self._start_ui, "Primary.TButton")
        self._action(page, "Dừng ứng dụng", self._stop_ui, "Danger.TButton")
        self.ui_command_preview = self._command_preview(page)

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
