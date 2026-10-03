"""Light ttk theme for the test bench, sized correctly on HiDPI desktops.

Fonts are declared in *points*.  Tk converts points to pixels with
``tk scaling`` (pixels per point), which Tk derives from the monitor's
reported size, while the desktop renders text at ``Xft.dpi``.  On a scaled
GNOME session these disagree (e.g. Tk 120 dpi vs Xft 192 dpi), so we set
``tk scaling`` from ``Xft.dpi`` and derive one factor for pixel paddings.
"""

from __future__ import absolute_import

import os
import subprocess
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk


COLORS = {
    "bg": "#F3F5F8",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFC",
    "border": "#D6DCE4",
    "border_strong": "#B8C2CF",
    "text": "#1E293B",
    "muted": "#64748B",
    "faint": "#94A3B8",
    "accent": "#2563EB",
    "accent_hover": "#1D4ED8",
    "accent_soft": "#E0EAFF",
    "header": "#0F172A",
    "header_text": "#F8FAFC",
    "header_muted": "#A5B4C8",
    "pass": "#15803D",
    "pass_bg": "#DCFCE7",
    "fail": "#B91C1C",
    "fail_bg": "#FEE2E2",
    "warn": "#B45309",
    "warn_bg": "#FEF3C7",
    "tech": "#6D28D9",
    "tech_bg": "#EDE9FE",
    "info_bg": "#EFF6FF",
    "select": "#DBEAFE",
    "log_bg": "#0F172A",
    "log_text": "#E2E8F0",
}

# (points, weight)
FONT_SPECS = {
    "body": (10, "normal"),
    "body_bold": (10, "bold"),
    "small": (9, "normal"),
    "small_bold": (9, "bold"),
    "section": (11, "bold"),
    "section_no": (11, "bold"),
    "title": (14, "bold"),
    "subtitle": (9, "normal"),
    "nav": (10, "bold"),
    "pill": (9, "bold"),
    "mono": (9, "normal"),
    "big": (16, "bold"),
}

SANS_CANDIDATES = ("Ubuntu", "Noto Sans", "DejaVu Sans", "Helvetica")
MONO_CANDIDATES = ("Ubuntu Mono", "Noto Sans Mono", "DejaVu Sans Mono", "Courier")


def xft_dpi():
    """``Xft.dpi`` from the X resource database, or ``None``."""
    try:
        output = subprocess.run(
            ["xrdb", "-query"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            timeout=2.0,
            check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in output.splitlines():
        if line.startswith("Xft.dpi:"):
            try:
                value = float(line.split(":", 1)[1])
            except ValueError:
                return None
            return value if value > 0 else None
    return None


def apply_dpi(root):
    """Align ``tk scaling`` with the desktop DPI; return the pixel factor."""
    dpi = xft_dpi()
    if dpi:
        root.tk.call("tk", "scaling", dpi / 72.0)
    else:
        dpi = float(root.tk.call("tk", "scaling")) * 72.0
    override = os.environ.get("AEB_TESTBENCH_SCALE")
    if override:
        try:
            return max(0.75, min(4.0, float(override)))
        except ValueError:
            pass
    return max(1.0, min(3.0, round(dpi / 96.0 * 4.0) / 4.0))


def _family(root, candidates):
    available = set(tkfont.families(root))
    for family in candidates:
        if family in available:
            return family
    return candidates[-1]


class Theme(object):
    def __init__(self, root):
        self.root = root
        self.scale = apply_dpi(root)
        self.colors = dict(COLORS)
        sans = _family(root, SANS_CANDIDATES)
        mono = _family(root, MONO_CANDIDATES)
        self.fonts = {}
        for name, (size, weight) in FONT_SPECS.items():
            family = mono if name == "mono" else sans
            self.fonts[name] = tkfont.Font(
                root=root, family=family, size=size, weight=weight
            )
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(name).configure(family=sans, size=10)
            except tk.TclError:
                pass
        try:
            tkfont.nametofont("TkFixedFont").configure(family=mono, size=9)
        except tk.TclError:
            pass
        self.row_height = self.fonts["body"].metrics("linespace") + self.px(8)
        self._configure_styles()

    def px(self, value):
        return int(round(value * self.scale))

    def font(self, name):
        return self.fonts[name]

    def _configure_styles(self):
        c = self.colors
        style = ttk.Style(self.root)
        style.theme_use("clam")
        root = self.root
        root.configure(background=c["bg"])
        root.option_add("*TCombobox*Listbox.font", self.fonts["body"])
        root.option_add("*TCombobox*Listbox.background", c["surface"])
        root.option_add("*TCombobox*Listbox.selectBackground", c["accent"])

        style.configure(
            ".",
            background=c["bg"],
            foreground=c["text"],
            font=self.fonts["body"],
            bordercolor=c["border"],
            lightcolor=c["surface"],
            darkcolor=c["border"],
            troughcolor=c["bg"],
            focuscolor=c["accent"],
            selectbackground=c["select"],
            selectforeground=c["text"],
        )
        for name, background in (
            ("TFrame", c["bg"]),
            ("Card.TFrame", c["surface"]),
            ("Alt.TFrame", c["surface_alt"]),
            ("Header.TFrame", c["header"]),
        ):
            style.configure(name, background=background)
        style.configure("Card.TFrame", relief="solid", borderwidth=1, bordercolor=c["border"])
        style.configure("Plain.TFrame", background=c["surface"])
        for name, background, foreground, font in (
            ("TLabel", c["bg"], c["text"], "body"),
            ("Card.TLabel", c["surface"], c["text"], "body"),
            ("CardBold.TLabel", c["surface"], c["text"], "body_bold"),
            ("Muted.TLabel", c["surface"], c["muted"], "small"),
            ("MutedBg.TLabel", c["bg"], c["muted"], "small"),
            ("Section.TLabel", c["surface"], c["text"], "section"),
            ("SectionNo.TLabel", c["accent"], "#FFFFFF", "section_no"),
            ("Title.TLabel", c["header"], c["header_text"], "title"),
            ("Subtitle.TLabel", c["header"], c["header_muted"], "subtitle"),
            ("Big.TLabel", c["surface"], c["text"], "big"),
            ("Mono.TLabel", c["surface"], c["text"], "mono"),
            ("Warn.TLabel", c["warn_bg"], c["warn"], "small"),
            ("Error.TLabel", c["fail_bg"], c["fail"], "small_bold"),
            ("Info.TLabel", c["info_bg"], c["text"], "small"),
        ):
            style.configure(name, background=background, foreground=foreground, font=self.fonts[font])
        style.configure("SectionNo.TLabel", padding=(self.px(7), 0))
        style.configure(
            "TButton",
            background=c["surface"],
            foreground=c["text"],
            bordercolor=c["border_strong"],
            padding=(self.px(10), self.px(4)),
            font=self.fonts["body"],
        )
        style.map(
            "TButton",
            background=[("disabled", c["bg"]), ("active", c["accent_soft"])],
            foreground=[("disabled", c["faint"])],
        )
        style.configure(
            "Accent.TButton",
            background=c["accent"],
            foreground="#FFFFFF",
            bordercolor=c["accent"],
            font=self.fonts["body_bold"],
            padding=(self.px(14), self.px(5)),
        )
        style.map(
            "Accent.TButton",
            background=[("disabled", c["border"]), ("active", c["accent_hover"])],
            foreground=[("disabled", c["muted"])],
        )
        style.configure(
            "Danger.TButton",
            foreground=c["fail"],
            bordercolor=c["fail"],
        )
        style.map("Danger.TButton", foreground=[("disabled", c["faint"])])
        style.configure(
            "Preset.TButton",
            background=c["surface"],
            padding=(self.px(12), self.px(4)),
            font=self.fonts["body_bold"],
        )
        style.map(
            "Preset.TButton",
            background=[("pressed", c["accent_soft"]), ("active", c["accent_soft"])],
            bordercolor=[("pressed", c["accent"])],
            foreground=[("pressed", c["accent_hover"])],
        )
        style.configure(
            "Nav.TButton",
            background=c["header"],
            foreground=c["header_muted"],
            bordercolor=c["header"],
            lightcolor=c["header"],
            darkcolor=c["header"],
            font=self.fonts["nav"],
            padding=(self.px(14), self.px(6)),
        )
        style.map(
            "Nav.TButton",
            background=[("active", "#1E293B")],
            foreground=[("active", c["header_text"])],
        )
        style.configure(
            "NavActive.TButton",
            background="#1E3A8A",
            foreground="#FFFFFF",
            bordercolor="#1E3A8A",
            lightcolor="#1E3A8A",
            darkcolor="#1E3A8A",
            font=self.fonts["nav"],
            padding=(self.px(14), self.px(6)),
        )
        style.map("NavActive.TButton", background=[("active", "#1E40AF")])
        for name, background in (("TCheckbutton", c["bg"]), ("Card.TCheckbutton", c["surface"])):
            style.configure(name, background=background, foreground=c["text"], font=self.fonts["body"])
            style.map(name, background=[("active", background)])
        style.configure("Small.TRadiobutton", background=c["surface"], font=self.fonts["small"])
        style.map("Small.TRadiobutton", background=[("active", c["surface"])])
        style.configure("Bold.TCheckbutton", background=c["surface"], font=self.fonts["body_bold"])
        style.map("Bold.TCheckbutton", background=[("active", c["surface"])])
        for name, background in (("TRadiobutton", c["bg"]), ("Card.TRadiobutton", c["surface"])):
            style.configure(name, background=background, foreground=c["text"], font=self.fonts["body"])
            style.map(name, background=[("active", background)])
        style.configure(
            "TEntry",
            fieldbackground=c["surface"],
            bordercolor=c["border_strong"],
            padding=(self.px(4), self.px(2)),
        )
        style.configure(
            "TSpinbox",
            fieldbackground=c["surface"],
            bordercolor=c["border_strong"],
            arrowsize=self.px(11),
            padding=(self.px(4), self.px(2)),
        )
        style.configure(
            "TCombobox",
            fieldbackground=c["surface"],
            bordercolor=c["border_strong"],
            arrowsize=self.px(12),
            padding=(self.px(4), self.px(2)),
        )
        style.configure(
            "Treeview",
            background=c["surface"],
            fieldbackground=c["surface"],
            foreground=c["text"],
            bordercolor=c["border"],
            rowheight=self.row_height,
            font=self.fonts["body"],
        )
        style.map(
            "Treeview",
            background=[("selected", c["select"])],
            foreground=[("selected", c["text"])],
        )
        style.configure(
            "Treeview.Heading",
            background=c["surface_alt"],
            foreground=c["muted"],
            font=self.fonts["small_bold"],
            bordercolor=c["border"],
            relief="flat",
            padding=(self.px(4), self.px(3)),
        )
        style.map("Treeview.Heading", background=[("active", c["accent_soft"])])
        style.configure(
            "Horizontal.TProgressbar",
            background=c["accent"],
            troughcolor=c["accent_soft"],
            bordercolor=c["border"],
            thickness=self.px(10),
        )
        style.configure(
            "TScrollbar",
            background=c["surface_alt"],
            troughcolor=c["bg"],
            bordercolor=c["border"],
            arrowcolor=c["muted"],
            arrowsize=self.px(12),
        )
        style.configure("TPanedwindow", background=c["bg"])
        style.configure("Sash", sashthickness=self.px(6), gripcount=0, background=c["bg"])
        style.configure("TSeparator", background=c["border"])
        style.configure("TNotebook", background=c["surface"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=(self.px(10), self.px(3)),
            font=self.fonts["small_bold"],
            background=c["bg"],
        )
        style.map("TNotebook.Tab", background=[("selected", c["surface"])])
        style.configure("TLabelframe", background=c["surface"])
        for name, background, foreground, border in (
            ("Step.TButton", c["surface"], c["muted"], c["border"]),
            ("StepActive.TButton", c["accent_soft"], c["accent_hover"], c["accent"]),
        ):
            style.configure(
                name,
                background=background,
                foreground=foreground,
                bordercolor=border,
                font=self.fonts["body_bold"],
                padding=(self.px(14), self.px(6)),
            )
            style.map(name, background=[("active", c["accent_soft"])])
        self._indicators(style)

    def _indicators(self, style):
        """Image check/radio indicators: crisp at any DPI, unlike clam's."""
        from ui.testbench.widgets import STATE_CHECKED, STATE_UNCHECKED, checkbox_images

        boxes = checkbox_images(self.root, self)
        self.indicator_images = [boxes[STATE_UNCHECKED], boxes[STATE_CHECKED]]
        style.element_create(
            "tb.Checkbutton.indicator",
            "image",
            boxes[STATE_UNCHECKED],
            ("selected", boxes[STATE_CHECKED]),
            sticky="w",
        )
        radio_off, radio_on = self._radio_images()
        self.indicator_images.extend((radio_off, radio_on))
        style.element_create(
            "tb.Radiobutton.indicator",
            "image",
            radio_off,
            ("selected", radio_on),
            sticky="w",
        )
        gap = self.px(4)
        for kind in ("Checkbutton", "Radiobutton"):
            style.layout(
                "T" + kind,
                [
                    (
                        kind + ".padding",
                        {
                            "sticky": "nswe",
                            "children": [
                                ("tb.{}.indicator".format(kind), {"side": "left", "sticky": ""}),
                                (
                                    kind + ".focus",
                                    {
                                        "side": "left",
                                        "sticky": "w",
                                        "children": [(kind + ".label", {"sticky": "nswe"})],
                                    },
                                ),
                            ],
                        },
                    )
                ],
            )
            style.configure("T" + kind, padding=(0, self.px(1)), indicatormargin=gap)
        del gap

    def _radio_images(self):
        c = self.colors
        size = max(12, self.px(14))
        pad = max(1, self.px(2))
        width = size + 3 * pad
        images = []
        center = pad + size / 2.0
        for selected in (False, True):
            image = tk.PhotoImage(master=self.root, width=width, height=size + 2 * pad)
            border = c["accent"] if selected else c["border_strong"]
            outer = size / 2.0
            inner = outer - max(1, self.px(1))
            dot = outer * 0.45
            for y in range(size + 2 * pad):
                row = []
                for x in range(width):
                    dx = x + 0.5 - center
                    dy = y + 0.5 - center
                    distance = (dx * dx + dy * dy) ** 0.5
                    if selected and distance <= dot:
                        row.append(c["accent"])
                    elif distance <= inner:
                        row.append(c["surface"])
                    elif distance <= outer:
                        row.append(border)
                    else:
                        row.append(None)
                for x, color in enumerate(row):
                    if color:
                        image.put(color, to=(x, y, x + 1, y + 1))
            images.append(image)
        return images[0], images[1]

