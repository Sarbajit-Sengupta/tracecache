from pathlib import Path
from unittest.mock import patch

import pytest

from tracecache.cli import main
from tracecache.output import atomic_write


def test_input_hardlink_is_not_overwritten(tmp_path: Path) -> None:
    source, alias = tmp_path / "input.jsonl", tmp_path / "alias.json"
    source.write_text('{"key":"a"}\n')
    alias.hardlink_to(source)
    original = source.read_bytes()
    assert main([str(source), "--output", str(alias)]) == 2
    assert source.read_bytes() == original
    assert alias.read_bytes() == original


def test_output_hardlinks_rejected(tmp_path: Path) -> None:
    source, report, svg = tmp_path / "input", tmp_path / "report", tmp_path / "svg"
    source.write_text('{"key":"a"}\n')
    report.write_text("unchanged")
    svg.hardlink_to(report)
    assert main([str(source), "--output", str(report), "--svg", str(svg)]) == 2
    assert report.read_text() == "unchanged"


@pytest.mark.parametrize("operation", ["os.replace", "os.fsync"])
def test_interrupted_output_preserves_previous_file(tmp_path: Path, operation: str) -> None:
    target = tmp_path / "report.json"
    target.write_text("old completed report")
    with patch("tracecache.output." + operation, side_effect=OSError("injected failure")):
        with pytest.raises(OSError):
            atomic_write(target, "new contents")
    assert target.read_text() == "old completed report"
    assert list(tmp_path.glob(".tracecache-*.tmp")) == []


def test_atomic_utf8_and_newline(tmp_path: Path) -> None:
    path = tmp_path / "report"
    atomic_write(path, "界\n")
    assert path.read_bytes() == "界\n".encode()
    atomic_write(path, "replacement\n")
    assert path.read_bytes() == b"replacement\n"


def test_output_failure_is_nonzero(tmp_path: Path) -> None:
    path = tmp_path / "trace"
    path.write_text('{"key":"a"}\n')
    assert main([str(path), "--output", str(tmp_path / "absent" / "out")]) == 2
