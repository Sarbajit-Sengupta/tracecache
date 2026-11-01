# Local validation record

Date: 1 November 2026. Local results: Windows / CPython 3.13.5. Hosted follow-up is recorded below.

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

Hosted follow-up: [run 41317805232](https://github.com/Sarbajit-Sengupta/tracecache/actions/runs/41317805232)
passed all four Windows/Linux × Python 3.13/3.14 jobs at commit
`f4b835080d751c957ef09908b25312d45c14556c`. Each passed lint, formatting, strict types, all 43 tests,
the coverage gate and wheel/source builds. Python 3.13 coverage was 98.84%; 3.14 was 98.82%.
Machine-readable job evidence is in hosted-ci.json. The source repository is public; no package
registry release or deployment is claimed.

Unfinished validation: real customer/public traces, independent human code review, fresh-process/RSS
benchmarking and external native-library performance comparisons.
