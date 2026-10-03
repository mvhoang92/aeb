"""Small reusable Tk widgets for the test bench."""

from __future__ import absolute_import

import tkinter as tk
from tkinter import ttk


STATE_UNCHECKED = "unchecked"
STATE_CHECKED = "checked"
STATE_PARTIAL = "partial"


def checkbox_images(root, theme):
    """Three PhotoImages (unchecked/checked/partial) drawn at the DPI scale."""
    c = theme.colors
    size = max(12, theme.px(14))
    pad = max(1, theme.px(2))
    width = size + 2 * pad
    images = {}
    for state in (STATE_UNCHECKED, STATE_CHECKED, STATE_PARTIAL):
        image = tk.PhotoImage(master=root, width=width + pad, height=width)
        x0, y0, x1, y1 = pad, pad, pad + size, pad + size
        border = c["border_strong"] if state == STATE_UNCHECKED else c["accent"]
        fill = c["surface"] if state == STATE_UNCHECKED else c["accent"]
        image.put(border, to=(x0, y0, x1, y1))
        line = max(1, theme.px(1))
        image.put(fill, to=(x0 + line, y0 + line, x1 - line, y1 - line))
        if state == STATE_PARTIAL:
            bar = max(2, theme.px(2))
            mid = (y0 + y1) // 2
            image.put("#FFFFFF", to=(x0 + size // 4, mid - bar // 2, x1 - size // 4, mid - bar // 2 + bar))
        elif state == STATE_CHECKED:
            stroke = max(2, theme.px(2))
            # Check mark: short leg down-right, then long leg up-right.
            points = []
            sx, sy = x0 + size * 0.22, y0 + size * 0.52
            mx, my = x0 + size * 0.42, y0 + size * 0.72
            ex, ey = x0 + size * 0.80, y0 + size * 0.28
            steps = size * 2
            for i in range(steps + 1):
                t = i / float(steps)
                points.append((sx + (mx - sx) * t, sy + (my - sy) * t))
                points.append((mx + (ex - mx) * t, my + (ey - my) * t))
            for px, py in points:
                ix, iy = int(px), int(py)
                image.put("#FFFFFF", to=(ix, iy, ix + stroke, iy + stroke))
        images[state] = image
    return images


class Tooltip(object):
    """Hover help for any widget (shown after a short delay)."""

    def __init__(self, widget, text, theme, delay_ms=450):
        self.widget = widget
        self.text = text
        self.theme = theme
        self.delay_ms = delay_ms
        self._after = None
        self._window = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self._after = self.widget.after(self.delay_ms, self._show)

    def _cancel(self):
        if self._after is not None:
            try:
                self.widget.after_cancel(self._after)
            except tk.TclError:
                pass
            self._after = None

    def _show(self):
        if self._window is not None or not self.text:
            return
        c = self.theme.colors
        x = self.widget.winfo_rootx() + self.theme.px(12)
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + self.theme.px(4)
        window = tk.Toplevel(self.widget)
        window.wm_overrideredirect(True)
        window.configure(background=c["border_strong"])
        label = tk.Label(
            window,
            text=self.text,
            justify="left",
            wraplength=self.theme.px(380),
            background="#FFFFF4",
            foreground=c["text"],
            font=self.theme.font("small"),
            padx=self.theme.px(8),
            pady=self.theme.px(5),
        )
        label.pack(padx=1, pady=1)
        window.wm_geometry("+{}+{}".format(x, y))
        self._window = window

    def _hide(self, _event=None):
        self._cancel()
        if self._window is not None:
            self._window.destroy()
            self._window = None


class ScrollFrame(ttk.Frame):
    """Vertically scrollable container; put children into ``.body``."""

    def __init__(self, master, theme, style="Plain.TFrame", **kwargs):
        ttk.Frame.__init__(self, master, style=style, **kwargs)
        background = theme.colors["surface"]
        self.canvas = tk.Canvas(
            self, highlightthickness=0, borderwidth=0, background=background
        )
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.body = ttk.Frame(self.canvas, style=style)
        self._window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.body.bind("<Configure>", self._on_body)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.bind_all_wheel(self.canvas)
        self.bind_all_wheel(self.body)

    def bind_all_wheel(self, widget):
        widget.bind("<Enter>", lambda _e: self._wheel(True), add="+")
        widget.bind("<Leave>", lambda _e: self._wheel(False), add="+")

    def _wheel(self, active):
        if active:
            self.canvas.bind_all("<Button-4>", lambda _e: self.canvas.yview_scroll(-2, "units"))
            self.canvas.bind_all("<Button-5>", lambda _e: self.canvas.yview_scroll(2, "units"))
            self.canvas.bind_all(
                "<MouseWheel>",
                lambda e: self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"),
            )
        else:
            for sequence in ("<Button-4>", "<Button-5>", "<MouseWheel>"):
                self.canvas.unbind_all(sequence)

    def _on_scroll(self, first, last):
        self.scrollbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.scrollbar.grid_remove()
        else:
            self.scrollbar.grid()

    def _on_body(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)


class Section(ttk.Frame):
    """White card with a numbered heading and a short explanation."""

    def __init__(self, master, theme, number, title, subtitle=None, scroll=False):
        ttk.Frame.__init__(self, master, style="Card.TFrame", padding=theme.px(1))
        self.theme = theme
        head = ttk.Frame(self, style="Plain.TFrame", padding=(theme.px(10), theme.px(8), theme.px(10), theme.px(2)))
        head.grid(row=0, column=0, sticky="ew")
        ttk.Label(head, text=str(number), style="SectionNo.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(head, text=title, style="Section.TLabel").grid(
            row=0, column=1, sticky="w", padx=(theme.px(8), 0)
        )
        self.head_right = ttk.Frame(head, style="Plain.TFrame")
        self.head_right.grid(row=0, column=2, sticky="e")
        head.columnconfigure(2, weight=1)
        if subtitle:
            self.subtitle = ttk.Label(
                head, text=subtitle, style="Muted.TLabel", justify="left"
            )
            self.subtitle.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(theme.px(2), 0))
            wrap_label(self.subtitle)
        if scroll:
            self.scroller = ScrollFrame(self, theme)
            self.scroller.grid(row=1, column=0, sticky="nsew")
            self.body = ttk.Frame(self.scroller.body, style="Plain.TFrame", padding=(theme.px(10), theme.px(4), theme.px(10), theme.px(10)))
            self.body.pack(fill="both", expand=True)
        else:
            self.body = ttk.Frame(self, style="Plain.TFrame", padding=(theme.px(10), theme.px(4), theme.px(10), theme.px(10)))
            self.body.grid(row=1, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)


def wrap_label(label, margin=4):
    """Make a label re-wrap its text to its current width."""

    def _configure(event):
        width = max(50, event.width - margin)
        if int(float(str(label.cget("wraplength") or 0))) != width:
            label.configure(wraplength=width)

    label.bind("<Configure>", _configure, add="+")
    return label


class Pill(tk.Label):
    """Rounded-looking status badge (flat label with coloured background)."""

    KINDS = {
        "online": ("pass", "pass_bg"),
        "offline": ("fail", "fail_bg"),
        "neutral": ("muted", "surface_alt"),
        "pass": ("pass", "pass_bg"),
        "fail": ("fail", "fail_bg"),
        "warn": ("warn", "warn_bg"),
        "tech": ("tech", "tech_bg"),
        "info": ("accent", "accent_soft"),
    }

    def __init__(self, master, theme, text="", kind="neutral", **kwargs):
        self.theme = theme
        tk.Label.__init__(
            self,
            master,
            text=text,
            font=theme.font("pill"),
            padx=theme.px(9),
            pady=theme.px(2),
            borderwidth=0,
            **kwargs
        )
        self.set(text, kind)

    def set(self, text, kind="neutral"):
        foreground, background = self.KINDS.get(kind, self.KINDS["neutral"])
        self.configure(
            text=text,
            foreground=self.theme.colors[foreground],
            background=self.theme.colors[background],
        )


def readonly_text(master, theme, height=3, mono=True, dark=False):
    c = theme.colors
    text = tk.Text(
        master,
        height=height,
        wrap="word",
        font=theme.font("mono" if mono else "small"),
        background=c["log_bg"] if dark else c["surface_alt"],
        foreground=c["log_text"] if dark else c["text"],
        insertbackground=c["log_text"] if dark else c["text"],
        relief="flat",
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=c["border"],
        highlightcolor=c["border"],
        padx=theme.px(8),
        pady=theme.px(6),
    )
    text.configure(state="disabled")
    return text


def set_text(widget, value):
    widget.configure(state="normal")
    widget.delete("1.0", "end")
    widget.insert("1.0", value)
    widget.configure(state="disabled")
