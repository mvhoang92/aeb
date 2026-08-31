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
../venv/bin/python -m compileall -q control core evaluation infrastructure perception scripts tests ui

git diff --check
```

Before public release, audit dataset/model licenses and use Release/LFS/external
storage for large artifacts.
