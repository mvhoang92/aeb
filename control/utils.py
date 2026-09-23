"""Small dependency-free control helpers."""

from __future__ import annotations

from typing import Optional


def first_existing_attr(obj: object, *names: str) -> Optional[float]:
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return float(value)
    return None

def set_if_present(obj: object, name: str, value: object) -> None:
    if hasattr(obj, name):
        setattr(obj, name, value)

def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))

def as_bool(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)
