# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import math
cimport numpy as np
import numpy as np

from more_itertools import consecutive_groups
from scipy.stats import linregress

np.import_array()

cdef double[:] spl2pressure(const double[:] spl):
    """transform SPL to pressure"""
    return np.power(10, np.divide(np.subtract(spl,105.0),20))


cdef double[:] pressure2spl(const double[:] pressure):
    """transform pressure to SPL"""
    return np.add(np.multiply(np.log10(pressure), 20), 105)


cdef double[:,:] spl2pressure2(const double[:,:] spl):
    """apply SPL to pressure for all measurements"""
    cdef p2 = np.zeros_like(spl)
    cdef Py_ssize_t i
    for i in range(spl.shape[0]):
        # spl 2 pressure and then square it
        p2[i] = np.square(spl2pressure(spl[i]))
    return p2


cdef double[:] apply_rms(const double[:,:] p2, idx):
    """"Compute RMS"""
    cdef Py_ssize_t len_idx = len(idx)
    cdef double[:] rms = np.zeros(p2.shape[1])
    cdef Py_ssize_t i
    for i in range(len_idx):
        rms = np.add(rms, p2[idx[i]])
    return pressure2spl(np.sqrt(np.divide(rms, len_idx)))


cdef double[:] apply_weigthed_rms(const double[:,:] p2, idx, const double[:] weigths):
    """"Compute "weigthed RMS"""
    cdef Py_ssize_t len_idx = len(idx)
    cdef double[:] rms = np.zeros(p2.shape[1])
    cdef double sum_weigths = 0.0
    cdef Py_ssize_t i
    for i in range(len_idx):
        rms = np.add(rms, np.multiply(p2[idx[i]],weigths[idx[i]]))
        sum_weigths += weigths[idx[i]]
    return pressure2spl(np.sqrt(np.divide(rms, sum_weigths)))


cpdef c_cea2034(const double[:,:] spl, idx, const double[:] weigths):
    """Compute CEA2034"""
    cdef Py_ssize_t len_spl = len(spl[0])
    cdef pressure2 = spl2pressure2(spl)
    cdef cea2034 = np.zeros([len(idx)+1, len_spl])
    cdef Py_ssize_t idx_lw = 0
    cdef Py_ssize_t idx_er = 1
    cdef Py_ssize_t idx_sp = len(idx)-1
    cdef Py_ssize_t idx_pir = idx_sp+1
    cdef Py_ssize_t i
    # compute all curves from cea2034
    for i in range(idx_sp):
        cea2034[i] = apply_rms(pressure2, idx[i])
    # ER is computed differently
    cdef double[:] er = np.zeros([len_spl])
    for i in range(2, 7):
        er = np.add(er, np.square(spl2pressure(cea2034[i])))
    cea2034[idx_er] = pressure2spl(np.sqrt(np.divide(er, 5)))
    # SP is weighted rms
    cea2034[idx_sp] = apply_weigthed_rms(pressure2, idx[idx_sp], weigths)
    # EIR
    pir_lw = spl2pressure(cea2034[idx_lw])
    pir_er = spl2pressure(cea2034[idx_er])
    pir_sp = spl2pressure(cea2034[idx_sp])
    cea2034[idx_pir] = pressure2spl(
        np.sqrt(
            np.multiply(0.12, np.power(pir_lw, 2))+
            np.multiply(0.44, np.power(pir_er, 2))+
            np.multiply(0.44, np.power(pir_sp, 2))
        )
    )
    return cea2034

cdef double LFX_DEFAULT = math.log10(300)

cdef double mad(const double[:] spl, Py_ssize_t imin, Py_ssize_t imax):
    return np.mean(np.abs(np.subtract(spl[imin:imax], np.mean(spl[imin:imax]))))

cpdef double c_nbd(const double[:] freq, interval, const double[:] spl):
    """Compute NBD see details in compute_scores.py"""
    return np.nanmean([mad(spl, imin,imax) for imin, imax in interval])

cdef first(l):
    """"Cython doesn't like lambdas: added a simple helper to bypass the issue"""
    return l[0]

cpdef double c_lfx(const double[:] freq, const double[:] lw, const double[:] sp):
    """Compute LFX see details in compute_scores.py"""
    cdef lw_min = np.searchsorted(freq, 300, side="right")
    cdef lw_max = np.searchsorted(freq, 10000, side="left")
    cdef double lw_ref = np.mean(lw[lw_min:lw_max])-6
    cdef lfx_range = [(i, f) for i, f in enumerate(freq[:lw_min]) if sp[i]<=lw_ref]
    if len(lfx_range) == 0:
        return math.log10(freq[0])

    lfx_grouped = consecutive_groups(lfx_range, first)
    lfx_list = list(next(lfx_grouped))
    if len(lfx_list) <= 1:
        return LFX_DEFAULT
    pos = lfx_list[-1][0]
    if len(freq) < pos-1:
        pos = pos +1
    return math.log10(freq[pos])

cpdef double c_sm(const double[:] freq, const double[:] spl):
    """Compute SM see details in compute_scores.py"""
    cdef f_min = np.searchsorted(freq, 100, side="right")
    cdef f_max = np.searchsorted(freq, 16000, side="left")
    cdef log_freq = np.log10(freq[f_min:f_max])
    _, _, r_value, _, _ = linregress(log_freq, spl[f_min:f_max])
    return r_value*r_value

cpdef c_score(
    const double[:] freq,
    intervals,
    const double[:] on,
    const double[:] lw,
    const double[:] sp,
    const double[:] pir
):
    """Compute score see details in compute_scores.py"""
    cdef nbd_on = c_nbd(freq, intervals, on)
    cdef nbd_pir = c_nbd(freq, intervals, pir)
    cdef sm_pir = c_sm(freq, pir)
    cdef lf_x = c_lfx(freq, lw, sp)
    cdef score = 12.69 - 2.49 * nbd_on - 2.99 * nbd_pir - 4.31 * lf_x + 2.32 * sm_pir
    return {
        "nbd_on": nbd_on,
        "nbd_pir": nbd_pir,
        "lfx": lf_x,
        "sm_pir": sm_pir,
        "pref_score": score
    }

cpdef c_score_peq(
    const double[:] freq,
    idx,
    intervals,
    const double[:] weigths,
    const double[:, :] spl_h,
    const double[:, :] spl_v,
    const double[:] peq
):
    """Compute score with a PEQ"""
    cdef spl_h_peq = np.zeros_like(spl_h)
    cdef spl_v_peq = np.zeros_like(spl_v)
    for i in range(spl_h.shape[0]):
        spl_h_peq[i] = np.add(spl_h[i], peq)
        spl_v_peq[i] = np.add(spl_v[i], peq)
    cdef spl = np.concatenate((spl_h_peq, spl_v_peq), axis=0)
    cdef spin = c_cea2034(spl, idx, weigths)
    return spin, c_score(freq, intervals, spl_h_peq[17], spin[0], spin[-2], spin[-1])


cpdef c_score_peq_approx(
    const double[:] freq,
    idx,
    intervals,
    const double [:,:] spin,
    const double [:] on,
    const double[:] peq
):
    """Compute score with a PEQ (faster)"""
    return c_score(
        freq,
        intervals,
        np.add(on,peq),        # on
        np.add(spin[0], peq),  # lw
        np.add(spin[-2], peq), # sp
        np.add(spin[-1], peq)  # pir
    )
