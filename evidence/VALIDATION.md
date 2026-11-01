# Local validation record

Date: 1 November 2026. Windows / CPython 3.13.5. No hosted CI run or public release is claimed.

- Ruff 0.15.6 lint: passed.
- Ruff format: all nine Python files formatted.
- Mypy 2.4.1, strict: passed for six source modules.
- Pytest 9.2.0: **43 passed** in the isolated declared development environment.
- Branch-aware coverage: **98.84%**, exceeding the configured 95% threshold.
- Hypothesis: 250 deterministic generated traces for cache equivalence/invariants; 150 generated
  target-sizing cases. The exhaustive test separately checks 3,280 traces at four capacities
  against a legal-victim enumeration oracle.
- Installed editable CLI reproduced the 11-request example: five cold misses and a minimum LRU
  capacity of five objects for target miss ratio 0.5.
- Seven shuffled benchmark repetitions and separate allocation measurements are preserved in
  benchmark.json; correctness parity is verified before measurements.

See tests.txt, quality.txt, example-report.json and BENCHMARK.md. Distribution/clean-wheel
verification results are recorded separately in distribution.json after packaging; this avoids
claiming that an untested build succeeded. The source manifest records exact reviewed file hashes.

Unfinished validation: Linux, Python 3.14, hosted CI, real customer/public traces, independent human
code review, fresh-process/RSS benchmarking and external native-library performance comparisons.
The GitHub Actions workflow is prepared locally; writing a workflow does not mean it has run.
