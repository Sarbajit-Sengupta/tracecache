"""Independent cache-policy simulators; all caches start empty.

Belady is an offline lower bound on misses under mandatory insertion and
equal object sizes. It is not an implementable online policy.
"""

import heapq
from collections import OrderedDict
from collections.abc import Sequence

from .profile import validate_capacity


def simulate(trace: Sequence[str], capacity: int, policy: str = "lru") -> int:
    validate_capacity(capacity)
    if policy not in {"lru", "fifo", "belady"}:
        raise ValueError("policy must be lru, fifo or belady")
    if capacity == 0:
        return len(trace)
    if policy == "belady":
        return _belady(trace, capacity)
    cache: OrderedDict[str, None] = OrderedDict()
    misses = 0
    for key in trace:
        if key in cache:
            if policy == "lru":
                cache.move_to_end(key)
        else:
            misses += 1
            if len(cache) == capacity:
                cache.popitem(last=False)
            cache[key] = None
    return misses


def _belady(trace: Sequence[str], capacity: int) -> int:
    never = len(trace)
    next_use = [never] * len(trace)
    future: dict[str, int] = {}
    for position in range(len(trace) - 1, -1, -1):
        key = trace[position]
        next_use[position] = future.get(key, never)
        future[key] = position
    cache: dict[str, int] = {}
    heap: list[tuple[int, str]] = []
    misses = 0
    for key, following in zip(trace, next_use, strict=True):
        if key not in cache:
            misses += 1
            if len(cache) == capacity:
                while heap:
                    negative_next, victim = heapq.heappop(heap)
                    if cache.get(victim) == -negative_next:
                        del cache[victim]
                        break
        cache[key] = following
        heapq.heappush(heap, (-following, key))
        # Lazy invalidation without unbounded heap growth on repeated hits.
        if len(heap) > 4 * capacity:
            heap = [(-following, key) for key, following in cache.items()]
            heapq.heapify(heap)
    return misses
