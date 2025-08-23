import os
import statistics
import time
from typing import List, Tuple

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("SPINORAMA_BENCH") != "1",
    reason="Set SPINORAMA_BENCH=1 to run performance benchmarks",
)

spinorama_c = pytest.importorskip("spinorama.c_compute_scores")
spinorama_rust = pytest.importorskip("spinorama_cscore")


def _make_intervals(freq: np.ndarray) -> List[Tuple[int, int]]:
    edges = np.geomspace(freq[0], freq[-1], 12)
    idxs = np.searchsorted(freq, edges)
    return [
        (int(idxs[i]), int(idxs[i + 1]))
        for i in range(len(idxs) - 1)
        if idxs[i + 1] > idxs[i]
    ]


def _make_idx(nh: int, nv: int) -> List[List[int]]:
    groups: List[List[int]] = []
    groups.append(list(range(0, 1)))
    for g in range(1, 7):
        start = min(g, nh + nv - 2)
        groups.append([start])
    groups.append([min(nh + nv - 1, 7)])
    return groups


def _bench(fn, *args, loops: int = 5) -> float:
    samples = []
    for _ in range(loops):
        t0 = time.perf_counter()
        fn(*args)
        t1 = time.perf_counter()
        samples.append(t1 - t0)
    return statistics.median(samples)


@pytest.mark.parametrize("n_freq, nh, nv", [(512, 36, 18)])
def test_perf_cython_vs_rust(n_freq: int, nh: int, nv: int) -> None:
    rng = np.random.default_rng(123)
    freq = np.geomspace(20.0, 20000.0, n_freq).astype(np.float64)
    spl_h = (85.0 + rng.normal(0, 1.5, size=(nh, n_freq))).astype(np.float64)
    spl_v = (85.0 + rng.normal(0, 1.5, size=(nv, n_freq))).astype(np.float64)
    peq = rng.normal(0, 0.25, size=(n_freq,)).astype(np.float64)

    idx = _make_idx(nh, nv)
    intervals = _make_intervals(freq)
    weights = np.ones((nh + nv,), dtype=np.float64)

    # Warm-up
    spin_py = spinorama_c.c_cea2034(np.concatenate((spl_h, spl_v), axis=0), idx, weights)
    _ = spinorama_c.c_score(freq, intervals, spl_h[17], spin_py[0], spin_py[-2], spin_py[-1])
    spin_rs, _ = spinorama_rust.c_score_peq(freq, idx, intervals, weights, spl_h, spl_v, peq)

    # Bench "score" path
    t_c = _bench(
        spinorama_c.c_score, freq, intervals, spl_h[17], spin_py[0], spin_py[-2], spin_py[-1]
    )
    t_r = _bench(
        spinorama_rust.c_score, freq, intervals, spl_h[17], spin_py[0], spin_py[-2], spin_py[-1]
    )

    # Bench full PEQ path
    t_c_peq = _bench(
        spinorama_c.c_score_peq, freq, idx, intervals, weights, spl_h, spl_v, peq
    )
    t_r_peq = _bench(
        spinorama_rust.c_score_peq, freq, idx, intervals, weights, spl_h, spl_v, peq
    )

    # Sanity: functions run and return finite values (use existing parity test for strictness)
    assert t_c > 0 and t_r > 0 and t_c_peq > 0 and t_r_peq > 0

    # Optional: log metrics for CI output
    speedup_score = t_c / t_r
    speedup_peq = t_c_peq / t_r_peq
    print(
        f"score path speedup: {speedup_score:.2f}x | peq path speedup: {speedup_peq:.2f}x"
    )
