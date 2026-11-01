import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tracecache.cli import main
from tracecache.report import analyze, render_svg
from tracecache.trace import TraceError, read_trace


def fixture(tmp_path: Path, raw: bytes = b'{"key":"a"}\n{"key":"b"}\n{"key":"a"}\n') -> Path:
    path = tmp_path / "trace.jsonl"
    path.write_bytes(raw)
    return path


def test_strict_read_fingerprint_and_privacy(tmp_path: Path) -> None:
    path = fixture(tmp_path)
    trace = read_trace(path)
    assert trace.keys == ("a", "b", "a")
    assert trace.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert trace.byte_count == path.stat().st_size
    report = analyze(trace, [0, 1, 2], window=2)
    assert report["minimum_lru_capacity"] is None
    assert report["curves"][2]["lru_misses"] == 2
    assert report["windows"][1]["start"] == 2
    assert report["windows"][1]["cold_start"] is True
    assert '"keys"' not in json.dumps(report)
    assert analyze(trace, [2, 0, 1, 2], window=2) == report


@pytest.mark.parametrize(
    "raw",
    [
        b"\n",
        b"{}\n",
        b"[]\n",
        b'{"key":1}\n',
        b'{"key":null}\n',
        b'{"key":""}\n',
        b'{"key":"a","size":20}\n',
        b'{"key":"\xff"}\n',
        b"not-json\n",
        b'{"key":"' + b"a" * 4097 + b'"}\n',
    ],
)
def test_invalid_records(tmp_path: Path, raw: bytes) -> None:
    with pytest.raises(TraceError, match="line 1"):
        read_trace(fixture(tmp_path, raw))


def test_limits(tmp_path: Path) -> None:
    path = fixture(tmp_path)
    with pytest.raises(TraceError, match="requests"):
        read_trace(path, max_requests=2)
    with pytest.raises(TraceError, match="line 1"):
        read_trace(path, max_line_bytes=5)
    with pytest.raises(TraceError, match="bytes"):
        read_trace(path, max_bytes=20)
    with pytest.raises(ValueError, match="positive"):
        read_trace(path, max_requests=0)
    assert len(read_trace(path, max_requests=3).keys) == 3


def test_duplicate_fields_rejected(tmp_path: Path) -> None:
    with pytest.raises(TraceError):
        read_trace(fixture(tmp_path, b'{"key":"a","key":"b"}\n'))


def test_cli_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(fixture(tmp_path)), "--capacities", "1,2"]) == 0
    assert json.loads(capsys.readouterr().out)["requests"] == 3


def test_utf8_crlf_and_missing_final_newline(tmp_path: Path) -> None:
    path = fixture(tmp_path, '{"key":"界"}\r\n{"key":"界"}'.encode())
    assert read_trace(path).keys == ("界", "界")


def test_cli_roundtrip_and_svg(tmp_path: Path) -> None:
    path = fixture(tmp_path)
    output, svg = tmp_path / "report.json", tmp_path / "curve.svg"
    assert (
        main(
            [
                str(path),
                "--capacities",
                "0,1,2",
                "--output",
                str(output),
                "--svg",
                str(svg),
                "--window",
                "2",
            ]
        )
        == 0
    )
    report = json.loads(output.read_text())
    assert report["requests"] == 3
    root = ET.fromstring(svg.read_text())
    assert len(root.findall(".//{http://www.w3.org/2000/svg}polyline")) == 3


@pytest.mark.parametrize(
    "arguments", [["--target", "nan"], ["--window", "-1"], ["--max-requests", "0"]]
)
def test_cli_invalid_options(tmp_path: Path, arguments: list[str]) -> None:
    assert main([str(fixture(tmp_path)), *arguments]) == 2


@pytest.mark.parametrize("capacities", ["", "-1", "a", "1,", ",".join(["1"] * 129)])
def test_cli_invalid_capacities(tmp_path: Path, capacities: str) -> None:
    with pytest.raises(SystemExit) as result:
        main([str(fixture(tmp_path)), "--capacities", capacities])
    assert result.value.code == 2


def test_cli_does_not_overwrite_input(tmp_path: Path) -> None:
    path = fixture(tmp_path)
    original = path.read_bytes()
    assert main([str(path), "--output", str(path)]) == 2
    assert path.read_bytes() == original
    output = tmp_path / "same"
    assert main([str(path), "--output", str(output), "--svg", str(output)]) == 2


def test_cli_process_exit_and_missing_input(tmp_path: Path) -> None:
    run = subprocess.run(
        [sys.executable, "-m", "tracecache.cli", str(fixture(tmp_path)), "--capacities", "0,2"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert run.returncode == 0
    assert json.loads(run.stdout)["requests"] == 3
    assert main([str(tmp_path / "missing")]) == 2


def test_report_validates_options(tmp_path: Path) -> None:
    trace = read_trace(fixture(tmp_path))
    with pytest.raises(ValueError):
        analyze(trace, [])
    with pytest.raises(ValueError):
        analyze(trace, [1], window=-1)


def test_empty_svg_is_valid(tmp_path: Path) -> None:
    trace = read_trace(fixture(tmp_path, b""))
    report = analyze(trace, [0])
    assert report["minimum_lru_capacity"] == 0
    ET.fromstring(render_svg(report))
