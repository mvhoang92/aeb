"""Main window of AEB Test Bench v2."""

from __future__ import absolute_import

import json
import tkinter as tk
from tkinter import messagebox, ttk

from ui.testbench.catalog import Catalog
from ui.testbench.execution import (
    carla_command_text,
    carla_listening,
    start_carla,
)
from ui.testbench.experiment import ExperimentPage
from ui.testbench.paths import CARLA_LOG_FILE, logs_root
from ui.testbench.plan import DEFAULT_HOST, DEFAULT_PORT
from ui.testbench.results_view import ResultsPage
from ui.testbench.theme import Theme
from ui.testbench.widgets import Pill, Tooltip


WINDOW_TITLE = "AEB Test Bench v2"
PAGES = ("experiment", "results")
PAGE_ALIASES = {
    "experiment": "experiment",
    "thi-nghiem": "experiment",
    "1": "experiment",
    "results": "results",
    "ket-qua": "results",
    "2": "results",
}


def page_name(value):
    if value is None:
        return "experiment"
    key = str(value).strip().lower()
    if key not in PAGE_ALIASES:
        raise ValueError("Trang không hợp lệ: {} (experiment | results)".format(value))
    return PAGE_ALIASES[key]


class TestBenchApp(object):
    def __init__(self, root, host=DEFAULT_HOST, port=DEFAULT_PORT, catalog=None):
        self.root = root
        self.host = host
        self.port = int(port)
        self.theme = Theme(root)
        self.catalog = catalog or Catalog.load()
        self.logs_root = logs_root()
        self._carla_starting = False
        root.title(WINDOW_TITLE)
        self._initial_geometry()
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)
        self._build_header()
        self.content = ttk.Frame(root)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)
        self.experiment = ExperimentPage(self.content, self)
        self.results = ResultsPage(self.content, self)
        self.pages = {"experiment": self.experiment, "results": self.results}
        self.current_page = None
        self.show_page("experiment")
        self.results.refresh()
        self._poll_carla()

    def _initial_geometry(self):
        px = self.theme.px
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = min(px(1440), int(screen_w * 0.96))
        height = min(px(880), int(screen_h * 0.92))
        self.root.geometry("{}x{}".format(width, height))
        self.root.minsize(min(px(1100), width), min(px(680), height))

    def _build_header(self):
        px = self.theme.px
        header = ttk.Frame(self.root, style="Header.TFrame", padding=(px(16), px(8)))
        header.grid(row=0, column=0, sticky="ew")
        brand = ttk.Frame(header, style="Header.TFrame")
        brand.grid(row=0, column=0, sticky="w")
        ttk.Label(brand, text=WINDOW_TITLE, style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            brand,
            text="Thiết kế · chạy · đọc kết quả thí nghiệm AEB trên CARLA 0.9.11",
            style="Subtitle.TLabel",
        ).pack(anchor="w")
        nav = ttk.Frame(header, style="Header.TFrame")
        nav.grid(row=0, column=1, sticky="w", padx=(px(28), 0))
        self.nav_buttons = {}
        for name, label in (("experiment", "Thí nghiệm"), ("results", "Kết quả")):
            button = ttk.Button(
                nav, text=label, style="Nav.TButton", command=lambda name=name: self.show_page(name)
            )
            button.pack(side="left", padx=(0, px(4)))
            self.nav_buttons[name] = button
        status = ttk.Frame(header, style="Header.TFrame")
        status.grid(row=0, column=2, sticky="e")
        header.columnconfigure(2, weight=1)
        self.carla_pill = Pill(status, self.theme, "CARLA ?", "neutral")
        self.carla_pill.pack(side="left", padx=(0, px(8)))
        self.carla_button = ttk.Button(status, text="Khởi động CARLA", command=self.start_carla)
        self.carla_button.pack(side="left")
        Tooltip(
            self.carla_button,
            "Chạy lệnh đã kiểm chứng:\n{}\nLog: {}".format(carla_command_text(), CARLA_LOG_FILE),
            self.theme,
        )

    # ---------------------------------------------------------------- pages
    def show_page(self, name):
        name = page_name(name)
        for key, page in self.pages.items():
            if key == name:
                page.grid(row=0, column=0, sticky="nsew")
            else:
                page.grid_remove()
        for key, button in self.nav_buttons.items():
            button.configure(style="NavActive.TButton" if key == name else "Nav.TButton")
        self.current_page = name

    # ---------------------------------------------------------------- CARLA
    def carla_online(self):
        return carla_listening(self.host, self.port)

    def _poll_carla(self):
        experiment = self.experiment
        if experiment.queue is not None and experiment.queue.running:
            # The running runner is the authoritative health signal.
            self.carla_pill.set("CARLA · đang dùng bởi hàng đợi", "info")
            self.root.after(5000, self._poll_carla)
            return
        online = self.carla_online()
        if online:
            self._carla_starting = False
            self.carla_pill.set("CARLA online · {}:{}".format(self.host, self.port), "online")
        elif self._carla_starting:
            self.carla_pill.set("CARLA đang khởi động…", "warn")
        else:
            self.carla_pill.set("CARLA offline · {}:{}".format(self.host, self.port), "offline")
        self.carla_button.state(["disabled"] if online or self._carla_starting else ["!disabled"])
        self.root.after(3000, self._poll_carla)

    def start_carla(self):
        if self.carla_online():
            return
        if not messagebox.askokcancel(
            "Khởi động CARLA",
            "Chạy CARLA 0.9.11 bằng lệnh đã kiểm chứng?\n\n{}\n\nLog: {}".format(
                carla_command_text(), CARLA_LOG_FILE
            ),
            parent=self.root,
        ):
            return
        try:
            pid = start_carla()
        except OSError as exc:
            messagebox.showerror("Khởi động CARLA", str(exc), parent=self.root)
            return
        self._carla_starting = True
        self.experiment.append_log("CARLA khởi động (pid {}), log: {}\n".format(pid, CARLA_LOG_FILE), "head")

    # ---------------------------------------------------------------- misc
    def copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)


def apply_cli(app, args):
    """Debug/automation hooks: preset, explicit selection, autostart."""
    experiment = app.experiment
    if args.preset:
        experiment.apply_preset(args.preset)
    if args.scenario:
        keys = []
        for item in args.scenario:
            suite_name, _, scenario_id = item.partition(":")
            suite = app.catalog.find_suite(suite_name)
            ids = [scenario_id] if scenario_id else suite.scenario_ids()
            for value in ids:
                keys.append(app.catalog.scenario((suite.rel, value)).key)
        experiment.set_selection(keys)
        experiment.preset_key = None
        experiment._update_preset_info()
    if args.policy:
        for key, var in experiment.policy_vars.items():
            var.set(key in args.policy)
    if args.device:
        experiment.device_var.set(args.device)
    if args.control_mode:
        experiment.mode_var.set(args.control_mode)
    if args.repeat:
        experiment.repeat_var.set(str(args.repeat))
    if args.scenario or args.policy:
        experiment.regenerate_run_id(only_if_auto=True)
    if args.run_id:
        experiment.run_id_var.set(args.run_id)
    experiment.refresh_plan()
    if args.select_run:
        app.results.refresh(select=args.select_run)
    app.show_page(args.page)
    if args.step:
        experiment.show_view(args.step)

    def report(plan, outcomes):
        payload = {
            "run_ids": [command.run_id for command in plan.commands],
            "outcomes": outcomes,
        }
        print("TESTBENCH-QUEUE-DONE " + json.dumps(payload), flush=True)
        if args.show_results_when_done:
            experiment.open_results()
        if args.exit_when_done:
            app.root.after(int(max(0.0, args.linger_s) * 1000), app.root.destroy)

    experiment.queue_finished_callbacks.append(report)
    if args.autostart:

        def autostart():
            plan = experiment.plan
            if plan is not None:
                print(
                    "TESTBENCH-PLAN " + json.dumps([command.argv for command in plan.commands]),
                    flush=True,
                )
            if not experiment.start_queue():
                print("TESTBENCH-AUTOSTART-FAILED", flush=True)
                if args.exit_when_done:
                    app.root.after(500, app.root.destroy)
                    app.exit_code = 2

        app.root.after(800, autostart)


def main(args):
    root = tk.Tk()
    app = TestBenchApp(root, port=args.port)
    app.exit_code = 0
    if args.geometry:
        root.geometry(args.geometry)
    apply_cli(app, args)
    root.mainloop()
    return app.exit_code
