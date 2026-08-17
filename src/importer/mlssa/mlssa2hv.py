#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Convert legacy MLSSA exports to spinorama HV text files.
#
# Current status:
# - `.FFT` text parsing is supported (freq / spl / phase).
# - `.TIM` binary parsing is not solved yet; this script provides
#   angle/name mapping and a probe mode to accelerate reverse engineering.
#

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import math
import re
import struct
import numpy as np


HEADER = "Freq[Hz]     dBSPL  Phase[Deg]\n"
MLSSA_MAGIC = 0xFFFFABCD

FFT_ROW_RE = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*$"
)


@dataclass
class Curve:
    freq: list[float]
    spl: list[float]
    phase: list[float]


@dataclass
class TimGraph:
    maxpoints: int
    slength: int
    cindex: int
    mindex: int
    highi: int
    lowi: int
    deltax: float


@dataclass
class TimInfo:
    path: Path
    algorithm: int
    delta_time_ms: float
    sample_count: int
    file_size: int
    data_offset: int
    title: str
    comment: str
    setup_offset: int | None
    fft_size: int | None
    window_type: int | None
    sample_rate_hz: float
    graph: TimGraph | None


@dataclass
class ConfidenceRow:
    filename: str
    axis: str
    angle: int
    source: str
    decode_mode: str
    fs: float
    plausibility: float
    points: int
    synthesized: bool
    quality: str = "n/a"


def parse_fft(path: Path) -> Curve:
    freq: list[float] = []
    spl: list[float] = []
    phase: list[float] = []
    for line in path.read_text(encoding="latin1").splitlines():
        m = FFT_ROW_RE.match(line)
        if not m:
            continue
        f = float(m.group(1))
        if f <= 0:
            continue
        freq.append(f)
        spl.append(float(m.group(2)))
        phase.append(float(m.group(3)))
    if not freq:
        msg = f"no freq/spl/phase rows found in {path}"
        raise ValueError(msg)
    return Curve(freq=freq, spl=spl, phase=phase)


def write_hv(path: Path, curve: Curve) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(HEADER)
        for a, b, c in zip(curve.freq, curve.spl, curve.phase, strict=False):
            f.write(f"{a:.6f} {b:.6f} {c:.6f}\n")


def tim_suffix_to_hv(suffix: str) -> tuple[str, int] | None:
    # Horizontal nominal measurements: 0..90
    if re.fullmatch(r"\d+", suffix):
        return ("H", int(suffix))
    # Horizontal with grille: 0G..90G
    if re.fullmatch(r"\d+G", suffix):
        return ("H", int(suffix[:-1]))
    # Vertical branches from this legacy set:
    # Axx and Bxx are treated as +V and -V respectively.
    if re.fullmatch(r"A\d+", suffix):
        return ("V", int(suffix[1:]))
    if re.fullmatch(r"B\d+", suffix):
        return ("V", -int(suffix[1:]))
    return None


def find_tim_angle_coverage(data_dir: Path) -> dict[str, set[int]]:
    result: dict[str, set[int]] = {"H": set(), "V": set()}
    for tim in sorted(data_dir.glob("*.TIM")):
        m = re.match(r"^[^-]+-(.+)\.TIM$", tim.name)
        if not m:
            continue
        mapped = tim_suffix_to_hv(m.group(1))
        if mapped is None:
            continue
        axis, angle = mapped
        result[axis].add(angle)
    return result


TIM_FIXED_HEADER_BYTES = 14
TIM_TITLE_BYTES = 80
TIM_COMMENT_BYTES = 60
TIM_SETUP_MIN_BYTES = 312
TIM_SETUP_GRAPH_OFFSET = 250


def _decode_c_string(data: bytes) -> str:
    return data.split(b"\0", 1)[0].decode("latin1", errors="replace").strip()


def parse_tim_header(path: Path) -> TimInfo:
    data = path.read_bytes()
    if len(data) < TIM_FIXED_HEADER_BYTES:
        msg = f"{path} too short"
        raise ValueError(msg)
    magic = struct.unpack_from("<I", data, 0)[0]
    if magic != MLSSA_MAGIC:
        msg = f"{path} invalid magic 0x{magic:08x}"
        raise ValueError(msg)
    algorithm = struct.unpack_from("<H", data, 4)[0]
    delta_time_ms = struct.unpack_from("<f", data, 6)[0]
    sample_count = struct.unpack_from("<I", data, 10)[0]
    if sample_count <= 0:
        msg = f"{path} has invalid sample count {sample_count}"
        raise ValueError(msg)
    if not math.isfinite(delta_time_ms) or delta_time_ms <= 0:
        msg = f"{path} has invalid delta_time {delta_time_ms!r}"
        raise ValueError(msg)

    data_bytes = sample_count * 4
    title_offset = TIM_FIXED_HEADER_BYTES + data_bytes
    comment_offset = title_offset + TIM_TITLE_BYTES
    setup_offset = comment_offset + TIM_COMMENT_BYTES
    if len(data) < title_offset:
        msg = f"{path} truncated: expected {title_offset} bytes through sample data, got {len(data)}"
        raise ValueError(
            msg
        )

    title = (
        _decode_c_string(data[title_offset:comment_offset]) if len(data) >= comment_offset else ""
    )
    comment = (
        _decode_c_string(data[comment_offset:setup_offset]) if len(data) >= setup_offset else ""
    )
    fft_size: int | None = None
    window_type: int | None = None
    graph: TimGraph | None = None
    if len(data) >= setup_offset + TIM_SETUP_MIN_BYTES:
        fft_size = struct.unpack_from("<I", data, setup_offset)[0]
        window_type = struct.unpack_from("<H", data, setup_offset + 4)[0]
        graph_offset = setup_offset + TIM_SETUP_GRAPH_OFFSET
        maxpoints, slength, cindex, mindex, highi, lowi = struct.unpack_from(
            "<IIIIII", data, graph_offset
        )
        deltax = struct.unpack_from("<f", data, graph_offset + 40)[0]
        graph = TimGraph(
            maxpoints=maxpoints,
            slength=slength,
            cindex=cindex,
            mindex=mindex,
            highi=highi,
            lowi=lowi,
            deltax=deltax,
        )
        if fft_size <= 0 or fft_size > 1 << 24:
            fft_size = None
        if window_type is not None and not 0 <= window_type <= 6:
            window_type = None
    else:
        setup_offset = None

    return TimInfo(
        path=path,
        algorithm=algorithm,
        delta_time_ms=delta_time_ms,
        sample_count=sample_count,
        file_size=len(data),
        data_offset=TIM_FIXED_HEADER_BYTES,
        title=title,
        comment=comment,
        setup_offset=setup_offset,
        fft_size=fft_size,
        window_type=window_type,
        sample_rate_hz=1000.0 / delta_time_ms,
        graph=graph,
    )


def decode_tim_samples(data: bytes, info: TimInfo) -> np.ndarray:
    end = info.data_offset + info.sample_count * 4
    if len(data) < end:
        msg = f"{info.path} truncated: expected {end} bytes, got {len(data)}"
        raise ValueError(msg)
    arr = np.frombuffer(data, dtype="<f4", count=info.sample_count, offset=info.data_offset)
    arr = arr.astype(np.float64)
    if not np.all(np.isfinite(arr)):
        msg = f"{info.path} contains non-finite TIM samples"
        raise ValueError(msg)
    return arr


def tim_window(window_type: int | None, n: int) -> np.ndarray:
    if n <= 0:
        return np.array([], dtype=np.float64)
    if window_type in (None, 0):
        return np.ones(n, dtype=np.float64)
    if window_type in (1, 2):
        full = np.hamming(n)
    elif window_type in (3, 4):
        full = np.hanning(n)
    elif window_type in (5, 6):
        full = blackman_harris(n)
    else:
        return np.ones(n, dtype=np.float64)
    if window_type in (2, 4, 6):
        half = np.ones(n, dtype=np.float64)
        if window_type == 2:
            half_full = np.hamming(2 * n)
        elif window_type == 4:
            half_full = np.hanning(2 * n)
        else:
            half_full = blackman_harris(2 * n)
        half[:] = half_full[n:]
        if half[0] != 0:
            half /= half[0]
        return half
    return full


def blackman_harris(n: int) -> np.ndarray:
    if n <= 1:
        return np.ones(n, dtype=np.float64)
    x = 2.0 * np.pi * np.arange(n) / (n - 1)
    return 0.35875 - 0.48829 * np.cos(x) + 0.14128 * np.cos(2.0 * x) - 0.01168 * np.cos(3.0 * x)


def tim_fft_segment(samples: np.ndarray, info: TimInfo) -> tuple[np.ndarray, int, int]:
    start = 0
    stop = len(samples)
    if info.graph is not None:
        m = int(info.graph.mindex)
        c = int(info.graph.cindex)
        lo = min(m, c)
        hi = max(m, c) + 1
        if 0 <= lo < hi <= len(samples) and hi - lo >= 16:
            start, stop = lo, hi
    return samples[start:stop], start, stop


def tim_to_curve(path: Path, mode: str = "f32le", fs: float | None = None) -> Curve:
    if mode != "f32le":
        raise ValueError("MLSSA TIM data is stored as little-endian float32 samples")
    info = parse_tim_header(path)
    data = path.read_bytes()
    samples = decode_tim_samples(data, info)
    sig, _, _ = tim_fft_segment(samples, info)
    if len(sig) < 16:
        msg = f"{path} decoded to too few windowed samples ({len(sig)})"
        raise ValueError(msg)
    sig = sig - np.mean(sig)
    nfft = info.fft_size or len(sig)
    if nfft < len(sig):
        nfft = 1 << (len(sig) - 1).bit_length()
    win = tim_window(info.window_type, len(sig))
    sp = np.fft.rfft(sig * win, n=nfft)
    freq = np.fft.rfftfreq(nfft, d=1.0 / (fs or info.sample_rate_hz))
    mag = 20.0 * np.log10(np.maximum(np.abs(sp), 1e-30))
    phase = np.angle(sp, deg=True)
    return Curve(freq=freq.tolist(), spl=mag.tolist(), phase=phase.tolist())


def plausibility_score(curve: Curve, min_freq: float, max_freq: float) -> float:
    f = np.array(curve.freq)
    s = np.array(curve.spl)
    p = np.array(curve.phase)
    m = (f >= min_freq) & (f <= max_freq) & np.isfinite(s) & np.isfinite(p)
    if m.sum() < 48:
        return 1e12
    ff = f[m]
    ss = s[m]
    # normalize away gain
    ss = ss - np.mean(ss)
    if np.max(ss) - np.min(ss) < 6.0:
        return 1e9
    # smoothness on log-f
    logf = np.log(ff)
    grid = np.linspace(logf.min(), logf.max(), 240)
    si = np.interp(grid, logf, ss)
    rough = float(np.std(np.diff(si, n=2)))
    # keep values in plausible dB-ish band (after centering this mostly checks outliers)
    outlier = float(np.mean(np.abs(si) > 40.0))
    return rough + 50.0 * outlier


def choose_decode_for_tim(path: Path, min_freq: float, max_freq: float) -> tuple[str, float]:
    info = parse_tim_header(path)
    return "f32le", float(info.sample_rate_hz)


def choose_decode_for_tim_scored(
    path: Path, min_freq: float, max_freq: float
) -> tuple[str, float, float]:
    info = parse_tim_header(path)
    c = tim_to_curve(path)
    score = plausibility_score(c, min_freq=min_freq, max_freq=max_freq)
    return "f32le", float(info.sample_rate_hz), float(score)


def curve_to_grid(curve: Curve, freq_grid: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    f = np.array(curve.freq)
    s = np.array(curve.spl)
    p = np.array(curve.phase)
    m = np.isfinite(f) & np.isfinite(s) & np.isfinite(p) & (f > 0)
    f = f[m]
    s = s[m]
    p = p[m]
    order = np.argsort(f)
    f = f[order]
    s = s[order]
    p = p[order]
    lf = np.log(f)
    lgrid = np.log(freq_grid)
    spl_i = np.interp(lgrid, lf, s)
    # phase via unit-circle interpolation
    pr = np.cos(np.deg2rad(p))
    pi = np.sin(np.deg2rad(p))
    pr_i = np.interp(lgrid, lf, pr)
    pi_i = np.interp(lgrid, lf, pi)
    phase_i = np.rad2deg(np.arctan2(pi_i, pr_i))
    return spl_i, phase_i


def smooth_spl_fractional_octave(freq: np.ndarray, spl: np.ndarray, frac: int) -> np.ndarray:
    if frac <= 0:
        return spl
    # Gaussian smoothing in log2(f) domain.
    x = np.log2(np.maximum(freq, 1e-9))
    out = np.empty_like(spl)
    sigma = 0.5 / frac
    two_sigma2 = 2.0 * sigma * sigma
    for i in range(len(freq)):
        w = np.exp(-((x - x[i]) ** 2) / two_sigma2)
        sw = np.sum(w)
        out[i] = spl[i] if sw <= 0 else float(np.sum(w * spl) / sw)
    return out


def apply_smoothing(curve: Curve, smoothing: int) -> Curve:
    if smoothing <= 0:
        return curve
    f = np.array(curve.freq)
    s = np.array(curve.spl)
    p = np.array(curve.phase)
    sm = smooth_spl_fractional_octave(f, s, smoothing)
    return Curve(freq=curve.freq, spl=sm.tolist(), phase=p.tolist())


def synthesize_axis_curves(
    axis_curves: dict[int, Curve],
    target_angles: list[int],
    freq_grid: np.ndarray,
    fill_unknown_with_onaxis: bool = False,
    unknown_spl_floor_db: float | None = None,
) -> dict[int, Curve]:
    known = sorted(axis_curves.keys())
    if not known:
        return {}
    grid_cache: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for a, c in axis_curves.items():
        grid_cache[a] = curve_to_grid(c, freq_grid)

    def interp_pair(a0: int, a1: int, at: int) -> tuple[np.ndarray, np.ndarray]:
        s0, p0 = grid_cache[a0]
        s1, p1 = grid_cache[a1]
        if a1 == a0:
            return s0, p0
        t = (at - a0) / (a1 - a0)
        s = s0 + t * (s1 - s0)
        # phase interpolation on unit circle
        z0 = np.exp(1j * np.deg2rad(p0))
        z1 = np.exp(1j * np.deg2rad(p1))
        z = (1 - t) * z0 + t * z1
        p = np.rad2deg(np.angle(z))
        return s, p

    out: dict[int, Curve] = {}
    for a in target_angles:
        if a in grid_cache:
            s, p = grid_cache[a]
        elif fill_unknown_with_onaxis and 0 in grid_cache:
            s, p = grid_cache[0]
        else:
            lower = [k for k in known if k < a]
            upper = [k for k in known if k > a]
            if lower and upper:
                s, p = interp_pair(lower[-1], upper[0], a)
            elif (-a) in grid_cache:
                s, p = grid_cache[-a]
            elif lower:
                s, p = grid_cache[lower[-1]]
            elif upper:
                s, p = grid_cache[upper[0]]
            else:
                if unknown_spl_floor_db is None:
                    continue
                s = np.full_like(freq_grid, float(unknown_spl_floor_db), dtype=float)
                p = np.zeros_like(freq_grid, dtype=float)
        out[a] = Curve(freq=freq_grid.tolist(), spl=s.tolist(), phase=p.tolist())
    return out


def apply_horizontal_symmetry(raw_h: dict[int, Curve]) -> dict[int, Curve]:
    out = dict(raw_h)
    for a, c in list(raw_h.items()):
        if a == 0:
            continue
        if -a not in out:
            out[-a] = c
    return out


def calibrate_curve_to_ref(curve: Curve, ref: Curve) -> tuple[Curve, float, float]:
    cf = np.array(curve.freq)
    cs = np.array(curve.spl)
    cp = np.array(curve.phase)
    rf = np.array(ref.freq)
    rs = np.array(ref.spl)
    rp = np.array(ref.phase)
    if len(cf) < 16 or len(rf) < 16:
        return curve, 0.0, 0.0
    fmin = max(float(np.min(cf)), float(np.min(rf)))
    fmax = min(float(np.max(cf)), float(np.max(rf)))
    if fmax <= fmin:
        return curve, 0.0, 0.0
    grid = np.geomspace(max(20.0, fmin), min(20000.0, fmax), 240)
    ci_s, ci_p = curve_to_grid(curve, grid)
    ri_s, ri_p = curve_to_grid(ref, grid)
    spl_offset = float(np.median(ri_s - ci_s))
    phase_offset = float(np.median(((ri_p - ci_p + 180.0) % 360.0) - 180.0))
    out = Curve(
        freq=curve.freq,
        spl=[v + spl_offset for v in curve.spl],
        phase=[((v + phase_offset + 180.0) % 360.0) - 180.0 for v in curve.phase],
    )
    return out, spl_offset, phase_offset


def probe_tim(path: Path, header_bytes: int | None = None) -> None:
    info = parse_tim_header(path)
    h = info.data_offset if header_bytes is None else header_bytes
    data = path.read_bytes()
    payload = data[h : h + info.sample_count * 4]
    n = len(payload) // 4
    graph = info.graph
    window = info.window_type if info.window_type is not None else -1
    fft_size = info.fft_size if info.fft_size is not None else 0
    print(
        f"{path.name}: alg={info.algorithm} delta_ms={info.delta_time_ms:.9g} "
        f"fs={info.sample_rate_hz:.6g} samples={info.sample_count} file={info.file_size} "
        f"data_offset={h} payload={len(payload)} n32={n} fft_size={fft_size} "
        f"window_type={window}"
    )
    if graph is not None:
        print(
            f"time graph: marker={graph.mindex} cursor={graph.cindex} "
            f"display=[{graph.lowi}, {graph.highi}] slength={graph.slength}"
        )
    if n <= 0:
        return
    le = [struct.unpack_from("<f", payload, i * 4)[0] for i in range(min(n, 12))]
    be = [struct.unpack_from(">f", payload, i * 4)[0] for i in range(min(n, 12))]
    print("first <f:", " ".join(f"{v:.6g}" for v in le))
    print("first >f:", " ".join(f"{v:.6g}" for v in be))


def cmd_export_fft(args: argparse.Namespace) -> int:
    curve = parse_fft(args.input_fft)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    # Generic exports for immediate re-use while TIM decoding is under development.
    out = output_dir / f"{args.speaker} _H 0.txt"
    write_hv(out, curve)
    print(f"wrote {out}")
    if args.mirror_to_v:
        out_v = output_dir / f"{args.speaker} _V 0.txt"
        write_hv(out_v, curve)
        print(f"wrote {out_v}")
    return 0


def cmd_coverage(args: argparse.Namespace) -> int:
    coverage = find_tim_angle_coverage(args.data_dir)
    h = sorted(coverage["H"])
    v = sorted(coverage["V"])
    print(f"H angles ({len(h)}): {h}")
    print(f"V angles ({len(v)}): {v}")
    # Typical spinorama coverage target in this project is 36 H + 36 V.
    missing_h = [a for a in range(-180, 181, 10) if a not in coverage["H"]]
    missing_v = [a for a in range(-90, 91, 10) if a not in coverage["V"]]
    print(f"missing H vs -180..180 step10 ({len(missing_h)}): {missing_h}")
    print(f"missing V vs -90..90 step10 ({len(missing_v)}): {missing_v}")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    probe_tim(args.input_tim, header_bytes=args.header_bytes)
    return 0


def cmd_export_tim(args: argparse.Namespace) -> int:
    data_dir: Path = args.data_dir
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    wrote = 0
    raw_curves: dict[str, dict[int, Curve]] = {"H": {}, "V": {}}
    confidence: list[ConfidenceRow] = []
    decoded_by_stem: dict[str, Curve] = {}
    locked_mode: str | None = None
    locked_fs: float | None = None

    tims = sorted(data_dir.glob("*.TIM"))
    if args.tim_include_regex:
        cre = re.compile(args.tim_include_regex)
        tims = [t for t in tims if cre.search(t.name)]

    if args.auto_decode and args.lock_auto_decode and tims:
        anchor = None
        if args.lock_anchor_regex:
            a_re = re.compile(args.lock_anchor_regex)
            for t in tims:
                if a_re.search(t.name):
                    anchor = t
                    break
        if anchor is None:
            anchor = tims[0]
        locked_mode, locked_fs, _ = choose_decode_for_tim_scored(
            anchor, min_freq=args.min_freq, max_freq=args.max_freq
        )
        print(f"locked decode from {anchor.name}: mode={locked_mode} fs={locked_fs}")

    for tim in tims:
        m = re.match(r"^[^-]+-(.+)\.TIM$", tim.name)
        if not m:
            continue
        mapped = tim_suffix_to_hv(m.group(1))
        if mapped is None:
            continue
        axis, angle = mapped
        mode = args.mode
        fs = args.fs
        plaus = 0.0
        if args.auto_decode:
            if locked_mode is not None and locked_fs is not None:
                mode, fs = locked_mode, locked_fs
                ctmp = tim_to_curve(tim, mode=mode, fs=fs)
                plaus = plausibility_score(ctmp, min_freq=args.min_freq, max_freq=args.max_freq)
            else:
                mode, fs, plaus = choose_decode_for_tim_scored(
                    tim, min_freq=args.min_freq, max_freq=args.max_freq
                )
        elif fs is None:
            fs = parse_tim_header(tim).sample_rate_hz
        curve = tim_to_curve(tim, mode=mode, fs=fs)
        if not args.auto_decode:
            plaus = plausibility_score(curve, min_freq=args.min_freq, max_freq=args.max_freq)
        # keep physically meaningful band
        points = [
            (f, s, p)
            for f, s, p in zip(curve.freq, curve.spl, curve.phase, strict=False)
            if args.min_freq <= f <= args.max_freq and math.isfinite(s) and math.isfinite(p)
        ]
        if len(points) < 16:
            continue
        c = Curve([x[0] for x in points], [x[1] for x in points], [x[2] for x in points])
        c = apply_smoothing(c, args.smoothing)
        raw_curves[axis][angle] = c
        stem = tim.stem
        decoded_by_stem[stem] = c
        confidence.append(
            ConfidenceRow(
                filename=tim.name,
                axis=axis,
                angle=angle,
                source="tim",
                decode_mode=mode,
                fs=float(fs),
                plausibility=float(plaus),
                points=len(c.freq),
                synthesized=False,
            )
        )

    if args.debug_angles:
        print(f"raw H angles: {sorted(raw_curves['H'].keys())}")
        print(f"raw V angles: {sorted(raw_curves['V'].keys())}")

    if args.horizontal_symmetry:
        raw_curves["H"] = apply_horizontal_symmetry(raw_curves["H"])
        if args.debug_angles:
            print(f"sym H angles: {sorted(raw_curves['H'].keys())}")

    # Optional second-pass calibration from available TIM<->FFT stem pairs.
    global_spl_offset = 0.0
    global_phase_offset = 0.0
    if args.calibrate_with_fft:
        spl_offsets: list[float] = []
        phase_offsets: list[float] = []
        for fft in sorted(data_dir.glob("*.FFT")):
            stem = fft.stem
            try:
                if stem not in decoded_by_stem:
                    t = data_dir / f"{stem}.TIM"
                    if not t.exists():
                        continue
                    if args.auto_decode:
                        m2, fs2, _ = choose_decode_for_tim_scored(
                            t, min_freq=args.min_freq, max_freq=args.max_freq
                        )
                    else:
                        m2, fs2 = args.mode, args.fs
                    decoded_by_stem[stem] = tim_to_curve(t, mode=m2, fs=fs2)
                ref = parse_fft(fft)
                calibrated, ds, dp = calibrate_curve_to_ref(decoded_by_stem[stem], ref)
                decoded_by_stem[stem] = calibrated
                spl_offsets.append(ds)
                phase_offsets.append(dp)
            except Exception:
                continue
        if spl_offsets:
            global_spl_offset = float(np.median(np.array(spl_offsets)))
            global_phase_offset = float(np.median(np.array(phase_offsets)))
            for axis in ("H", "V"):
                for angle, c in list(raw_curves[axis].items()):
                    raw_curves[axis][angle] = Curve(
                        freq=c.freq,
                        spl=[v + global_spl_offset for v in c.spl],
                        phase=[
                            ((v + global_phase_offset + 180.0) % 360.0) - 180.0 for v in c.phase
                        ],
                    )

    # Ensure vertical on-axis exists for downstream loaders that expect Freq in V frame.
    if 0 not in raw_curves["V"] and 0 in raw_curves["H"]:
        raw_curves["V"][0] = raw_curves["H"][0]

    if args.synthesize_72:
        freq_grid = np.geomspace(
            max(args.min_freq, 20.0), min(args.max_freq, 20000.0), args.grid_points
        )
        if args.target_h == "pm90":
            target_h = [a for a in range(-90, 91, 10)]
        else:
            target_h = [a for a in range(-170, 190, 10)]
        if args.target_v == "pm90":
            target_v = [a for a in range(-90, 91, 10)]
        else:
            target_v = [a for a in range(-170, 190, 10)]
        synth_h = synthesize_axis_curves(
            raw_curves["H"],
            target_h,
            freq_grid,
            fill_unknown_with_onaxis=args.fill_unknown_with_onaxis,
            unknown_spl_floor_db=args.unknown_spl_floor_db,
        )
        synth_v = synthesize_axis_curves(
            raw_curves["V"],
            target_v,
            freq_grid,
            fill_unknown_with_onaxis=args.fill_unknown_with_onaxis,
            unknown_spl_floor_db=args.unknown_spl_floor_db,
        )
        for axis, curves in [("H", synth_h), ("V", synth_v)]:
            for angle, c in sorted(curves.items()):
                out = output_dir / f"{args.speaker} _{axis} {angle}.txt"
                write_hv(out, apply_smoothing(c, args.smoothing))
                wrote += 1
                if args.report_confidence and not any(
                    row.axis == axis and row.angle == angle for row in confidence
                ):
                    confidence.append(
                        ConfidenceRow(
                            filename=f"{args.speaker} _{axis} {angle}.txt",
                            axis=axis,
                            angle=angle,
                            source="synth",
                            decode_mode="n/a",
                            fs=0.0,
                            plausibility=0.0,
                            points=len(c.freq),
                            synthesized=True,
                        )
                    )
    else:
        for axis, curves in raw_curves.items():
            for angle, c in sorted(curves.items()):
                out = output_dir / f"{args.speaker} _{axis} {angle}.txt"
                write_hv(out, apply_smoothing(c, args.smoothing))
                wrote += 1
    print(f"wrote {wrote} files to {output_dir}")
    if args.calibrate_with_fft:
        print(
            f"calibration offsets applied: spl_offset={global_spl_offset:.4f} dB "
            f"phase_offset={global_phase_offset:.4f} deg"
        )
    if args.report_confidence:

        def classify_quality(row: ConfidenceRow) -> str:
            if row.synthesized:
                return "synth"
            if row.plausibility <= args.quality_good_max:
                return "good"
            if row.plausibility <= args.quality_warn_max:
                return "warn"
            return "bad"

        for row in confidence:
            row.quality = classify_quality(row)

        report = output_dir / "mlssa_confidence_report.csv"
        with report.open("w", encoding="utf-8") as f:
            f.write(
                "filename,axis,angle,source,decode_mode,fs,plausibility,points,synthesized,quality\n"
            )
            for row in sorted(confidence, key=lambda r: (r.axis, r.angle, r.source, r.filename)):
                f.write(
                    f"{row.filename},{row.axis},{row.angle},{row.source},{row.decode_mode},"
                    f"{row.fs:.6f},{row.plausibility:.6f},{row.points},{int(row.synthesized)},{row.quality}\n"
                )
        flagged = [
            row for row in confidence if (not row.synthesized) and row.quality in ("warn", "bad")
        ]
        flags_report = output_dir / "mlssa_confidence_flags.csv"
        with flags_report.open("w", encoding="utf-8") as f:
            f.write("filename,axis,angle,decode_mode,fs,plausibility,points,quality\n")
            for row in sorted(flagged, key=lambda r: (r.quality, r.axis, r.angle, r.filename)):
                f.write(
                    f"{row.filename},{row.axis},{row.angle},{row.decode_mode},"
                    f"{row.fs:.6f},{row.plausibility:.6f},{row.points},{row.quality}\n"
                )
        summary = {
            "total_rows": len(confidence),
            "decoded_rows": sum(1 for r in confidence if not r.synthesized),
            "synthesized_rows": sum(1 for r in confidence if r.synthesized),
            "decoded_good": sum(
                1 for r in confidence if (not r.synthesized) and r.quality == "good"
            ),
            "decoded_warn": sum(
                1 for r in confidence if (not r.synthesized) and r.quality == "warn"
            ),
            "decoded_bad": sum(1 for r in confidence if (not r.synthesized) and r.quality == "bad"),
            "flagged_rows": len(flagged),
            "calibration_spl_offset_db": global_spl_offset,
            "calibration_phase_offset_deg": global_phase_offset,
            "quality_good_max": args.quality_good_max,
            "quality_warn_max": args.quality_warn_max,
        }
        (output_dir / "mlssa_confidence_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        print(f"wrote confidence report: {report}")
        print(f"wrote flags report: {flags_report}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MLSSA importer helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_export = sub.add_parser("export-fft", help="export one FFT file to HV txt")
    p_export.add_argument("--speaker", required=True)
    p_export.add_argument("--input-fft", type=Path, required=True)
    p_export.add_argument("--output-dir", type=Path, required=True)
    p_export.add_argument("--mirror-to-v", action="store_true")
    p_export.set_defaults(func=cmd_export_fft)

    p_cov = sub.add_parser("coverage", help="report TIM-derived H/V angle coverage")
    p_cov.add_argument("--data-dir", type=Path, required=True)
    p_cov.set_defaults(func=cmd_coverage)

    p_probe = sub.add_parser("probe-tim", help="dump TIM header and early sample decode")
    p_probe.add_argument("--input-tim", type=Path, required=True)
    p_probe.add_argument("--header-bytes", type=int, default=None)
    p_probe.set_defaults(func=cmd_probe)

    p_export_tim = sub.add_parser(
        "export-tim", help="export mapped TIM files to HV txt via FFT decode"
    )
    p_export_tim.add_argument("--speaker", required=True)
    p_export_tim.add_argument("--data-dir", type=Path, required=True)
    p_export_tim.add_argument("--output-dir", type=Path, required=True)
    p_export_tim.add_argument("--mode", default="f32le", choices=["f32le"])
    p_export_tim.add_argument(
        "--fs",
        type=float,
        default=None,
        help="Override TIM sample rate in Hz; defaults to the rate stored in each TIM file.",
    )
    p_export_tim.add_argument("--auto-decode", action="store_true")
    p_export_tim.add_argument(
        "--lock-auto-decode",
        action="store_true",
        help="When auto-decode is enabled, lock one mode/fs for all files.",
    )
    p_export_tim.add_argument(
        "--lock-anchor-regex",
        default=None,
        help="Regex to choose lock anchor TIM file (e.g. 'RUSR-0G\\\\.TIM').",
    )
    p_export_tim.add_argument(
        "--tim-include-regex",
        default=None,
        help="Only process TIM filenames matching this regex.",
    )
    p_export_tim.add_argument("--synthesize-72", action="store_true")
    p_export_tim.add_argument("--calibrate-with-fft", action="store_true")
    p_export_tim.add_argument("--report-confidence", action="store_true")
    p_export_tim.add_argument("--fill-unknown-with-onaxis", action="store_true")
    p_export_tim.add_argument("--debug-angles", action="store_true")
    p_export_tim.add_argument(
        "--horizontal-symmetry",
        action="store_true",
        help="Mirror available horizontal angles (+theta <-> -theta) before synthesis.",
    )
    p_export_tim.add_argument(
        "--unknown-spl-floor-db",
        type=float,
        default=-100.0,
        help="SPL value used for completely unknown synthesized angles (default: -100 dB).",
    )
    p_export_tim.add_argument("--target-h", choices=["full", "pm90"], default="full")
    p_export_tim.add_argument("--target-v", choices=["full", "pm90"], default="full")
    p_export_tim.add_argument("--quality-good-max", type=float, default=1.5)
    p_export_tim.add_argument("--quality-warn-max", type=float, default=3.0)
    p_export_tim.add_argument("--grid-points", type=int, default=600)
    p_export_tim.add_argument(
        "--smoothing",
        type=int,
        default=0,
        help="Fractional octave smoothing denominator: 6=1/6, 24=1/24, 0=off",
    )
    p_export_tim.add_argument("--min-freq", type=float, default=20.0)
    p_export_tim.add_argument("--max-freq", type=float, default=20000.0)
    p_export_tim.set_defaults(func=cmd_export_tim)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
