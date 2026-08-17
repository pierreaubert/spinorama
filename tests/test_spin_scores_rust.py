import math
from typing import List, Tuple

import numpy as np
import pytest

# Skip tests if the Rust module isn't available yet
spinorama_c = pytest.importorskip("spinorama.compute_scores_cython.compute_scores_cython")
spinorama_rust = pytest.importorskip("compute_scores_rust")


def _make_intervals(freq: np.ndarray) -> List[Tuple[int, int]]:
    # Mimic intervals used by Python version: e.g., 50Hz bands on log scale
    # For parity, create 10 intervals across the supported range
    edges = np.geomspace(freq[0], freq[-1], 12)
    idxs = np.searchsorted(freq, edges)
    return [(int(idxs[i]), int(idxs[i + 1])) for i in range(len(idxs) - 1) if idxs[i + 1] > idxs[i]]


def _make_idx(nh: int, nv: int) -> List[List[int]]:
    # Build a minimal idx layout similar to CEA2034 indices used in code
    # 0: LW group; 1: ER placeholder; 2..6 used by ER computation in both impls
    # Last group is SP (weighted)
    # Here we approximate groups by contiguous ranges in [0..nh+nv)
    groups = []
    # 0: LW uses first horizontal row set
    groups.append(list(range(0, 1)))
    # 1..6: other groups (ensure at least 7 total before SP)
    for g in range(1, 7):
        start = min(g, nh + nv - 2)
        groups.append([start])
    # SP group is the last index list
    groups.append([min(nh + nv - 1, 7)])
    return groups


@pytest.mark.parametrize("n_freq, nh, nv", [(512, 36, 18), (256, 18, 12)])
def test_c_score_parity(n_freq: int, nh: int, nv: int) -> None:
    rng = np.random.default_rng(123)
    freq = np.geomspace(20.0, 20000.0, n_freq).astype(np.float64)

    # Build H/V SPL arrays around ~85 dB with small variations
    spl_h = (85.0 + rng.normal(0, 1.5, size=(nh, n_freq))).astype(np.float64)
    spl_v = (85.0 + rng.normal(0, 1.5, size=(nv, n_freq))).astype(np.float64)

    peq = rng.normal(0, 0.3, size=(n_freq,)).astype(np.float64)

    # Build spin-like arrays via the cython impl for a canonical baseline
    idx = _make_idx(nh, nv)

    # Weights for SP group: one per measurement row (H+V)
    weights = np.ones((nh + nv,), dtype=np.float64)

    # Compose SPL full array and compute spin using both
    spl = np.concatenate((spl_h, spl_v), axis=0)
    spin_py = spinorama_c.c_cea2034(spl, idx, weights)

    intervals = _make_intervals(freq)

    # Compute score path (no PEQ) for both paths using arrays from above
    res_py = spinorama_c.c_score(freq, intervals, spl_h[17], spin_py[0], spin_py[-2], spin_py[-1])
    res_rs = spinorama_rust.c_score(
        freq, intervals, spl_h[17], spin_py[0], spin_py[-2], spin_py[-1]
    )

    for k in ("nbd_on", "nbd_pir", "lfx", "sm_pir", "pref_score"):
        assert k in res_rs
        assert math.isfinite(res_rs[k])
        assert math.isfinite(res_py[k])

    # Tight tolerance where feasible; allow small FP drift
    assert abs(res_py["nbd_on"] - res_rs["nbd_on"]) < 1e-6
    assert abs(res_py["nbd_pir"] - res_rs["nbd_pir"]) < 1e-6
    assert abs(res_py["lfx"] - res_rs["lfx"]) < 1e-6
    assert abs(res_py["sm_pir"] - res_rs["sm_pir"]) < 1e-9
    assert abs(res_py["pref_score"] - res_rs["pref_score"]) < 1e-6


@pytest.mark.parametrize("n_freq, nh, nv", [(512, 36, 18)])
def test_c_score_peq_paths_parity(n_freq: int, nh: int, nv: int) -> None:
    rng = np.random.default_rng(321)
    freq = np.geomspace(20.0, 20000.0, n_freq).astype(np.float64)

    spl_h = (85.0 + rng.normal(0, 1.0, size=(nh, n_freq))).astype(np.float64)
    spl_v = (85.0 + rng.normal(0, 1.0, size=(nv, n_freq))).astype(np.float64)

    peq = rng.normal(0, 0.25, size=(n_freq,)).astype(np.float64)

    idx = _make_idx(nh, nv)
    weights = np.ones((nh + nv,), dtype=np.float64)
    intervals = _make_intervals(freq)

    spin_py, score_py = spinorama_c.c_score_peq(freq, idx, intervals, weights, spl_h, spl_v, peq)
    spin_rs, score_rs = spinorama_rust.c_score_peq(freq, idx, intervals, weights, spl_h, spl_v, peq)

    # Compare spin arrays
    assert np.allclose(spin_py, spin_rs, atol=1e-6)

    for k in ("nbd_on", "nbd_pir", "lfx", "sm_pir", "pref_score"):
        assert k in score_rs
        assert math.isfinite(score_rs[k])
        assert math.isfinite(score_py[k])
        assert abs(score_py[k] - score_rs[k]) < 1e-6

    # Approx path should be close to full path
    # c_score_peq_approx expects spin WITHOUT PEQ; compute original spin from raw SPL
    spl_full = np.concatenate((spl_h, spl_v), axis=0)
    spin_orig = spinorama_rust.c_cea2034(spl_full, idx, weights)
    score_rs_ap = spinorama_rust.c_score_peq_approx(freq, intervals, spin_orig, spl_h[17], peq)
    assert abs(score_rs_ap["pref_score"] - score_rs["pref_score"]) < 1e-6
