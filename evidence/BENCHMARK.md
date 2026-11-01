# Measured crossover, not a universal speedup

Raw samples and machine metadata: [benchmark.json](benchmark.json).
Command: `python benchmarks/run.py --requests 50000 --repeat 7`.
Measured locally on 1 November 2026, Python 3.13.5, Windows. See JSON for platform/processor.

Workload: 50,000 synthetic requests, seed 1729, two hot-set phases (128 then 256 keys), with
20% interleaved unique scan traffic. Capacities are 8,16,...,512 objects. Each row below uses the
first K of those capacities. This workload was constructed for the experiment, not collected
from a customer or production deployment.

| Capacities queried | Exact Fenwick profile + queries, median s | K independent LRU replays, median s | Observation |
|---:|---:|---:|---|
| 1 | 0.3029102 | 0.0175015 | Replay is about 17.3× faster |
| 4 | 0.3926183 | 0.0808305 | Replay is about 4.9× faster |
| 16 | 0.3087835 | 0.3032789 | Effectively similar on this noisy run |
| 64 | 0.3239602 | 0.8767821 | Profile is about 2.7× faster |

Separate tracemalloc measurements found **965,200 bytes** peak Python allocations for profiling,
versus **87,688 bytes** for 64 sequential replays. The trace was constructed before tracking;
these numbers exclude input storage and are not process RSS. Sequential replays release each
cache, so their memory does not grow as K resident caches. Profiling's tree deliberately trades
space for queries at every capacity.

Correctness is checked before timing: every profiled result must equal the replay result.
Every case receives a warm-up. Every repetition shuffles all cases with a seeded generator.
Garbage collection happens before timed regions. Inputs, parsing, generation and disk IO are
excluded. The retained arrays and returned result objects are included in the operation.
No tracemalloc overhead is included in timing; its peak measurement uses a separate call.

Limitations: one host, one workload family, no CPU affinity, no isolated-process repetitions,
background load and power management uncontrolled. Raw min/max/samples are retained because
profile timing varies. No statistical significance or portable crossover point is asserted.
Whole-CLI FIFO/Belady runs are not included in these profiling-only measurements. No comparison
against compiled libraries was performed.

Next experiments should vary trace size, distinct count and workload family, use fresh processes,
measure process-tree RSS and include a licensed public trace. Those experiments are not completed.
