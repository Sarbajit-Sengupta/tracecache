"""Strict, bounded JSON Lines input with a fingerprint of the exact bytes."""

import csv
import gzip
import hashlib
import json
import zlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class TraceError(ValueError):
    """Invalid input with a line-numbered diagnostic."""


class _LineReadable(Protocol):
    def readline(self, size: int = -1, /) -> bytes: ...


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("duplicate JSON field")
        result[name] = value
    return result


@dataclass(frozen=True)
class Trace:
    keys: tuple[str, ...]
    sha256: str
    byte_count: int
    trace_format: str = "jsonl"


def read_trace(
    path: Path,
    *,
    max_requests: int = 1_000_000,
    max_line_bytes: int = 65_536,
    max_bytes: int = 128 * 1024 * 1024,
    trace_format: str = "jsonl",
) -> Trace:
    if min(max_requests, max_line_bytes, max_bytes) < 1:
        raise ValueError("input limits must be positive")
    if trace_format not in {"jsonl", "csv"}:
        raise ValueError("trace format must be jsonl or csv")
    if path.stat().st_size > max_bytes:
        raise TraceError(f"input file exceeds {max_bytes} bytes")
    keys: list[str] = []
    digest = hashlib.sha256()
    total = 0

    def lines(stream: _LineReadable) -> Iterator[str]:
        nonlocal total
        line_number = 0
        while raw := stream.readline(max_line_bytes + 1):
            line_number += 1
            if len(raw) > max_line_bytes:
                raise TraceError(f"line {line_number}: exceeds {max_line_bytes} bytes")
            total += len(raw)
            if total > max_bytes:
                raise TraceError(f"trace exceeds {max_bytes} bytes")
            digest.update(raw)
            try:
                yield raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise TraceError(f"line {line_number}: invalid UTF-8") from exc

    def append(key: object, line_number: int) -> None:
        if len(keys) == max_requests:
            raise TraceError(f"trace exceeds {max_requests} requests")
        if not isinstance(key, str) or not key or len(key) > 4096:
            raise TraceError(f"line {line_number}: key must be a 1–4096 character string")
        keys.append(key)

    opener = gzip.open if path.suffix.lower() == ".gz" else open
    try:
        with opener(path, "rb") as stream:
            if trace_format == "jsonl":
                for line_number, line in enumerate(lines(stream), 1):
                    try:
                        record = json.loads(line, object_pairs_hook=_unique_fields)
                    except (ValueError, RecursionError) as exc:
                        raise TraceError(f"line {line_number}: invalid JSON") from exc
                    if not isinstance(record, dict) or set(record) != {"key"}:
                        raise TraceError(f"line {line_number}: expected exactly one field: key")
                    append(record["key"], line_number)
            else:
                reader = csv.reader(lines(stream), strict=True)
                if next(reader, None) != ["key"]:
                    raise TraceError("CSV must have exactly one header: key")
                for row in reader:
                    if len(row) != 1:
                        raise TraceError(f"line {reader.line_num}: expected one key column")
                    append(row[0], reader.line_num)
    except (EOFError, zlib.error, gzip.BadGzipFile, csv.Error) as exc:
        raise TraceError("invalid or truncated compressed/CSV trace") from exc
    return Trace(tuple(keys), digest.hexdigest(), total, trace_format)
