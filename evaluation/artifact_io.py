"""Artifact hashing, path resolution, Git state and CSV output."""

from __future__ import annotations

import csv
import functools
import hashlib
import subprocess
from pathlib import Path

from infrastructure.workspace import resolve_project_path as resolve_workspace_path


AEB_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = AEB_ROOT.parent


@functools.lru_cache(maxsize=32)
def sha256_file(path):
    path = Path(path)
    digest = hashlib.sha256()
    with open(str(path), "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def resolve_project_path(value):
    if not value:
        return None
    return resolve_workspace_path(
        value,
        project_root=PROJECT_ROOT,
        aeb_root=AEB_ROOT,
    )

def git_state(repository):
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            universal_newlines=True,
        ).strip()
        status = subprocess.check_output(
            ["git", "-C", str(repository), "status", "--porcelain"],
            universal_newlines=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None, None
    return commit, bool(status.strip())

def write_csv(path, fieldnames, rows):
    with open(str(path), "w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
