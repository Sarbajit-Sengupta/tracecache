import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tracecache import profile_lru, simulate
from tracecache.cli import main
from tracecache.report import analyze
from tracecache.trace import Trace, read_trace
from tracecache.verify import load_report, verify


@given(
    st.lists(st.sampled_from(["a", "b", "c", "d"]), max_size=100),
    st.integers(min_value=1, max_value=15),
)
@settings(max_examples=100, derandomize=True)
def test_warmed_window_counts_partition_global_counts(keys: list[str], window: int) -> None:
    trace = Trace(tuple(keys), "synthetic", 0)
    report = analyze(trace, [0, 1, 3, 5], window=window, window_mode="warm")
    for column, capacity in enumerate([0, 1, 3, 5]):
        total = sum(w["misses"][column]["lru_misses"] for w in report["windows"])
        assert total == profile_lru(keys).misses(capacity)
    assert all(not row["cold_start"] for row in report["windows"])


def test_warmed_and_cold_windows_differ() -> None:
    trace = Trace(("a", "b", "a", "b"), "synthetic", 0)
    warm = analyze(trace, [2], window=2, window_mode="warm")
    cold = analyze(trace, [2], window=2)
    assert warm["windows"][1]["misses"][0]["lru_misses"] == 0
    assert cold["windows"][1]["misses"][0]["lru_misses"] == 2
    with pytest.raises(ValueError, match="window mode"):
        analyze(trace, [2], window_mode="invalid")


def test_boundary_capacities_avoid_replaying_trace() -> None:
    trace = Trace(("a", "b", "a"), "synthetic", 0)
    with patch("tracecache.report.simulate", side_effect=AssertionError("unneeded replay")):
        report = analyze(trace, [0, 2, 10**9])
    for row in report["curves"]:
        for policy in ["lru", "fifo", "belady"]:
            assert row[policy + "_misses"] == simulate(trace.keys, row["capacity"], policy)


def test_verify_round_trip_and_tampering(tmp_path: Path) -> None:
    source, output = tmp_path / "trace", tmp_path / "report"
    source.write_bytes(b'{"key":"a"}\n{"key":"a"}\n')
    assert (
        main([str(source), "--output", str(output), "--window", "1", "--window-mode", "warm"]) == 0
    )
    assert main([str(source), "--verify", str(output)]) == 0
    report = load_report(output)
    changed = copy.deepcopy(report)
    changed["curves"][0]["lru_misses"] += 1
    output.write_text(json.dumps(changed))
    assert main([str(source), "--verify", str(output)]) == 1
    output.write_text(json.dumps(report))
    source.write_bytes(b'{"key":"b"}\n{"key":"b"}\n')
    assert main([str(source), "--verify", str(output)]) == 1
    assert main([str(source), "--verify", str(output), "--output", str(tmp_path / "x")]) == 2


@pytest.mark.parametrize(
    "patches",
    [
        {"schema_version": 1},
        {"tool_version": "unknown"},
        {"curves": []},
        {"curves": [None]},
        {"curves": [{"capacity": True}]},
        {"window_size": -1},
        {"window_size": True},
        {"target_miss_ratio": "0.5"},
        {"target_miss_ratio": True},
        {"target_miss_ratio": float("nan")},
        {"window_mode": []},
    ],
)
def test_verify_rejects_malformed_configuration(patches: dict[str, object]) -> None:
    trace = Trace(("a",), "synthetic", 0)
    report = analyze(trace, [1])
    report.update(patches)
    with pytest.raises(ValueError):
        verify(trace, report)


@pytest.mark.parametrize(
    "raw", [b"invalid", b"[]", b'{"a":1,"a":2}', b"[" * 2000, b" " * 1_048_577]
)
def test_invalid_report_files(tmp_path: Path, raw: bytes) -> None:
    path = tmp_path / "report"
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        load_report(path)


def test_verifier_checks_trace_format(tmp_path: Path) -> None:
    path = tmp_path / "trace.csv"
    path.write_bytes(b"key\na\na\n")
    trace = read_trace(path, trace_format="csv")
    report = analyze(trace, [1])
    assert verify(trace, report)
    report["trace_format"] = "jsonl"
    assert not verify(trace, report)
