# Design decisions and invariants

## Decision 001: exact equal-sized model first

Choosing equal-sized objects gives a precise relationship between reuse distance and LRU misses.
A byte-capacity simulator with oversized-object bypass has different semantics and cannot be
silently substituted. Variable-size Belady is not generally an optimal oracle. The schema rejects
size fields instead of pretending they were modeled. TTL/admission/write semantics are out of scope.

## Decision 002: a positional Fenwick tree

Before processing position i, each distinct key has exactly one active marker: its latest position
strictly before i. The sum of all markers equals the distinct count. If a key's last position was p,
`active - prefix(p)` counts more-recent distinct objects; this is its zero-based reuse distance.
Remove marker p, insert marker i. First references increase active and compulsory misses.

The array uses signed 64-bit counters and one element per reference plus a sentinel. With the
reader's default bounds, counts fit comfortably. Last positions and distance counts are Python
integers. A tree indexed by requests is straightforward to verify but consumes O(N) memory even
when U is small. A compact order-statistics tree could reduce this, at an implementation cost.
No approximate result is used while claiming exactness.

## Decision 003: independent validation paths

The fast profiler and OrderedDict replay do not share hit logic. The tests add a simple list oracle.
For Belady, tests enumerate every possible legal eviction rather than duplicating next-use logic.
There are 3,280 short traces and four capacities, totaling 13,120 independent comparisons.
Generated traces verify monotonic LRU curves and minimal sizing. FIFO deliberately fails monotonicity
on a known anomaly trace; the tool does not use LRU's monotonic sizing logic for FIFO.

## Decision 004: bounded lazy Belady heap

The resident map contains the current next-use index of each cached key. Heap entries are negative
indices so the farthest future is popped first. Superseded entries are discarded on pop. Every
resident has a current heap entry. Equal future indices can occur for keys never used again;
either is a valid victim. After the heap exceeds 4C entries it is rebuilt from the resident map.
This bounds ordinary heap storage while preserving the next-victim rule. Precomputed next-use
positions still take O(N) memory; this is deliberately offline.

## Decision 005: evidence and privacy boundaries

Reports use schema version 1 and a SHA-256 of the exact trace bytes. They omit keys and local input
paths. The same trace/options produce the same JSON payload (no timestamp noise). Two differently
encoded traces with identical key sequences may have different hashes. Empty input is explicit.

This is local analysis, not a sandbox or a cryptographic attestation system. A report can be edited
after generation. Hashing does not prove who collected the trace or anonymize low-entropy inputs.
Output paths are explicit and can overwrite prior reports; errors return a nonzero exit. Check the
command exit code and fingerprint before accepting evidence. Multi-artifact writes are not atomic.

## Decision 006: no premature native backend or web UI

The implementation's purpose is auditable algorithmic behavior and useful developer ergonomics.
A native backend may be justified by profiling later. A dashboard would add dependencies without
improving the core sizing model. Static SVG is sufficient to share the measured curve.

## Definition of done, local MVP

- Reader, profiler, policies, sizing and reports execute without remote services.
- Independent/exhaustive/property tests and boundary regressions pass.
- Ruff, formatting, strict mypy and >=95% branch-aware coverage pass.
- A wheel installs in a clean environment and its CLI reproduces the documented example.
- Benchmark includes raw repetitions, allocation peaks, workload definition and negative results.
- README/license/contribution guidance and a future hosted CI workflow are included.

The four hosted Windows/Linux Python 3.13/3.14 CI jobs subsequently passed; see evidence/hosted-ci.json.
Real workloads, future performance and research extensions are not included in that completion claim.
