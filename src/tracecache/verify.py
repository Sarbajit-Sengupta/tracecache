"""Recompute a report's declared analysis; this is not proof of trace provenance."""

import json
from pathlib import Path
from typing import Any

from . import __version__
from .profile import validate_capacity
from .report import analyze
from .trace import Trace, _unique_fields


def load_report(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        raw = stream.read(1_048_577)
    if len(raw) > 1_048_576:
        raise ValueError("verification report exceeds 1 MiB")
    try:
        report = json.loads(raw, object_pairs_hook=_unique_fields)
    except (ValueError, RecursionError) as exc:
        raise ValueError("invalid verification report JSON") from exc
    if not isinstance(report, dict):
        raise ValueError("verification report must be an object")
    return report


def verify(trace: Trace, report: dict[str, Any]) -> bool:
    if report.get("schema_version") != 2 or report.get("tool_version") != __version__:
        raise ValueError("verification requires schema 2 and the current tool version")
    curves = report.get("curves")
    if not isinstance(curves, list) or not 1 <= len(curves) <= 128:
        raise ValueError("verification requires 1–128 capacity rows")
    capacities = []
    for row in curves:
        if not isinstance(row, dict) or "capacity" not in row:
            raise ValueError("verification requires a capacity in every row")
        validate_capacity(row["capacity"])
        capacities.append(row["capacity"])
    window = report.get("window_size")
    target = report.get("target_miss_ratio")
    if isinstance(window, bool) or not isinstance(window, int) or window < 0:
        raise ValueError("invalid verification window size")
    if isinstance(target, bool) or not isinstance(target, (int, float)):
        raise ValueError("invalid verification target")
    mode = report.get("window_mode")
    if not isinstance(mode, str) or mode not in {"cold", "warm"}:
        raise ValueError("invalid verification window mode")
    computed = analyze(trace, capacities, target=target, window=window, window_mode=mode)
    return computed == report
