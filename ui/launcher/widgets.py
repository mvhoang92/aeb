"""Reusable launcher widgets (scrollable page, cards, status pill, preview)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional, Tuple

from ui.launcher.commands import command_text
from ui.launcher.theme import COLORS, Theme, _hex, _mix


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #
class WrapLabel(ttk.Label):
    """Label that re-wraps its text to the width it is given."""

    def __init__(self, parent: tk.Misc, **kwargs):
        super().__init__(parent, **kwargs)
        self.bind("<Configure>", self._rewrap, add="+")

    def _rewrap(self, event: tk.Event) -> None:
        width = max(1, event.width - 2)
        if str(self.cget("wraplength")) != str(width):
            self.configure(wraplength=width)


class ElidedLabel(ttk.Label):
    """Single-line label that ends with an ellipsis instead of being clipped."""

    def __init__(self, parent: tk.Misc, font, text: str = "", **kwargs):
        super().__init__(parent, width=1, **kwargs)
        self._font = font
        self._full_text = text
        self._available = 0
        self.bind("<Configure>", self._on_configure, add="+")
        self.set_text(text)

    def set_text(self, text: str) -> None:
        self._full_text = text
        self._refit()

    def _on_configure(self, event: tk.Event) -> None:
        if event.width != self._available:
            self._available = event.width
            self._refit()

    def _refit(self) -> None:
        text = self._full_text
        available = self._available - 4
        if available > 0 and self._font.measure(text) > available:
            while text and self._font.measure(text + "…") > available:
                text = text[:-1]
            text = text.rstrip(" ,") + "…"
        if self.cget("text") != text:
            self.configure(text=text)


# --------------------------------------------------------------------------- #
# Scrollable page
# --------------------------------------------------------------------------- #
class ScrollableFrame(ttk.Frame):
    """Vertical scroll container; ``body`` is where content goes.

    The scrollbar overlays the right padding and only appears when the content
    is taller than the viewport, so showing it never re-wraps the content.
    """

    _registry: Dict[str, "ScrollableFrame"] = {}

    def __init__(self, parent: tk.Misc, theme: Theme, padding: Tuple[int, ...]):
        super().__init__(parent, style="Page.TFrame")
        self.theme = theme
        self.canvas = tk.Canvas(
            self,
            background=COLORS["background"],
            highlightthickness=0,
            borderwidth=0,
            yscrollincrement=theme.px(24),
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.scrollbar = ttk.Scrollbar(
            self,
            orient=tk.VERTICAL,
            command=self.canvas.yview,
            style="Page.Vertical.TScrollbar",
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.body = ttk.Frame(self.canvas, style="Page.TFrame", padding=padding)
        self._window = self.canvas.create_window(0, 0, window=self.body, anchor=tk.NW)
        self.body.bind("<Configure>", self._on_body_configure, add="+")
        self.canvas.bind("<Configure>", self._on_canvas_configure, add="+")
        ScrollableFrame._registry[str(self.canvas)] = self

    def _on_body_configure(self, _event=None) -> None:
        height = self.body.winfo_reqheight()
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), height))
        self._update_scrollbar()

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)
        self._on_body_configure()

    def _update_scrollbar(self) -> None:
        needed = self.body.winfo_reqheight() > self.canvas.winfo_height() + 1
        if needed:
            self.scrollbar.place(relx=1.0, rely=0.0, relheight=1.0, anchor=tk.NE)
        else:
            self.scrollbar.place_forget()
            self.canvas.yview_moveto(0.0)

    def scroll_units(self, units: int) -> None:
        if self.body.winfo_reqheight() > self.canvas.winfo_height() + 1:
            self.canvas.yview_scroll(units, "units")

    @classmethod
    def install_mouse_wheel(cls, root: tk.Misc) -> None:
        """Route wheel events over a page to that page's scroll container."""

        # A wheel over a combobox/spinbox would silently change its value
        # while the user only wanted to scroll the page.
        for widget_class in ("TCombobox", "TSpinbox"):
            for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                root.unbind_class(widget_class, sequence)

        def target(event: tk.Event) -> Optional["ScrollableFrame"]:
            try:
                widget = root.winfo_containing(event.x_root, event.y_root)
            except (KeyError, tk.TclError):
                return None
            while widget is not None:
                found = cls._registry.get(str(widget))
                if found is not None:
                    return found
                widget = widget.master
            return None

        def on_wheel(event: tk.Event, units: int) -> None:
            scroller = target(event)
            if scroller is not None:
                scroller.scroll_units(units)

        root.bind_all("<Button-4>", lambda event: on_wheel(event, -2), add="+")
        root.bind_all("<Button-5>", lambda event: on_wheel(event, 2), add="+")
        root.bind_all(
            "<MouseWheel>",
            lambda event: on_wheel(event, -2 if event.delta > 0 else 2),
            add="+",
        )


class Page(ttk.Frame):
    """A workflow page: scrollable form area plus a fixed action footer."""

    def __init__(self, parent: tk.Misc, theme: Theme, hint: str):
        super().__init__(parent, style="Page.TFrame")
        px = theme.px
        self.footer = ttk.Frame(self, style="Footer.TFrame", padding=theme.pad(22, 12, 22, 14))
        self.footer.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Frame(self, height=1, background=COLORS["border"]).pack(side=tk.BOTTOM, fill=tk.X)
        self.actions = ttk.Frame(self.footer, style="Footer.TFrame")
        self.actions.pack(fill=tk.X, pady=(0, px(10)))
        self.scroll = ScrollableFrame(self, theme, padding=theme.pad(22, 14, 30, 6))
        self.scroll.pack(fill=tk.BOTH, expand=True)
        self.body = self.scroll.body
        WrapLabel(self.body, text=hint, style="PageHint.TLabel").pack(
            fill=tk.X, pady=(0, px(12))
        )


def card(parent: tk.Misc, theme: Theme, title: Optional[str] = None) -> ttk.Frame:
    """Pack a white bordered card into ``parent`` and return its content frame."""
    px = theme.px
    outer = tk.Frame(
        parent,
        background=COLORS["surface"],
        highlightthickness=max(1, int(theme.scale)),
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["border"],
        borderwidth=0,
    )
    outer.pack(fill=tk.X, pady=(0, px(12)))
    inner = ttk.Frame(outer, style="Card.TFrame", padding=theme.pad(18, 12, 18, 14))
    inner.pack(fill=tk.BOTH, expand=True)
    if title:
        ttk.Label(inner, text=title, style="CardTitle.TLabel").pack(anchor=tk.W, pady=(0, px(8)))
    body = ttk.Frame(inner, style="Card.TFrame")
    body.pack(fill=tk.X)
    return body


def form_grid(parent: tk.Misc, theme: Theme, columns: int = 2) -> ttk.Frame:
    """A label/field grid with ``columns`` label+field pairs per row."""
    form = ttk.Frame(parent, style="Card.TFrame")
    form.pack(fill=tk.X)
    for index in range(columns):
        form.columnconfigure(index * 2, weight=0)
        form.columnconfigure(index * 2 + 1, weight=1, uniform="field")
    # Spare width goes mostly to an empty trailing column so fields keep a
    # readable length on wide windows but can still shrink on narrow ones.
    form.columnconfigure(columns * 2, weight=1)
    return form


def field_label(form: tk.Misc, theme: Theme, text: str, row: int, column: int = 0) -> ttk.Label:
    px = theme.px
    label = ttk.Label(form, text=text, style="Field.TLabel")
    label.grid(
        row=row,
        column=column * 2,
        sticky=tk.W,
        padx=(px(20) if column else 0, px(10)),
        pady=px(5),
    )
    return label


def place_field(widget: tk.Widget, theme: Theme, row: int, column: int = 0, span: int = 1, sticky=tk.EW) -> tk.Widget:
    widget.grid(
        row=row,
        column=column * 2 + 1,
        columnspan=span * 2 - 1,
        sticky=sticky,
        pady=theme.px(5),
    )
    return widget


# --------------------------------------------------------------------------- #
# Status pill
# --------------------------------------------------------------------------- #
def disc_image(root: tk.Misc, diameter: int, color: str, background: str) -> tk.PhotoImage:
    samples = 4
    fg, bg = _hex(color), _hex(background)
    radius = diameter / 2.0
    rows: List[str] = []
    for y in range(diameter):
        row = []
        for x in range(diameter):
            inside = 0
            for sy in range(samples):
                for sx in range(samples):
                    fx = x + (sx + 0.5) / samples - radius
                    fy = y + (sy + 0.5) / samples - radius
                    if fx * fx + fy * fy <= radius * radius:
                        inside += 1
            mixed = _mix(bg, fg, inside / float(samples * samples))
            row.append("#{:02x}{:02x}{:02x}".format(*(int(round(c * 255)) for c in mixed)))
        rows.append("{" + " ".join(row) + "}")
    image = tk.PhotoImage(master=root, width=diameter, height=diameter)
    image.put(" ".join(rows))
    return image


class StatusPill(tk.Canvas):
    """Rounded CARLA status badge that always sizes itself to its text."""

    KINDS = {
        "online": ("success_soft", "success_text", "success"),
        "offline": ("danger_soft", "danger_text", "danger"),
        "warning": ("warning_soft", "warning_text", "warning"),
        "checking": ("neutral_soft", "muted", "muted"),
    }

    def __init__(self, parent: tk.Misc, theme: Theme, background: str):
        self.theme = theme
        self.height = theme.px(30)
        super().__init__(
            parent,
            height=self.height,
            width=theme.px(120),
            background=background,
            highlightthickness=0,
            borderwidth=0,
        )
        self._background = background
        self._images: Dict[str, Tuple[tk.PhotoImage, tk.PhotoImage]] = {}
        self._state: Tuple[str, str] = ("", "")

    def _kind_images(self, kind: str) -> Tuple[tk.PhotoImage, tk.PhotoImage]:
        if kind not in self._images:
            soft, _text, dot = (COLORS[name] for name in self.KINDS[kind])
            self._images[kind] = (
                disc_image(self, self.height, soft, self._background),
                disc_image(self, self.theme.px(9), dot, soft),
            )
        return self._images[kind]

    def set(self, text: str, kind: str) -> None:
        if kind not in self.KINDS:
            kind = "checking"
        if self._state == (text, kind):
            return
        self._state = (text, kind)
        px = self.theme.px
        font = self.theme.font("pill")
        cap, dot = self._kind_images(kind)
        soft, text_color, _dot = (COLORS[name] for name in self.KINDS[kind])
        height = self.height
        dot_size = px(9)
        width = px(14) + dot_size + px(8) + font.measure(text) + px(16)
        self.configure(width=width)
        self.delete("all")
        self.create_image(0, 0, image=cap, anchor=tk.NW)
        self.create_image(width - height, 0, image=cap, anchor=tk.NW)
        self.create_rectangle(height // 2, 0, width - height // 2, height, fill=soft, width=0)
        self.create_image(px(14), height // 2, image=dot, anchor=tk.W)
        self.create_text(
            px(14) + dot_size + px(8),
            height // 2,
            text=text,
            anchor=tk.W,
            fill=text_color,
            font=font,
        )


# --------------------------------------------------------------------------- #
# Command preview
# --------------------------------------------------------------------------- #
PREVIEW_MIN_LINES = 2
PREVIEW_MAX_LINES = 4


def command_preview(parent: tk.Misc, theme: Theme) -> tk.Text:
    """Dark command box with a copy button; returns the (read-only) Text."""
    px = theme.px
    box = tk.Frame(parent, background=COLORS["console"], borderwidth=0)
    box.pack(fill=tk.X)
    header = tk.Frame(box, background=COLORS["console"])
    header.pack(fill=tk.X, padx=px(12), pady=(px(8), 0))
    tk.Label(
        header,
        text="LỆNH SẼ CHẠY",
        background=COLORS["console"],
        foreground=COLORS["console_muted"],
        font=theme.font("caps"),
    ).pack(side=tk.LEFT)
    row = tk.Frame(box, background=COLORS["console"])
    row.pack(fill=tk.X, pady=(px(2), px(6)))
    widget = tk.Text(
        row,
        height=PREVIEW_MIN_LINES,
        wrap=tk.WORD,
        font=theme.font("mono"),
        background=COLORS["console"],
        foreground=COLORS["console_text"],
        selectbackground=COLORS["primary"],
        inactiveselectbackground=COLORS["navy_soft"],
        relief=tk.FLAT,
        borderwidth=0,
        highlightthickness=0,
        padx=px(12),
        pady=px(6),
        state=tk.DISABLED,
        cursor="xterm",
    )

    copy_button = ttk.Button(header, text="Sao chép lệnh", style="Console.TButton")

    def copy_command() -> None:
        text = widget.get("1.0", tk.END).strip()
        if text:
            widget.clipboard_clear()
            widget.clipboard_append(text)
            copy_button.configure(text="Đã sao chép ✓")
            widget.after(1400, lambda: copy_button.configure(text="Sao chép lệnh"))

    copy_button.configure(command=copy_command)
    copy_button.pack(side=tk.RIGHT)
    widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
    scrollbar = ttk.Scrollbar(
        row,
        orient=tk.VERTICAL,
        command=widget.yview,
        style="Preview.Vertical.TScrollbar",
    )
    widget.configure(yscrollcommand=scrollbar.set)
    widget._aeb_scrollbar = scrollbar  # shown by fit_preview_height when needed
    widget.bind("<Configure>", lambda _event: schedule_fit_preview(widget), add="+")
    return widget


def fit_preview_height(widget: tk.Text) -> None:
    """Grow the preview to show the whole command (within limits)."""
    try:
        counted = widget.count("1.0", "end-1c", "displaylines")
    except tk.TclError:
        return
    if isinstance(counted, tuple):
        counted = counted[0] if counted else 0
    needed = (counted or 0) + 1
    lines = max(PREVIEW_MIN_LINES, min(PREVIEW_MAX_LINES, needed))
    if int(widget.cget("height")) != lines:
        widget.configure(height=lines)
    scrollbar = getattr(widget, "_aeb_scrollbar", None)
    if scrollbar is not None:
        if needed > PREVIEW_MAX_LINES and not scrollbar.winfo_ismapped():
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4))
        elif needed <= PREVIEW_MAX_LINES and scrollbar.winfo_ismapped():
            scrollbar.pack_forget()


def set_preview(widget: tk.Text, command: List[str]) -> None:
    widget.configure(state=tk.NORMAL)
    widget.delete("1.0", tk.END)
    widget.insert("1.0", command_text(command))
    widget.configure(state=tk.DISABLED)
    schedule_fit_preview(widget)


def schedule_fit_preview(widget: tk.Text) -> None:
    """Coalesce height fitting: many variable traces may fire per click."""
    if getattr(widget, "_aeb_fit_pending", False):
        return
    widget._aeb_fit_pending = True

    def run() -> None:
        widget._aeb_fit_pending = False
        fit_preview_height(widget)

    widget.after_idle(run)
