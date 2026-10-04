"""The ``AebLauncher`` main window: sidebar, pages, status and log."""

from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

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
    carla_listening,
)
from ui.launcher.theme import COLORS, configure_style
from ui.launcher.widgets import (
    ElidedLabel,
    Page,
    ScrollableFrame,
    StatusPill,
    WrapLabel,
    card,
    command_preview,
    field_label,
    form_grid,
    place_field,
    set_preview,
)


# (key, sidebar label, page title, hint)
PAGES = (
    (
        "carla",
        "CARLA server",
        "CARLA server",
        "Cấu hình simulator trước, sau đó kiểm tra trạng thái kết nối ở góc trên bên phải.",
    ),
    (
        "apps",
        "Ứng dụng",
        "Ứng dụng trực quan",
        "Chọn màn hình quan sát và scenario. Các tùy chọn AEB chỉ xuất hiện trong lệnh khi phù hợp.",
    ),
    (
        "tests",
        "Kiểm thử",
        "Kiểm thử có kiểm soát",
        "Chạy scenario radar/fusion, unit test hoặc audit dataset từ cùng một giao diện.",
    ),
    (
        "video",
        "Ghi video",
        "Ghi video scenario",
        "Chọn encoder, độ phân giải và thời gian nán; video được lưu trong external workspace.",
    ),
)
PAGE_KEYS = tuple(page[0] for page in PAGES)

# Logical (96-dpi) sizes; multiplied by the display scale at runtime.
# Kept below 80% of a 1536x864 logical desktop so GNOME does not auto-maximize.
DEFAULT_SIZE = (1140, 760)
MINIMUM_SIZE = (940, 640)
SIDEBAR_WIDTH = 204
LOG_DEFAULT_HEIGHT = 140  # header bar + ~5 log lines
LOG_MINIMUM_HEIGHT = 112
TOP_MINIMUM_HEIGHT = 330
# The log gives way (down to its minimum) before the page area drops below this.
TOP_COMFORT_HEIGHT = 480


def page_index(name: Optional[str]) -> int:
    """Map a ``--page`` value (key, alias or 1-based number) to an index."""
    if not name:
        return 0
    name = str(name).strip().lower()
    aliases = {"server": "carla", "ui": "apps", "app": "apps", "test": "tests", "kiem-thu": "tests"}
    name = aliases.get(name, name)
    if name.isdigit() and 1 <= int(name) <= len(PAGES):
        return int(name) - 1
    if name in PAGE_KEYS:
        return PAGE_KEYS.index(name)
    raise ValueError("Unknown page {!r}; use one of {}".format(name, ", ".join(PAGE_KEYS)))


class AebLauncher(
    ServerPageMixin,
    AppsPageMixin,
    TestingPageMixin,
    VideoPageMixin,
):
    _set_preview = staticmethod(set_preview)

    def __init__(self, root: tk.Tk, initial_page: int = 0):
        self.root = root
        self.root.title("AEB Control Center · CARLA 0.9.11")
        self.theme = configure_style(self.root)
        self._apply_window_size()
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

        self._build_layout()
        self.root.bind("<F5>", lambda _event: self._check_server_now())
        self.root.bind("<Control-l>", lambda _event: self._clear_log())
        for index in range(4):
            self.root.bind(
                "<Control-{}>".format(index + 1),
                lambda _event, selected=index: self._show_page(selected),
            )
        self.host.trace_add("write", lambda *_args: self._refresh_command_preview())
        self.port.trace_add("write", lambda *_args: self._refresh_command_preview())
        self._refresh_command_preview()
        self._show_page(initial_page)
        self.root.after(100, self._drain_output)
        self.root.after(500, self._poll_processes)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    # Window and layout
    # ------------------------------------------------------------------ #
    def _apply_window_size(self) -> None:
        px = self.theme.px
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = min(px(DEFAULT_SIZE[0]), screen_width - px(40))
        height = min(px(DEFAULT_SIZE[1]), screen_height - px(96))
        self.root.geometry("{}x{}".format(width, height))
        self.root.minsize(min(px(MINIMUM_SIZE[0]), width), min(px(MINIMUM_SIZE[1]), height))

    def _build_layout(self) -> None:
        px = self.theme.px
        self.paned = tk.PanedWindow(
            self.root,
            orient=tk.VERTICAL,
            sashwidth=px(6),
            sashrelief=tk.FLAT,
            borderwidth=0,
            background=COLORS["border"],
            opaqueresize=True,
            sashcursor="sb_v_double_arrow",
        )
        self.paned.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(self.paned, style="Page.TFrame")
        top.columnconfigure(0, minsize=px(SIDEBAR_WIDTH))
        top.columnconfigure(1, weight=1)
        top.rowconfigure(0, weight=1)
        self._build_sidebar(top).grid(row=0, column=0, sticky=tk.NSEW)

        main = ttk.Frame(top, style="Page.TFrame")
        main.grid(row=0, column=1, sticky=tk.NSEW)
        self._build_header(main)
        container = ttk.Frame(main, style="Page.TFrame")
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        self.pages: List[Page] = []
        for _key, _label, _title, hint in PAGES:
            page = Page(container, self.theme, hint)
            page.grid(row=0, column=0, sticky=tk.NSEW)
            self.pages.append(page)
        self.server_tab, self.ui_tab, self.test_tab, self.video_tab = self.pages

        self._build_server_tab()
        self._build_ui_tab()
        self._build_test_tab()
        self._build_video_tab()

        console = self._build_console(self.paned)
        self.console = console
        self.paned.add(top, stretch="always", minsize=px(TOP_MINIMUM_HEIGHT))
        self.paned.add(
            console,
            stretch="never",
            minsize=px(LOG_MINIMUM_HEIGHT),
            height=px(LOG_DEFAULT_HEIGHT),
        )
        ScrollableFrame.install_mouse_wheel(self.root)
        self._log_height_user: Optional[int] = None
        self.paned.bind("<ButtonRelease-1>", self._remember_log_height, add="+")
        self.paned.bind("<Configure>", lambda _event: self.root.after_idle(self._fit_log_pane), add="+")

    def _remember_log_height(self, _event=None) -> None:
        """The user dragged the sash: keep their log height on later resizes."""
        self.root.after_idle(
            lambda: setattr(self, "_log_height_user", self.console.winfo_height())
        )

    def _fit_log_pane(self) -> None:
        px = self.theme.px
        total = self.paned.winfo_height()
        if total <= 1:
            return
        desired = self._log_height_user or px(LOG_DEFAULT_HEIGHT)
        height = min(desired, total - px(TOP_COMFORT_HEIGHT))
        height = max(px(LOG_MINIMUM_HEIGHT), height)
        sash = total - height - int(self.paned.cget("sashwidth"))
        if abs(self.paned.sash_coord(0)[1] - sash) > 1:
            self.paned.sash_place(0, 0, max(0, sash))

    def _build_sidebar(self, parent: tk.Misc) -> ttk.Frame:
        px = self.theme.px
        sidebar = ttk.Frame(parent, style="Sidebar.TFrame", padding=(0, px(20), 0, px(14)))
        brand = ttk.Frame(sidebar, style="Sidebar.TFrame", padding=(px(18), 0, px(12), px(18)))
        brand.pack(fill=tk.X)
        ttk.Label(brand, text="AEB", style="Brand.TLabel").pack(anchor=tk.W)
        ttk.Label(brand, text="Control Center", style="BrandSub.TLabel").pack(anchor=tk.W)
        ttk.Label(brand, text="CARLA 0.9.11", style="SidebarNote.TLabel").pack(
            anchor=tk.W, pady=(px(2), 0)
        )
        ttk.Label(
            brand,
            text="Khởi động CARLA, chạy demo, kiểm thử và ghi video tại một nơi.",
            style="SidebarNote.TLabel",
            wraplength=px(SIDEBAR_WIDTH - 34),
            justify=tk.LEFT,
        ).pack(fill=tk.X, pady=(px(10), 0))

        ttk.Label(sidebar, text="QUY TRÌNH", style="SidebarCaps.TLabel").pack(
            anchor=tk.W, padx=px(18), pady=(px(4), px(6))
        )
        self.page_var = tk.IntVar(value=0)
        self.nav_buttons: List[ttk.Radiobutton] = []
        for index, (_key, label, _title, _hint) in enumerate(PAGES):
            button = ttk.Radiobutton(
                sidebar,
                text="{}    {}".format(index + 1, label),
                value=index,
                variable=self.page_var,
                style="Nav.TRadiobutton",
                command=lambda selected=index: self._show_page(selected),
                takefocus=True,
            )
            button.pack(fill=tk.X, padx=px(8), pady=px(1))
            self.nav_buttons.append(button)

        shortcuts = ttk.Frame(sidebar, style="Sidebar.TFrame", padding=(px(18), 0, px(12), 0))
        shortcuts.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(shortcuts, text="PHÍM TẮT", style="SidebarCaps.TLabel").pack(
            anchor=tk.W, pady=(0, px(4))
        )
        for keys, action in (
            ("Ctrl+1…4", "chuyển trang"),
            ("F5", "kiểm tra CARLA"),
            ("Ctrl+L", "xóa nhật ký"),
        ):
            row = ttk.Frame(shortcuts, style="Sidebar.TFrame")
            row.pack(fill=tk.X)
            ttk.Label(row, text=keys, style="SidebarNote.TLabel", width=9).pack(side=tk.LEFT)
            ttk.Label(row, text=action, style="SidebarNote.TLabel").pack(side=tk.LEFT)
        return sidebar

    def _build_header(self, parent: tk.Misc) -> None:
        px = self.theme.px
        header = ttk.Frame(parent, style="Header.TFrame", padding=(px(22), px(12), px(18), px(12)))
        header.pack(fill=tk.X)
        tk.Frame(parent, height=1, background=COLORS["border"]).pack(fill=tk.X)
        # Pack right-hand items first so the status pill is never squeezed out.
        ttk.Button(
            header,
            text="Kiểm tra kết nối",
            style="Small.TButton",
            command=self._check_server_now,
        ).pack(side=tk.RIGHT, padx=(px(10), 0))
        self.status_pill = StatusPill(header, self.theme, COLORS["surface"])
        self.status_pill.pack(side=tk.RIGHT)
        self.status_pill.set("Đang kiểm tra...", "checking")
        self.page_title = ttk.Label(header, text="", style="PageTitle.TLabel")
        self.page_title.pack(side=tk.LEFT)

    def _build_console(self, parent: tk.Misc) -> ttk.Frame:
        px = self.theme.px
        console = ttk.Frame(parent, style="Console.TFrame")
        header = ttk.Frame(console, style="Console.TFrame", padding=(px(18), px(7), px(12), px(7)))
        header.pack(fill=tk.X)
        ttk.Button(
            header,
            text="Dừng tiến trình…",
            style="ConsoleDanger.TButton",
            command=self._stop_selected_process,
        ).pack(side=tk.RIGHT)
        ttk.Button(
            header,
            text="Xóa nhật ký",
            style="Console.TButton",
            command=self._clear_log,
        ).pack(side=tk.RIGHT, padx=(0, px(8)))
        ttk.Label(header, text="NHẬT KÝ TIẾN TRÌNH", style="ConsoleTitle.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text="Đang chạy:", style="ConsoleMuted.TLabel").pack(
            side=tk.LEFT, padx=(px(18), px(5))
        )
        self.process_label = ElidedLabel(
            header,
            self.theme.font("small"),
            text="Không có",
            style="ConsoleValue.TLabel",
        )
        self.process_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, px(10)))

        body = tk.Frame(console, background=COLORS["console"])
        body.pack(fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(body, orient=tk.VERTICAL, style="Console.Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log = tk.Text(
            body,
            height=4,
            wrap=tk.WORD,
            font=self.theme.font("mono"),
            background=COLORS["console"],
            foreground=COLORS["console_text"],
            insertbackground="#FFFFFF",
            selectbackground=COLORS["primary"],
            inactiveselectbackground=COLORS["navy_soft"],
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            padx=px(16),
            pady=px(8),
            state=tk.DISABLED,
            yscrollcommand=scrollbar.set,
        )
        scrollbar.configure(command=self.log.yview)
        self.log.pack(fill=tk.BOTH, expand=True)
        return console

    def _show_page(self, index: int) -> None:
        index = max(0, min(len(self.pages) - 1, int(index)))
        for position, page in enumerate(self.pages):
            if position == index:
                page.grid()
            else:
                page.grid_remove()
        self.page_var.set(index)
        self.page_title.configure(text=PAGES[index][2])

    # ------------------------------------------------------------------ #
    # Shared page helpers
    # ------------------------------------------------------------------ #
    def _command_preview(self, page: Page) -> tk.Text:
        return command_preview(page.footer, self.theme)

    def _card(self, page: Page, title: Optional[str] = None) -> ttk.Frame:
        return card(page.body, self.theme, title)

    def _form(self, parent: tk.Misc, columns: int = 2) -> ttk.Frame:
        return form_grid(parent, self.theme, columns)

    def _field(self, form: tk.Misc, text: str, widget: tk.Widget, row: int, column: int = 0, span: int = 1, sticky=tk.EW) -> tk.Widget:
        field_label(form, self.theme, text, row, column)
        return place_field(widget, self.theme, row, column, span, sticky)

    def _action(self, page: Page, text: str, command, style: str = "TButton") -> ttk.Button:
        button = ttk.Button(page.actions, text=text, style=style, command=command)
        button.pack(side=tk.LEFT, padx=(0, self.theme.px(8)))
        return button

    def _note(self, parent: tk.Misc, text: str) -> None:
        WrapLabel(parent, text=text, style="Note.TLabel").pack(
            fill=tk.X, pady=(self.theme.px(8), 0)
        )

    # ------------------------------------------------------------------ #
    # Values, previews and processes
    # ------------------------------------------------------------------ #
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
        opened = carla_listening(self.host.get(), port, timeout=0.5)
        if opened:
            status = "ONLINE  {}:{}".format(self.host.get(), port)
            status_kind = "online"
        else:
            rows = carla_process_rows()
            if rows:
                status = "CẦN DỌN  {}:{} · {} process".format(
                    self.host.get(),
                    port,
                    len(rows),
                )
                status_kind = "warning"
            else:
                status = "OFFLINE  {}:{}".format(self.host.get(), port)
                status_kind = "offline"
        self.server_status.set(status)
        if hasattr(self, "status_pill"):
            self.status_pill.set(status, status_kind)

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
        self.process_label.set_text(", ".join(names) if names else "Không có")

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
