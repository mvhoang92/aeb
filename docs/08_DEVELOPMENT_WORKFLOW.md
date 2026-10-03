# Development Workflow

1. Start from a clean, pushed branch and record rollback tag/commit.
2. Separate structural refactor, cleanup and algorithm research branches.
3. Use small commits with compatibility wrappers.
4. Never delete dataset/log/output as an incidental code change.
5. Run unit, claim, compile/import and whitespace gates after each checkpoint.
6. Run CARLA/CUDA smoke when runtime/policy/path behavior changes.
7. Do not merge automatically; present validation evidence for review.

Technical failures may be retried only with recorded reason. Algorithmic FAIL
must remain in summaries. No post-hold-out tuning and no reuse of frozen
hold-out for a new algorithm.

Canonical commands:

```bash
../venv/bin/python -m unittest discover -s tests -q
../venv/bin/python scripts/validate_v4_manuscript_claims.py
../venv/bin/python scripts/validate_v5_manuscript_claims.py
../venv/bin/python scripts/validate_v51_manuscript_claims.py
../venv/bin/python scripts/validate_v52_manuscript_claims.py
../venv/bin/python -m compileall -q control core evaluation infrastructure perception scripts tests ui

git diff --check
```

## Continuous integration

`.github/workflows/tests.yml` runs on every push and pull request
(`ubuntu-22.04`, Python 3.7.17, pinned
`environments/requirements-ci-py37.txt`, plus `poppler-utils`, `python3-tk`,
`python3-yaml` and `xvfb` from apt). It runs the unit tests and the four
manuscript validators against tracked frozen evidence only; it has no CARLA,
GPU or `aeb_workspace`.

The job sets `AEB_CI=1`. Only then do the guards in `tests/ci_support.py` turn
a missing CARLA 0.9.11 PythonAPI egg (not on PyPI) or a missing sibling CARLA
install (`../CarlaUE4.sh`, `../venv`) into an explicit `AEB_CI:` skip. On the
workstation the guards are inert, so a missing resource still fails. Reproduce
the CI job locally with a throwaway venv:

```bash
/usr/bin/python3.7 -m venv /tmp/aeb-ci-venv
/tmp/aeb-ci-venv/bin/python -m pip install -r environments/requirements-ci-py37.txt
AEB_CI=1 MPLBACKEND=Agg /tmp/aeb-ci-venv/bin/python -m unittest discover -s tests -v
```

Before public release, audit dataset/model licenses and use Release/LFS/external
storage for large artifacts.
