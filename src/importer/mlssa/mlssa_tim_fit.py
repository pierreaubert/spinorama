#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import re

import numpy as np

from mlssa2hv import decode_tim_samples, parse_tim_header, tim_fft_segment, tim_window


FFT_ROW_RE = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*$"
)


@dataclass
class RefCurve:
    freq: np.ndarray
    mag: np.ndarray
    phase: np.ndarray


def load_fft(path: Path) -> RefCurve:
    f, m, p = [], [], []
    for line in path.read_text(encoding="latin1").splitlines():
        mm = FFT_ROW_RE.match(line)
        if not mm:
            continue
        ff = float(mm.group(1))
        if ff <= 0:
            continue
        f.append(ff)
        m.append(float(mm.group(2)))
        p.append(float(mm.group(3)))
    return RefCurve(np.array(f), np.array(m), np.array(p))


def wrap_deg(x: np.ndarray) -> np.ndarray:
    return ((x + 180.0) % 360.0) - 180.0


def score_candidate(
    sig: np.ndarray, fs: float, nfft: int, window_type: int | None, ref: RefCurve
) -> float:
    n = len(sig)
    if n < 16:
        return 1e9
    sig = sig - np.mean(sig)
    win = tim_window(window_type, n)
    sp = np.fft.rfft(sig * win, n=nfft)
    f = np.fft.rfftfreq(nfft, d=1.0 / fs)
    mag = 20.0 * np.log10(np.maximum(np.abs(sp), 1e-30))
    phase = np.angle(sp, deg=True)
    # interpolate to reference grid
    valid = (ref.freq >= f[0]) & (ref.freq <= f[-1])
    if valid.sum() < 80:
        return 1e9
    rf = ref.freq[valid]
    rm = ref.mag[valid]
    rp = ref.phase[valid]
    mi = np.interp(rf, f, mag)
    pi = np.interp(rf, f, phase)
    # best constant gain offset
    off = np.mean(rm - mi)
    md = (mi + off) - rm
    pd = wrap_deg(pi - rp)
    return float(np.sqrt(np.mean(md * md)) + 0.08 * np.sqrt(np.mean(pd * pd)))


def fit_one(tim_path: Path, fft_path: Path, _header_bytes: int) -> dict:
    raw = tim_path.read_bytes()
    info = parse_tim_header(tim_path)
    ref = load_fft(fft_path)
    samples = decode_tim_samples(raw, info)
    sig, start, stop = tim_fft_segment(samples, info)
    nfft = info.fft_size or len(sig)
    if nfft < len(sig):
        nfft = 1 << (len(sig) - 1).bit_length()
    s = score_candidate(sig, info.sample_rate_hz, nfft, info.window_type, ref)
    return {
        "score": s,
        "tim": tim_path.name,
        "fft": fft_path.name,
        "mode": "f32le",
        "fs": info.sample_rate_hz,
        "n": len(sig),
        "window_start": int(start),
        "window_stop": int(stop),
        "fft_size": int(nfft),
        "window_type": int(info.window_type if info.window_type is not None else 0),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Fit MLSSA TIM decode mode against reference FFT files"
    )
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--header-bytes", type=int, default=14, help=argparse.SUPPRESS)
    ap.add_argument("--output-json", type=Path, default=None)
    args = ap.parse_args()

    pairs = [
        ("RUSR-LFG.TIM", "RUSR-LFG.FFT"),
        ("RUSR-HFG.TIM", "RUSR-HFG.FFT"),
        ("RUSR-PO.TIM", "RUSR-PO.FFT"),
    ]
    results = []
    for t, f in pairs:
        tp = args.data_dir / t
        fp = args.data_dir / f
        if tp.exists() and fp.exists():
            results.append(fit_one(tp, fp, args.header_bytes))
    if not results:
        raise SystemExit("no TIM/FFT training pairs found")
    for r in results:
        print(
            f"{r['tim']} vs {r['fft']}: mode={r['mode']} fs={r['fs']} score={r['score']:.4f} n={r['n']}"
        )

    # choose globally most frequent/lowest score
    by_mode = {}
    for r in results:
        key = (r["mode"], r["fs"])
        by_mode.setdefault(key, []).append(r["score"])
    winner, scores = min(by_mode.items(), key=lambda kv: (len(kv[1]) * -1, float(np.mean(kv[1]))))
    out = {
        "header_bytes": args.header_bytes,
        "mode": winner[0],
        "fs": float(winner[1]),
        "pair_results": results,
        "winner_mean_score": float(np.mean(scores)),
    }
    print(f"winner: mode={out['mode']} fs={out['fs']} mean_score={out['winner_mean_score']:.4f}")
    if args.output_json:
        for r in out["pair_results"]:
            r["score"] = float(r["score"])
            r["fs"] = float(r["fs"])
        args.output_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"wrote {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
