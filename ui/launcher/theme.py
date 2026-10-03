"""Colours and ttk styles for the launcher."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


COLORS = {
    "background": "#F3F6FB",
    "surface": "#FFFFFF",
    "surface_muted": "#EAF0F8",
    "navy": "#10243E",
    "navy_soft": "#183653",
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "success": "#0F9D78",
    "warning": "#D97706",
    "danger": "#DC3545",
    "text": "#172033",
    "muted": "#607089",
    "border": "#D8E1ED",
    "console": "#0B1220",
    "console_text": "#D7E3F4",
}


def configure_style(root: tk.Misc) -> None:
    root.configure(background=COLORS["background"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    default_font = ("DejaVu Sans", 10)
    style.configure(".", font=default_font, foreground=COLORS["text"])
    style.configure("TFrame", background=COLORS["background"])
    style.configure("Card.TFrame", background=COLORS["surface"])
    style.configure("Hero.TFrame", background=COLORS["navy"])
    style.configure(
        "HeroTitle.TLabel",
        background=COLORS["navy"],
        foreground="#FFFFFF",
        font=("DejaVu Sans", 20, "bold"),
    )
    style.configure(
        "HeroSubtitle.TLabel",
        background=COLORS["navy"],
        foreground="#BFD0E5",
        font=("DejaVu Sans", 10),
    )
    style.configure(
        "SectionTitle.TLabel",
        background=COLORS["background"],
        foreground=COLORS["navy"],
        font=("DejaVu Sans", 13, "bold"),
    )
    style.configure(
        "SectionHint.TLabel",
        background=COLORS["background"],
        foreground=COLORS["muted"],
    )
    style.configure(
        "CardTitle.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["navy"],
        font=("DejaVu Sans", 11, "bold"),
    )
    style.configure(
        "Muted.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["muted"],
    )
    style.configure(
        "Status.TLabel",
        background=COLORS["navy_soft"],
        foreground="#FFFFFF",
        font=("DejaVu Sans", 10, "bold"),
        padding=(12, 7),
    )
    style.configure("Online.Status.TLabel", background=COLORS["success"])
    style.configure("Offline.Status.TLabel", background=COLORS["danger"])
    style.configure("Warning.Status.TLabel", background=COLORS["warning"])

    style.configure(
        "TButton",
        background=COLORS["surface_muted"],
        foreground=COLORS["text"],
        padding=(12, 7),
        borderwidth=0,
    )
    style.map("TButton", background=[("active", COLORS["border"])])
    style.configure(
        "Primary.TButton",
        background=COLORS["primary"],
        foreground="#FFFFFF",
        font=("DejaVu Sans", 10, "bold"),
        padding=(15, 8),
    )
    style.map(
        "Primary.TButton",
        background=[("active", COLORS["primary_hover"])],
        foreground=[("disabled", "#E5E7EB")],
    )
    style.configure(
        "Danger.TButton",
        background="#FDE8EA",
        foreground=COLORS["danger"],
        padding=(12, 7),
    )
    style.map("Danger.TButton", background=[("active", "#F8CDD2")])
    style.configure(
        "Hero.TButton",
        background="#FFFFFF",
        foreground=COLORS["navy"],
        padding=(12, 7),
        borderwidth=0,
    )
    style.map("Hero.TButton", background=[("active", "#DCE8F6")])

    style.configure(
        "TNotebook",
        background=COLORS["background"],
        borderwidth=0,
        tabmargins=(0, 0, 0, 0),
    )
    style.configure(
        "TNotebook.Tab",
        background=COLORS["surface_muted"],
        foreground=COLORS["muted"],
        padding=(18, 10),
        font=("DejaVu Sans", 10, "bold"),
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLORS["surface"])],
        foreground=[("selected", COLORS["primary"])],
    )
    style.configure(
        "Card.TLabelframe",
        background=COLORS["surface"],
        bordercolor=COLORS["border"],
        relief=tk.SOLID,
        borderwidth=1,
    )
    style.configure(
        "Card.TLabelframe.Label",
        background=COLORS["surface"],
        foreground=COLORS["navy"],
        font=("DejaVu Sans", 10, "bold"),
    )
    style.configure(
        "Panel.TLabelframe",
        background=COLORS["background"],
        bordercolor=COLORS["border"],
        relief=tk.SOLID,
        borderwidth=1,
    )
    style.configure(
        "Panel.TLabelframe.Label",
        background=COLORS["background"],
        foreground=COLORS["navy"],
        font=("DejaVu Sans", 10, "bold"),
    )
    style.configure("TLabel", background=COLORS["background"])
    style.configure("TCheckbutton", background=COLORS["background"])
    style.map("TCheckbutton", background=[("active", COLORS["background"])])
    style.configure("TEntry", padding=5, fieldbackground=COLORS["surface"])
    style.configure("TCombobox", padding=5, fieldbackground=COLORS["surface"])
    style.configure("TSpinbox", padding=5, fieldbackground=COLORS["surface"])
