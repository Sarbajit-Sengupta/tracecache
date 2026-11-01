"""Reproducible microbenchmark: exact all-capacity profile vs K LRU replays.

No comparison with compiled cache simulators is implied. Input creation,
validation and filesystem IO are excluded from timed regions. Tracemalloc
is measured in separate invocations, not during the timing samples.
"""

import argparse
import gc
import hashlib
import json
import platform
import random
import statistics
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path

from tracecache import profile_lru, simulate


def workload(size: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    # Two hot-set phases separated by a scan. Entirely synthetic.
    return [
        str(
            (rng.randrange(128) if i < size // 2 else 1000 + rng.randrange(256))
            if i % 5
            else 100_000 + i
        )
        for i in range(size)
    ]


def measure_all(
    cases: dict[str, Callable[[], object]], repeat: int, seed: int
) -> dict[str, dict[str, object]]:
    samples: dict[str, list[float]] = {name: [] for name in cases}
    for call in cases.values():
        call()  # warm up every case
    rng = random.Random(seed)
    for _ in range(repeat):
        order = list(cases)
        rng.shuffle(order)  # reduce fixed method/order drift
        for name in order:
            gc.collect()
            started = time.perf_counter_ns()
            cases[name]()
            samples[name].append((time.perf_counter_ns() - started) / 1e9)
    result = {}
    for name, call in cases.items():
        gc.collect()
        tracemalloc.start()
        call()
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        result[name] = {
            "seconds": samples[name],
            "median_seconds": statistics.median(samples[name]),
            "min_seconds": min(samples[name]),
            "max_seconds": max(samples[name]),
            "python_allocation_peak_bytes": peak,
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=50_000)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--output", type=Path, default=Path("evidence/benchmark.json"))
    args = parser.parse_args()
    if args.requests < 1 or args.repeat < 3:
        parser.error("requests must be positive; repeat must be at least three")
    trace = workload(args.requests, args.seed)
    capacities = list(range(8, 513, 8))
    profile = profile_lru(trace)
    expected = [simulate(trace, c) for c in capacities]
    assert [profile.misses(c) for c in capacities] == expected
    cases: dict[str, Callable[[], object]] = {}
    for count in [1, 4, 16, len(capacities)]:
        selected = capacities[:count]

        def indexed(selected: list[int] = selected) -> list[int]:
            p = profile_lru(trace)
            return [p.misses(c) for c in selected]

        def replay(selected: list[int] = selected) -> list[int]:
            return [simulate(trace, c) for c in selected]

        cases[f"profile-{count}"] = indexed
        cases[f"replay-{count}"] = replay
    measurements = measure_all(cases, args.repeat, args.seed)
    rows = {
        str(count): {
            "fenwick_profile": measurements[f"profile-{count}"],
            "ordered_dict_replays": measurements[f"replay-{count}"],
        }
        for count in [1, 4, 16, len(capacities)]
    }
    result = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "requests": len(trace),
        "seed": args.seed,
        "workload": "synthetic two hot sets with 20% unique scan traffic",
        "trace_sha256": hashlib.sha256(json.dumps(trace).encode()).hexdigest(),
        "capacities": capacities,
        "repetitions": args.repeat,
        "sample_order": "seeded shuffle of all cases in every repetition after one warmup",
        "results": rows,
        "limitations": "single process/host; no CPU affinity; Python allocations exclude input; "
        "not RSS; only own OrderedDict baseline; no external performance claim",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
