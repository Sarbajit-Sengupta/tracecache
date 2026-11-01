# TraceCache

**Find the cache capacity your observed workload can actually use.**

TraceCache is an offline Python library and CLI for equal-sized-object caches. It computes an exact
LRU miss curve, compares FIFO/LRU with offline-optimal Belady, and finds the smallest LRU capacity
that meets a chosen miss ratio on the supplied trace. Reports include a trace fingerprint, cold
miss floor and optional cold-start phase windows. No API key, GPU, server or runtime dependency.

![Example miss curves](evidence/example-curve.svg)

## Why it is useful

Increasing cache capacity cannot eliminate compulsory first-reference misses. A replacement policy
can also leave recoverable hits on the table. The tool separates those two effects and exposes the
assumptions behind its answer. It does not predict future demand, estimate dollars saved, or
recommend deploying an oracle with knowledge of future requests.

## Install and run

Requires CPython **3.13 or newer**. Tested locally on Windows 11 / Python 3.13.5. The included CI
matrix targets Windows/Linux and Python 3.13/3.14; hosted execution is pending publication.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\tracecache examples/scan.jsonl --capacities 0,1,2,3,4,5 --target 0.5
```

Start with `git clone https://github.com/Sarbajit-Sengupta/tracecache.git` and `cd tracecache`.
On Linux/macOS use `.venv/bin/python` and `.venv/bin/tracecache`.

Write an evidence report and a standalone chart:

```powershell
.venv\Scripts\tracecache examples/scan.jsonl --capacities 0,1,2,3,4,5 --target 0.5 --window 6 --output report.json --svg curve.svg
```

The example has **11 requests, 5 distinct objects**. Its minimum capacity for an observed miss
ratio at most 0.5 is **5 objects**. Capacity 2 has 7 LRU misses; capacity 5 has 5. Those numbers are
reproduced in [the checked example report](evidence/example-report.json).

### Input contract

One UTF-8 JSON object per line, with exactly one field and a nonempty string key:

```json
{"key":"object-a"}
{"key":"object-b"}
{"key":"object-a"}
```

Blank lines, duplicate fields, extra fields, nonstring keys and invalid JSON fail with a diagnostic.
An empty file is valid and has zero misses and miss ratio 0. CRLF and a missing final newline work.
Keys are limited to 4096 characters; each line to 65,536 bytes including its newline; input to
128 MiB and one million requests by default. `--max-requests` changes the request cap. Increasing
it can use substantially more RAM. These bounds do not make the parser a hostile-code sandbox.

Capacities count **objects, not bytes**, and must be nonnegative integers. Up to 128 capacities
can be selected. A target is a finite miss ratio in [0,1]. An unreachable target produces
`"minimum_lru_capacity": null`, rather than an invented estimate. Reports contain counts and
fingerprints, not request keys or input paths. A fingerprint is not anonymization: dictionary
attacks can identify predictable traces, and callers must review artifacts before sharing them.

Exit 0 means analysis completed; exit 2 means an input, option or IO error. CLI usage errors also
exit 2. Files are local and no network is contacted. Input and output paths must differ. Output
files are overwritten if explicitly selected; multi-file output is not transactional. Never
interpret a preexisting file as evidence that a failed new command completed; check the exit code
and trace fingerprint.

## How it works

```mermaid
flowchart LR
    A[Bounded JSONL reader] --> B[Keys and SHA-256]
    B --> C[Fenwick LRU profile]
    B --> D[LRU FIFO Belady replay]
    C --> E[Exact capacity queries]
    D --> F[JSON evidence]
    E --> F
    F --> G[Standalone SVG]
```

The profiler maintains one active marker at each object's last reference position in a Fenwick
tree. On reuse, the number of more-recent distinct objects is its stack distance `d`. A fully
associative LRU cache hits exactly when `capacity > d`. A distance histogram and cumulative counts
allow capacity queries without replaying the trace for every size.

| Component | Time | Auxiliary space |
|---|---|---|
| Exact LRU profile | O(N log N) | O(N+U) |
| LRU capacity query | O(log D) | O(1) |
| Minimum-capacity query | O(log U log D) | O(1) |
| LRU/FIFO simulation, one capacity | O(N) | O(min(C,U)) |
| Belady, one capacity | O(N log(C+1)) amortized | O(N+U+C) |

N is requests, U distinct objects, D observed distance bins, C capacity. Input storage is additional.
The Belady heap uses lazy invalidation and periodic compaction to prevent unlimited heap growth on
long hit streaks. Its next-use array retains O(N) state. The CLI replays FIFO and Belady for each
selected capacity, so whole-command performance differs from profiling-only benchmark results.

### Model and limitations

- Initially empty, fully associative caches, equal object sizes, no TTL, invalidations, prefetch,
  admission rejection, writes or variable retrieval costs; mandatory insertion after a miss.
- Belady's optimality applies to this equal-sized paging model. It is an offline bound, not a
  practical online replacement policy or an optimal variable-size cache algorithm.
- Window analysis restarts each cache. It measures local cold-start behavior, **not** interval
  misses in a continuously warmed global simulation.
- Exact processing retains the trace and an O(N) tree. This is not a streaming billion-request
  analyzer. Input caps constrain ordinary use, not every possible memory/time exhaustion case.
- No original cache algorithm is claimed. This is an original implementation and engineering
  artifact built around classical methods. It is not a replacement for native high-throughput
  simulators or an independently validated production service.

## Library example

```python
from tracecache import profile_lru, simulate

trace = ["a", "b", "a", "c", "a"]
profile = profile_lru(trace)
assert profile.misses(2) == 3
assert profile.minimum_capacity(0.6) == 2
assert simulate(trace, 2, "belady") <= profile.misses(2)
```

Library functions expect sequences of string keys. The reader is the strict format-validation
boundary. Do not mutate a sequence during analysis.

## Development and verification

```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pip install --no-deps -e .
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m mypy
.venv\Scripts\python -m pytest --cov=tracecache --cov-branch --cov-fail-under=95
.venv\Scripts\python -m build
```

See [evidence/tests.txt](evidence/tests.txt) and [validation notes](evidence/VALIDATION.md) for actual
local results. No hosted green badge is shown before hosted checks have run.

Tests include a separate list-based LRU oracle, deterministic Hypothesis-generated traces and
all **3,280 traces of length 0–7 over three symbols**, with four capacities each, compared against
exhaustive legal-victim search. Additional regressions cover FIFO's capacity anomaly, unreachable
targets, zero capacity, long hot-key traces, malformed/oversized input and CLI output. Coverage
measures executed paths; independent oracles provide the stronger correctness evidence.

## Performance evidence

```powershell
.venv\Scripts\python benchmarks/run.py --requests 50000 --repeat 7 --output evidence/benchmark.json
```

The benchmark compares one exact all-capacity profile plus queries with repeated independent
OrderedDict LRU simulations. It verifies equality before measurement, warms all cases, shuffles
case order in every repetition, and records raw timings and separate Python-allocation peaks.
It excludes input construction and IO. Read [the measured results](evidence/BENCHMARK.md).

This is a synthetic workload on one machine. No comparison against libCacheSim, PyMimircache or
real production workloads was run. For a few capacities a direct O(N) simulation can be faster
and much smaller. The point is the measured crossover, not a universal speed claim.

## Prior art and design decisions

[Mattson et al.](https://doi.org/10.1147/sj.92.0078) established stack-based storage analysis.
[libCacheSim](https://github.com/1a1a11a/libCacheSim) and
[PyMimircache](https://github.com/1a1a11a/PyMimircache) offer mature profiling/simulation features.
This implementation was written here, without copying their implementations. See
[docs/design.md](docs/design.md) for invariants and deliberate trade-offs.

## Roadmap

1. Run the included Windows/Linux CI matrix after publication approval.
2. Validate adapters against independently licensed public application traces.
3. Profile wall time/RSS in fresh subprocesses over several trace lengths and workload families.
4. Add continuous-state phase statistics separately from cold-start windows.
5. Explore weighted/sampled analysis only with model-specific proofs and independent oracles.

No item on that list is presented as implemented. See [CONTRIBUTING.md](CONTRIBUTING.md).

License: [MIT](LICENSE).
