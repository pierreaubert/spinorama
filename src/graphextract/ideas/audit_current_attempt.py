"""Reproduce the planning audit without changing the extraction implementation.

From src/graphextract:
  rtk proxy env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.. ../../.venv/bin/python \
    research/audit_current_attempt.py --output research/audit_results_2026-09-10.json

These probes document existing behavior; they are not production acceptance tests.
"""

import argparse
import hashlib
import importlib.util
import json
import logging
import math
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import scipy

from graphextract.eval_extraction import compare_curves
from spinorama.extract.axis_calibrate import AxisCalibration, calibrate_axes
from spinorama.extract.color_segment import CurveColorSpec, segment_curves
from spinorama.extract.curve_trace import trace_single_curve
from spinorama.extract.plot_detect import detect_plot_regions


def audit() -> dict:
    logging.disable(logging.CRITICAL)
    root = Path(__file__).resolve().parents[1]
    source_paths = [
        root / 'eval_extraction.py',
        root / 'extract_spinorama_colors.py',
        *sorted((root.parent / 'spinorama' / 'extract').glob('*.py')),
    ]
    result = {
        'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
        'git_revision': subprocess.check_output(
            ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True
        ).strip(),
        'environment': {
            'python': platform.python_version(),
            'opencv': cv2.__version__,
            'numpy': np.__version__,
            'scipy': scipy.__version__,
            'pytesseract_available': importlib.util.find_spec('pytesseract') is not None,
        },
        'source_sha256': {
            str(path.relative_to(root.parent)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in source_paths
        },
        'sample_images': [],
    }
    for path in sorted((root / 'datas').glob('*.png')):
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError(f'Cannot read sample image: {path}')
        regions = detect_plot_regions(img)
        item = {
            'file': path.name,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'width': img.shape[1],
            'height': img.shape[0],
            'regions': [],
        }
        for region in regions:
            crop = img[region.y:region.y + region.h, region.x:region.x + region.w]
            region_result = {
                'bbox_xywh': [region.x, region.y, region.w, region.h], 'title': region.title,
            }
            try:
                cal = calibrate_axes(crop, region)
                region_result.update({
                    'x_range': [cal.freq_min, cal.freq_max],
                    'y_range': [cal.db_min, cal.db_max],
                })
            except Exception as exc:
                region_result['calibration_error'] = type(exc).__name__ + ': ' + str(exc)
            item['regions'].append(region_result)
        result['sample_images'].append(item)

    gt_x = np.geomspace(20, 20000, 1000)
    result['two_endpoints_only'] = compare_curves(
        [(20., 80.), (20000., 80.)], gt_x, np.full(1000, 80.)
    ).to_dict()

    img = np.full((120, 200, 3), 255, np.uint8)
    img[50, 10:190] = (0, 0, 255)
    spec = CurveColorSpec(name='red', hsv_ranges=[((0, 100, 100), (10, 255, 255))])
    masks = segment_curves(img, [spec])
    result['one_pixel_line'] = {
        'input_pixels': 180, 'output_pixels': int(np.count_nonzero(masks.get('red', []))),
    }

    cal = AxisCalibration(
        log_freq_a=199 / 3, log_freq_b=-(199 / 3) * math.log10(20),
        db_c=-1, db_d=100,
        plot_x_min=0, plot_x_max=199, plot_y_min=0, plot_y_max=119,
    )
    mask = np.zeros((120, 200), np.uint8)
    mask[50, :] = 255
    mask[50, 100] = 0
    mask[45, 100] = 255
    points = trace_single_curve(mask, cal)
    nearest = min(points, key=lambda p: abs(cal.freq_to_pixel_x(p[0]) - 100))
    output_y = cal.db_to_pixel_y(nearest[1])
    result['smoothing_spike'] = {
        'source_y_pixel': 45, 'output_y_pixel': output_y,
        'absolute_pixel_error': abs(output_y - 45),
    }
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    payload = json.dumps(audit(), indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.write_text(payload)
        print(f'Audit written to {args.output}')
    else:
        print(payload, end='')
