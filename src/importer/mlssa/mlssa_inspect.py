#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# MLSSA data inspection helper.
#
# This script is intentionally conservative:
# - `.TIM` parsing only reads header-level metadata we can verify.
# - `.FFT` parsing extracts frequency / SPL / phase triplets from text.
#

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import re
import struct


MLSSA_MAGIC = 0xFFFFABCD


@dataclass
class TimInfo:
    path: Path
    algorithm: int
    delta_time_ms: float
    sample_count: int
    file_size: int
    data_offset: int
    setup_offset: int | None
    fft_size: int | None
    window_type: int | None
    marker_index: int | None
    cursor_index: int | None
    sample_rate_hz: float


def parse_tim_info(path: Path) -> TimInfo:
    data = path.read_bytes()
    if len(data) < 14:
        msg = f"{path} is too short ({len(data)} bytes)"
        raise ValueError(msg)
    magic = struct.unpack_from("<I", data, 0)[0]
    if magic != MLSSA_MAGIC:
        msg = f"{path} has bad MLSSA magic: 0x{magic:08x}"
        raise ValueError(msg)
    algorithm = struct.unpack_from("<H", data, 4)[0]
    delta_time_ms = struct.unpack_from("<f", data, 6)[0]
    sample_count = struct.unpack_from("<I", data, 10)[0]
    file_size = len(data)
    data_offset = 14
    setup_offset = data_offset + sample_count * 4 + 80 + 60
    fft_size = None
    window_type = None
    marker_index = None
    cursor_index = None
    if sample_count > 0 and delta_time_ms > 0 and len(data) >= setup_offset + 312:
        fft_size = struct.unpack_from("<I", data, setup_offset)[0]
        window_type = struct.unpack_from("<H", data, setup_offset + 4)[0]
        graph_offset = setup_offset + 250
        cursor_index = struct.unpack_from("<I", data, graph_offset + 8)[0]
        marker_index = struct.unpack_from("<I", data, graph_offset + 12)[0]
    return TimInfo(
        path=path,
        algorithm=algorithm,
        delta_time_ms=delta_time_ms,
        sample_count=sample_count,
        file_size=file_size,
        data_offset=data_offset,
        setup_offset=setup_offset if len(data) >= setup_offset else None,
        fft_size=fft_size,
        window_type=window_type,
        marker_index=marker_index,
        cursor_index=cursor_index,
        sample_rate_hz=1000.0 / delta_time_ms if delta_time_ms > 0 else 0.0,
    )


@dataclass
class FftInfo:
    path: Path
    title: str
    points: list[tuple[float, float, float]]


FFT_ROW_RE = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*$"
)


def parse_fft(path: Path) -> FftInfo:
    lines = path.read_text(encoding="latin1").splitlines()
    title = lines[0].strip() if lines else ""
    points: list[tuple[float, float, float]] = []
    for line in lines:
        m = FFT_ROW_RE.match(line)
        if not m:
            continue
        freq, spl, phase = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
        if freq <= 0:
            continue
        points.append((freq, spl, phase))
    return FftInfo(path=path, title=title, points=points)


def inspect_dir(data_dir: Path) -> None:
    tim_files = sorted(data_dir.glob("*.TIM"))
    fft_files = sorted(data_dir.glob("*.FFT"))

    print(f"TIM files: {len(tim_files)}")
    for tim in tim_files:
        info = parse_tim_info(tim)
        print(
            f"  {tim.name:12s} alg={info.algorithm} fs={info.sample_rate_hz:9.3f}Hz "
            f"samples={info.sample_count:6d} file={info.file_size:7d}B "
            f"data@{info.data_offset:3d} fft={info.fft_size or 0:5d} "
            f"win={info.window_type if info.window_type is not None else -1:2d} "
            f"marker={info.marker_index if info.marker_index is not None else -1:5d} "
            f"cursor={info.cursor_index if info.cursor_index is not None else -1:5d}"
        )

    print(f"\nFFT files: {len(fft_files)}")
    for fft in fft_files:
        info = parse_fft(fft)
        min_f = info.points[0][0] if info.points else 0.0
        max_f = info.points[-1][0] if info.points else 0.0
        print(
            f"  {fft.name:12s} points={len(info.points):4d} "
            f"f=[{min_f:.3f}, {max_f:.3f}] title={info.title[:64]}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect MLSSA .TIM/.FFT files")
    parser.add_argument("data_dir", type=Path, help="Directory containing MLSSA files")
    args = parser.parse_args()
    inspect_dir(args.data_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
