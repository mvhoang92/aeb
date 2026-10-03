"""'Kết quả' screen: browse run directories, inspect one, compare two."""

from __future__ import absolute_import

import subprocess
import tkinter as tk
from tkinter import ttk

from ui.testbench.results import (
    OUTCOME_FAIL,
    OUTCOME_MIXED,
    OUTCOME_PASS,
    find_run,
    list_runs,
    load_summaries,
    paired_comparison,
    planned_runs,
    totals,
)
from ui.testbench.widgets import Section, Tooltip, wrap_label


OUTCOME_TEXT = {
    OUTCOME_PASS: "PASS",
    OUTCOME_FAIL: "FAIL",
    OUTCOME_MIXED: "lẫn",
}

PAIR_LABELS = (
    ("both_pass", "Cả hai PASS"),
    ("a_only_pass", "Chỉ A PASS"),
    ("b_only_pass", "Chỉ B PASS"),
    ("both_fail", "Cả hai FAIL"),
    ("mixed", "Lặp không nhất quán"),
)

PAIRED_NOTE = (
    "So sánh theo điều kiện có tên (named condition) chung của hai run: một "
    "điều kiện PASS khi mọi lần lặp PASS — cùng logic bảng cặp (McNemar) của "
    "paper. Bảng chỉ mô tả, không tính p-value; chỉ có ý nghĩa khi hai run "
    "dùng cùng file kịch bản, seed, chế độ và số lần lặp."
)


def _yes(value):
    return "có" if value else "không"


def _num(value, digits=2):
    if value is None:
        return "—"
    return "{:.{d}f}".format(value, d=digits)


def _pct(value):
    return "—" if value is None else "{:.0f}%".format(100.0 * value)


class ResultsPage(ttk.Frame):
    def __init__(self, master, app):
        ttk.Frame.__init__(self, master, style="TFrame")
        self.app = app
        self.theme = app.theme
        self.px = self.theme.px
        self.runs = []
        self.search_var = tk.StringVar()
        self.tb_only_var = tk.BooleanVar(value=False)
        self.search_var.trace_add("write", lambda *_: self._fill_runs())
        self.tb_only_var.trace_add("write", lambda *_: self._fill_runs())
        self._build()

    def _build(self):
        px = self.px
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        frame = ttk.Frame(self)
        frame.grid(row=0, column=0, sticky="nsew", padx=px(12), pady=px(10))
        frame.columnconfigure(0, weight=44, uniform="results")
        frame.columnconfigure(1, weight=56, uniform="results")
        frame.rowconfigure(0, weight=1)
        self._build_list(frame).grid(row=0, column=0, sticky="nsew", padx=(0, px(8)))
        self._build_detail(frame).grid(row=0, column=1, sticky="nsew")

    def _build_list(self, master):
        px = self.px
        section = Section(
            master,
            self.theme,
            "A",
            "Các lần chạy",
            "Thư mục log dưới {} (mới nhất trước). Chọn 1 run để xem chi tiết; giữ "
            "Ctrl và chọn run thứ 2 để so sánh cặp.".format(self.app.logs_root),
        )
        body = section.body
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)
        row = ttk.Frame(body, style="Plain.TFrame")
        row.grid(row=0, column=0, sticky="ew", pady=(0, px(6)))
        row.columnconfigure(1, weight=1)
        ttk.Label(row, text="Tìm", style="Card.TLabel").grid(row=0, column=0, padx=(0, px(6)))
        ttk.Entry(row, textvariable=self.search_var).grid(row=0, column=1, sticky="ew")
        ttk.Checkbutton(
            row, text="Chỉ run tb_*", variable=self.tb_only_var, style="Card.TCheckbutton"
        ).grid(row=0, column=2, padx=(px(8), 0))
        ttk.Button(row, text="Làm mới", command=self.refresh).grid(row=0, column=3, padx=(px(6), 0))
        frame = ttk.Frame(body, style="Plain.TFrame")
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        columns = ("run_id", "pass", "date", "system", "suite")
        self.run_tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="extended")
        for column, text, width, stretch in (
            ("run_id", "Run-id", 175, True),
            ("pass", "PASS", 58, False),
            ("date", "Cập nhật", 96, False),
            ("system", "Hệ thống", 112, False),
            ("suite", "Suite", 110, True),
        ):
            self.run_tree.heading(column, text=text, anchor="w")
            self.run_tree.column(column, width=px(width), minwidth=px(40), stretch=stretch)
        c = self.theme.colors
        self.run_tree.tag_configure("allpass", foreground=c["pass"])
        self.run_tree.tag_configure("somefail", foreground=c["fail"])
        self.run_tree.tag_configure("nometa", foreground=c["faint"])
        self.run_tree.tag_configure("incomplete", foreground=c["warn"], background=c["warn_bg"])
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.run_tree.yview)
        self.run_tree.configure(yscrollcommand=scroll.set)
        self.run_tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.run_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_select())
        self.count_label = ttk.Label(body, text="", style="Muted.TLabel")
        self.count_label.grid(row=2, column=0, sticky="w", pady=(px(4), 0))
        return section

    def _build_detail(self, master):
        px = self.px
        section = Section(master, self.theme, "B", "Chi tiết / so sánh", None)
        body = section.body
        body.columnconfigure(0, weight=1)
        body.rowconfigure(3, weight=1)
        self.detail_title = ttk.Label(body, text="Chọn một run ở bên trái.", style="Big.TLabel")
        self.detail_title.grid(row=0, column=0, sticky="w")
        self.detail_meta = ttk.Label(body, text="", style="Muted.TLabel", justify="left")
        self.detail_meta.grid(row=1, column=0, sticky="ew", pady=(px(2), px(6)))
        wrap_label(self.detail_meta)
        self.tiles = ttk.Frame(body, style="Plain.TFrame")
        self.tiles.grid(row=2, column=0, sticky="ew", pady=(0, px(8)))
        frame = ttk.Frame(body, style="Plain.TFrame")
        frame.grid(row=3, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.rows_tree = ttk.Treeview(frame, show="headings", selectmode="browse")
        c = self.theme.colors
        self.rows_tree.tag_configure("pass", foreground=c["pass"])
        self.rows_tree.tag_configure("fail", background=c["fail_bg"], foreground=c["fail"])
        self.rows_tree.tag_configure("mixed", background=c["warn_bg"], foreground=c["warn"])
        self.rows_tree.tag_configure("a_only", background=c["info_bg"])
        self.rows_tree.tag_configure("b_only", background=c["tech_bg"])
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.rows_tree.yview)
        hscroll = ttk.Scrollbar(frame, orient="horizontal", command=self.rows_tree.xview)
        self.rows_tree.configure(yscrollcommand=scroll.set, xscrollcommand=hscroll.set)
        self.rows_tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        hscroll.grid(row=1, column=0, sticky="ew")
        footer = ttk.Frame(body, style="Plain.TFrame")
        footer.grid(row=4, column=0, sticky="ew", pady=(px(6), 0))
        footer.columnconfigure(0, weight=1)
        self.footer_note = ttk.Label(footer, text="", style="Muted.TLabel", justify="left")
        self.footer_note.grid(row=0, column=0, sticky="ew")
        wrap_label(self.footer_note)
        self.copy_button = ttk.Button(footer, text="Sao chép lệnh gốc", command=self._copy_command)
        self.copy_button.grid(row=0, column=1, padx=(px(6), 0))
        self.open_button = ttk.Button(footer, text="Mở thư mục", command=self._open_folder)
        self.open_button.grid(row=0, column=2, padx=(px(6), 0))
        return section

    # ---------------------------------------------------------------- list
    def refresh(self, select=None):
        self.runs = list_runs(self.app.logs_root)
        self._fill_runs()
        if select:
            present = [run_id for run_id in select if self.run_tree.exists(run_id)]
            if present:
                self.run_tree.selection_set(present)
                self.run_tree.focus(present[0])
                top = min(present, key=self.run_tree.index)
                self.run_tree.see(top)

    def _fill_runs(self):
        tree = self.run_tree
        selection = tree.selection()
        tree.delete(*tree.get_children(""))
        tokens = [token for token in self.search_var.get().lower().split() if token]
        shown = 0
        for run in self.runs:
            if self.tb_only_var.get() and not run.run_id.startswith("tb_"):
                continue
            haystack = " ".join(
                (run.run_id, run.policy_label, run.suite_name, run.control_mode)
            ).lower()
            if not all(token in haystack for token in tokens):
                continue
            tag = "nometa"
            pass_text = run.pass_text
            if run.has_metadata and run.completed:
                tag = "allpass" if not run.failed else "somefail"
                planned = self._planned(run)
                if planned and run.completed < planned:
                    tag = "incomplete"
                    pass_text += " · dở {}/{}".format(run.completed, planned)
            tree.insert(
                "",
                "end",
                iid=run.run_id,
                values=(run.run_id, pass_text, run.short_date_text, run.short_label, run.suite_stem),
                tags=(tag,),
            )
            shown += 1
        self.count_label.configure(text="{} / {} run".format(shown, len(self.runs)))
        keep = [iid for iid in selection if tree.exists(iid)]
        if keep:
            tree.selection_set(keep)

    def _planned(self, run):
        cache = self.__dict__.setdefault("_planned_cache", {})
        key = (run.run_id, run.command)
        if key not in cache:
            cache[key] = planned_runs(run, self.app.catalog)
        return cache[key]

    def _on_select(self):
        selection = self.run_tree.selection()
        if len(selection) == 1:
            self.show_run(selection[0])
        elif len(selection) == 2:
            self.show_pair(selection[0], selection[1])
        elif not selection:
            self._clear("Chọn một run ở bên trái.")
        else:
            self._clear("Chọn tối đa 2 run để so sánh cặp.")

    # -------------------------------------------------------------- detail
    def _clear(self, title):
        self.current = None
        self.detail_title.configure(text=title)
        self.detail_meta.configure(text="")
        self.footer_note.configure(text="")
        for child in self.tiles.winfo_children():
            child.destroy()
        self.rows_tree.delete(*self.rows_tree.get_children(""))

    def _tile(self, column, label, value, kind="neutral", tooltip=None):
        c = self.theme.colors
        background, foreground = {
            "pass": (c["pass_bg"], c["pass"]),
            "fail": (c["fail_bg"], c["fail"]),
            "warn": (c["warn_bg"], c["warn"]),
            "info": (c["info_bg"], c["accent"]),
        }.get(kind, (c["surface_alt"], c["text"]))
        frame = tk.Frame(self.tiles, background=background, padx=self.px(10), pady=self.px(4))
        frame.grid(row=0, column=column, sticky="nsew", padx=(0, self.px(6)))
        tk.Label(frame, text=label, background=background, foreground=c["muted"], font=self.theme.font("small")).pack(anchor="w")
        tk.Label(frame, text=value, background=background, foreground=foreground, font=self.theme.font("big")).pack(anchor="w")
        if tooltip:
            Tooltip(frame, tooltip, self.theme)

    def _set_columns(self, columns):
        tree = self.rows_tree
        tree.delete(*tree.get_children(""))
        tree.configure(columns=[name for name, _, _, _ in columns])
        for name, text, width, anchor in columns:
            tree.heading(name, text=text, anchor=anchor)
            tree.column(name, width=self.px(width), minwidth=self.px(36), stretch=(name == "reason"), anchor=anchor)

    def show_run(self, run_id):
        run = find_run(self.runs, run_id)
        if run is None:
            return
        self._clear(run.run_id)
        self.current = run
        meta = run.metadata
        rows = load_summaries(run.path)
        parts = [
            "Hệ thống: {}".format(run.policy_label),
            "Kịch bản: {}".format(run.scenario_config or "?"),
            "Sensor: {}".format(run.sensor_config or "?"),
            "Chế độ: {} · lặp {} · seed {}".format(run.control_mode or "?", run.repeat or "?", run.seed if run.seed is not None else "?"),
        ]
        environment = meta.get("runtime_environment") or {}
        providers = environment.get("available_providers") or meta.get("model_providers_configured")
        if run.policy_key and run.policy_key != "radar_only" and providers:
            parts.append("Provider: {}".format(", ".join(str(p) for p in providers)))
        if meta.get("git_commit"):
            parts.append(
                "Commit {}{}".format(str(meta.get("git_commit"))[:8], " (dirty)" if meta.get("git_dirty") else "")
            )
        parts.append("Cập nhật: {}".format(run.date_text))
        self.detail_meta.configure(text="   ·   ".join(parts))
        stats = totals(rows)
        all_pass = stats["total"] and stats["passed"] == stats["total"]
        planned = self._planned(run)
        if planned and stats["total"] < planned:
            self._tile(
                0,
                "PASS · DỞ {}/{} lượt".format(stats["total"], planned),
                "{}/{}".format(stats["passed"], stats["total"]),
                "warn",
            )
        else:
            self._tile(0, "PASS", "{}/{}".format(stats["passed"], stats["total"]), "pass" if all_pass else "fail")
        self._tile(1, "TP", stats["tp"], "neutral", "Phải phanh và đã phanh")
        self._tile(2, "FN", stats["fn"], "fail" if stats["fn"] else "neutral", "Phải phanh nhưng không phanh (bỏ sót)")
        self._tile(3, "FP", stats["fp"], "warn" if stats["fp"] else "neutral", "Không được phanh nhưng đã phanh (phanh nhầm)")
        self._tile(4, "TN", stats["tn"], "neutral", "Không được phanh và không phanh")
        self._tile(5, "Precision", _pct(stats["precision"]), "info", "TP / (TP + FP)")
        self._tile(6, "Recall", _pct(stats["recall"]), "info", "TP / (TP + FN)")
        self._tile(7, "Va chạm", stats["collisions"], "fail" if stats["collisions"] else "neutral")
        self._set_columns(
            (
                ("scenario", "Kịch bản", 190, "w"),
                ("run", "Lần", 36, "e"),
                ("status", "Kết quả", 60, "w"),
                ("exp_brake", "Phải phanh?", 80, "w"),
                ("brake", "Đã phanh", 66, "w"),
                ("exp_coll", "VC chấp nhận?", 92, "w"),
                ("coll", "Va chạm", 60, "w"),
                ("gap", "Gap min m", 72, "e"),
                ("t_brake", "Phanh lúc s", 78, "e"),
                ("reason", "Lý do FAIL", 220, "w"),
            )
        )
        for index, row in enumerate(rows):
            ok = row["status"] == "PASS"
            self.rows_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    row["scenario_id"],
                    row["run_index"],
                    row["status"] or "?",
                    _yes(row["expected_brake"]),
                    _yes(row["brake_activated"]),
                    _yes(row["expected_collision"]),
                    _yes(row["collision"]),
                    _num(row["minimum_bumper_gap_m"]),
                    _num(row["first_brake_s"]),
                    row["failure_reason"],
                ),
                tags=("pass" if ok else "fail",),
            )
        if not rows:
            self.footer_note.configure(text="Run này chưa có summary (có thể bị dừng trước scenario đầu tiên).")
        elif planned and len(rows) < planned:
            self.footer_note.configure(
                text="⚠ Run DỞ DANG: {}/{} lượt chạy theo lệnh gốc (thường do CARLA crash hoặc bị "
                "dừng). Có thể chạy tiếp bằng --resume với cùng run-id (cần cùng commit, "
                "working tree sạch).".format(len(rows), planned)
            )
        else:
            self.footer_note.configure(
                text="Dương tính = kịch bản phải phanh. TP/FP/TN/FN tính trên từng "
                "lượt chạy (scenario-run); lặp lại không phải mẫu độc lập."
            )

    def show_pair(self, run_a_id, run_b_id):
        run_a = find_run(self.runs, run_a_id)
        run_b = find_run(self.runs, run_b_id)
        if run_a is None or run_b is None:
            return
        # Older run first so A/B reads chronologically.
        if run_a.sort_time > run_b.sort_time:
            run_a, run_b = run_b, run_a
        self._clear("So sánh cặp: A vs B")
        self.current = None
        comparison = paired_comparison(load_summaries(run_a.path), load_summaries(run_b.path))
        lines = [
            "A = {} · {} · {}".format(run_a.run_id, run_a.policy_label, run_a.suite_name or "?"),
            "B = {} · {} · {}".format(run_b.run_id, run_b.policy_label, run_b.suite_name or "?"),
        ]
        cautions = []
        if run_a.scenario_config != run_b.scenario_config:
            cautions.append("khác file kịch bản")
        if run_a.control_mode != run_b.control_mode:
            cautions.append("khác chế độ điều khiển")
        if run_a.repeat != run_b.repeat:
            cautions.append("khác số lần lặp")
        if run_a.seed != run_b.seed:
            cautions.append("khác seed")
        if cautions:
            lines.append("⚠ Lưu ý: " + ", ".join(cautions) + ".")
        self.detail_meta.configure(text="\n".join(lines))
        table = comparison["table"]
        kinds = {"both_pass": "pass", "a_only_pass": "info", "b_only_pass": "info", "both_fail": "fail", "mixed": "warn"}
        for column, (key, label) in enumerate(PAIR_LABELS):
            count = len(table[key])
            self._tile(column, label, count, kinds[key] if count else "neutral")
        self._tile(
            len(PAIR_LABELS),
            "Điều kiện chung",
            len(comparison["common"]),
            "neutral",
            "Chỉ có ở A: {} · chỉ có ở B: {}".format(len(comparison["only_in_a"]), len(comparison["only_in_b"])),
        )
        self._set_columns(
            (
                ("scenario", "Điều kiện (scenario_id)", 260, "w"),
                ("a", "A", 70, "w"),
                ("b", "B", 70, "w"),
                ("cell", "Ô trong bảng cặp", 170, "w"),
            )
        )
        cell_of = {}
        for key, label in PAIR_LABELS:
            for scenario_id in table[key]:
                cell_of[scenario_id] = (key, label)
        tags = {"both_pass": "pass", "a_only_pass": "a_only", "b_only_pass": "b_only", "both_fail": "fail", "mixed": "mixed"}
        order = {key: index for index, (key, _) in enumerate(PAIR_LABELS)}
        common = sorted(comparison["common"], key=lambda sid: (order[cell_of[sid][0]] if cell_of[sid][0] != "both_pass" else 9, sid))
        for index, scenario_id in enumerate(common):
            key, label = cell_of[scenario_id]
            self.rows_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    scenario_id,
                    OUTCOME_TEXT[comparison["outcome_a"][scenario_id]],
                    OUTCOME_TEXT[comparison["outcome_b"][scenario_id]],
                    label,
                ),
                tags=(tags[key],),
            )
        self.footer_note.configure(text=PAIRED_NOTE)

    # -------------------------------------------------------------- actions
    def _copy_command(self):
        run = getattr(self, "current", None)
        if run is not None and run.command:
            self.app.copy_to_clipboard(run.command)

    def _open_folder(self):
        run = getattr(self, "current", None)
        if run is None:
            return
        try:
            subprocess.Popen(["xdg-open", str(run.path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass
