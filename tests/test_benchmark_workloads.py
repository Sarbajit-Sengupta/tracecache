import importlib.util
from pathlib import Path

import pytest

from tracecache import profile_lru, simulate


@pytest.mark.parametrize("kind", ["phases", "uniform", "cyclic", "hot"])
def test_workload_reproducibility_and_baseline_parity(kind: str) -> None:
    location = Path(__file__).resolve().parents[1] / "benchmarks" / "run.py"
    spec = importlib.util.spec_from_file_location("tracecache_benchmark", location)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    keys = module.workload(1200, 1729, kind)
    assert len(keys) == 1200
    assert keys == module.workload(1200, 1729, kind)
    profile = profile_lru(keys)
    assert [profile.misses(c) for c in [0, 8, 64, 1024, 4096]] == [
        simulate(keys, c) for c in [0, 8, 64, 1024, 4096]
    ]
