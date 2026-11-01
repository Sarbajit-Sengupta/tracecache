"""TraceCache command line; reports go to stdout unless --output is supplied."""

import argparse
import json
import sys
from pathlib import Path

from .report import analyze, render_svg
from .trace import read_trace


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
    parser.add_argument("--max-requests", type=int, default=1_000_000)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--svg", type=Path)
    args = parser.parse_args(argv)
    try:
        inputs = args.trace.resolve()
        destinations = [p.resolve() for p in (args.output, args.svg) if p is not None]
        if inputs in destinations or len(set(destinations)) != len(destinations):
            raise ValueError("input and output paths must be distinct")
        trace = read_trace(args.trace, max_requests=args.max_requests)
        report = analyze(trace, args.capacities, target=args.target, window=args.window)
        serialized = json.dumps(report, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.write_text(serialized, encoding="utf-8")
        else:
            sys.stdout.write(serialized)
        if args.svg:
            args.svg.write_text(render_svg(report), encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"tracecache: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
