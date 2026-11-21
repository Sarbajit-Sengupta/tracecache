"""Deterministic, key-free evidence reports and standalone SVG curves."""

from collections import OrderedDict
from collections.abc import Sequence
from typing import Any

from . import __version__
from .profile import profile_lru
from .simulate import simulate
from .trace import Trace


def analyze(
    trace: Trace,
    capacities: Sequence[int],
    *,
    target: float = 0.1,
    window: int = 0,
    window_mode: str = "cold",
) -> dict[str, Any]:
    if not capacities:
        raise ValueError("at least one capacity is required")
    if window < 0:
        raise ValueError("window must be nonnegative")
    if window_mode not in {"cold", "warm"}:
        raise ValueError("window mode must be cold or warm")
    profile = profile_lru(trace.keys)
    minimum = profile.minimum_capacity(target)
    rows = []
    for capacity in sorted(set(capacities)):
        lru = profile.misses(capacity)
        if capacity == 0 or capacity >= profile.unique_objects:
            # All mandatory-insertion policies share the same boundary counts.
            fifo = optimal = lru
        else:
            fifo = simulate(trace.keys, capacity, "fifo")
            optimal = simulate(trace.keys, capacity, "belady")
        rows.append(
            {
                "capacity": capacity,
                "lru_misses": lru,
                "fifo_misses": fifo,
                "belady_misses": optimal,
                "lru_gap_to_offline_optimum": lru - optimal,
            }
        )
    windows: list[dict[str, Any]] = []
    if window:
        for start in range(0, len(trace.keys), window):
            section = trace.keys[start : start + window]
            local = profile_lru(section) if window_mode == "cold" else None
            windows.append(
                {
                    "start": start,
                    "stop": start + len(section),
                    "cold_start": window_mode == "cold",
                    "misses": [
                        {"capacity": c, "lru_misses": local.misses(c) if local else 0}
                        for c in sorted(set(capacities))
                    ],
                }
            )
        if window_mode == "warm":
            for column, capacity in enumerate(sorted(set(capacities))):
                cache: OrderedDict[str, None] = OrderedDict()
                for position, key in enumerate(trace.keys):
                    if key in cache:
                        cache.move_to_end(key)
                    else:
                        row_index = position // window
                        entry = windows[row_index]["misses"][column]
                        entry["lru_misses"] += 1
                        if capacity:
                            if len(cache) == capacity:
                                cache.popitem(last=False)
                            cache[key] = None
    return {
        "schema_version": 2,
        "tool_version": __version__,
        "trace_sha256": trace.sha256,
        "trace_bytes": trace.byte_count,
        "trace_format": trace.trace_format,
        "requests": profile.requests,
        "unique_objects": profile.unique_objects,
        "cold_misses": profile.cold_misses,
        "model": "initially empty, fully associative, equal-sized objects, mandatory insertion",
        "target_miss_ratio": target,
        "minimum_lru_capacity": minimum,
        "recommendation_scope": "observed trace only; no future-workload guarantee",
        "curves": rows,
        "windows": windows,
        "window_size": window,
        "window_mode": window_mode,
    }


def render_svg(report: dict[str, Any]) -> str:
    rows = report["curves"]
    maximum = max(row["capacity"] for row in rows) or 1
    requests = report["requests"] or 1
    elements = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 420" '
        'role="img" aria-labelledby="title desc">',
        '<title id="title">Cache miss-ratio curves</title>',
        '<desc id="desc">Observed LRU and FIFO misses compared with offline Belady. '
        "Capacity is measured in equal-sized objects.</desc>",
        '<rect width="760" height="420" fill="#101827"/>',
        '<g fill="#e2e8f0" font-family="sans-serif" font-size="13">',
        '<text x="60" y="30" font-size="20">TraceCache · measured cache behavior</text>',
        '<text x="60" y="400">Capacity (objects) · offline, cold-start trace</text>',
    ]
    for tick in range(5):
        y = 340 - tick * 70
        elements.extend(
            [
                f'<path d="M60 {y} H700" stroke="#334155"/>',
                f'<text x="12" y="{y + 4}">{tick * 25}%</text>',
            ]
        )
    for field, color, label in [
        ("lru_misses", "#38bdf8", "LRU"),
        ("fifo_misses", "#fbbf24", "FIFO"),
        ("belady_misses", "#a78bfa", "Belady (offline)"),
    ]:
        points = " ".join(
            f"{60 + row['capacity'] / maximum * 640:.2f},{340 - row[field] / requests * 280:.2f}"
            for row in rows
        )
        elements.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.5"/>'
        )
        offset = {"LRU": 60, "FIFO": 210, "Belady (offline)": 360}[label]
        elements.append(f'<text x="{offset}" y="365" fill="{color}">{label}</text>')
    elements.extend(
        [
            '<text x="60" y="385">0</text>',
            f'<text x="660" y="385">{maximum}</text>',
            "</g></svg>",
        ]
    )
    return "\n".join(elements) + "\n"
