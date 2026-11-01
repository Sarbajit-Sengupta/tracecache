"""TraceCache command line; reports go to stdout unless --output is supplied."""

import argparse
import json
import sys
from pathlib import Path

from .output import atomic_write, check_distinct
from .report import analyze, render_svg
from .trace import read_trace
from .verify import load_report, verify


def _capacities(value: str) -> list[int]:
    try:
        result = [int(piece) for piece in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("capacities must be comma-separated integers") from exc
    if not result or min(result) < 0 or len(result) > 128:
        raise argparse.ArgumentTypeError("provide 1–128 nonnegative capacities")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Exact offline cache sizing for equal-sized objects"
    )
    parser.add_argument("trace", type=Path, help='JSONL: one {"key":"object-id"} per line')
    parser.add_argument("--capacities", type=_capacities, default=[0, 16, 64, 256])
    parser.add_argument("--target", type=float, default=0.1, help="observed target miss ratio")
    parser.add_argument("--window", type=int, default=0, help="cold-start phase window in requests")
    parser.add_argument("--window-mode", choices=["cold", "warm"], default="cold")
    parser.add_argument("--format", choices=["jsonl", "csv"], default="jsonl")
    parser.add_argument(
        "--verify", type=Path, help="recompute an existing report instead of writing"
    )
    parser.add_argument("--max-requests", type=int, default=1_000_000)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--svg", type=Path)
    args = parser.parse_args(argv)
    try:
        check_distinct([args.trace, *[p for p in (args.output, args.svg) if p is not None]])
        trace = read_trace(args.trace, max_requests=args.max_requests, trace_format=args.format)
        if args.verify:
            if args.output or args.svg:
                raise ValueError("--verify cannot be combined with output files")
            if not verify(trace, load_report(args.verify)):
                print(
                    "tracecache: report does not match the trace and recomputed counts",
                    file=sys.stderr,
                )
                return 1
            print("Verified: trace fingerprint and all recomputed report fields match.")
            return 0
        report = analyze(
            trace,
            args.capacities,
            target=args.target,
            window=args.window,
            window_mode=args.window_mode,
        )
        serialized = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if args.output:
            atomic_write(args.output, serialized)
        else:
            sys.stdout.write(serialized)
        if args.svg:
            atomic_write(args.svg, render_svg(report))
    except (OSError, ValueError) as exc:
        print(f"tracecache: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
