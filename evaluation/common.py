"""Small numeric and formatting helpers used by evaluation modules."""

from __future__ import annotations


def optional_round(value, digits):
    if value is None:
        return None
    return round(float(value), digits)

def numeric_values(rows, key):
    return [
        float(row[key])
        for row in rows
        if row.get(key) is not None and row.get(key) != ""
    ]

def max_value(rows, key):
    values = numeric_values(rows, key)
    return max(values) if values else 0

def format_number(value, digits):
    if value is None:
        return "--"
    return ("{:." + str(digits) + "f}").format(float(value))
