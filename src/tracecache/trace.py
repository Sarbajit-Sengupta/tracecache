"""Strict, bounded JSON Lines input with a fingerprint of the exact bytes."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


class TraceError(ValueError):
    """Invalid input with a line-numbered diagnostic."""


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


def read_trace(
    path: Path,
    *,
    max_requests: int = 1_000_000,
    max_line_bytes: int = 65_536,
    max_bytes: int = 128 * 1024 * 1024,
) -> Trace:
    if min(max_requests, max_line_bytes, max_bytes) < 1:
        raise ValueError("input limits must be positive")
    keys: list[str] = []
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as stream:
        line_number = 0
        while raw := stream.readline(max_line_bytes + 1):
            line_number += 1
            if len(raw) > max_line_bytes:
                raise TraceError(f"line {line_number}: exceeds {max_line_bytes} bytes")
            total += len(raw)
            if total > max_bytes:
                raise TraceError(f"trace exceeds {max_bytes} bytes")
            if len(keys) == max_requests:
                raise TraceError(f"trace exceeds {max_requests} requests")
            digest.update(raw)
            try:
                record = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_fields)
            except (UnicodeDecodeError, ValueError, RecursionError) as exc:
                raise TraceError(f"line {line_number}: invalid UTF-8 JSON") from exc
            if not isinstance(record, dict) or set(record) != {"key"}:
                raise TraceError(f"line {line_number}: expected exactly one field: key")
            key = record["key"]
            if not isinstance(key, str) or not key or len(key) > 4096:
                raise TraceError(f"line {line_number}: key must be a 1–4096 character string")
            keys.append(key)
    return Trace(tuple(keys), digest.hexdigest(), total)
