"""'Thí nghiệm' screen: the five numbered steps of an experiment."""

from __future__ import absolute_import

import queue
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from ui.testbench.catalog import (
    EXPECT_ALL,
    EXPECT_COLLISION_OK,
    EXPECTATION_LABELS,
    expectation_text,
    group_label,
    scenario_facts,
    TAG_LABELS,
)
from ui.testbench.execution import (
    OUTCOME_ALGO_FAIL,
    OUTCOME_ALL_PASS,
    OUTCOME_HARD_STOP,
    OUTCOME_LABELS,
    OUTCOME_PENDING,
    OUTCOME_RUNNING,
    OUTCOME_SKIPPED,
    OUTCOME_STOPPED,
    OUTCOME_TECH_ERROR,
    CommandQueue,
)
from ui.testbench.paths import AEB_ROOT
from ui.testbench.plan import (
    PAPER_SEED,
    PRESETS,
    ExperimentOptions,
    build_plan,
    default_run_id_template,
    format_duration,
)
from ui.testbench.policies import (
    CONTROL_MODE_HINT,
    CONTROL_MODES,
    DEVICE_CUDA,
    DEVICE_HINT,
    DEVICE_LABELS,
    POLICIES,
    sensor_config_for,
)
from ui.testbench.widgets import (
    STATE_CHECKED,
    STATE_PARTIAL,
    STATE_UNCHECKED,
    Pill,
    Section,
    Tooltip,
    checkbox_images,
    readonly_text,
    set_text,
    wrap_label,
)


OUTCOME_TAGS = {
    OUTCOME_PENDING: "pending",
    OUTCOME_RUNNING: "running",
    OUTCOME_ALL_PASS: "pass",
    OUTCOME_ALGO_FAIL: "fail",
    OUTCOME_HARD_STOP: "tech",
    OUTCOME_TECH_ERROR: "tech",
    OUTCOME_STOPPED: "stopped",
    OUTCOME_SKIPPED: "stopped",
}

PLAN_NOTE = (
    "Mỗi cặp (file kịch bản × hệ thống) là MỘT lệnh và MỘT thư mục log. Chọn "
    "cả suite → không truyền --scenario (giống chiến dịch của paper); chọn một "
    "phần → truyền nhiều --scenario trong cùng lệnh. Không tạo YAML tạm, nên "
    "SHA-256 ghi trong run_metadata.json là của file suite thật. Thời gian chỉ "
    "là ước lượng."
)


def _speed(value):
    return "" if value is None else "{:g}".format(value)


class ExperimentPage(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master, style="TFrame")
        self.app = app
        self.theme = app.theme
        self.catalog = app.catalog
        self.px = self.theme.px
        self.selected = set()
        self.preset_key = None
        self.run_id_edited = False
        self._suspend_traces = False
        self._plan_after = None
        self._filter_after = None
        self.plan = None
        self.queue = None
        self.queue_plan = None
        self.events = queue.Queue()
        self.queue_finished_callbacks = []
        self.images = checkbox_images(self, self.theme)
        self._build_vars()
        self._build()
        self.rebuild_tree()
        self.schedule_plan()

    # ------------------------------------------------------------------ vars
    def _build_vars(self):
        self.search_var = tk.StringVar()
        self.expect_var = tk.StringVar(value=EXPECT_ALL)
        self.only_selected_var = tk.BooleanVar(value=False)
        self.policy_vars = {key: tk.BooleanVar(value=(key == "radar_only")) for key in POLICIES}
        self.device_var = tk.StringVar(value=DEVICE_CUDA)
        self.mode_var = tk.StringVar(value="physics")
        self.repeat_var = tk.StringVar(value="1")
        self.seed_var = tk.StringVar(value=str(PAPER_SEED))
        self.cooldown_var = tk.StringVar(value="1")
        self.reload_var = tk.StringVar(value="1")
        self.load_map_var = tk.BooleanVar(value=True)
        self.evidence_var = tk.BooleanVar(value=False)
        self.resume_var = tk.BooleanVar(value=False)
        self.stop_tech_var = tk.BooleanVar(value=True)
        self.run_id_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.schedule_filter())
        self.expect_var.trace_add("write", lambda *_: self.rebuild_tree())
        self.only_selected_var.trace_add("write", lambda *_: self.rebuild_tree())
        for key, var in self.policy_vars.items():
            var.trace_add("write", lambda *_: self._on_system_change())
        self.device_var.trace_add("write", lambda *_: self._on_system_change())
        for var in (
            self.mode_var,
            self.repeat_var,
            self.seed_var,
            self.cooldown_var,
            self.reload_var,
            self.load_map_var,
            self.evidence_var,
            self.resume_var,
        ):
            var.trace_add("write", lambda *_: self.schedule_plan())
        self.run_id_var.trace_add("write", lambda *_: self._on_run_id_write())

    # ----------------------------------------------------------------- build
    def _build(self):
        px = self.px
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_step_bar().grid(row=0, column=0, sticky="ew", padx=px(12), pady=(px(10), px(6)))
        views = ttk.Frame(self)
        views.grid(row=1, column=0, sticky="nsew", padx=px(12), pady=(0, px(10)))
        views.columnconfigure(0, weight=1)
        views.rowconfigure(0, weight=1)

        # Steps 1-3: define the experiment.
        self.design_view = ttk.Frame(views)
        self.design_view.columnconfigure(0, weight=1)
        self.design_view.rowconfigure(1, weight=1)
        self._build_preset_bar(self.design_view).grid(row=0, column=0, sticky="ew", pady=(0, px(8)))
        columns = ttk.Frame(self.design_view)
        columns.grid(row=1, column=0, sticky="nsew")
        columns.columnconfigure(0, weight=46, uniform="design")
        columns.columnconfigure(1, weight=27, uniform="design")
        columns.columnconfigure(2, weight=27, uniform="design")
        columns.rowconfigure(0, weight=1)
        self.section1 = self._build_scenarios(columns)
        self.section1.grid(row=0, column=0, sticky="nsew", padx=(0, px(8)))
        self.section2 = self._build_system(columns)
        self.section2.grid(row=0, column=1, sticky="nsew", padx=(0, px(8)))
        self.section3 = self._build_design(columns)
        self.section3.grid(row=0, column=2, sticky="nsew")

        # Steps 4-5: review the plan, then run it.
        self.run_view = ttk.PanedWindow(views, orient="vertical")
        self.section4 = self._build_plan(self.run_view)
        self.section5 = self._build_run(self.run_view)
        self.run_view.add(self.section4, weight=46)
        self.run_view.add(self.section5, weight=54)
        for view in (self.design_view, self.run_view):
            view.grid(row=0, column=0, sticky="nsew")
        self.show_view("design")

    def _build_step_bar(self):
        px = self.px
        bar = ttk.Frame(self, style="TFrame")
        self.step_buttons = {}
        for index, (name, text) in enumerate(
            (
                ("design", "1  Kịch bản   ·   2  Hệ thống   ·   3  Thiết kế"),
                ("run", "4  Kế hoạch chạy   ·   5  Chạy"),
            )
        ):
            button = ttk.Button(bar, text=text, style="Step.TButton", command=lambda name=name: self.show_view(name))
            button.grid(row=0, column=index, padx=(0, px(4)))
            self.step_buttons[name] = button
        self.step_summary = ttk.Label(bar, text="", style="MutedBg.TLabel")
        self.step_summary.grid(row=0, column=2, sticky="e", padx=(px(10), px(10)))
        bar.columnconfigure(2, weight=1)
        self.next_button = ttk.Button(bar, text="", style="Accent.TButton", command=self._toggle_view)
        self.next_button.grid(row=0, column=3, sticky="e")
        return bar

    def show_view(self, name):
        self.current_view = name
        if name == "design":
            self.run_view.grid_remove()
            self.design_view.grid()
            self.next_button.configure(text="Xem kế hoạch & chạy  →")
        else:
            self.design_view.grid_remove()
            self.run_view.grid()
            self.next_button.configure(text="←  Quay lại thiết kế")
        for key, button in self.step_buttons.items():
            button.configure(style="StepActive.TButton" if key == name else "Step.TButton")

    def _toggle_view(self):
        self.show_view("run" if self.current_view == "design" else "design")

    def _build_preset_bar(self, master):
        px = self.px
        bar = ttk.Frame(master, style="Card.TFrame", padding=(px(10), px(6)))
        ttk.Label(bar, text="Mẫu thí nghiệm", style="CardBold.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(bar, text="một cú nhấp điền sẵn mục 1–3, vẫn sửa được", style="Muted.TLabel").grid(
            row=1, column=0, sticky="w"
        )
        buttons = ttk.Frame(bar, style="Plain.TFrame")
        buttons.grid(row=0, column=1, rowspan=2, sticky="w", padx=(px(14), px(10)))
        self.preset_buttons = {}
        for index, (key, preset) in enumerate(PRESETS.items()):
            button = ttk.Button(
                buttons,
                text=preset.label,
                style="Preset.TButton",
                command=lambda key=key: self.apply_preset(key),
            )
            button.grid(row=0, column=index, padx=(0, px(6)))
            Tooltip(button, preset.summary, self.theme)
            self.preset_buttons[key] = button
        self.preset_info = ttk.Label(bar, text="", style="Card.TLabel", justify="left")
        self.preset_info.grid(row=0, column=2, rowspan=2, sticky="ew")
        wrap_label(self.preset_info)
        self.full_repeat_button = ttk.Button(bar, text="", command=self._use_full_repeat)
        self.full_repeat_button.grid(row=0, column=3, rowspan=2, sticky="e", padx=(px(8), 0))
        self.full_repeat_button.grid_remove()
        bar.columnconfigure(2, weight=1)
        self.preset_info.configure(
            text="Chưa chọn mẫu: tự chọn kịch bản, hệ thống và thiết kế thí nghiệm bên dưới."
        )
        return bar

    # §1 ---------------------------------------------------------------------
    def _build_scenarios(self, master):
        px = self.px
        section = Section(
            master,
            self.theme,
            1,
            "Kịch bản — kiểm tra cái gì",
            "File suite → nhóm tình huống → kịch bản. Bấm ô vuông để chọn cả suite, "
            "cả nhóm hoặc từng kịch bản; bấm vào tên để xem chi tiết bên dưới.",
        )
        self.selected_label = ttk.Label(section.head_right, text="", style="CardBold.TLabel")
        self.selected_label.pack(side="right")
        body = section.body
        body.columnconfigure(0, weight=1)
        search_row = ttk.Frame(body, style="Plain.TFrame")
        search_row.grid(row=0, column=0, sticky="ew")
        search_row.columnconfigure(1, weight=1)
        ttk.Label(search_row, text="Tìm", style="Card.TLabel").grid(row=0, column=0, padx=(0, px(6)))
        self.search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew")
        Tooltip(
            self.search_entry,
            "Gõ một hoặc nhiều từ (mọi từ phải khớp): id, mô tả, loại, nhóm hoặc "
            "tên file. Ví dụ: 'ccrs 80', 'cut_in', 'holdout ghost'.",
            self.theme,
        )
        ttk.Button(search_row, text="Xóa", command=lambda: self.search_var.set("")).grid(
            row=0, column=2, padx=(px(6), 0)
        )
        filter_row = ttk.Frame(body, style="Plain.TFrame")
        filter_row.grid(row=1, column=0, sticky="ew", pady=(px(6), px(4)))
        counts = self.catalog.expectation_counts()
        for key, label in EXPECTATION_LABELS.items():
            text = "Mọi kỳ vọng" if key == EXPECT_ALL else "{} ({})".format(label, counts[key])
            radio = ttk.Radiobutton(
                filter_row,
                text=text,
                value=key,
                variable=self.expect_var,
                style="Small.TRadiobutton",
            )
            radio.pack(side="left", padx=(0, px(8)))
            if key == EXPECT_COLLISION_OK:
                Tooltip(
                    radio,
                    "Kịch bản khai báo expected_collision: true (va chạm là kết quả "
                    "được chấp nhận). Hiện có {} kịch bản như vậy trong các file "
                    "YAML.".format(counts[key]),
                    self.theme,
                )

        tree_frame = ttk.Frame(body, style="Plain.TFrame")
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        columns = ("expect", "ego", "gap", "dur")
        self.tree = ttk.Treeview(tree_frame, columns=columns, selectmode="browse", height=8)
        self.tree.heading("#0", text="Suite / nhóm / kịch bản", anchor="w")
        for column, text, width, anchor in (
            ("expect", "Kỳ vọng", 86, "w"),
            ("ego", "Ego", 44, "e"),
            ("gap", "Gap", 42, "e"),
            ("dur", "t (s)", 44, "e"),
        ):
            self.tree.heading(column, text=text, anchor=anchor)
            self.tree.column(column, width=px(width), minwidth=px(40), stretch=False, anchor=anchor)
        self.tree.column("#0", width=px(230), minwidth=px(160), stretch=True)
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        c = self.theme.colors
        self.tree.tag_configure("suite", font=self.theme.font("body_bold"))
        self.tree.tag_configure("group", foreground=c["muted"])
        self.tree.tag_configure("nobrake", foreground=c["text"])
        self.tree.bind("<Button-1>", self._on_tree_click, add="+")
        self.tree.bind("<Double-Button-1>", self._on_tree_double, add="+")
        self.tree.bind("<space>", self._on_tree_space)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.show_detail())

        actions = ttk.Frame(body, style="Plain.TFrame")
        actions.grid(row=3, column=0, sticky="ew", pady=(px(6), px(6)))
        ttk.Button(actions, text="Chọn tất cả đang hiện", command=self.select_visible).pack(side="left")
        ttk.Button(actions, text="Bỏ chọn tất cả", command=self.clear_selection).pack(
            side="left", padx=(px(6), 0)
        )
        ttk.Checkbutton(
            actions,
            text="Chỉ hiện đã chọn",
            variable=self.only_selected_var,
            style="Card.TCheckbutton",
        ).pack(side="left", padx=(px(10), 0))
        ttk.Button(actions, text="Thu gọn", command=lambda: self._expand_all(False)).pack(side="right")
        self.detail = readonly_text(body, self.theme, height=9, mono=False)
        self.detail.configure(tabs=(px(150),), wrap="word", spacing1=px(1))
        self.detail.tag_configure("title", font=self.theme.font("body_bold"), spacing3=px(3))
        self.detail.tag_configure("label", foreground=c["muted"])
        self.detail.tag_configure("muted", foreground=c["muted"])
        self.detail.tag_configure("brake", foreground=c["accent"], font=self.theme.font("small_bold"))
        self.detail.grid(row=4, column=0, sticky="ew")
        body.rowconfigure(2, weight=1)
        return section

    # §2 ---------------------------------------------------------------------
    def _build_system(self, master):
        px = self.px
        section = Section(
            master,
            self.theme,
            2,
            "Hệ thống được kiểm tra",
            "Chọn một hoặc nhiều chính sách phanh. Chọn nhiều → cùng kịch bản chạy "
            "cho từng chính sách để so sánh cặp ở màn Kết quả.",
            scroll=True,
        )
        body = section.body
        body.columnconfigure(0, weight=1)
        row = 0
        self.policy_config_labels = {}
        for key, item in POLICIES.items():
            ttk.Checkbutton(
                body, text=item.label, variable=self.policy_vars[key], style="Bold.TCheckbutton"
            ).grid(row=row, column=0, sticky="w", pady=(px(4) if row else 0, 0))
            explanation = ttk.Label(body, text=item.explanation, style="Muted.TLabel", justify="left")
            explanation.grid(row=row + 1, column=0, sticky="ew", padx=(px(24), 0))
            wrap_label(explanation)
            config = ttk.Label(body, text="", style="Mono.TLabel", foreground=self.theme.colors["accent"])
            config.grid(row=row + 2, column=0, sticky="ew", padx=(px(24), 0), pady=(px(1), 0))
            wrap_label(config)
            Tooltip(
                config,
                "Runner: {}\nSensor config được chọn theo thiết bị (chỉ đọc, không "
                "sửa).".format(item.runner),
                self.theme,
            )
            self.policy_config_labels[key] = config
            row += 3
        ttk.Separator(body).grid(row=row, column=0, sticky="ew", pady=px(8))
        row += 1
        ttk.Label(body, text="Thiết bị chạy YOLO (camera)", style="CardBold.TLabel").grid(
            row=row, column=0, sticky="w"
        )
        row += 1
        devices = ttk.Frame(body, style="Plain.TFrame")
        devices.grid(row=row, column=0, sticky="w")
        for key, label in DEVICE_LABELS.items():
            ttk.Radiobutton(
                devices, text=label, value=key, variable=self.device_var, style="Card.TRadiobutton"
            ).pack(anchor="w")
        row += 1
        hint = ttk.Label(body, text=DEVICE_HINT, style="Muted.TLabel", justify="left")
        hint.grid(row=row, column=0, sticky="ew", padx=(px(24), 0))
        wrap_label(hint)
        row += 1
        ttk.Separator(body).grid(row=row, column=0, sticky="ew", pady=px(8))
        row += 1
        ttk.Label(body, text="Chế độ điều khiển xe", style="CardBold.TLabel").grid(
            row=row, column=0, sticky="w"
        )
        row += 1
        modes = ttk.Frame(body, style="Plain.TFrame")
        modes.grid(row=row, column=0, sticky="w")
        for key, label in CONTROL_MODES.items():
            ttk.Radiobutton(
                modes, text=label, value=key, variable=self.mode_var, style="Card.TRadiobutton"
            ).pack(side="left", padx=(0, px(8)))
        row += 1
        hint = ttk.Label(body, text=CONTROL_MODE_HINT, style="Muted.TLabel", justify="left")
        hint.grid(row=row, column=0, sticky="ew", padx=(px(24), 0))
        wrap_label(hint)
        self._update_policy_labels()
        return section

    # §3 ---------------------------------------------------------------------
    def _build_design(self, master):
        px = self.px
        section = Section(
            master,
            self.theme,
            3,
            "Thiết kế thí nghiệm",
            "Các tham số truyền cho runner. Rê chuột lên ô nhập để xem giải thích đầy đủ.",
            scroll=True,
        )
        body = section.body
        body.columnconfigure(1, weight=1)
        self._design_row = 0

        def field(label, widget_factory, hint, tooltip=None):
            row = self._design_row
            ttk.Label(body, text=label, style="Card.TLabel").grid(
                row=row, column=0, sticky="w", pady=(px(5), 0), padx=(0, px(8))
            )
            widget = widget_factory(body)
            widget.grid(row=row, column=1, sticky="w", pady=(px(5), 0))
            note = ttk.Label(body, text=hint, style="Muted.TLabel", justify="left")
            note.grid(row=row + 1, column=0, columnspan=2, sticky="ew")
            wrap_label(note)
            if tooltip:
                Tooltip(widget, tooltip, self.theme)
            self._design_row += 2
            return widget

        def check(label, variable, hint, tooltip=None):
            row = self._design_row
            widget = ttk.Checkbutton(body, text=label, variable=variable, style="Card.TCheckbutton")
            widget.grid(row=row, column=0, columnspan=2, sticky="w", pady=(px(5), 0))
            note = ttk.Label(body, text=hint, style="Muted.TLabel", justify="left")
            note.grid(row=row + 1, column=0, columnspan=2, sticky="ew", padx=(px(24), 0))
            wrap_label(note)
            if tooltip:
                Tooltip(widget, tooltip, self.theme)
            self._design_row += 2
            return widget

        field(
            "Số lần lặp (--repeat)",
            lambda parent: ttk.Spinbox(parent, from_=1, to=50, width=5, textvariable=self.repeat_var),
            "Lặp lại để đo tính nhất quán, không phải mẫu độc lập. Giao thức paper: 5.",
            "Mỗi kịch bản chạy N lần trong cùng thư mục log. Thống kê theo điều "
            "kiện có tên (named condition): một điều kiện PASS khi mọi lần lặp PASS.",
        )
        field(
            "Seed (--seed)",
            lambda parent: ttk.Entry(parent, width=8, textvariable=self.seed_var),
            "Ghi vào metadata và áp dụng cho Python/NumPy. Paper dùng 2026.",
        )
        field(
            "Nghỉ giữa kịch bản, s",
            lambda parent: ttk.Spinbox(
                parent, from_=0, to=30, increment=0.5, width=5, textvariable=self.cooldown_var
            ),
            "--scenario-cooldown-s: tick thêm để CARLA dọn actor/sensor (mặc định 1).",
        )
        field(
            "Reload world mỗi N",
            lambda parent: ttk.Spinbox(parent, from_=0, to=100, width=5, textvariable=self.reload_var),
            "--reload-world-every: 1 = ổn định nhất với CARLA 0.9.11 (mặc định); "
            "0 = không reload, nhanh hơn nhưng dễ crash ở batch dài.",
        )
        check(
            "Tự load map của suite (--load-map)",
            self.load_map_var,
            "Nếu CARLA đang ở map khác (Town04), runner tự load; tắt thì runner báo lỗi.",
        )
        check(
            "Ghi video bằng chứng (--record-evidence)",
            self.evidence_var,
            "Video chase camera + ảnh tại các mốc AEB. Chậm hơn đáng kể.",
        )
        check(
            "Tiếp tục run-id có sẵn (--resume)",
            self.resume_var,
            "Sau khi hàng đợi bị ngắt: bỏ qua scenario-run đã xong. Cần working "
            "tree sạch, cùng commit, config không đổi.",
        )
        check(
            "Dừng hàng đợi khi gặp lỗi kỹ thuật",
            self.stop_tech_var,
            "CARLA crash / thiếu CUDA làm các lệnh sau vô nghĩa. FAIL thuật toán "
            "là bằng chứng và KHÔNG dừng hàng đợi.",
        )
        row = self._design_row
        ttk.Label(body, text="Run-id (tên thư mục log)", style="Card.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(px(8), 0)
        )
        entry_row = ttk.Frame(body, style="Plain.TFrame")
        entry_row.grid(row=row + 1, column=0, columnspan=2, sticky="ew")
        entry_row.columnconfigure(0, weight=1)
        self.run_id_entry = ttk.Entry(entry_row, textvariable=self.run_id_var, font=self.theme.font("mono"))
        self.run_id_entry.grid(row=0, column=0, sticky="ew")
        regenerate = ttk.Button(entry_row, text="Tạo lại", command=self.regenerate_run_id)
        regenerate.grid(row=0, column=1, padx=(px(6), 0))
        Tooltip(regenerate, "Tạo lại run-id theo mẫu thí nghiệm và thời điểm hiện tại.", self.theme)
        note = ttk.Label(
            body,
            text="{policy} → radar_only / hard_gate_cuda / fallback_cuda; {suite} → "
            "tên file suite. Tự sinh theo lựa chọn, sửa được.",
            style="Muted.TLabel",
            justify="left",
        )
        note.grid(row=row + 2, column=0, columnspan=2, sticky="ew")
        wrap_label(note)
        return section

    # §4 ---------------------------------------------------------------------
    def _build_plan(self, master):
        px = self.px
        section = Section(
            master,
            self.theme,
            4,
            "Kế hoạch chạy",
            "Mỗi dòng là một lệnh = một thư mục log. Kiểm tra lệnh, số lượt chạy và "
            "thời gian ước lượng trước khi bấm Chạy.",
        )
        how = ttk.Label(section.head_right, text="Cách dựng lệnh ⓘ", style="Muted.TLabel", cursor="question_arrow")
        how.pack(side="right", padx=(self.px(12), 0))
        Tooltip(how, PLAN_NOTE, self.theme, delay_ms=150)
        self.plan_total = ttk.Label(section.head_right, text="", style="CardBold.TLabel")
        self.plan_total.pack(side="right")
        body = section.body
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        frame = ttk.Frame(body, style="Plain.TFrame")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        columns = ("no", "system", "suite", "chosen", "mode", "runs", "eta", "run_id", "status")
        self.plan_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse", height=4)
        for column, text, width, stretch, anchor in (
            ("no", "#", 30, False, "e"),
            ("system", "Hệ thống", 230, False, "w"),
            ("suite", "File kịch bản", 170, True, "w"),
            ("chosen", "Chọn", 90, False, "w"),
            ("mode", "Chế độ", 84, False, "w"),
            ("runs", "Lượt", 50, False, "e"),
            ("eta", "Ước lượng", 86, False, "w"),
            ("run_id", "Run-id → thư mục log", 230, True, "w"),
            ("status", "Trạng thái", 130, False, "w"),
        ):
            self.plan_tree.heading(column, text=text, anchor=anchor)
            self.plan_tree.column(column, width=px(width), minwidth=px(30), stretch=stretch, anchor=anchor)
        c = self.theme.colors
        self.plan_tree.tag_configure("pending", foreground=c["text"])
        self.plan_tree.tag_configure("running", background=c["accent_soft"])
        self.plan_tree.tag_configure("pass", background=c["pass_bg"], foreground=c["pass"])
        self.plan_tree.tag_configure("fail", background=c["fail_bg"], foreground=c["fail"])
        self.plan_tree.tag_configure("tech", background=c["tech_bg"], foreground=c["tech"])
        self.plan_tree.tag_configure("stopped", foreground=c["muted"])
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.plan_tree.yview)
        self.plan_tree.configure(yscrollcommand=scroll.set)
        self.plan_tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.plan_tree.bind("<<TreeviewSelect>>", lambda _e: self._show_command())
        self.plan_messages = readonly_text(body, self.theme, height=2, mono=False)
        self.plan_messages.tag_configure("error", foreground=c["fail"], font=self.theme.font("small_bold"))
        self.plan_messages.tag_configure("warn", foreground=c["warn"])
        self.plan_messages.tag_configure("ok", foreground=c["pass"])
        self.plan_messages.grid(row=1, column=0, sticky="ew", pady=(px(6), 0))
        command_row = ttk.Frame(body, style="Plain.TFrame")
        command_row.grid(row=2, column=0, sticky="ew", pady=(px(6), 0))
        command_row.columnconfigure(0, weight=1)
        self.command_preview = readonly_text(command_row, self.theme, height=3)
        self.command_preview.grid(row=0, column=0, rowspan=2, sticky="nsew")
        ttk.Button(command_row, text="Sao chép lệnh", command=self._copy_command).grid(
            row=0, column=1, sticky="new", padx=(px(6), 0)
        )
        ttk.Button(command_row, text="Sao chép cả kế hoạch", command=self._copy_plan).grid(
            row=1, column=1, sticky="new", padx=(px(6), 0), pady=(px(4), 0)
        )
        return section

    # §5 ---------------------------------------------------------------------
    def _build_run(self, master):
        px = self.px
        section = Section(
            master,
            self.theme,
            5,
            "Chạy",
            "Hàng đợi chạy tuần tự từng lệnh. Exit 1 = có FAIL thuật toán (là bằng "
            "chứng). Exit 3 = HARD-STOP kỹ thuật (thiếu CUDA) — không phải FAIL.",
        )
        self.run_pill = Pill(section.head_right, self.theme, "Sẵn sàng", "neutral")
        self.run_pill.pack(side="right")
        body = section.body
        body.columnconfigure(0, weight=1)
        body.rowconfigure(3, weight=1)
        buttons = ttk.Frame(body, style="Plain.TFrame")
        buttons.grid(row=0, column=0, sticky="ew")
        self.run_button = ttk.Button(buttons, text="▶  Chạy kế hoạch", style="Accent.TButton", command=self.start_queue)
        self.run_button.pack(side="left")
        self.stop_current_button = ttk.Button(
            buttons, text="Dừng lệnh hiện tại", style="Danger.TButton", command=self.stop_current
        )
        self.stop_current_button.pack(side="left", padx=(px(6), 0))
        self.stop_queue_button = ttk.Button(
            buttons, text="Dừng hàng đợi", style="Danger.TButton", command=self.stop_queue
        )
        self.stop_queue_button.pack(side="left", padx=(px(6), 0))
        self.results_button = ttk.Button(buttons, text="Xem kết quả →", command=self.open_results)
        self.results_button.pack(side="right")
        Tooltip(
            self.stop_current_button,
            "Gửi SIGINT để runner tự dọn actor và trả CARLA về chế độ bất đồng bộ; "
            "nếu không dừng sau 10 s thì SIGTERM, rồi SIGKILL.",
            self.theme,
        )
        self.progress = ttk.Progressbar(body, mode="determinate", maximum=1.0)
        self.progress.grid(row=1, column=0, sticky="ew", pady=(px(8), px(4)))
        self.progress_label = ttk.Label(body, text="Chưa chạy.", style="Card.TLabel")
        self.progress_label.grid(row=2, column=0, sticky="ew")
        log_frame = ttk.Frame(body, style="Plain.TFrame")
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(px(6), 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log = readonly_text(log_frame, self.theme, height=6, dark=True)
        self.log.configure(wrap="none")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=log_scroll.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log.tag_configure("pass", foreground="#4ADE80")
        self.log.tag_configure("fail", foreground="#F87171")
        self.log.tag_configure("tech", foreground="#C4B5FD", font=self.theme.font("small_bold"))
        self.log.tag_configure("head", foreground="#93C5FD")
        self.log.tag_configure("muted", foreground="#94A3B8")
        self._update_run_buttons()
        return section

    # ------------------------------------------------------------- tree view
    def schedule_filter(self):
        if self._filter_after is not None:
            self.after_cancel(self._filter_after)
        self._filter_after = self.after(180, self.rebuild_tree)

    def rebuild_tree(self):
        self._filter_after = None
        focus = self.tree.focus()
        open_suites = set(
            iid for iid in self.tree.get_children("") if self.tree.item(iid, "open")
        )
        searching = bool(self.search_var.get().strip()) or self.expect_var.get() != EXPECT_ALL
        only = self.selected if self.only_selected_var.get() else None
        visible = self.catalog.filter(self.search_var.get(), self.expect_var.get(), only)
        self.tree.delete(*self.tree.get_children(""))
        self.visible = visible
        for rel, scenarios in visible.items():
            suite = self.catalog.suite(rel)
            sid = "S|" + rel
            tags = "  ·  ".join(TAG_LABELS[tag] for tag in suite.tags)
            text = "{}  ({})".format(suite.title, len(scenarios))
            if tags:
                text += "   [{}]".format(tags)
            self.tree.insert(
                "",
                "end",
                iid=sid,
                text=" " + text,
                open=searching or only is not None or sid in open_suites,
                tags=("suite",),
                values=("", "", "", ""),
            )
            for group, members in suite.groups(scenarios):
                gid = "G|{}|{}".format(rel, group)
                self.tree.insert(
                    sid,
                    "end",
                    iid=gid,
                    text=" {}  ({})".format(group_label(group), len(members)),
                    open=True,
                    tags=("group",),
                    values=("", "", "", ""),
                )
                for scenario in members:
                    expect = "Phanh" if scenario.expected_brake else "Không phanh"
                    if scenario.expected_collision:
                        expect += " · VC ok"
                    self.tree.insert(
                        gid,
                        "end",
                        iid="C|{}|{}".format(rel, scenario.id),
                        text=" " + scenario.id,
                        values=(
                            expect,
                            _speed(scenario.ego_speed_kph),
                            _speed(scenario.initial_gap_m),
                            _speed(scenario.duration_s),
                        ),
                    )
        self.refresh_marks()
        if focus and self.tree.exists(focus):
            self.tree.focus(focus)
            self.tree.selection_set(focus)
            self.tree.see(focus)
        elif not visible:
            set_text(self.detail, "Không có kịch bản nào khớp bộ lọc.")

    def _keys_under(self, iid):
        kind, rest = iid.split("|", 1)
        if kind == "C":
            rel, scenario_id = rest.rsplit("|", 1)
            return [(rel, scenario_id)]
        if kind == "G":
            rel, group = rest.rsplit("|", 1)
            return [s.key for s in self.visible.get(rel, []) if s.group == group]
        return [s.key for s in self.visible.get(rest, [])]

    def _state(self, keys):
        chosen = sum(1 for key in keys if key in self.selected)
        if chosen == 0:
            return STATE_UNCHECKED
        if chosen == len(keys):
            return STATE_CHECKED
        return STATE_PARTIAL

    def refresh_marks(self):
        for sid in self.tree.get_children(""):
            self.tree.item(sid, image=self.images[self._state(self._keys_under(sid))])
            for gid in self.tree.get_children(sid):
                self.tree.item(gid, image=self.images[self._state(self._keys_under(gid))])
                for cid in self.tree.get_children(gid):
                    self.tree.item(cid, image=self.images[self._state(self._keys_under(cid))])
        suites = len(set(rel for rel, _ in self.selected))
        self.selected_label.configure(
            text="Đã chọn: {} kịch bản{}".format(
                len(self.selected), " · {} file".format(suites) if suites > 1 else ""
            )
        )

    def toggle(self, iid):
        keys = self._keys_under(iid)
        if not keys:
            return
        if self._state(keys) == STATE_CHECKED:
            self.selected.difference_update(keys)
        else:
            self.selected.update(keys)
        self._on_selection_change()

    def _on_selection_change(self):
        self.preset_key = None
        self._update_preset_info()
        if self.only_selected_var.get():
            self.rebuild_tree()
        else:
            self.refresh_marks()
        self.regenerate_run_id(only_if_auto=True)
        self.schedule_plan()

    def _on_tree_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return None
        element = str(self.tree.identify_element(event.x, event.y))
        if "image" in element:
            self.tree.focus(iid)
            self.tree.selection_set(iid)
            self.toggle(iid)
            return "break"
        return None

    def _on_tree_double(self, event):
        iid = self.tree.identify_row(event.y)
        if iid and iid.startswith("C|"):
            self.toggle(iid)
            return "break"
        return None

    def _on_tree_space(self, _event):
        iid = self.tree.focus()
        if iid:
            self.toggle(iid)
        return "break"

    def select_visible(self):
        for scenarios in self.visible.values():
            self.selected.update(s.key for s in scenarios)
        self._on_selection_change()

    def clear_selection(self):
        self.selected.clear()
        self._on_selection_change()

    def _expand_all(self, expand):
        for sid in self.tree.get_children(""):
            self.tree.item(sid, open=expand)

    def set_selection(self, keys, expand=True):
        self.selected = set(tuple(key) for key in keys)
        self.search_var.set("")
        self.expect_var.set(EXPECT_ALL)
        self.only_selected_var.set(False)
        self.rebuild_tree()
        rels = set(rel for rel, _ in self.selected)
        first = None
        for sid in self.tree.get_children(""):
            is_selected = sid[2:] in rels
            self.tree.item(sid, open=bool(expand and is_selected))
            if is_selected and first is None:
                first = sid
        if first:
            self.tree.see(first)
            self.tree.focus(first)
            self.tree.selection_set(first)
        self.refresh_marks()

    # --------------------------------------------------------------- detail
    def show_detail(self):
        iid = self.tree.focus()
        if not iid:
            return
        kind, rest = iid.split("|", 1)
        widget = self.detail
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        if kind == "C":
            rel, scenario_id = rest.rsplit("|", 1)
            scenario = self.catalog.scenario((rel, scenario_id))
            widget.insert("end", scenario.id, "title")
            widget.insert("end", "   " + expectation_text(scenario) + "\n", "brake")
            if scenario.description:
                widget.insert("end", scenario.description + "\n")
            for label, value in scenario_facts(scenario):
                widget.insert("end", label, "label")
                widget.insert("end", "\t{}\n".format(value))
        elif kind == "G":
            rel, group = rest.rsplit("|", 1)
            members = [s for s in self.visible.get(rel, []) if s.group == group]
            brake = sum(1 for s in members if s.expected_brake)
            widget.insert("end", group_label(group), "title")
            widget.insert("end", "\n")
            widget.insert("end", "File", "label")
            widget.insert("end", "\t{}\n".format(rel))
            widget.insert("end", "Số kịch bản", "label")
            widget.insert(
                "end",
                "\t{} ({} phải phanh, {} không được phanh)\n".format(
                    len(members), brake, len(members) - brake
                ),
            )
            ids = ", ".join(s.id for s in members[:12])
            if len(members) > 12:
                ids += ", …"
            widget.insert("end", "Gồm", "label")
            widget.insert("end", "\t{}\n".format(ids))
        else:
            suite = self.catalog.suite(rest)
            brake = sum(1 for s in suite.scenarios if s.expected_brake)
            widget.insert("end", suite.title, "title")
            widget.insert("end", "\n")
            if suite.summary:
                widget.insert("end", suite.summary + "\n")
            widget.insert("end", "File", "label")
            widget.insert("end", "\t{}\n".format(suite.rel))
            widget.insert("end", "Số kịch bản", "label")
            widget.insert(
                "end",
                "\t{} ({} phải phanh, {} không được phanh)\n".format(
                    len(suite.scenarios), brake, len(suite.scenarios) - brake
                ),
            )
            widget.insert("end", "Nhóm", "label")
            widget.insert(
                "end",
                "\t{}\n".format(
                    "; ".join(
                        "{} ({})".format(group_label(g), len(m)) for g, m in suite.groups()
                    )
                ),
            )
            widget.insert("end", "Chế độ mặc định", "label")
            widget.insert("end", "\t{} · map {}\n".format(suite.default_control_mode, suite.map))
            if suite.header and suite.header != suite.summary:
                widget.insert("end", "Ghi chú trong file", "label")
                widget.insert("end", "\t{}\n".format(suite.header), "muted")
        widget.configure(state="disabled")

    # ------------------------------------------------------------ section 2
    def _on_system_change(self):
        if self._suspend_traces:
            return
        self.preset_key = None
        self._update_preset_info()
        self._update_policy_labels()
        self.regenerate_run_id(only_if_auto=True)
        self.schedule_plan()

    def _update_policy_labels(self):
        device = self.device_var.get()
        for key, label in self.policy_config_labels.items():
            label.configure(text=sensor_config_for(key, device))

    # ------------------------------------------------------------- presets
    def apply_preset(self, key):
        preset = PRESETS[key]
        self._suspend_traces = True
        try:
            for policy_key, var in self.policy_vars.items():
                var.set(policy_key in preset.policies)
            self.device_var.set(preset.device)
            self.mode_var.set(preset.control_mode)
            self.repeat_var.set(str(preset.repeat))
            self.seed_var.set(str(PAPER_SEED))
            self.cooldown_var.set("1")
            self.reload_var.set("1")
            self.load_map_var.set(True)
            self.evidence_var.set(False)
            self.resume_var.set(False)
        finally:
            self._suspend_traces = False
        keys = []
        for rel in preset.suites:
            suite = self.catalog.find_suite(rel)
            keys.extend(s.key for s in suite.scenarios)
        self.set_selection(keys)
        self._update_policy_labels()
        self.preset_key = key
        self.run_id_edited = False
        self.regenerate_run_id()
        self._update_preset_info()
        self.schedule_plan()

    def _preset_label(self):
        return self.preset_key if self.preset_key else "custom"

    def _update_preset_info(self):
        for key, button in self.preset_buttons.items():
            button.state(["pressed"] if key == self.preset_key else ["!pressed"])
        if not self.preset_key:
            self.preset_info.configure(
                text="Thí nghiệm tùy chỉnh (custom): kịch bản/hệ thống đã khác mẫu."
            )
            self.full_repeat_button.grid_remove()
            return
        preset = PRESETS[self.preset_key]
        self.preset_info.configure(text="{}: {}".format(preset.label, preset.summary))
        self._update_full_repeat_button()

    def _update_full_repeat_button(self):
        if not self.preset_key:
            self.full_repeat_button.grid_remove()
            return
        preset = PRESETS[self.preset_key]
        try:
            repeat = int(self.repeat_var.get())
        except ValueError:
            repeat = 0
        if preset.full_repeat <= 1 or repeat == preset.full_repeat:
            self.full_repeat_button.grid_remove()
            return
        options = self.current_options()
        if options is None:
            self.full_repeat_button.grid_remove()
            return
        options.repeat = preset.full_repeat
        plan = build_plan(
            self.catalog,
            self.selected,
            self.selected_policies(),
            options,
            "probe_{policy}_{suite}",
            self.app.logs_root,
            path_exists=lambda _p: False,
        )
        self.full_repeat_button.configure(
            text="Dùng {} lần lặp (giao thức paper, {})".format(
                preset.full_repeat, format_duration(plan.total_estimate_s)
            )
        )
        self.full_repeat_button.grid()

    def _use_full_repeat(self):
        if self.preset_key:
            self.repeat_var.set(str(PRESETS[self.preset_key].full_repeat))

    # -------------------------------------------------------------- run-id
    def _on_run_id_write(self):
        if not self._suspend_traces:
            self.run_id_edited = True
        self.schedule_plan()

    def regenerate_run_id(self, only_if_auto=False):
        if only_if_auto and self.run_id_edited:
            return
        multi_suite = len(set(rel for rel, _ in self.selected)) > 1
        self._set_run_id(default_run_id_template(self._preset_label(), datetime.now(), multi_suite))
        self.run_id_edited = False
        self.schedule_plan()

    def _set_run_id(self, value):
        self._suspend_traces = True
        try:
            self.run_id_var.set(value)
        finally:
            self._suspend_traces = False

    # ---------------------------------------------------------------- plan
    def selected_policies(self):
        return [key for key, var in self.policy_vars.items() if var.get()]

    def current_options(self):
        try:
            return ExperimentOptions(
                repeat=int(self.repeat_var.get()),
                seed=int(self.seed_var.get()),
                cooldown_s=float(self.cooldown_var.get()),
                reload_every=int(self.reload_var.get()),
                load_map=bool(self.load_map_var.get()),
                record_evidence=bool(self.evidence_var.get()),
                resume=bool(self.resume_var.get()),
                control_mode=self.mode_var.get(),
                device=self.device_var.get(),
                port=int(self.app.port),
            )
        except (ValueError, tk.TclError):
            return None

    def schedule_plan(self):
        if self._plan_after is not None:
            try:
                self.after_cancel(self._plan_after)
            except tk.TclError:
                pass
        self._plan_after = self.after(150, self.refresh_plan)

    def refresh_plan(self):
        self._plan_after = None
        if self.queue is not None and self.queue.running:
            return
        if self.queue_plan is not None:
            # Leaving the finished queue's view: a fresh timestamp avoids
            # colliding with the run directories it just created.
            self.queue_plan = None
            if not self.run_id_edited:
                self._set_run_id(
                    default_run_id_template(
                        self._preset_label(),
                        datetime.now(),
                        len(set(rel for rel, _ in self.selected)) > 1,
                    )
                )
        options = self.current_options()
        if options is None:
            self.plan = None
            self._render_plan(None, ["Tham số ở mục 3 không hợp lệ (cần số)."])
            return
        self.plan = build_plan(
            self.catalog,
            self.selected,
            self.selected_policies(),
            options,
            self.run_id_var.get(),
            self.app.logs_root,
        )
        self._render_plan(self.plan)
        self._update_full_repeat_button()

    def _render_plan(self, plan, extra_errors=()):
        tree = self.plan_tree
        tree.delete(*tree.get_children(""))
        errors = list(extra_errors)
        warnings = []
        if plan is not None:
            errors.extend(plan.errors)
            warnings.extend(plan.warnings)
            for command in plan.commands:
                tree.insert(
                    "",
                    "end",
                    iid=str(command.index - 1),
                    values=self._plan_row(command, OUTCOME_PENDING),
                    tags=("pending",),
                )
            if plan.commands:
                tree.selection_set("0")
                tree.focus("0")
            self.plan_total.configure(
                text="{} lệnh · {} lượt chạy · {} (ước lượng)".format(
                    len(plan.commands), plan.total_runs, format_duration(plan.total_estimate_s)
                )
                if plan.commands
                else ""
            )
        else:
            self.plan_total.configure(text="")
        if errors:
            summary = "✖ " + errors[0]
        elif plan is not None and plan.commands:
            summary = "Kế hoạch: {} lệnh · {} lượt chạy · {}".format(
                len(plan.commands), plan.total_runs, format_duration(plan.total_estimate_s)
            )
            if warnings:
                summary += " · ⚠ {} lưu ý".format(len(warnings))
        else:
            summary = ""
        self.step_summary.configure(text=summary)
        widget = self.plan_messages
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        for message in errors:
            widget.insert("end", "✖ " + message + "\n", "error")
        for message in warnings:
            widget.insert("end", "⚠ " + message + "\n", "warn")
        if plan is not None and plan.ok and not warnings:
            widget.insert(
                "end",
                "✔ Kế hoạch hợp lệ. Log ghi vào {}/<run-id>/".format(self.app.logs_root),
                "ok",
            )
        widget.configure(state="disabled")
        self._show_command()
        self._update_run_buttons()

    def _plan_row(self, command, outcome, progress=None):
        system = command.policy_label
        if command.device:
            system += " · " + command.device.upper()
        status = OUTCOME_LABELS[outcome]
        if progress:
            status = progress
        return (
            command.index,
            system,
            command.suite_rel.rsplit("/", 1)[-1],
            command.selection_text,
            command.control_mode,
            command.scenario_runs,
            format_duration(command.estimate_s),
            command.run_id + (" (đã có)" if command.log_dir_exists else ""),
            status,
        )

    def _active_plan(self):
        return self.queue_plan if self.queue_plan is not None else self.plan

    def _show_command(self):
        plan = self._active_plan()
        selection = self.plan_tree.selection()
        if not plan or not plan.commands or not selection:
            set_text(self.command_preview, "Chưa có lệnh nào — chọn kịch bản (mục 1) và hệ thống (mục 2).")
            return
        command = plan.commands[int(selection[0])]
        set_text(
            self.command_preview,
            "# cwd: {}   → log: {}\n{}".format(AEB_ROOT, command.log_dir, command.text()),
        )

    def _copy_command(self):
        plan = self._active_plan()
        selection = self.plan_tree.selection()
        if plan and plan.commands and selection:
            self.app.copy_to_clipboard(plan.commands[int(selection[0])].text(with_cwd=True))

    def _copy_plan(self):
        plan = self._active_plan()
        if plan and plan.commands:
            self.app.copy_to_clipboard(plan.script_text())

    # ----------------------------------------------------------------- run
    def _update_run_buttons(self):
        running = self.queue is not None and self.queue.running
        can_run = (not running) and self.plan is not None and self.plan.ok
        self.run_button.state(["!disabled"] if can_run else ["disabled"])
        self.stop_current_button.state(["!disabled"] if running else ["disabled"])
        self.stop_queue_button.state(["!disabled"] if running else ["disabled"])

    def start_queue(self):
        if self.queue is not None and self.queue.running:
            return False
        self.refresh_plan()
        plan = self.plan
        if plan is None or not plan.ok:
            return False
        if not self.app.carla_online():
            self.append_log(
                "CARLA chưa chạy ở {}:{} — bật CARLA trước (nút ở góc trên phải).\n".format(
                    self.app.host, self.app.port
                ),
                "tech",
            )
            self.run_pill.set("CARLA offline", "offline")
            return False
        self.queue_plan = plan
        self.queue_state = {}
        self._render_plan(plan)
        self.queue = CommandQueue(
            plan.commands,
            emit=lambda event, payload: self.events.put((event, payload)),
            stop_on_technical=bool(self.stop_tech_var.get()),
        )
        self.total_runs = max(1, plan.total_runs)
        self.done_before = 0
        self.progress.configure(value=0.0)
        self.append_log(
            "=== Bắt đầu hàng đợi: {} lệnh, {} lượt chạy, {} ===\n".format(
                len(plan.commands), plan.total_runs, format_duration(plan.total_estimate_s)
            ),
            "head",
        )
        self.run_pill.set("Đang chạy", "info")
        self.show_view("run")
        self.queue.start()
        self._update_run_buttons()
        self.after(100, self._drain_events)
        return True

    def stop_current(self):
        if self.queue is not None and self.queue.running:
            self.append_log("--- Yêu cầu dừng lệnh hiện tại (SIGINT) ---\n", "tech")
            self.queue.stop_current()

    def stop_queue(self):
        if self.queue is not None and self.queue.running:
            self.append_log("--- Yêu cầu dừng cả hàng đợi ---\n", "tech")
            self.queue.stop_queue()

    def append_log(self, text, tag=None):
        widget = self.log
        widget.configure(state="normal")
        widget.insert("end", text, tag or ())
        lines = int(widget.index("end-1c").split(".")[0])
        if lines > 6000:
            widget.delete("1.0", "{}.0".format(lines - 5000))
        widget.see("end")
        widget.configure(state="disabled")

    def _drain_events(self):
        try:
            while True:
                event, payload = self.events.get_nowait()
                self._handle_event(event, payload)
        except queue.Empty:
            pass
        if self.queue is not None and (self.queue.running or not self.events.empty()):
            self.after(120, self._drain_events)
        else:
            self._update_run_buttons()

    def _handle_event(self, event, payload):
        plan = self.queue_plan
        if event == "start":
            (index,) = payload
            command = plan.commands[index]
            self.append_log(
                "\n▶ Lệnh {}/{}: {} · {}\n$ {}\n".format(
                    index + 1, len(plan.commands), command.policy_label, command.suite_rel, command.text()
                ),
                "head",
            )
            self.plan_tree.item(str(index), values=self._plan_row(command, OUTCOME_RUNNING), tags=("running",))
            self.plan_tree.see(str(index))
            self.progress_label.configure(text="Lệnh {}/{} đang khởi động…".format(index + 1, len(plan.commands)))
        elif event == "line":
            index, text = payload
            tag = None
            stripped = text.strip()
            if stripped.startswith("PASS"):
                tag = "pass"
            elif stripped.startswith("FAIL"):
                tag = "fail"
            elif "HARD-STOP" in text or text.startswith("Traceback") or "Error" in text:
                tag = "tech"
            elif text.startswith("["):
                tag = "head"
            self.append_log(text + "\n", tag)
        elif event == "progress":
            index, state = payload
            command = plan.commands[index]
            done = self.done_before + state.done
            self.progress.configure(value=min(1.0, done / float(self.total_runs)))
            current = ""
            if state.current_scenario:
                current = " · {} (lần {}/{})".format(state.current_scenario, state.current_run, state.repeat)
            self.progress_label.configure(
                text="Lệnh {}/{}{} · {}/{} lượt · PASS {} · FAIL {}".format(
                    index + 1,
                    len(plan.commands),
                    current,
                    done,
                    self.total_runs,
                    state.passed,
                    state.failed,
                )
            )
            self.step_summary.configure(
                text="Đang chạy: lệnh {}/{} · {}/{} lượt".format(
                    index + 1, len(plan.commands), done, self.total_runs
                )
            )
            progress = "Đang chạy {}/{}".format(state.done, command.scenario_runs)
            self.plan_tree.item(str(index), values=self._plan_row(command, OUTCOME_RUNNING, progress))
        elif event == "end":
            index, outcome, returncode, state = payload
            command = plan.commands[index]
            self.done_before += max(state.done, 0)
            label = OUTCOME_LABELS[outcome]
            if outcome == OUTCOME_ALGO_FAIL:
                label = "FAIL {}/{} (exit 1)".format(state.failed, state.done)
            elif outcome == OUTCOME_ALL_PASS:
                label = "PASS {}/{}".format(state.passed, state.done)
            elif outcome == OUTCOME_HARD_STOP:
                label = "HARD-STOP (exit {})".format(returncode)
            elif outcome == OUTCOME_TECH_ERROR:
                label = "Lỗi kỹ thuật (exit {})".format(returncode)
            self.plan_tree.item(
                str(index),
                values=self._plan_row(command, outcome, label),
                tags=(OUTCOME_TAGS[outcome],),
            )
            tag = {"pass": "pass", "fail": "fail", "tech": "tech"}.get(OUTCOME_TAGS[outcome], "muted")
            message = "■ Lệnh {} kết thúc: {} — exit {}".format(index + 1, label, returncode)
            if outcome == OUTCOME_HARD_STOP:
                message += " · lỗi môi trường kỹ thuật, KHÔNG phải thuật toán FAIL"
            elif outcome == OUTCOME_TECH_ERROR and state.last_error:
                message += " · " + state.last_error
            self.append_log(message + "\n", tag)
        elif event == "finished":
            (outcomes,) = payload
            self._on_queue_finished(outcomes)

    def _on_queue_finished(self, outcomes):
        plan = self.queue_plan
        for index, outcome in enumerate(outcomes):
            if outcome == OUTCOME_SKIPPED:
                command = plan.commands[index]
                self.plan_tree.item(
                    str(index), values=self._plan_row(command, outcome), tags=("stopped",)
                )
        counts = {}
        for outcome in outcomes:
            counts[outcome] = counts.get(outcome, 0) + 1
        if counts.get(OUTCOME_HARD_STOP) or counts.get(OUTCOME_TECH_ERROR):
            self.run_pill.set("Có lỗi kỹ thuật", "tech")
        elif counts.get(OUTCOME_ALGO_FAIL):
            self.run_pill.set("Xong · có FAIL", "fail")
        elif counts.get(OUTCOME_STOPPED) or counts.get(OUTCOME_SKIPPED):
            self.run_pill.set("Đã dừng", "warn")
        else:
            self.run_pill.set("Xong · PASS", "pass")
        self.append_log(
            "=== Hàng đợi kết thúc: {} ===\n".format(
                ", ".join("{} {}".format(OUTCOME_LABELS[k], v) for k, v in counts.items())
            ),
            "head",
        )
        self.last_run_ids = [
            command.run_id
            for command, outcome in zip(plan.commands, outcomes)
            if outcome not in (OUTCOME_SKIPPED, OUTCOME_HARD_STOP)
        ]
        self.last_outcomes = outcomes
        self.app.results.refresh(select=self.last_run_ids[:2])
        self._update_run_buttons()
        for callback in list(self.queue_finished_callbacks):
            callback(plan, outcomes)

    def open_results(self):
        run_ids = getattr(self, "last_run_ids", None) or []
        self.app.show_page("results")
        if run_ids:
            self.app.results.refresh(select=run_ids[:2])
