# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
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

"""Evaluation framework for curve extraction quality.

Closed-loop evaluation: render Plotly JSON → PNG, extract curves from PNG,
compare extracted vs original ground truth decoded from bdata.
"""

from __future__ import annotations

import base64
import html as html_mod
import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import numpy.typing as npt
from scipy.interpolate import interp1d
from scipy.stats import pearsonr

from spinorama import logger
from spinorama.extract.axis_calibrate import AxisCalibration, calibration_from_plotly_layout
from spinorama.extract.color_segment import segment_curves
from spinorama.extract.curve_trace import trace_single_curve
from graphextract.extract_spinorama_colors import CURVE_HEX_COLORS, GRAPH_TYPE_SPECS

# Trace names to skip when loading ground truth
_SKIP_PATTERNS = {"slope", "zone", "Band", "Midrange"}


@dataclass
class PlotlyGroundTruth:
    """Ground truth data loaded from a Plotly JSON file."""

    curves: dict[str, tuple[npt.NDArray, npt.NDArray]]
    y2_curve_names: set[str]


def load_plotly_ground_truth(json_path: str | Path) -> PlotlyGroundTruth:
    """Load ground truth curves from a Plotly JSON file.

    Decodes bdata-encoded x/y arrays from each visible, non-fill trace.
    Tracks which traces use yaxis2.

    Args:
        json_path: Path to the Plotly JSON file.

    Returns:
        PlotlyGroundTruth with curves dict and set of y2 curve names.
    """
    with open(json_path) as f:
        fig_data = json.load(f)

    curves: dict[str, tuple[npt.NDArray, npt.NDArray]] = {}
    y2_names: set[str] = set()

    for trace in fig_data.get("data", []):
        # Skip invisible traces
        if trace.get("visible") is False:
            continue

        # Skip fill traces
        if trace.get("fill") in ("toself", "tonexty"):
            continue

        name = trace.get("name", "")

        # Skip slope/zone/Band/Midrange traces
        if any(pat in name for pat in _SKIP_PATTERNS):
            continue

        x_data = trace.get("x")
        y_data = trace.get("y")
        if x_data is None or y_data is None:
            continue

        x_arr = _decode_trace_data(x_data)
        y_arr = _decode_trace_data(y_data)

        if x_arr is not None and y_arr is not None and len(x_arr) == len(y_arr) and len(x_arr) > 0:
            curves[name] = (x_arr, y_arr)
            if trace.get("yaxis") == "y2":
                y2_names.add(name)

    return PlotlyGroundTruth(curves=curves, y2_curve_names=y2_names)


def _decode_trace_data(data: dict | list) -> npt.NDArray | None:
    """Decode Plotly trace data, handling both bdata and plain arrays."""
    if isinstance(data, list):
        return np.array(data, dtype=np.float64)

    if isinstance(data, dict) and "bdata" in data:
        raw = base64.b64decode(data["bdata"])
        dtype_str = data.get("dtype", "f8")
        # Map Plotly dtype strings to numpy dtypes
        dtype_map = {"f8": "<f8", "f4": "<f4", "i4": "<i4", "i2": "<i2"}
        np_dtype = dtype_map.get(dtype_str, f"<{dtype_str}")
        return np.frombuffer(raw, np_dtype)

    return None


def render_plotly_to_png(
    json_path: str | Path,
    width: int = 1200,
    height: int = 800,
) -> npt.NDArray:
    """Render a Plotly JSON file to a BGR image array.

    Args:
        json_path: Path to the Plotly JSON file.
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        BGR numpy array (h, w, 3).
    """
    import plotly.io as pio

    with open(json_path) as f:
        raw_json = f.read()

    fig = pio.from_json(raw_json)
    # Disable autoexpand so rendered margins match the JSON-specified values exactly
    fig.update_layout(margin=dict(autoexpand=False))
    png_bytes = fig.to_image(format="png", width=width, height=height)

    # Decode PNG bytes to BGR array
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        msg = f"Failed to decode rendered PNG for {json_path}"
        raise RuntimeError(msg)

    return img


@dataclass
class CurveMetrics:
    """Quality metrics for a single extracted curve vs ground truth."""

    rms_error_db: float
    max_abs_error_db: float
    correlation: float
    frequency_coverage: float

    def to_dict(self) -> dict:
        return {
            "rms_error_db": round(self.rms_error_db, 4),
            "max_abs_error_db": round(self.max_abs_error_db, 4),
            "correlation": round(self.correlation, 6),
            "frequency_coverage": round(self.frequency_coverage, 4),
        }


def compare_curves(
    extracted_pts: list[tuple[float, float]],
    gt_x: npt.NDArray,
    gt_y: npt.NDArray,
    n_grid_points: int = 500,
) -> CurveMetrics:
    """Compare extracted curve points against ground truth.

    Interpolates both curves onto a common log-spaced frequency grid
    in the overlapping frequency range.

    Args:
        extracted_pts: List of (freq_hz, dB) from extraction.
        gt_x: Ground truth frequency array.
        gt_y: Ground truth dB array.
        n_grid_points: Number of interpolation points.

    Returns:
        CurveMetrics with RMS error, max error, correlation, and coverage.
    """
    if len(extracted_pts) < 2:
        return CurveMetrics(
            rms_error_db=float("inf"),
            max_abs_error_db=float("inf"),
            correlation=0.0,
            frequency_coverage=0.0,
        )

    ext_x = np.array([p[0] for p in extracted_pts])
    ext_y = np.array([p[1] for p in extracted_pts])

    # Overlapping frequency range
    overlap_min = max(ext_x.min(), gt_x.min())
    overlap_max = min(ext_x.max(), gt_x.max())

    if overlap_min >= overlap_max:
        return CurveMetrics(
            rms_error_db=float("inf"),
            max_abs_error_db=float("inf"),
            correlation=0.0,
            frequency_coverage=0.0,
        )

    # Common log-spaced grid
    grid = np.logspace(np.log10(overlap_min), np.log10(overlap_max), n_grid_points)

    # Interpolate both curves on log10(freq)
    gt_interp = interp1d(np.log10(gt_x), gt_y, kind="linear", bounds_error=False, fill_value=np.nan)
    ext_interp = interp1d(
        np.log10(ext_x), ext_y, kind="linear", bounds_error=False, fill_value=np.nan
    )

    gt_on_grid = gt_interp(np.log10(grid))
    ext_on_grid = ext_interp(np.log10(grid))

    # Only compare where both have valid data
    valid = np.isfinite(gt_on_grid) & np.isfinite(ext_on_grid)
    n_valid = int(np.sum(valid))
    if n_valid < 2:
        return CurveMetrics(
            rms_error_db=float("inf"),
            max_abs_error_db=float("inf"),
            correlation=0.0,
            frequency_coverage=0.0,
        )

    diff = ext_on_grid[valid] - gt_on_grid[valid]
    rms = float(np.sqrt(np.mean(diff**2)))
    max_abs = float(np.max(np.abs(diff)))

    # Handle constant input (all identical values)
    gt_std = float(np.std(gt_on_grid[valid]))
    ext_std = float(np.std(ext_on_grid[valid]))
    if gt_std < 1e-10 or ext_std < 1e-10:
        # Correlation is undefined for constant input; if both are constant and close, it's a match
        corr = 1.0 if rms < 0.01 else 0.0
    else:
        corr, _ = pearsonr(gt_on_grid[valid], ext_on_grid[valid])

    # Coverage: fraction of GT frequency range covered by extraction
    gt_range_log = np.log10(gt_x.max()) - np.log10(gt_x.min())
    overlap_range_log = np.log10(overlap_max) - np.log10(overlap_min)
    coverage = overlap_range_log / gt_range_log if gt_range_log > 0 else 0.0

    return CurveMetrics(
        rms_error_db=rms,
        max_abs_error_db=max_abs,
        correlation=float(corr),
        frequency_coverage=float(coverage),
    )


@dataclass
class SingleGraphResult:
    """Full result of evaluating one graph, including artifacts for HTML report."""

    file_path: str
    graph_type: str
    status: str
    error: str | None
    curves: dict[str, dict]
    rendered_img: npt.NDArray | None = None
    gt_curves: dict[str, tuple[npt.NDArray, npt.NDArray]] = field(default_factory=dict)
    extracted_curves: dict[str, list[tuple[float, float]]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialisable dict (without images/arrays)."""
        return {
            "file_path": self.file_path,
            "graph_type": self.graph_type,
            "status": self.status,
            "curves": self.curves,
            "error": self.error,
        }


def evaluate_single_graph(
    json_path: str | Path,
    graph_type: str,
    calibration_mode: str = "oracle",
    render_width: int = 1200,
    render_height: int = 800,
) -> SingleGraphResult:
    """Evaluate extraction quality for a single Plotly graph file.

    Args:
        json_path: Path to the Plotly JSON file.
        graph_type: One of 'CEA2034', 'On Axis', 'Early Reflections', 'Estimated In-Room Response'.
        calibration_mode: 'oracle' uses layout metadata, 'auto' uses full OCR/grid pipeline.
        render_width: Width for PNG rendering.
        render_height: Height for PNG rendering.

    Returns:
        SingleGraphResult with metrics, rendered image, ground truth, and extracted curves.
    """
    json_path = Path(json_path)

    def _err(msg: str) -> SingleGraphResult:
        return SingleGraphResult(
            file_path=str(json_path),
            graph_type=graph_type,
            status="error",
            error=msg,
            curves={},
        )

    curve_specs = GRAPH_TYPE_SPECS.get(graph_type)
    if curve_specs is None:
        return _err(f"Unknown graph type: {graph_type}")

    # Load ground truth
    gt_data = load_plotly_ground_truth(json_path)
    if not gt_data.curves:
        return _err("No ground truth curves found")

    gt_curves = gt_data.curves
    y2_curve_names = gt_data.y2_curve_names

    # Render to PNG
    img = render_plotly_to_png(json_path, width=render_width, height=render_height)

    # Build calibration
    with open(json_path) as f:
        fig_data = json.load(f)
    layout = fig_data.get("layout", {})

    if calibration_mode == "oracle":
        calibration = calibration_from_plotly_layout(layout, render_width, render_height)
        # Build y2 calibration if layout has yaxis2
        calibration_y2 = None
        if layout.get("yaxis2") and y2_curve_names:
            calibration_y2 = calibration_from_plotly_layout(
                layout,
                render_width,
                render_height,
                yaxis_key="yaxis2",
            )
    else:
        # Auto: use the full extraction pipeline's calibration
        from spinorama.extract.plot_detect import PlotRegion

        region = PlotRegion(x=0, y=0, w=render_width, h=render_height, title=graph_type)
        from spinorama.extract.axis_calibrate import calibrate_axes

        calibration = calibrate_axes(img, region)
        calibration_y2 = None

    # Extract the plot area from the image using calibration bounds
    plot_img = img[
        calibration.plot_y_min : calibration.plot_y_max,
        calibration.plot_x_min : calibration.plot_x_max,
    ]

    # Color segmentation
    masks = segment_curves(plot_img, curve_specs)

    def _adjusted(cal: AxisCalibration) -> AxisCalibration:
        """Adjust calibration for cropped image."""
        return AxisCalibration(
            log_freq_a=cal.log_freq_a,
            log_freq_b=cal.log_freq_b - calibration.plot_x_min,
            db_c=cal.db_c,
            db_d=cal.db_d - calibration.plot_y_min,
            plot_x_min=0,
            plot_x_max=calibration.plot_x_max - calibration.plot_x_min,
            plot_y_min=0,
            plot_y_max=calibration.plot_y_max - calibration.plot_y_min,
        )

    adjusted_cal = _adjusted(calibration)
    adjusted_cal_y2 = _adjusted(calibration_y2) if calibration_y2 else None

    curve_metrics: dict[str, dict] = {}
    extracted_curves: dict[str, list[tuple[float, float]]] = {}
    for curve_name, mask in masks.items():
        # Use y2 calibration for curves on the right axis
        if curve_name in y2_curve_names and adjusted_cal_y2:
            cal = adjusted_cal_y2
        else:
            cal = adjusted_cal
        extracted_pts = trace_single_curve(mask, cal)
        if not extracted_pts:
            logger.debug("No points traced for '%s' in %s", curve_name, json_path.name)
            continue

        extracted_curves[curve_name] = extracted_pts

        # Find matching ground truth curve
        gt_match = gt_curves.get(curve_name)
        if gt_match is None:
            logger.debug("No ground truth for '%s' in %s", curve_name, json_path.name)
            continue

        gt_x, gt_y = gt_match
        metrics = compare_curves(extracted_pts, gt_x, gt_y)
        curve_metrics[curve_name] = metrics.to_dict()

    status = "success" if curve_metrics else "error"
    error = None if curve_metrics else "No curves matched between extraction and ground truth"

    return SingleGraphResult(
        file_path=str(json_path),
        graph_type=graph_type,
        status=status,
        error=error,
        curves=curve_metrics,
        rendered_img=img,
        gt_curves=gt_curves,
        extracted_curves=extracted_curves,
    )


def evaluate_batch(
    file_list: list[tuple[Path, str]],
    calibration_mode: str = "oracle",
) -> list[SingleGraphResult]:
    """Run evaluate_single_graph for a list of files.

    Args:
        file_list: List of (json_path, graph_type) tuples.
        calibration_mode: 'oracle' or 'auto'.

    Returns:
        List of SingleGraphResult.
    """
    results: list[SingleGraphResult] = []
    for json_path, graph_type in file_list:
        try:
            result = evaluate_single_graph(json_path, graph_type, calibration_mode)
        except Exception as exc:
            result = SingleGraphResult(
                file_path=str(json_path),
                graph_type=graph_type,
                status="error",
                error=str(exc),
                curves={},
            )
            logger.warning("Failed on %s: %s", json_path, exc)
        results.append(result)
    return results


def compute_aggregate_stats(results: list[SingleGraphResult]) -> dict:
    """Compute aggregate statistics from evaluation results.

    Returns:
        Dict with 'by_graph_type', 'by_curve_name', and 'worst_cases'.
    """
    gt_metrics: dict[str, dict[str, list[float]]] = {}
    gt_counts: dict[str, tuple[int, int]] = {}  # (total, success)
    by_curve_name: dict[str, dict[str, list[float]]] = {}

    for r in results:
        gt = r.graph_type
        total, success = gt_counts.get(gt, (0, 0))
        total += 1
        if gt not in gt_metrics:
            gt_metrics[gt] = {"rms": [], "max_abs": [], "corr": [], "coverage": []}

        if r.status != "success":
            gt_counts[gt] = (total, success)
            continue
        success += 1
        gt_counts[gt] = (total, success)

        for curve_name, metrics in r.curves.items():
            if curve_name not in by_curve_name:
                by_curve_name[curve_name] = {"rms": [], "max_abs": [], "corr": [], "coverage": []}

            rms = metrics["rms_error_db"]
            max_abs = metrics["max_abs_error_db"]
            corr = metrics["correlation"]
            cov = metrics["frequency_coverage"]

            if np.isfinite(rms):
                gt_metrics[gt]["rms"].append(rms)
                by_curve_name[curve_name]["rms"].append(rms)
            if np.isfinite(max_abs):
                gt_metrics[gt]["max_abs"].append(max_abs)
                by_curve_name[curve_name]["max_abs"].append(max_abs)
            gt_metrics[gt]["corr"].append(corr)
            by_curve_name[curve_name]["corr"].append(corr)
            gt_metrics[gt]["coverage"].append(cov)
            by_curve_name[curve_name]["coverage"].append(cov)

    def _summarize(values: list[float]) -> dict:
        if not values:
            return {}
        arr = np.array(values)
        return {
            "mean": round(float(np.mean(arr)), 4),
            "median": round(float(np.median(arr)), 4),
            "std": round(float(np.std(arr)), 4),
            "p90": round(float(np.percentile(arr, 90)), 4),
            "p95": round(float(np.percentile(arr, 95)), 4),
            "max": round(float(np.max(arr)), 4),
            "count": len(values),
        }

    agg_by_graph: dict[str, dict] = {}
    for gt, data in gt_metrics.items():
        total, success = gt_counts[gt]
        agg_by_graph[gt] = {
            "success_rate": round(success / total, 4) if total > 0 else 0.0,
            "total": total,
            "success": success,
            "rms_error_db": _summarize(data["rms"]),
            "max_abs_error_db": _summarize(data["max_abs"]),
            "correlation": _summarize(data["corr"]),
            "frequency_coverage": _summarize(data["coverage"]),
        }

    agg_by_curve: dict[str, dict] = {}
    for cn, data in by_curve_name.items():
        agg_by_curve[cn] = {
            "rms_error_db": _summarize(data["rms"]),
            "max_abs_error_db": _summarize(data["max_abs"]),
            "correlation": _summarize(data["corr"]),
            "frequency_coverage": _summarize(data["coverage"]),
        }

    # Worst cases: top 10 by RMS error across all files/curves
    worst_cases: list[dict] = []
    for r in results:
        if r.status != "success":
            continue
        for curve_name, metrics in r.curves.items():
            rms = metrics["rms_error_db"]
            if np.isfinite(rms):
                worst_cases.append(
                    {
                        "file_path": r.file_path,
                        "graph_type": r.graph_type,
                        "curve_name": curve_name,
                        "rms_error_db": rms,
                        "max_abs_error_db": metrics["max_abs_error_db"],
                    }
                )

    worst_cases.sort(key=lambda x: x["rms_error_db"], reverse=True)
    worst_cases = worst_cases[:10]

    return {
        "by_graph_type": agg_by_graph,
        "by_curve_name": agg_by_curve,
        "worst_cases": worst_cases,
    }


def _img_to_data_uri(img: npt.NDArray) -> str:
    """Encode a BGR image as a base64 PNG data URI."""
    _, buf = cv2.imencode(".png", img)
    b64 = base64.b64encode(buf.tobytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _downsample_for_json(
    pts: list[tuple[float, float]], max_points: int = 300
) -> tuple[list[float], list[float]]:
    """Thin a point list to at most max_points for the inline Plotly chart."""
    if len(pts) <= max_points:
        return [p[0] for p in pts], [p[1] for p in pts]
    step = len(pts) / max_points
    indices = [int(i * step) for i in range(max_points)]
    return [pts[i][0] for i in indices], [pts[i][1] for i in indices]


_Y2_CURVES = {"Sound Power DI", "Early Reflections DI"}


def _build_plotly_traces_json(
    result: SingleGraphResult,
) -> str:
    """Build a JSON array of Plotly trace objects for one graph result.

    DI curves (Sound Power DI, Early Reflections DI) are placed on yaxis2 (right).
    """
    traces: list[dict] = []

    # Ground truth curves (solid lines)
    for name, (gt_x, gt_y) in result.gt_curves.items():
        xs, ys = _downsample_for_json(list(zip(gt_x.tolist(), gt_y.tolist())))
        color = CURVE_HEX_COLORS.get(name, "#888888")
        trace: dict = {
            "x": xs,
            "y": ys,
            "mode": "lines",
            "name": f"{name} (truth)",
            "line": {"color": color, "width": 2},
            "legendgroup": name,
        }
        if name in _Y2_CURVES:
            trace["yaxis"] = "y2"
        traces.append(trace)

    # Extracted curves (dashed lines)
    for name, pts in result.extracted_curves.items():
        xs, ys = _downsample_for_json(pts)
        color = CURVE_HEX_COLORS.get(name, "#888888")
        trace = {
            "x": xs,
            "y": ys,
            "mode": "lines",
            "name": f"{name} (extracted)",
            "line": {"color": color, "width": 2, "dash": "dash"},
            "legendgroup": name,
        }
        if name in _Y2_CURVES:
            trace["yaxis"] = "y2"
        traces.append(trace)

    return json.dumps(traces)


def generate_html_report(
    results: list[SingleGraphResult],
    output_path: str | Path,
    aggregate: dict | None = None,
) -> Path:
    """Generate a self-contained HTML report showing original vs extracted curves.

    For each evaluated file the report shows:
    - the rendered original image
    - a metrics table
    - an interactive Plotly chart with ground truth (solid) vs extracted (dashed) curves

    Args:
        results: List of SingleGraphResult from evaluate_batch.
        output_path: Where to write the HTML file.
        aggregate: Optional pre-computed aggregate stats to include as summary.

    Returns:
        Path to the written HTML file.
    """
    output_path = Path(output_path)

    # ── summary section ────────────────────────────────────────────
    summary_html = ""
    if aggregate:
        rows = ""
        for gt, stats in aggregate["by_graph_type"].items():
            rms = stats.get("rms_error_db", {})
            corr = stats.get("correlation", {})
            cov = stats.get("frequency_coverage", {})
            rows += (
                f"<tr><td>{html_mod.escape(gt)}</td>"
                f"<td>{stats['success']}/{stats['total']}</td>"
                f"<td>{rms.get('median', '-')}</td>"
                f"<td>{rms.get('p95', '-')}</td>"
                f"<td>{corr.get('median', '-')}</td>"
                f"<td>{cov.get('median', '-')}</td></tr>\n"
            )
        summary_html = f"""
<section class="summary">
<h2>Aggregate Summary</h2>
<table>
<thead><tr>
  <th>Graph Type</th><th>Success</th>
  <th>RMS median</th><th>RMS p95</th>
  <th>Corr median</th><th>Coverage median</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>
</section>
"""

    # ── per-file sections ──────────────────────────────────────────
    file_sections: list[str] = []
    for idx, r in enumerate(results):
        escaped_path = html_mod.escape(r.file_path)

        # Status badge
        if r.status == "success":
            badge = '<span class="badge ok">OK</span>'
        else:
            badge = f'<span class="badge err">ERROR: {html_mod.escape(r.error or "unknown")}</span>'

        # Original image
        img_tag = ""
        if r.rendered_img is not None:
            img_tag = f'<img src="{_img_to_data_uri(r.rendered_img)}" alt="original render">'

        # Metrics table
        metrics_rows = ""
        for cname, m in r.curves.items():
            metrics_rows += (
                f"<tr><td>{html_mod.escape(cname)}</td>"
                f"<td>{m['rms_error_db']:.2f}</td>"
                f"<td>{m['max_abs_error_db']:.2f}</td>"
                f"<td>{m['correlation']:.4f}</td>"
                f"<td>{m['frequency_coverage']:.1%}</td></tr>\n"
            )
        metrics_table = ""
        if metrics_rows:
            metrics_table = f"""
<table class="metrics">
<thead><tr><th>Curve</th><th>RMS (dB)</th><th>Max (dB)</th><th>Corr</th><th>Coverage</th></tr></thead>
<tbody>{metrics_rows}</tbody>
</table>"""

        # Plotly chart div — height matches image aspect ratio (2:3)
        chart_div = ""
        if r.extracted_curves or r.gt_curves:
            traces_json = _build_plotly_traces_json(r)
            div_id = f"chart_{idx}"
            has_y2 = any(n in _Y2_CURVES for n in r.gt_curves) or any(
                n in _Y2_CURVES for n in r.extracted_curves
            )
            y2_layout = ""
            if has_y2:
                y2_layout = 'yaxis2: {title: "DI (dB)", overlaying: "y", side: "right", showgrid: false, zeroline: true, zerolinecolor: "#ccc", range: [-5, 25]},'
            chart_div = f"""
<div id="{div_id}" class="chart"></div>
<script>
Plotly.newPlot("{div_id}", {traces_json}, {{
  xaxis: {{type: "log", title: "Frequency (Hz)", range: [Math.log10(20), Math.log10(20000)]}},
  yaxis: {{title: "SPL (dB)"}},
  {y2_layout}
  legend: {{orientation: "h", y: -0.08}},
  margin: {{t: 30, b: 60}},
  height: 600,
}}, {{responsive: true}});
</script>"""

        file_sections.append(f"""
<section class="file-result">
<h3>{html_mod.escape(r.graph_type)} &mdash; {badge}</h3>
<p class="path">{escaped_path}</p>
<div class="columns">
  <div class="col">{img_tag}</div>
  <div class="col">{chart_div}</div>
</div>
{metrics_table}
</section>
""")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Extraction Evaluation Report</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #fafafa; color: #222; }}
  h1 {{ border-bottom: 2px solid #333; padding-bottom: 8px; }}
  h2 {{ margin-top: 32px; }}
  h3 {{ margin: 0 0 8px; }}
  table {{ border-collapse: collapse; margin: 12px 0; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: right; }}
  th {{ background: #eee; text-align: center; }}
  td:first-child, th:first-child {{ text-align: left; }}
  .summary table {{ width: auto; }}
  .file-result {{ background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 16px; margin: 20px 0; }}
  .path {{ font-size: 0.85em; color: #666; word-break: break-all; margin: 0 0 10px; }}
  .badge {{ padding: 2px 8px; border-radius: 4px; font-size: 0.85em; font-weight: 600; }}
  .badge.ok {{ background: #d4edda; color: #155724; }}
  .badge.err {{ background: #f8d7da; color: #721c24; }}
  .columns {{ display: flex; gap: 16px; flex-wrap: wrap; }}
  .col {{ flex: 1 1 45%; min-width: 300px; }}
  .col img {{ width: 100%; height: auto; border: 1px solid #ddd; }}
  .chart {{ width: 100%; }}
  .metrics {{ width: 100%; }}
</style>
</head>
<body>
<h1>Extraction Evaluation Report</h1>
{summary_html}
<h2>Per-file Results ({len(results)} files)</h2>
{"".join(file_sections)}
</body>
</html>
"""

    output_path.write_text(page, encoding="utf-8")
    logger.info("HTML report written to %s", output_path)
    return output_path
