"""Artifact hashing, path resolution, Git state and CSV output."""

from __future__ import annotations

import csv
import functools
import hashlib
import subprocess
from pathlib import Path


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
    path = Path(str(value))
    if path.is_absolute():
        return path
    for base in (PROJECT_ROOT, AEB_ROOT):
        candidate = base / path
        if candidate.exists():
            return candidate
    return PROJECT_ROOT / path

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
