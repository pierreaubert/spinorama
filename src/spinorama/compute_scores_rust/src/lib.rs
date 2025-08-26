use ndarray::{Array1, Array2, Axis};
use ndarray::{s};
use ndarray::concatenate;
use numpy::{IntoPyArray, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
use numpy::{ToPyArray, PyArrayMethods};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyDict;

fn spl2pressure(spl: &Array1<f64>) -> Array1<f64> {
    // 10^((spl-105)/20)
    spl.mapv(|v| 10f64.powf((v - 105.0) / 20.0))
}

fn cea2034_array(spl: &Array2<f64>, idx: &[Vec<usize>], weights: &Array1<f64>) -> Array2<f64> {
    let len_spl = spl.shape()[1];
    let p2 = spl2pressure2(spl);
    let idx_sp = idx.len() - 1;
    let idx_lw = 0usize;
    let idx_er = 1usize;
    let idx_pir = idx_sp + 1;

    let mut cea = Array2::<f64>::zeros((idx.len() + 1, len_spl));

    for i in 0..idx_sp {
        let curve = apply_rms(&p2, &idx[i]);
        cea.row_mut(i).assign(&curve);
    }

    // ER: indices 2..=6 per original logic
    let mut er_p2 = Array1::<f64>::zeros(len_spl);
    for i in 2..=6 {
        let pres = spl2pressure(&cea.row(i).to_owned());
        er_p2 = &er_p2 + &pres.mapv(|v| v * v);
    }
    let er = er_p2.mapv(|v| (v / 5.0).sqrt());
    let er_spl = pressure2spl(&er);
    cea.row_mut(idx_er).assign(&er_spl);

    // SP weighted
    let sp_curve = apply_weighted_rms(&p2, &idx[idx_sp], weights);
    cea.row_mut(idx_sp).assign(&sp_curve);

    // PIR
    let lw_p = spl2pressure(&cea.row(idx_lw).to_owned());
    let er_p = spl2pressure(&cea.row(idx_er).to_owned());
    let sp_p = spl2pressure(&cea.row(idx_sp).to_owned());
    let mut pir = Array1::<f64>::zeros(len_spl);
    for ((pir_v, lw), (er, sp)) in pir.iter_mut().zip(lw_p.iter()).zip(er_p.iter().zip(sp_p.iter())) {
        *pir_v = (0.12 * lw * lw + 0.44 * er * er + 0.44 * sp * sp).sqrt();
    }
    let pir_spl = pressure2spl(&pir);
    cea.row_mut(idx_pir).assign(&pir_spl);

    cea
}

fn pressure2spl(p: &Array1<f64>) -> Array1<f64> {
    // 20*log10(p) + 105
    p.mapv(|v| 20.0 * v.log10() + 105.0)
}

fn spl2pressure2(spl: &Array2<f64>) -> Array2<f64> {
    // square(pressure) per row
    let mut out = Array2::<f64>::zeros(spl.raw_dim());
    for (mut row_out, row_in) in out.axis_iter_mut(Axis(0)).zip(spl.axis_iter(Axis(0))) {
        let p = spl2pressure(&row_in.to_owned());
        row_out.assign(&p.mapv(|x| x * x));
    }
    out
}

fn apply_rms(p2: &Array2<f64>, idx: &[usize]) -> Array1<f64> {
    // sqrt(sum(p2[idx]) / len) then to SPL
    let ncols = p2.shape()[1];
    let mut acc = Array1::<f64>::zeros(ncols);
    for &i in idx {
        acc = &acc + &p2.row(i).to_owned();
    }
    let len_idx = idx.len() as f64;
    let r = acc.mapv(|v| (v / len_idx).sqrt());
    pressure2spl(&r)
}

fn apply_weighted_rms(p2: &Array2<f64>, idx: &[usize], weights: &Array1<f64>) -> Array1<f64> {
    let ncols = p2.shape()[1];
    let mut acc = Array1::<f64>::zeros(ncols);
    let mut sum_w = 0.0;
    for &i in idx {
        let w = weights[i];
        acc = &acc + &(p2.row(i).to_owned() * w);
        sum_w += w;
    }
    let r = acc.mapv(|v| (v / sum_w).sqrt());
    pressure2spl(&r)
}

fn mad(spl: &Array1<f64>, imin: usize, imax: usize) -> f64 {
    let slice = spl.slice(s![imin..imax]).to_owned();
    let m = slice.mean().unwrap_or(0.0);
    let diffs = slice.mapv(|v| (v - m).abs());
    diffs.mean().unwrap_or(f64::NAN)
}

fn consecutive_groups_first_group(indices: &[(usize, f64)]) -> Vec<(usize, f64)> {
    // Return the first group of consecutive indices
    if indices.is_empty() {
        return Vec::new();
    }
    let mut group: Vec<(usize, f64)> = Vec::new();
    let mut prev = indices[0].0;
    group.push(indices[0]);
    for &(i, f) in indices.iter().skip(1) {
        if i == prev + 1 {
            group.push((i, f));
            prev = i;
        } else {
            break; // only first group
        }
    }
    group
}

fn r_squared(x: &Array1<f64>, y: &Array1<f64>) -> f64 {
    // Pearson correlation squared
    let n = x.len() as f64;
    if n == 0.0 { return f64::NAN; }
    let mx = x.mean().unwrap_or(0.0);
    let my = y.mean().unwrap_or(0.0);
    let mut num = 0.0;
    let mut sxx = 0.0;
    let mut syy = 0.0;
    for (xi, yi) in x.iter().zip(y.iter()) {
        let dx = *xi - mx;
        let dy = *yi - my;
        num += dx * dy;
        sxx += dx * dx;
        syy += dy * dy;
    }
    if sxx == 0.0 || syy == 0.0 { return f64::NAN; }
    let r = num / (sxx.sqrt() * syy.sqrt());
    r * r
}

#[pyfunction]
fn c_cea2034<'py>(
    py: Python<'py>,
    spl: PyReadonlyArray2<'_, f64>,
    idx: Vec<Vec<usize>>, // list of index groups; last is SP group
    weights: PyReadonlyArray1<'_, f64>,
) -> PyResult<Bound<'py, PyArray2<f64>>> {
    let spl = spl.as_array();
    let weights = weights.as_array();
    let len_spl = spl.shape()[1];
    let p2 = spl2pressure2(&spl.to_owned());

    let idx_sp = idx.len() - 1;
    let idx_lw = 0usize;
    let idx_er = 1usize;
    let idx_pir = idx_sp + 1;

    let mut cea = Array2::<f64>::zeros((idx.len() + 1, len_spl));

    for i in 0..idx_sp {
        let curve = apply_rms(&p2, &idx[i]);
        cea.row_mut(i).assign(&curve);
    }

    // ER: indices 2..=6 per original logic
    let mut er_p2 = Array1::<f64>::zeros(len_spl);
    for i in 2..=6 {
        let pres = spl2pressure(&cea.row(i).to_owned());
        er_p2 = &er_p2 + &pres.mapv(|v| v * v);
    }
    let er = er_p2.mapv(|v| (v / 5.0).sqrt());
    let er_spl = pressure2spl(&er);
    cea.row_mut(idx_er).assign(&er_spl);

    // SP weighted
    let sp_curve = apply_weighted_rms(&p2, &idx[idx_sp], &weights.to_owned());
    cea.row_mut(idx_sp).assign(&sp_curve);

    // PIR
    let lw_p = spl2pressure(&cea.row(idx_lw).to_owned());
    let er_p = spl2pressure(&cea.row(idx_er).to_owned());
    let sp_p = spl2pressure(&cea.row(idx_sp).to_owned());
    let mut pir = Array1::<f64>::zeros(len_spl);
    for ((pir_v, lw), (er, sp)) in pir.iter_mut().zip(lw_p.iter()).zip(er_p.iter().zip(sp_p.iter())) {
        *pir_v = (0.12 * lw * lw + 0.44 * er * er + 0.44 * sp * sp).sqrt();
    }
    let pir_spl = pressure2spl(&pir);
    cea.row_mut(idx_pir).assign(&pir_spl);

    Ok(cea.into_pyarray(py))
}

#[pyfunction]
fn c_nbd(freq: PyReadonlyArray1<'_, f64>, intervals: Vec<(usize, usize)>, spl: PyReadonlyArray1<'_, f64>) -> PyResult<f64> {
    let _ = freq; // unused but keep signature parity
    let spl = spl.as_array();
    let mut vals: Vec<f64> = Vec::with_capacity(intervals.len());
    for (imin, imax) in intervals {
        vals.push(mad(&spl.to_owned(), imin, imax));
    }
    // nanmean
    let mut sum = 0.0;
    let mut count = 0.0;
    for v in vals {
        if v.is_finite() { sum += v; count += 1.0; }
    }
    if count == 0.0 { Ok(f64::NAN) } else { Ok(sum / count) }
}

#[pyfunction]
fn c_lfx(freq: PyReadonlyArray1<'_, f64>, lw: PyReadonlyArray1<'_, f64>, sp: PyReadonlyArray1<'_, f64>) -> PyResult<f64> {
    let freq = freq.as_array();
    let lw = lw.as_array();
    let sp = sp.as_array();

    // bounds
    let lw_min = freq.iter().position(|&f| f > 300.0).unwrap_or(freq.len());
    let lw_max = freq.iter().position(|&f| f >= 10000.0).unwrap_or(freq.len());
    if lw_min >= lw_max { return Ok((300.0f64).log10()); }

    let lw_ref = lw.slice(s![lw_min..lw_max]).mean().unwrap_or(0.0) - 6.0;
    let mut lfx_range: Vec<(usize, f64)> = Vec::new();
    for (i, (&f, &spv)) in freq.iter().take(lw_min).zip(sp.iter().take(lw_min)).enumerate() {
        if spv <= lw_ref {
            lfx_range.push((i, f));
        }
    }
    if lfx_range.is_empty() {
        return Ok(freq[0].log10());
    }
    let group = consecutive_groups_first_group(&lfx_range);
    if group.len() <= 1 {
        return Ok((300.0f64).log10());
    }
    let mut pos = group.last().unwrap().0;
    if freq.len() < pos - 1 { pos += 1; }
    Ok(freq[pos].log10())
}

#[pyfunction]
fn c_sm(freq: PyReadonlyArray1<'_, f64>, spl: PyReadonlyArray1<'_, f64>) -> PyResult<f64> {
    let freq = freq.as_array();
    let spl = spl.as_array();

    // slice between 100..16000
    let f_min = freq.iter().position(|&f| f > 100.0).unwrap_or(freq.len());
    let f_max = freq.iter().position(|&f| f >= 16000.0).unwrap_or(freq.len());
    if f_min >= f_max { return Err(PyValueError::new_err("invalid frequency range for c_sm")); }

    let x: Array1<f64> = freq.slice(s![f_min..f_max]).mapv(|v| v.log10());
    let y: Array1<f64> = spl.slice(s![f_min..f_max]).to_owned();
    Ok(r_squared(&x, &y))
}

#[pyfunction]
fn c_score(
    freq: PyReadonlyArray1<'_, f64>,
    intervals: Vec<(usize, usize)>,
    on: PyReadonlyArray1<'_, f64>,
    lw: PyReadonlyArray1<'_, f64>,
    sp: PyReadonlyArray1<'_, f64>,
    pir: PyReadonlyArray1<'_, f64>,
) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let freq = freq.as_array();
        let on = on.as_array();
        let lw = lw.as_array();
        let sp = sp.as_array();
        let pir = pir.as_array();

        // nbd_on, nbd_pir
        let mut nbd_on = 0.0;
        let mut nbd_pir = 0.0;
        let mut cnt = 0.0;
        for (imin, imax) in intervals.iter().copied() {
            nbd_on += mad(&on.to_owned(), imin, imax);
            nbd_pir += mad(&pir.to_owned(), imin, imax);
            cnt += 1.0;
        }
        if cnt > 0.0 { nbd_on /= cnt; nbd_pir /= cnt; } else { nbd_on = f64::NAN; nbd_pir = f64::NAN; }

        // sm_pir
        let f_min = freq.iter().position(|&f| f > 100.0).unwrap_or(freq.len());
        let f_max = freq.iter().position(|&f| f >= 16000.0).unwrap_or(freq.len());
        if f_min >= f_max { return Err(PyValueError::new_err("invalid frequency range for c_score")); }
        let x = freq.slice(s![f_min..f_max]).mapv(|v| v.log10());
        let y = pir.slice(s![f_min..f_max]).to_owned();
        let sm_pir = r_squared(&x, &y);

        // lfx
        let lw_min = freq.iter().position(|&f| f > 300.0).unwrap_or(freq.len());
        let lw_max = freq.iter().position(|&f| f >= 10000.0).unwrap_or(freq.len());
        let lf_x = if lw_min < lw_max {
            let lw_ref = lw.slice(s![lw_min..lw_max]).mean().unwrap_or(0.0) - 6.0;
            let mut lfx_range: Vec<(usize, f64)> = Vec::new();
            for (i, (&f, &spv)) in freq.iter().take(lw_min).zip(sp.iter().take(lw_min)).enumerate() {
                if spv <= lw_ref { lfx_range.push((i, f)); }
            }
            if lfx_range.is_empty() { freq[0].log10() } else {
                let group = consecutive_groups_first_group(&lfx_range);
                if group.len() <= 1 { (300.0f64).log10() } else {
                    let mut pos = group.last().unwrap().0;
                    if freq.len() < pos - 1 { pos += 1; }
                    freq[pos].log10()
                }
            }
        } else {
            (300.0f64).log10()
        };

        let score = 12.69 - 2.49 * nbd_on - 2.99 * nbd_pir - 4.31 * lf_x + 2.32 * sm_pir;
        let dict = PyDict::new(py);
        dict.set_item("nbd_on", nbd_on)?;
        dict.set_item("nbd_pir", nbd_pir)?;
        dict.set_item("lfx", lf_x)?;
        dict.set_item("sm_pir", sm_pir)?;
        dict.set_item("pref_score", score)?;
        Ok(dict.into())
    })
}

#[pyfunction]
fn c_score_peq<'py>(
    py: Python<'py>,
    freq: PyReadonlyArray1<'_, f64>,
    idx: Vec<Vec<usize>>,
    intervals: Vec<(usize, usize)>,
    weights: PyReadonlyArray1<'_, f64>,
    spl_h: PyReadonlyArray2<'_, f64>,
    spl_v: PyReadonlyArray2<'_, f64>,
    peq: PyReadonlyArray1<'_, f64>,
) -> PyResult<(Bound<'py, PyArray2<f64>>, PyObject)> {
    let weights = weights.as_array();
    let spl_h = spl_h.as_array();
    let spl_v = spl_v.as_array();
    let peq = peq.as_array();

    if peq.len() != spl_h.shape()[1] || peq.len() != spl_v.shape()[1] {
        return Err(PyValueError::new_err("peq length must match SPL columns"));
    }

    // add PEQ to each row
    let mut spl_h_peq = Array2::<f64>::zeros(spl_h.raw_dim());
    for (mut row_out, row_in) in spl_h_peq.axis_iter_mut(Axis(0)).zip(spl_h.axis_iter(Axis(0))) {
        row_out.assign(&(&row_in.to_owned() + &peq));
    }
    let mut spl_v_peq = Array2::<f64>::zeros(spl_v.raw_dim());
    for (mut row_out, row_in) in spl_v_peq.axis_iter_mut(Axis(0)).zip(spl_v.axis_iter(Axis(0))) {
        row_out.assign(&(&row_in.to_owned() + &peq));
    }

    let spl_full = concatenate(Axis(0), &[spl_h_peq.view(), spl_v_peq.view()])
        .map_err(|e| PyValueError::new_err(format!("concatenate failed: {}", e)))?;
    let spin_nd = cea2034_array(&spl_full, &idx, &weights.to_owned());

    // Prepare rows for scoring
    let on = spl_h_peq.row(17).to_owned();
    let lw = spin_nd.row(0).to_owned();
    let sp_row = spin_nd.row(spin_nd.shape()[0]-2).to_owned();
    let pir = spin_nd.row(spin_nd.shape()[0]-1).to_owned();

    // Compute score inline using c_score logic
    let freq_arr = freq.as_array();
    let mut nbd_on = 0.0;
    let mut nbd_pir = 0.0;
    let mut cnt = 0.0;
    for (imin, imax) in intervals.iter().copied() {
        nbd_on += mad(&on.to_owned(), imin, imax);
        nbd_pir += mad(&pir.to_owned(), imin, imax);
        cnt += 1.0;
    }
    if cnt > 0.0 { nbd_on /= cnt; nbd_pir /= cnt; } else { nbd_on = f64::NAN; nbd_pir = f64::NAN; }
    let f_min = freq_arr.iter().position(|&f| f > 100.0).unwrap_or(freq_arr.len());
    let f_max = freq_arr.iter().position(|&f| f >= 16000.0).unwrap_or(freq_arr.len());
    if f_min >= f_max { return Err(PyValueError::new_err("invalid frequency range for c_score_peq")); }
    let x = freq_arr.slice(s![f_min..f_max]).mapv(|v| v.log10());
    let y = pir.slice(s![f_min..f_max]).to_owned();
    let sm_pir = r_squared(&x, &y);
    let lw_min = freq_arr.iter().position(|&f| f > 300.0).unwrap_or(freq_arr.len());
    let lw_max = freq_arr.iter().position(|&f| f >= 10000.0).unwrap_or(freq_arr.len());
    let lf_x = if lw_min < lw_max {
        let lw_ref = lw.slice(s![lw_min..lw_max]).mean().unwrap_or(0.0) - 6.0;
        let mut lfx_range: Vec<(usize, f64)> = Vec::new();
        for (i, (&f, &spv)) in freq_arr.iter().take(lw_min).zip(sp_row.iter().take(lw_min)).enumerate() {
            if spv <= lw_ref { lfx_range.push((i, f)); }
        }
        if lfx_range.is_empty() { freq_arr[0].log10() } else {
            let group = consecutive_groups_first_group(&lfx_range);
            if group.len() <= 1 { (300.0f64).log10() } else {
                let mut pos = group.last().unwrap().0;
                if freq_arr.len() < pos - 1 { pos += 1; }
                freq_arr[pos].log10()
            }
        }
    } else { (300.0f64).log10() };
    let score = 12.69 - 2.49 * nbd_on - 2.99 * nbd_pir - 4.31 * lf_x + 2.32 * sm_pir;

    let dict = PyDict::new(py);
    dict.set_item("nbd_on", nbd_on)?;
    dict.set_item("nbd_pir", nbd_pir)?;
    dict.set_item("lfx", lf_x)?;
    dict.set_item("sm_pir", sm_pir)?;
    dict.set_item("pref_score", score)?;

    // Return spin as Bound PyArray2
    let spin_py = numpy::PyArray2::from_owned_array(py, spin_nd);
    Ok((spin_py, dict.into()))
}

#[pyfunction]
fn c_score_peq_approx(
    freq: PyReadonlyArray1<'_, f64>,
    intervals: Vec<(usize, usize)>,
    spin: PyReadonlyArray2<'_, f64>,
    on: PyReadonlyArray1<'_, f64>,
    peq: PyReadonlyArray1<'_, f64>,
) -> PyResult<PyObject> {
    Python::with_gil(|py| {
        let spin = spin.as_array();
        let on = on.as_array();
        let peq = peq.as_array();
        let on2 = &on.to_owned() + &peq;
        let lw = spin.row(0).to_owned();
        let sp = spin.row(spin.shape()[0]-2).to_owned();
        let pir = spin.row(spin.shape()[0]-1).to_owned();
        c_score(
            freq,
            intervals,
            on2.view().to_pyarray(py).readonly(),
            lw.view().to_pyarray(py).readonly(),
            sp.view().to_pyarray(py).readonly(),
            pir.view().to_pyarray(py).readonly(),
        )
    })
}

#[pymodule]
fn compute_scores_rust(_py: Python, m: &Bound<PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(c_cea2034, m)?)?;
    m.add_function(wrap_pyfunction!(c_nbd, m)?)?;
    m.add_function(wrap_pyfunction!(c_lfx, m)?)?;
    m.add_function(wrap_pyfunction!(c_sm, m)?)?;
    m.add_function(wrap_pyfunction!(c_score, m)?)?;
    m.add_function(wrap_pyfunction!(c_score_peq, m)?)?;
    m.add_function(wrap_pyfunction!(c_score_peq_approx, m)?)?;
    Ok(())
}
