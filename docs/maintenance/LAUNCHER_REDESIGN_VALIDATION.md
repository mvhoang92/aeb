# Launcher Redesign Validation

## Change

- Removed the misspelled `laucher.py` compatibility entry point by maintainer
  request. `launcher.py` is the sole desktop launcher.
- Reworked the Tk interface as **AEB Control Center** with a consistent color
  system, clear four-step workflow, colored CARLA status, command-copy actions,
  resizable process console and clearer Vietnamese labels.
- Added keyboard shortcuts: `Ctrl+1` … `Ctrl+4` switch workflow tabs, `F5`
  checks CARLA and `Ctrl+L` clears the process log.
- Added automatic re-execution through `/usr/bin/python3` when the currently
  activated CARLA/YOLO virtual environment does not provide Tkinter.
- Updated current documentation and launcher tests. Frozen report/paper history
  was not rewritten.

## Compatibility boundary

This is an intentional entry-point breaking change only for callers that still
spell the file `laucher.py`. Process commands, scenario selection, policy
configuration and runtime behavior were not changed. AST comparison against the
previous commit matched all command builders and start/stop methods.

## Validation

- 96 unit/golden/compatibility tests: PASS.
- Canonical `launcher.py --check`: PASS, 66 scenarios.
- `python3 launcher.py --check` from the Tkinter-free CARLA venv: PASS via
  deterministic system-Python fallback.
- Headless Tk build at 1240×900: PASS.
- All four tabs instantiated and command previews remained visible: PASS.
- Compile audit and `git diff --check`: PASS.
- Workspace, report-v3/paper-v4 and paper-v5 validators: PASS.

## Sidebar redesign (2026-10-03)

- `launcher.py` is now a thin entry point; the UI lives in `ui/launcher/`
  (`commands.py` pure command builders, `processes.py`, `theme.py`,
  `widgets.py`, `app.py`, `pages/`).
- Tabs replaced by a left sidebar, scrollable pages, a fixed command footer and
  a resizable process log; Tk scaling follows `Xft.dpi` (override with
  `AEB_LAUNCHER_SCALE`). New options: `--page carla|apps|tests|video`,
  `--geometry WxH`.
- A dump of 15,536 generated commands/previews was byte-identical before the
  split, after the split and after the redesign. Tests:
  `tests/test_launcher_commands.py`, `tests/test_launcher_gui.py` (xvfb).
