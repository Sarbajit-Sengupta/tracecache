"""Mattson stack-distance profiling with a Fenwick tree of last occurrences.

Distances count distinct objects referenced since the previous occurrence.
A reuse at distance d hits a fully associative LRU cache iff capacity > d.
"""

from array import array
from bisect import bisect_left
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite


def validate_capacity(capacity: int) -> None:
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 0:
        raise ValueError("capacity must be a nonnegative integer object count")


class _Fenwick:
    def __init__(self, size: int) -> None:
        self.tree = array("q", [0]) * (size + 1)

    def add(self, index: int, delta: int) -> None:
        while index < len(self.tree):
            self.tree[index] += delta
            index += index & -index

    def prefix(self, index: int) -> int:
        total = 0
        while index:
            total += self.tree[index]
            index -= index & -index
        return total


@dataclass(frozen=True)
class LRUProfile:
    requests: int
    unique_objects: int
    cold_misses: int
    distances: tuple[int, ...]
    cumulative_hits: tuple[int, ...]

    def misses(self, capacity: int) -> int:
        validate_capacity(capacity)
        index = bisect_left(self.distances, capacity)
        hits = self.cumulative_hits[index - 1] if index else 0
        return self.requests - hits

    def miss_ratio(self, capacity: int) -> float:
        misses = self.misses(capacity)
        return misses / self.requests if self.requests else 0.0

    def minimum_capacity(self, target_miss_ratio: float) -> int | None:
        """Smallest object capacity meeting the observed target, or None.

        This is an in-sample sizing result, not a prediction of future traffic.
        """
        if not isfinite(target_miss_ratio) or not 0 <= target_miss_ratio <= 1:
            raise ValueError("target miss ratio must be finite and between zero and one")
        if self.miss_ratio(0) <= target_miss_ratio:
            return 0
        lo, hi = 1, self.unique_objects
        if self.miss_ratio(hi) > target_miss_ratio:
            return None
        while lo < hi:
            mid = (lo + hi) // 2
            if self.miss_ratio(mid) <= target_miss_ratio:
                hi = mid
            else:
                lo = mid + 1
        return lo


def profile_lru(trace: Sequence[str]) -> LRUProfile:
    """Compute exact LRU misses at all capacities in O(N log N) time.

    Tree storage is O(N), last-occurrence storage is O(U). Input is retained
    by the caller. This implementation deliberately does not claim streaming
    or bounded-memory processing of arbitrarily large traces.
    """
    tree = _Fenwick(len(trace))
    last: dict[str, int] = {}
    histogram: Counter[int] = Counter()
    active = 0
    for position, key in enumerate(trace, 1):
        previous = last.get(key)
        if previous is not None:
            histogram[active - tree.prefix(previous)] += 1
            tree.add(previous, -1)
        else:
            active += 1
        tree.add(position, 1)
        last[key] = position
    distances = tuple(sorted(histogram))
    cumulative: list[int] = []
    total = 0
    for distance in distances:
        total += histogram[distance]
        cumulative.append(total)
    return LRUProfile(len(trace), active, active, distances, tuple(cumulative))
