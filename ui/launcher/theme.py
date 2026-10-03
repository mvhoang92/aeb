"""Colours, DPI-aware fonts and ttk styles for the launcher.

Every size in the launcher (fonts, paddings, window geometry) is expressed in
logical pixels and multiplied by one scale factor.  The factor is measured
from how the X server renders point-sized text (``Xft.dpi``), so the window
looks the same on a 96-dpi screen and on a HiDPI/fractionally-scaled desktop
where Tk would otherwise draw 2x fonts inside a 1x window.
"""

from __future__ import annotations

import os
import subprocess
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Dict, Iterable, List, Optional, Tuple


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
    # Redesign additions (same navy/blue family).
    "border_strong": "#B8C6D9",
    "sidebar_active": "#21436B",
    "sidebar_hover": "#1A3656",
    "sidebar_text": "#E6EEF8",
    "sidebar_muted": "#8EA4C0",
    "success_soft": "#E3F5EE",
    "success_text": "#0B6E54",
    "danger_soft": "#FDE8EA",
    "danger_text": "#B4232F",
    "warning_soft": "#FDF0DC",
    "warning_text": "#94510A",
    "neutral_soft": "#E8EDF4",
    "console_header": "#111B2E",
    "console_muted": "#8796AE",
    "disabled": "#9AA8BB",
}

SANS_FAMILIES = ("DejaVu Sans", "Noto Sans", "Liberation Sans")
# DejaVu Sans Mono stacks Vietnamese tone marks badly; Noto Sans Mono does not.
MONO_FAMILIES = ("Noto Sans Mono", "DejaVu Sans Mono", "Ubuntu Mono")

# name -> (logical pixel size, weight)
FONT_SPECS = {
    "body": (13, "normal"),
    "body_bold": (13, "bold"),
    "small": (12, "normal"),
    "caps": (11, "bold"),
    "card_title": (14, "bold"),
    "page_title": (18, "bold"),
    "brand": (21, "bold"),
    "brand_sub": (12, "normal"),
    "nav": (14, "normal"),
    "nav_number": (12, "bold"),
    "pill": (12, "bold"),
    "mono": (12, "normal"),
}


def xft_dpi() -> Optional[float]:
    """Return ``Xft.dpi`` from the X resource database, if the desktop set it."""
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


def measure_scale(root: tk.Misc) -> float:
    """Align Tk with the desktop DPI and return the logical-pixel factor.

    Xft draws point sizes at ``Xft.dpi`` while Tk converts pixel sizes to
    points with ``tk scaling`` (derived from the monitor's reported mm).  On a
    fractionally scaled GNOME desktop these disagree (e.g. 192 vs 120 dpi), so
    pixel-sized fonts would come out 1.6x too large.  Setting ``tk scaling``
    from ``Xft.dpi`` makes pixel sizes exact; the factor is then dpi / 96.
    """
    dpi = xft_dpi()
    if dpi:
        root.tk.call("tk", "scaling", dpi / 72.0)
    else:
        dpi = float(root.tk.call("tk", "scaling")) * 72.0
    override = os.environ.get("AEB_LAUNCHER_SCALE")
    if override:
        try:
            return max(0.75, min(4.0, float(override)))
        except ValueError:
            pass
    return max(1.0, min(3.0, round(dpi / 96.0 * 4.0) / 4.0))


def first_family(root: tk.Misc, candidates: Iterable[str]) -> str:
    available = set(tkfont.families(root))
    candidates = tuple(candidates)
    for family in candidates:
        if family in available:
            return family
    return candidates[-1]


class Theme:
    """Scale factor, named fonts and generated images for one Tk root."""

    def __init__(self, root: tk.Misc):
        self.root = root
        self.scale = measure_scale(root)
        sans = first_family(root, SANS_FAMILIES)
        mono = first_family(root, MONO_FAMILIES)
        self.fonts: Dict[str, tkfont.Font] = {}
        for name, (size, weight) in FONT_SPECS.items():
            family = mono if name == "mono" else sans
            self.fonts[name] = tkfont.Font(
                root,
                name="Aeb{}".format(name.title().replace("_", "")),
                family=family,
                size=-self.px(size),
                weight=weight,
                exists=False,
            )
        self.images: Dict[str, tk.PhotoImage] = {}

    def px(self, value: float) -> int:
        return int(round(value * self.scale))

    def pad(self, *values: float) -> Tuple[int, ...]:
        return tuple(self.px(value) for value in values)

    def font(self, name: str) -> tkfont.Font:
        return self.fonts[name]


# --------------------------------------------------------------------------- #
# Anti-aliased checkbox images (Tk has no vector checkbox at HiDPI sizes)
# --------------------------------------------------------------------------- #
def _hex(color: str) -> Tuple[float, float, float]:
    color = color.lstrip("#")
    return tuple(int(color[index:index + 2], 16) / 255.0 for index in (0, 2, 4))


def _mix(base, top, alpha):
    return tuple(b * (1.0 - alpha) + t * alpha for b, t in zip(base, top))


def _rounded_rect_inside(x, y, x0, y0, x1, y1, radius):
    cx = min(max(x, x0 + radius), x1 - radius)
    cy = min(max(y, y0 + radius), y1 - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2 and x0 <= x <= x1 and y0 <= y <= y1


def _segment_distance(px_, py_, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px_ - ax) * dx + (py_ - ay) * dy) / float(dx * dx + dy * dy)))
    return ((px_ - ax - t * dx) ** 2 + (py_ - ay - t * dy) ** 2) ** 0.5


def checkbox_image(
    root: tk.Misc,
    size: int,
    background: str,
    border: str,
    fill: str,
    check: str,
    checked: bool,
    gap: int = 0,
) -> tk.PhotoImage:
    samples = 4
    stroke = max(1.0, size / 11.0)
    radius = size * 0.22
    bg, bd, fl, ck = (_hex(background), _hex(border), _hex(fill), _hex(check))
    tick = [(0.24, 0.53), (0.43, 0.71), (0.77, 0.31)]
    tick = [(x * size, y * size) for x, y in tick]
    thickness = max(1.6, size / 7.5)
    rows: List[str] = []
    for y in range(size):
        row = []
        for x in range(size):
            color = [0.0, 0.0, 0.0]
            for sy in range(samples):
                for sx in range(samples):
                    fx = x + (sx + 0.5) / samples
                    fy = y + (sy + 0.5) / samples
                    sample = bg
                    if _rounded_rect_inside(fx, fy, 0.5, 0.5, size - 0.5, size - 0.5, radius):
                        inner = _rounded_rect_inside(
                            fx, fy, 0.5 + stroke, 0.5 + stroke,
                            size - 0.5 - stroke, size - 0.5 - stroke,
                            max(0.0, radius - stroke),
                        )
                        sample = fl if inner else bd
                        if checked:
                            distance = min(
                                _segment_distance(fx, fy, *tick[0], *tick[1]),
                                _segment_distance(fx, fy, *tick[1], *tick[2]),
                            )
                            if distance <= thickness / 2.0:
                                sample = ck
                    color = [c + s for c, s in zip(color, sample)]
            color = [c / (samples * samples) for c in color]
            row.append("#{:02x}{:02x}{:02x}".format(*(int(round(c * 255)) for c in color)))
        row.extend([background] * gap)  # space between the box and its label
        rows.append("{" + " ".join(row) + "}")
    image = tk.PhotoImage(master=root, width=size + gap, height=size)
    image.put(" ".join(rows))
    return image


def _checkbox_images(theme: Theme) -> Dict[str, tk.PhotoImage]:
    size = theme.px(17)
    surface = COLORS["surface"]
    spec = {
        "off": (surface, COLORS["border_strong"], surface, surface, False),
        "off_hover": (surface, COLORS["primary"], surface, surface, False),
        "off_disabled": (surface, COLORS["border"], COLORS["background"], surface, False),
        "on": (surface, COLORS["primary"], COLORS["primary"], "#FFFFFF", True),
        "on_hover": (surface, COLORS["primary_hover"], COLORS["primary_hover"], "#FFFFFF", True),
        "on_disabled": (surface, COLORS["disabled"], COLORS["disabled"], "#FFFFFF", True),
    }
    return {
        name: checkbox_image(theme.root, size, *values, gap=theme.px(8))
        for name, values in spec.items()
    }


# --------------------------------------------------------------------------- #
# ttk styles
# --------------------------------------------------------------------------- #
def configure_style(root: tk.Misc) -> Theme:
    theme = Theme(root)
    px = theme.px
    fonts = theme.fonts
    root.configure(background=COLORS["background"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # Combobox drop-down lists are classic Tk listboxes.
    root.option_add("*TCombobox*Listbox.font", fonts["body"])
    root.option_add("*TCombobox*Listbox.background", COLORS["surface"])
    root.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", COLORS["primary"])
    root.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")
    root.option_add("*TCombobox*Listbox.borderWidth", 0)
    root.option_add("*Menu.font", fonts["body"])

    style.configure(
        ".",
        font=fonts["body"],
        foreground=COLORS["text"],
        background=COLORS["background"],
        bordercolor=COLORS["border"],
        lightcolor=COLORS["surface"],
        darkcolor=COLORS["border"],
        troughcolor=COLORS["background"],
        focuscolor=COLORS["primary"],
        selectbackground=COLORS["primary"],
        selectforeground="#FFFFFF",
    )

    # Frames ---------------------------------------------------------------
    style.configure("TFrame", background=COLORS["background"])
    style.configure("Page.TFrame", background=COLORS["background"])
    style.configure("Card.TFrame", background=COLORS["surface"])
    style.configure("Header.TFrame", background=COLORS["surface"])
    style.configure("Footer.TFrame", background=COLORS["surface"])
    style.configure("Sidebar.TFrame", background=COLORS["navy"])
    style.configure("Console.TFrame", background=COLORS["console_header"])
    style.configure("Hero.TFrame", background=COLORS["navy"])

    # Labels ---------------------------------------------------------------
    style.configure("TLabel", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure("Field.TLabel", background=COLORS["surface"], foreground=COLORS["muted"])
    style.configure("Muted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"])
    style.configure("Note.TLabel", background=COLORS["surface"], foreground=COLORS["muted"], font=fonts["small"])
    style.configure(
        "CardTitle.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["navy"],
        font=fonts["card_title"],
    )
    style.configure(
        "Caps.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["muted"],
        font=fonts["caps"],
    )
    style.configure(
        "PageTitle.TLabel",
        background=COLORS["surface"],
        foreground=COLORS["navy"],
        font=fonts["page_title"],
    )
    style.configure(
        "PageHint.TLabel",
        background=COLORS["background"],
        foreground=COLORS["muted"],
    )
    style.configure(
        "Brand.TLabel",
        background=COLORS["navy"],
        foreground="#FFFFFF",
        font=fonts["brand"],
    )
    style.configure(
        "BrandSub.TLabel",
        background=COLORS["navy"],
        foreground=COLORS["sidebar_muted"],
        font=fonts["brand_sub"],
    )
    style.configure(
        "SidebarCaps.TLabel",
        background=COLORS["navy"],
        foreground=COLORS["sidebar_muted"],
        font=fonts["caps"],
    )
    style.configure(
        "SidebarNote.TLabel",
        background=COLORS["navy"],
        foreground=COLORS["sidebar_muted"],
        font=fonts["small"],
    )
    style.configure(
        "ConsoleTitle.TLabel",
        background=COLORS["console_header"],
        foreground="#FFFFFF",
        font=fonts["caps"],
    )
    style.configure(
        "ConsoleMuted.TLabel",
        background=COLORS["console_header"],
        foreground=COLORS["console_muted"],
        font=fonts["small"],
    )
    style.configure(
        "ConsoleValue.TLabel",
        background=COLORS["console_header"],
        foreground=COLORS["console_text"],
        font=fonts["small"],
    )

    # Sidebar navigation (radio buttons without indicator) -----------------
    style.layout(
        "Nav.TRadiobutton",
        [
            (
                "Radiobutton.padding",
                {
                    "sticky": "nswe",
                    "children": [
                        (
                            "Radiobutton.focus",
                            {"sticky": "nswe", "children": [("Radiobutton.label", {"sticky": "w"})]},
                        )
                    ],
                },
            )
        ],
    )
    style.configure(
        "Nav.TRadiobutton",
        background=COLORS["navy"],
        foreground=COLORS["sidebar_text"],
        font=fonts["nav"],
        padding=theme.pad(14, 10, 12, 10),
        focuscolor=COLORS["navy"],
        anchor="w",
    )
    style.map(
        "Nav.TRadiobutton",
        background=[("selected", COLORS["sidebar_active"]), ("active", COLORS["sidebar_hover"])],
        foreground=[("selected", "#FFFFFF")],
        focuscolor=[("focus", COLORS["sidebar_muted"])],
    )

    # Buttons --------------------------------------------------------------
    button_padding = theme.pad(14, 7)
    style.configure(
        "TButton",
        background=COLORS["surface_muted"],
        foreground=COLORS["text"],
        bordercolor=COLORS["surface_muted"],
        lightcolor=COLORS["surface_muted"],
        darkcolor=COLORS["surface_muted"],
        focuscolor=COLORS["primary"],
        padding=button_padding,
        borderwidth=1,
        anchor="center",
    )
    style.map(
        "TButton",
        background=[("disabled", COLORS["background"]), ("pressed", COLORS["border_strong"]), ("active", COLORS["border"])],
        bordercolor=[("active", COLORS["border"])],
        lightcolor=[("active", COLORS["border"])],
        darkcolor=[("active", COLORS["border"])],
        foreground=[("disabled", COLORS["disabled"])],
    )
    style.configure(
        "Primary.TButton",
        background=COLORS["primary"],
        foreground="#FFFFFF",
        bordercolor=COLORS["primary"],
        lightcolor=COLORS["primary"],
        darkcolor=COLORS["primary"],
        font=fonts["body_bold"],
        padding=theme.pad(18, 7),
    )
    style.map(
        "Primary.TButton",
        background=[("pressed", COLORS["navy_soft"]), ("active", COLORS["primary_hover"])],
        bordercolor=[("active", COLORS["primary_hover"])],
        lightcolor=[("active", COLORS["primary_hover"])],
        darkcolor=[("active", COLORS["primary_hover"])],
        foreground=[("disabled", "#E5E7EB")],
    )
    style.configure(
        "Danger.TButton",
        background=COLORS["danger_soft"],
        foreground=COLORS["danger_text"],
        bordercolor=COLORS["danger_soft"],
        lightcolor=COLORS["danger_soft"],
        darkcolor=COLORS["danger_soft"],
        padding=button_padding,
    )
    style.map(
        "Danger.TButton",
        background=[("pressed", "#F3B8BF"), ("active", "#F8CDD2")],
        bordercolor=[("active", "#F8CDD2")],
        lightcolor=[("active", "#F8CDD2")],
        darkcolor=[("active", "#F8CDD2")],
    )
    style.configure(
        "Small.TButton",
        font=fonts["small"],
        padding=theme.pad(10, 4),
    )
    style.configure(
        "Console.TButton",
        background=COLORS["navy_soft"],
        foreground=COLORS["console_text"],
        bordercolor=COLORS["navy_soft"],
        lightcolor=COLORS["navy_soft"],
        darkcolor=COLORS["navy_soft"],
        focuscolor=COLORS["console_muted"],
        font=fonts["small"],
        padding=theme.pad(10, 4),
    )
    style.map(
        "Console.TButton",
        background=[("pressed", COLORS["navy"]), ("active", COLORS["sidebar_active"])],
        bordercolor=[("active", COLORS["sidebar_active"])],
        lightcolor=[("active", COLORS["sidebar_active"])],
        darkcolor=[("active", COLORS["sidebar_active"])],
    )
    style.configure(
        "ConsoleDanger.TButton",
        background="#3A1E2A",
        foreground="#FFB4BC",
        bordercolor="#3A1E2A",
        lightcolor="#3A1E2A",
        darkcolor="#3A1E2A",
        focuscolor=COLORS["console_muted"],
        font=fonts["small"],
        padding=theme.pad(10, 4),
    )
    style.map(
        "ConsoleDanger.TButton",
        background=[("pressed", "#2A141D"), ("active", "#5A2433")],
        bordercolor=[("active", "#5A2433")],
        lightcolor=[("active", "#5A2433")],
        darkcolor=[("active", "#5A2433")],
    )

    # Inputs ---------------------------------------------------------------
    field_padding = theme.pad(8, 5)
    for widget_style in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(
            widget_style,
            fieldbackground=COLORS["surface"],
            background=COLORS["surface_muted"],
            foreground=COLORS["text"],
            bordercolor=COLORS["border_strong"],
            lightcolor=COLORS["surface"],
            darkcolor=COLORS["surface"],
            arrowcolor=COLORS["muted"],
            insertcolor=COLORS["text"],
            padding=field_padding,
        )
        style.map(
            widget_style,
            fieldbackground=[("disabled", COLORS["background"]), ("readonly", COLORS["surface"])],
            foreground=[("disabled", COLORS["disabled"])],
            bordercolor=[("disabled", COLORS["border"]), ("focus", COLORS["primary"]), ("hover", COLORS["muted"])],
            lightcolor=[("focus", COLORS["surface"])],
            arrowcolor=[("disabled", COLORS["disabled"]), ("active", COLORS["primary"])],
            background=[("disabled", COLORS["background"]), ("active", COLORS["border"]), ("pressed", COLORS["border_strong"])],
            # Readonly comboboxes should not look "selected" when focused.
            selectbackground=[("readonly", "!focus", COLORS["surface"]), ("readonly", "focus", COLORS["surface_muted"])],
            selectforeground=[("readonly", COLORS["text"])],
        )
    style.configure("TCombobox", arrowsize=px(13))
    style.configure("TSpinbox", arrowsize=px(13))

    # Check buttons (image indicator so it scales with the UI) --------------
    theme.images.update(_checkbox_images(theme))
    images = theme.images
    try:
        style.element_create(
            "Aeb.Checkbutton.indicator",
            "image",
            images["off"],
            ("disabled", "selected", images["on_disabled"]),
            ("disabled", images["off_disabled"]),
            ("active", "selected", images["on_hover"]),
            ("selected", images["on"]),
            ("active", images["off_hover"]),
            sticky="",
        )
    except tk.TclError:
        pass  # element already exists (second root in the same interpreter)
    style.layout(
        "TCheckbutton",
        [
            (
                "Checkbutton.padding",
                {
                    "sticky": "nswe",
                    "children": [
                        ("Aeb.Checkbutton.indicator", {"side": "left", "sticky": ""}),
                        (
                            "Checkbutton.focus",
                            {
                                "side": "left",
                                "sticky": "w",
                                "children": [("Checkbutton.label", {"sticky": "nswe"})],
                            },
                        ),
                    ],
                },
            )
        ],
    )
    style.configure(
        "TCheckbutton",
        background=COLORS["surface"],
        foreground=COLORS["text"],
        focuscolor=COLORS["primary"],
        padding=theme.pad(0, 4, 4, 4),
    )
    style.map(
        "TCheckbutton",
        background=[("active", COLORS["surface"])],
        foreground=[("disabled", COLORS["disabled"])],
    )

    # Scrollbars -----------------------------------------------------------
    for orient, trough, thumb in (
        ("Vertical", "Vertical.Scrollbar.trough", "Vertical.Scrollbar.thumb"),
    ):
        for prefix, trough_color, thumb_color, active_color in (
            ("Page", COLORS["background"], "#C3CFDF", "#9FB0C6"),
            ("Console", COLORS["console"], "#2B3A55", "#3E5174"),
            ("Preview", COLORS["console"], "#2B3A55", "#3E5174"),
        ):
            name = "{}.{}.TScrollbar".format(prefix, orient)
            style.layout(
                name,
                [(trough, {"sticky": "ns", "children": [(thumb, {"expand": "1", "sticky": "nswe"})]})],
            )
            style.configure(
                name,
                troughcolor=trough_color,
                background=thumb_color,
                bordercolor=trough_color,
                lightcolor=thumb_color,
                darkcolor=thumb_color,
                arrowsize=px(9),
                gripcount=0,
                borderwidth=0,
            )
            style.map(
                name,
                background=[("active", active_color), ("pressed", active_color)],
                lightcolor=[("active", active_color)],
                darkcolor=[("active", active_color)],
            )

    style.configure("TSeparator", background=COLORS["border"])
    return theme
