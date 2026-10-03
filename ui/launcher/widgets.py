"""Reusable launcher widgets."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List

from ui.launcher.commands import command_text
from ui.launcher.theme import COLORS


def section_intro(parent: ttk.Frame, title: str, hint: str) -> None:
    ttk.Label(parent, text=title, style="SectionTitle.TLabel").pack(anchor=tk.W)
    ttk.Label(
        parent,
        text=hint,
        style="SectionHint.TLabel",
    ).pack(anchor=tk.W, pady=(2, 11))


def command_preview(parent: ttk.Frame) -> tk.Text:
    header = ttk.Frame(parent)
    header.pack(fill=tk.X, pady=(9, 4))
    ttk.Label(
        header,
        text="LỆNH SẼ CHẠY",
        style="SectionHint.TLabel",
    ).pack(side=tk.LEFT)
    widget = tk.Text(
        parent,
        height=3,
        wrap=tk.WORD,
        font=("DejaVu Sans Mono", 9),
        background=COLORS["console"],
        foreground=COLORS["console_text"],
        selectbackground=COLORS["primary"],
        relief=tk.FLAT,
        padx=10,
        pady=7,
        state=tk.DISABLED,
    )

    def copy_command() -> None:
        text = widget.get("1.0", tk.END).strip()
        if text:
            widget.clipboard_clear()
            widget.clipboard_append(text)

    ttk.Button(header, text="Sao chép lệnh", command=copy_command).pack(side=tk.RIGHT)
    widget.pack(fill=tk.X)
    return widget


def set_preview(widget: tk.Text, command: List[str]) -> None:
    widget.configure(state=tk.NORMAL)
    widget.delete("1.0", tk.END)
    widget.insert("1.0", command_text(command))
    widget.configure(state=tk.DISABLED)
