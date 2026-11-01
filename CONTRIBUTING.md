# Contributing

Discuss a changed cache model or new policy before implementing it. A bug report should provide
a minimal synthetic trace, exact command, expected counts and actual output. Do not post private
production traces or credentials.

Use Python 3.13+, install the locked development requirements and editable package as documented
in README, then run Ruff, formatting, strict mypy, pytest with coverage and the package build.
CI must pass on the supported Windows/Linux matrix when hosted. Keep changes focused.

New algorithms need independent oracles and model assumptions. Performance claims need a runnable
benchmark, raw repeated measurements, input identity, machine details and a legitimate baseline.
Do not alter tests solely to agree with an incorrect implementation. Report regressions and losses.
If using AI assistance, follow applicable project policies and accurately describe validation;
do not imply independent human review that did not occur.

New input formats should have bounded parsing and reject unsupported semantics. Reports must
remain key-free unless an explicit new output contract is reviewed. Do not accept raw shell
commands or execute input data.
