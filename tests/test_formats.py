import csv
import gzip
import hashlib
import io
from pathlib import Path

import pytest

from tracecache.cli import main
from tracecache.trace import TraceError, read_trace


def test_gzip_matches_plain_content(tmp_path: Path) -> None:
    raw = '{"key":"界"}\n{"key":"b"}\n{"key":"界"}\n'.encode()
    plain, compressed = tmp_path / "trace.jsonl", tmp_path / "trace.jsonl.gz"
    plain.write_bytes(raw)
    compressed.write_bytes(gzip.compress(raw, mtime=0))
    assert read_trace(compressed) == read_trace(plain)
    assert read_trace(compressed).sha256 == hashlib.sha256(raw).hexdigest()


def test_gzip_decoded_limits(tmp_path: Path) -> None:
    path = tmp_path / "trace.gz"
    path.write_bytes(gzip.compress(b'{"key":"a"}\n' * 1000, mtime=0))
    with pytest.raises(TraceError, match="bytes"):
        read_trace(path, max_bytes=100)
    with pytest.raises(TraceError, match="requests"):
        read_trace(path, max_requests=10)
    with pytest.raises(TraceError, match="line 1"):
        read_trace(path, max_line_bytes=5)


@pytest.mark.parametrize("payload", [b"not gzip", gzip.compress(b'{"key":"a"}\n')[:-5]])
def test_bad_gzip_is_cli_error(tmp_path: Path, payload: bytes) -> None:
    path = tmp_path / "bad.gz"
    path.write_bytes(payload)
    assert main([str(path)]) == 2


@pytest.mark.parametrize("compressed", [False, True])
def test_csv_multiline_unicode_and_quoting(tmp_path: Path, compressed: bool) -> None:
    keys = ["a,b", 'quote"value', "two\nlines", "界", "a,b"]
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["key"])
    writer.writerows([[key] for key in keys])
    raw = stream.getvalue().encode()
    path = tmp_path / ("trace.csv.gz" if compressed else "trace.csv")
    path.write_bytes(gzip.compress(raw, mtime=0) if compressed else raw)
    trace = read_trace(path, trace_format="csv")
    assert trace.keys == tuple(keys)
    assert trace.trace_format == "csv"
    assert trace.byte_count == len(raw)
    assert trace.sha256 == hashlib.sha256(raw).hexdigest()
    assert main([str(path), "--format", "csv", "--capacities", "1,4"]) == 0


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"other\na\n",
        b"key,extra\na,b\n",
        b"key\na,b\n",
        b'key\n"unterminated',
        b"key\n\n",
        b'key\n""\n',
    ],
)
def test_invalid_csv(tmp_path: Path, payload: bytes) -> None:
    path = tmp_path / "bad.csv"
    path.write_bytes(payload)
    with pytest.raises(TraceError):
        read_trace(path, trace_format="csv")


def test_csv_limits_and_header_only(tmp_path: Path) -> None:
    path = tmp_path / "trace.csv"
    path.write_bytes(b"key\na\nb\n")
    assert read_trace(path, trace_format="csv", max_requests=2).keys == ("a", "b")
    with pytest.raises(TraceError, match="requests"):
        read_trace(path, trace_format="csv", max_requests=1)
    path.write_bytes(b"key\n")
    assert read_trace(path, trace_format="csv").keys == ()
    with pytest.raises(ValueError, match="format"):
        read_trace(path, trace_format="xml")
