from functools import lru_cache
from itertools import product

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tracecache import profile_lru, simulate


def naive_lru(trace: list[str], capacity: int) -> int:
    """Independent list implementation, not the production OrderedDict simulator."""
    stack: list[str] = []
    misses = 0
    for key in trace:
        if key in stack:
            stack.remove(key)
        else:
            misses += 1
        stack.insert(0, key)
        del stack[capacity:]
    return misses


def exhaustive_optimal(trace: tuple[str, ...], capacity: int) -> int:
    """Enumerate every legal victim; no next-use logic shared with Belady."""

    @lru_cache(None)
    def visit(position: int, cache: frozenset[str]) -> int:
        if position == len(trace):
            return 0
        key = trace[position]
        if key in cache:
            return visit(position + 1, cache)
        if capacity == 0:
            return 1 + visit(position + 1, cache)
        if len(cache) < capacity:
            return 1 + visit(position + 1, cache | {key})
        return 1 + min(visit(position + 1, (cache - {v}) | {key}) for v in cache)

    return visit(0, frozenset())


@given(st.lists(st.sampled_from(["a", "b", "c", "d", "e", "界"]), max_size=160))
@settings(max_examples=250, derandomize=True)
def test_profile_against_independent_reference(trace: list[str]) -> None:
    profile = profile_lru(trace)
    for capacity in range(9):
        expected = naive_lru(trace, capacity)
        assert profile.misses(capacity) == expected
        assert simulate(trace, capacity, "lru") == expected
        assert simulate(trace, capacity, "belady") <= expected
    assert profile.cold_misses == len(set(trace))
    assert profile.misses(len(set(trace))) == len(set(trace))
    assert all(profile.misses(c) >= profile.misses(c + 1) for c in range(8))


def test_belady_matches_exhaustive_search() -> None:
    for length in range(8):
        for trace in product("abc", repeat=length):
            for capacity in range(4):
                assert simulate(trace, capacity, "belady") == exhaustive_optimal(trace, capacity)


@given(
    st.lists(st.sampled_from(["a", "b", "c", "d"]), max_size=80),
    st.floats(min_value=0, max_value=1, allow_nan=False),
)
@settings(max_examples=150, derandomize=True)
def test_sizing_is_minimal(trace: list[str], target: float) -> None:
    profile = profile_lru(trace)
    answer = profile.minimum_capacity(target)
    valid = [c for c in range(len(set(trace)) + 1) if profile.miss_ratio(c) <= target]
    assert answer == (min(valid) if valid else None)


def test_known_distances_and_boundary() -> None:
    p = profile_lru(list("abaca"))
    assert p.distances == (1,)
    assert p.cumulative_hits == (2,)
    assert [p.misses(c) for c in range(4)] == [5, 5, 3, 3]
    assert p.minimum_capacity(0.5) is None
    assert p.minimum_capacity(0.6) == 2


def test_fifo_can_exhibit_belady_anomaly() -> None:
    trace = list("123412512345")
    assert simulate(trace, 3, "fifo") == 9
    assert simulate(trace, 4, "fifo") == 10


@pytest.mark.parametrize("capacity", [-1, True, 1.5, "2"])
def test_bad_capacities(capacity: int) -> None:
    with pytest.raises(ValueError):
        profile_lru(["a"]).misses(capacity)
    with pytest.raises(ValueError):
        simulate(["a"], capacity)


@pytest.mark.parametrize("target", [float("nan"), float("inf"), -0.01, 1.01])
def test_bad_target(target: float) -> None:
    with pytest.raises(ValueError):
        profile_lru([]).minimum_capacity(target)


def test_empty_and_hot_object() -> None:
    assert profile_lru([]).miss_ratio(0) == 0
    assert profile_lru([]).minimum_capacity(0) == 0
    for policy in ["lru", "fifo", "belady"]:
        assert simulate([], 2, policy) == 0
        assert simulate(["a"] * 50_000, 1, policy) == 1
    assert profile_lru(["a"] * 50_000).misses(1) == 1


def test_unknown_policy_rejected_even_if_empty() -> None:
    with pytest.raises(ValueError):
        simulate([], 0, "unknown")
