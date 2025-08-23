#!/usr/bin/env python3
"""
Benchmark Rust vs Cython implementations for spinorama scoring.

Usage:
  .venv/bin/python scripts/bench_scores.py

It prints timings for:
- c_score (Cython) vs c_score (Rust)
- c_score_peq (Cython) vs c_score_peq (Rust)

Note: ensure the Rust extension is installed in the venv:
  .venv/bin/maturin develop --release -m rust-cscore/Cargo.toml
"""
from __future__ import annotations

import statistics
import time
from typing import List, Tuple

import numpy as np

import spinorama.c_compute_scores as cpy
import spinorama_cscore as rs


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


def bench_once(n_freq: int = 512, nh: int = 36, nv: int = 18) -> None:
    rng = np.random.default_rng(42)
    freq = np.geomspace(20.0, 20000.0, n_freq).astype(np.float64)
    spl_h = (85.0 + rng.normal(0, 1.5, size=(nh, n_freq))).astype(np.float64)
    spl_v = (85.0 + rng.normal(0, 1.5, size=(nv, n_freq))).astype(np.float64)
    peq = rng.normal(0, 0.25, size=(n_freq,)).astype(np.float64)

    idx = _make_idx(nh, nv)
    weights = np.ones((nh + nv,), dtype=np.float64)
    intervals = _make_intervals(freq)

    # Warmup JIT paths and caches
    spin_py = cpy.c_cea2034(np.concatenate((spl_h, spl_v), axis=0), idx, weights)
    _ = cpy.c_score(freq, intervals, spl_h[17], spin_py[0], spin_py[-2], spin_py[-1])
    spin_rs, score_rs = rs.c_score_peq(freq, idx, intervals, weights, spl_h, spl_v, peq)
    _ = rs.c_score_peq_approx(freq, intervals, spin_rs, spl_h[17], peq)

    # Timings
    def timeit(fn, *args, loops: int = 10) -> Tuple[float, float]:
        samples: List[float] = []
        for _ in range(loops):
            t0 = time.perf_counter()
            fn(*args)
            t1 = time.perf_counter()
            samples.append(t1 - t0)
        return statistics.median(samples), statistics.stdev(samples) if len(samples) > 1 else 0.0

    # Score path (no peq)
    med_c, std_c = timeit(
        cpy.c_score, freq, intervals, spl_h[17], spin_py[0], spin_py[-2], spin_py[-1]
    )
    med_r, std_r = timeit(
        rs.c_score, freq, intervals, spl_h[17], spin_py[0], spin_py[-2], spin_py[-1]
    )

    # Full PEQ path
    med_c_peq, std_c_peq = timeit(
        cpy.c_score_peq, freq, idx, intervals, weights, spl_h, spl_v, peq
    )
    med_r_peq, std_r_peq = timeit(
        rs.c_score_peq, freq, idx, intervals, weights, spl_h, spl_v, peq
    )

    def fmt(sec: float) -> str:
        return f"{sec * 1e6:.1f} µs"

    print("== Benchmark: c_score (no PEQ) ==")
    print(f"Cython: {fmt(med_c)} ± {fmt(std_c)}")
    print(f"Rust  : {fmt(med_r)} ± {fmt(std_r)}  | speedup: {med_c/med_r if med_r>0 else float('nan'):.2f}x")
    print()

    print("== Benchmark: c_score_peq (full path) ==")
    print(f"Cython: {fmt(med_c_peq)} ± {fmt(std_c_peq)}")
    print(f"Rust  : {fmt(med_r_peq)} ± {fmt(std_r_peq)} | speedup: {med_c_peq/med_r_peq if med_r_peq>0 else float('nan'):.2f}x")


if __name__ == "__main__":
    bench_once()
