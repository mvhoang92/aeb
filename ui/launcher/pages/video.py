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
        self._section_intro(
            self.video_tab,
            "Ghi video scenario",
            "Chọn encoder, độ phân giải và thời gian nán; video được lưu trong external workspace.",
        )
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

        ttk.Label(form, text="Chờ sau test (s)").grid(row=2, column=2, sticky=tk.W, pady=6)
        ttk.Spinbox(
            form,
            from_=0.0,
            to=20.0,
            increment=0.5,
            textvariable=self.video_linger,
            width=8,
        ).grid(row=2, column=3, sticky=tk.W, padx=8)

        ttk.Label(form, text="Tối đa (s)").grid(row=3, column=0, sticky=tk.W)
        ttk.Spinbox(
            form,
            from_=10.0,
            to=300.0,
            increment=5.0,
            textvariable=self.video_max_seconds,
            width=8,
        ).grid(row=3, column=1, sticky=tk.W, padx=(8, 24))

        ttk.Label(form, text="Cooldown (s)").grid(row=3, column=2, sticky=tk.W)
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
        ttk.Button(
            actions,
            text="Dừng quay",
            style="Danger.TButton",
            command=self._stop_video,
        ).pack(side=tk.LEFT, padx=8)
        self.video_command_preview = self._command_preview(self.video_tab)

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
