# Launcher Redesign Validation

## Change

- Removed the misspelled `laucher.py` compatibility entry point by maintainer
  request. `launcher.py` is the sole desktop launcher.
- Reworked the Tk interface as **AEB Control Center** with a consistent color
  system, clear four-step workflow, colored CARLA status, command-copy actions,
  resizable process console and clearer Vietnamese labels.
- Added keyboard shortcuts: `Ctrl+1` … `Ctrl+4` switch workflow tabs, `F5`
  checks CARLA and `Ctrl+L` clears the process log.
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
- Headless Tk build at 1240×900: PASS.
- All four tabs instantiated and command previews remained visible: PASS.
- Compile audit and `git diff --check`: PASS.
- Workspace, report-v3/paper-v4 and paper-v5 validators: PASS.
