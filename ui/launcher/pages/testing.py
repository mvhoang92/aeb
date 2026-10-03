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
        page = self.test_tab
        px = self.theme.px

        test_card = self._card(page, "Bài kiểm thử")
        form = self._form(test_card)
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
            width=22,
        )
        self._field(form, "Loại kiểm thử", test_combo, row=0)
        test_combo.bind("<<ComboboxSelected>>", self._on_test_selection)
        self.test_scenario_combo = ttk.Combobox(
            form,
            textvariable=self.test_scenario,
            values=["Tất cả"] + self.scenarios,
            state="readonly",
            width=22,
        )
        self._field(form, "Scenario", self.test_scenario_combo, row=0, column=1)
        self._field(
            form,
            "Scenario config",
            ttk.Label(form, textvariable=self.scenario_config_name),
            row=1,
            span=2,
            sticky=tk.W,
        )

        batch_form = self._form(self._card(page, "Tham số batch"))
        self.test_control_combo = ttk.Combobox(
            batch_form,
            textvariable=self.test_control_mode,
            values=("physics", "deterministic"),
            state="readonly",
            width=14,
        )
        self._field(batch_form, "Chế độ điều khiển", self.test_control_combo, row=0)
        self.test_repeat_spin = ttk.Spinbox(
            batch_form,
            from_=1,
            to=20,
            textvariable=self.test_repeat,
            width=8,
        )
        self._field(batch_form, "Số lần lặp", self.test_repeat_spin, row=0, column=1)
        self._field(
            batch_form,
            "Run ID",
            ttk.Entry(batch_form, textvariable=self.test_run_id, width=18),
            row=1,
        )
        self._field(
            batch_form,
            "Cooldown (s)",
            ttk.Spinbox(
                batch_form,
                from_=0.0,
                to=10.0,
                increment=0.5,
                textvariable=self.test_cooldown,
                width=8,
            ),
            row=1,
            column=1,
        )
        self._field(
            batch_form,
            "Reload world mỗi N bài",
            ttk.Spinbox(
                batch_form,
                from_=0,
                to=20,
                textvariable=self.test_reload_every,
                width=8,
            ),
            row=2,
        )

        options = ttk.Frame(batch_form, style="Card.TFrame")
        options.grid(row=3, column=0, columnspan=4, sticky=tk.W, pady=(px(6), 0))
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
        self.evidence_check.pack(side=tk.LEFT, padx=(px(24), 0))

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

        self._action(page, "Chạy kiểm thử", self._start_test, "Primary.TButton")
        self._action(page, "Dừng kiểm thử", self._stop_test, "Danger.TButton")
        self.test_command_preview = self._command_preview(page)
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
