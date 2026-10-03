"""Scenario video recording page."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import List

from ui.launcher.commands import VideoSettings, video_command
from ui.launcher.config import AEB_ROOT, BRAKE_MODES
from ui.launcher.processes import ProcessSpec, port_open


class VideoPageMixin:
    """Mixed into ``AebLauncher``; uses its Tk variables and helpers."""

    def _build_video_tab(self) -> None:
        page = self.video_tab

        output_form = self._form(self._card(page, "Scenario và đầu ra"))
        self.video_scenario_combo = ttk.Combobox(
            output_form,
            textvariable=self.video_scenario,
            values=["Tất cả"] + self.scenarios,
            state="readonly",
            width=22,
        )
        self._field(output_form, "Scenario", self.video_scenario_combo, row=0)
        self._field(
            output_form,
            "Run ID",
            ttk.Entry(output_form, textvariable=self.video_run_id, width=18),
            row=0,
            column=1,
        )
        self._field(
            output_form,
            "Độ phân giải",
            ttk.Combobox(
                output_form,
                textvariable=self.video_resolution,
                values=("1500x850", "1600x900", "1280x720", "1920x1080"),
                width=12,
            ),
            row=1,
        )
        self._field(
            output_form,
            "Encoder",
            ttk.Combobox(
                output_form,
                textvariable=self.video_encoder,
                values=("h264_nvenc", "libx264"),
                state="readonly",
                width=12,
            ),
            row=1,
            column=1,
        )
        self._field(
            output_form,
            "Scenario config",
            ttk.Label(output_form, textvariable=self.scenario_config_name),
            row=2,
            span=2,
            sticky=tk.W,
        )

        timing_card = self._card(page, "Phanh và thời gian")
        timing_form = self._form(timing_card)
        self._field(
            timing_form,
            "Loại phanh",
            ttk.Combobox(
                timing_form,
                textvariable=self.video_brake_mode,
                values=BRAKE_MODES,
                state="readonly",
                width=14,
            ),
            row=0,
        )
        self._field(
            timing_form,
            "Chờ sau test (s)",
            ttk.Spinbox(
                timing_form,
                from_=0.0,
                to=20.0,
                increment=0.5,
                textvariable=self.video_linger,
                width=8,
            ),
            row=0,
            column=1,
        )
        self._field(
            timing_form,
            "Tối đa (s)",
            ttk.Spinbox(
                timing_form,
                from_=10.0,
                to=300.0,
                increment=5.0,
                textvariable=self.video_max_seconds,
                width=8,
            ),
            row=1,
        )
        self._field(
            timing_form,
            "Cooldown (s)",
            ttk.Spinbox(
                timing_form,
                from_=0.0,
                to=20.0,
                increment=0.5,
                textvariable=self.video_cooldown,
                width=8,
            ),
            row=1,
            column=1,
        )
        self._field(
            timing_form,
            "Reload world mỗi N video",
            ttk.Spinbox(
                timing_form,
                from_=0,
                to=20,
                textvariable=self.video_reload_every,
                width=8,
            ),
            row=2,
        )
        ttk.Checkbutton(
            timing_form,
            text="Realistic mode: hết nguy hiểm thì nhả phanh/chạy tiếp",
            variable=self.video_realistic,
            command=self._refresh_command_preview,
        ).grid(row=3, column=0, columnspan=4, sticky=tk.W, pady=(self.theme.px(6), 0))

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

        self._action(page, "Quay video", self._start_video, "Primary.TButton")
        self._action(page, "Dừng quay", self._stop_video, "Danger.TButton")
        self.video_command_preview = self._command_preview(page)

    def _video_settings(self) -> VideoSettings:
        return VideoSettings(
            scenario_config=self._current_scenario_config(),
            run_id=self.video_run_id.get(),
            resolution=self.video_resolution.get(),
            encoder=self.video_encoder.get(),
            linger_s=self._float_value(self.video_linger, 4.0),
            max_seconds=self._float_value(self.video_max_seconds, 90.0),
            cooldown_s=self._float_value(self.video_cooldown, 2.0),
            reload_every=self._int_value(self.video_reload_every, 0),
            scenario=self.video_scenario.get(),
            brake_mode=self.video_brake_mode.get(),
            realistic=self.video_realistic.get(),
        )

    def _video_command(self) -> List[str]:
        return video_command(self._video_settings())

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
