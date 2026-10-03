"""Controlled test page (scenario batches, unit tests, dataset audit)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import List

from ui.launcher.commands import CheckSettings, check_command
from ui.launcher.config import AEB_ROOT, TEST_SCRIPTS
from ui.launcher.processes import ProcessSpec, port_open


class TestingPageMixin:
    """Mixed into ``AebLauncher``; uses its Tk variables and helpers."""

    def _build_test_tab(self) -> None:
        self._section_intro(
            self.test_tab,
            "Kiểm thử có kiểm soát",
            "Chạy scenario radar/fusion, unit test hoặc audit dataset từ cùng một giao diện.",
        )
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

        ttk.Label(form, text="Chế độ điều khiển").grid(row=1, column=0, sticky=tk.W, pady=6)
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
        ttk.Label(form, text="Cooldown (s)").grid(row=2, column=2, sticky=tk.W)
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
        ttk.Button(
            actions,
            text="Dừng kiểm thử",
            style="Danger.TButton",
            command=self._stop_test,
        ).pack(side=tk.LEFT, padx=8)
        self.test_command_preview = self._command_preview(self.test_tab)
        self._on_test_selection()

    def _check_settings(self) -> CheckSettings:
        return CheckSettings(
            test_type=self.test_type.get(),
            scenario_config=self._current_scenario_config(),
            control_mode=self.test_control_mode.get(),
            repeat=self._int_value(self.test_repeat, 1),
            cooldown_s=self._float_value(self.test_cooldown, 1.0),
            reload_every=self._int_value(self.test_reload_every, 0),
            scenario=self.test_scenario.get(),
            load_map=self.test_load_map.get(),
            record_evidence=self.test_record_evidence.get(),
            run_id=self.test_run_id.get(),
        )

    def _test_command(self) -> List[str]:
        return check_command(self._check_settings())

    def _on_test_selection(self, _event=None) -> None:
        radar_test = self.test_type.get() in TEST_SCRIPTS
        state = "readonly" if radar_test else "disabled"
        self.test_scenario_combo.configure(state=state)
        self.test_control_combo.configure(state=state)
        self.test_repeat_spin.configure(state="normal" if radar_test else "disabled")
        self.load_map_check.configure(state="normal" if radar_test else "disabled")
        self.evidence_check.configure(state="normal" if radar_test else "disabled")
        self._refresh_command_preview()

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
