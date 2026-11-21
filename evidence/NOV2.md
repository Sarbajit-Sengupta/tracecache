# Version 0.2 engineering and validation

Eight project improvements were implemented on 2 November 2026:

1. Protect input and output files against hard-link alias collisions.
2. Atomically replace each report/chart, preserving completed output when writes fail.
3. Read gzip streams with decompressed size/line/request limits and corruption diagnostics.
4. Import strict single-key CSV, including quoted multiline/Unicode records.
5. Measure warmed-cache phase misses while retaining cold-start windows.
6. Avoid FIFO/Belady replays at zero and full-fit capacity boundaries.
7. Recompute saved reports, rejecting malformed configuration and reporting mismatches.
8. Benchmark four reproducible workload families with checked baseline parity.

These are improvements to the account owner's project, not eight external maintainer acceptances.
No production adoption or third-party review is claimed. Earlier 0.1 results are retained as
historical evidence and must not be described as validation of this new version.

## Benchmarks

20,000 requests, seed 1729, five shuffled timing repetitions per case and separate allocation
measurement, on the same local Windows/Python 3.13.5 environment. Raw samples are in
benchmarks-nov2/{phases,uniform,cyclic,hot}.json. Every capacity result is compared with independent
OrderedDict simulation before timing. Inputs are synthetic and require no external credentials.

| Workload | Profile + 64 queries, median s | 64 LRU replays, median s | Interpretation |
|---|---:|---:|---|
| Two hot phases with scan traffic | 0.0506 | 0.1568 | Profile about 3.1× faster |
| Uniform over 4096 objects | 0.0506 | 0.2322 | Profile about 4.6× faster |
| Cyclic over 1024 objects | 0.0687 | 0.3283 | Profile about 4.8× faster |
| Single hot object | 0.0555 | 0.0555 | No meaningful profiling speedup |

Direct replay is faster for one capacity in every family. All raw samples and allocation peaks
are retained, and no significance or universal crossover claim is made. Timing excludes input
creation/IO and does not measure the entire multi-policy CLI. These results are not comparisons
with compiled libraries. CPU affinity, background load and thermal state were uncontrolled.

The expanded regression results are in tests-nov2.txt. Hosted 0.2 checks are recorded separately
after they run; the earlier hosted-ci.json describes the 0.1 baseline only.

Local final checks: **88 passed**, branch-aware coverage **99.24%**; Ruff lint/format and strict
mypy passed. The wheel and source distribution built successfully using the pinned setuptools
backend. The wheel was installed without runtime dependencies in a clean environment and its
CLI generated and verified a warmed-window report. See distribution-nov2.json for its hash.
