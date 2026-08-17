#!/usr/bin/env python3
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

"""CLI: Extract curves from PNG images and generate an HTML report.

Usage:
    python scripts/report_extraction.py \\
        --input-dir src/graphextract/datas \\
        --output report_extraction.html
"""

import argparse
import base64
import html as html_mod
import json
import logging
import sys
from pathlib import Path

import cv2
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from spinorama import logger, setup_logger
from spinorama.extract_distortion import ExtractionResult, extract_curves
from spinorama.extract_plot_detect import detect_plot_regions
from spinorama.extract_axis_calibrate import calibrate_axes
from spinorama.extract_color_segment import DEFAULT_CURVE_SPECS, segment_curves
from spinorama.extract_curve_trace import trace_single_curve


# Klippel curve colors for the chart
CURVE_COLORS: dict[str, str] = {
    "Fundamental": "#22a652",
    "THD": "#d62728",
    "2nd Harmonic": "#8c564b",
    "3rd Harmonic": "#1f77b4",
    "4th Harmonic": "#7f7f7f",
    "5th Harmonic": "#bcbd22",
}


def _img_to_data_uri(img: np.ndarray) -> str:
    _, buf = cv2.imencode(".png", img)
    b64 = base64.b64encode(buf.tobytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _process_image(image_path: Path) -> dict:
    """Process a single PNG image and return extraction results."""
    img = cv2.imread(str(image_path))
    if img is None:
        return {"file": image_path.name, "status": "error", "error": f"Cannot read {image_path}"}

    regions = detect_plot_regions(img)
    if not regions:
        return {"file": image_path.name, "status": "error", "error": "No plot regions detected"}

    all_curves: dict[str, list[tuple[float, float]]] = {}
    region_infos: list[dict] = []

    for region in regions:
        plot_img = img[region.y : region.y + region.h, region.x : region.x + region.w]
        calibration = calibrate_axes(plot_img, region)

        masks = segment_curves(plot_img, DEFAULT_CURVE_SPECS)

        region_curves: dict[str, list[tuple[float, float]]] = {}
        for curve_name, mask in masks.items():
            pts = trace_single_curve(mask, calibration)
            if pts:
                region_curves[curve_name] = pts
                # prefix with region title if available
                key = f"{region.title} - {curve_name}" if region.title else curve_name
                all_curves[key] = pts

        region_infos.append(
            {
                "title": region.title,
                "x": region.x,
                "y": region.y,
                "w": region.w,
                "h": region.h,
                "calibration": {
                    "freq_min": round(calibration.freq_min, 1),
                    "freq_max": round(calibration.freq_max, 1),
                    "db_min": round(calibration.db_min, 1),
                    "db_max": round(calibration.db_max, 1),
                },
                "curves": {
                    name: {
                        "n_points": len(pts),
                        "freq_range": [
                            round(min(p[0] for p in pts), 1),
                            round(max(p[0] for p in pts), 1),
                        ],
                        "db_range": [
                            round(min(p[1] for p in pts), 1),
                            round(max(p[1] for p in pts), 1),
                        ],
                        "mean_db": round(sum(p[1] for p in pts) / len(pts), 1),
                    }
                    for name, pts in region_curves.items()
                },
            }
        )

    return {
        "file": image_path.name,
        "status": "success",
        "img": img,
        "n_regions": len(regions),
        "regions": region_infos,
        "curves": all_curves,
    }


def _downsample(
    pts: list[tuple[float, float]], max_points: int = 400
) -> tuple[list[float], list[float]]:
    if len(pts) <= max_points:
        return [p[0] for p in pts], [p[1] for p in pts]
    step = len(pts) / max_points
    indices = [int(i * step) for i in range(max_points)]
    return [pts[i][0] for i in indices], [pts[i][1] for i in indices]


def _build_traces_json(curves: dict[str, list[tuple[float, float]]]) -> str:
    traces: list[dict] = []
    for name, pts in curves.items():
        xs, ys = _downsample(pts)
        # strip region prefix to find color
        base_name = name.split(" - ")[-1] if " - " in name else name
        color = CURVE_COLORS.get(base_name, "#888888")
        traces.append(
            {
                "x": xs,
                "y": ys,
                "mode": "lines",
                "name": name,
                "line": {"color": color, "width": 2},
            }
        )
    return json.dumps(traces)


def generate_report(results: list[dict], output_path: Path) -> None:
    """Generate a self-contained HTML report styled like spinorama.org."""

    # Summary stats
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    total_curves = sum(len(r.get("curves", {})) for r in results)

    # Per-file sections
    file_sections: list[str] = []
    for idx, r in enumerate(results):
        escaped_file = html_mod.escape(r["file"])

        if r["status"] != "success":
            file_sections.append(f"""
<div class="box mb-5">
  <div class="level">
    <div class="level-left"><h3 class="title is-5 mb-0">{escaped_file}</h3></div>
    <div class="level-right"><span class="tag is-danger is-medium">Error</span></div>
  </div>
  <p class="has-text-danger">{html_mod.escape(r.get("error", "Unknown error"))}</p>
</div>""")
            continue

        # Original image
        img_uri = _img_to_data_uri(r["img"])

        # Metrics table rows
        metrics_rows = ""
        for reg_info in r["regions"]:
            reg_title = reg_info["title"] or "Plot"
            cal = reg_info["calibration"]
            for cname, cinfo in reg_info["curves"].items():
                metrics_rows += (
                    f"<tr>"
                    f"<td>{html_mod.escape(cname)}</td>"
                    f"<td class='has-text-right'>{cinfo['n_points']}</td>"
                    f"<td class='has-text-right'>{cinfo['freq_range'][0]:.0f} - {cinfo['freq_range'][1]:.0f}</td>"
                    f"<td class='has-text-right'>{cinfo['db_range'][0]:.1f} - {cinfo['db_range'][1]:.1f}</td>"
                    f"<td class='has-text-right'>{cinfo['mean_db']:.1f}</td>"
                    f"</tr>\n"
                )

        # Calibration info
        cal_rows = ""
        for i, reg_info in enumerate(r["regions"]):
            cal = reg_info["calibration"]
            reg_title = reg_info["title"] or f"Region {i + 1}"
            cal_rows += (
                f"<tr>"
                f"<td>{html_mod.escape(reg_title)}</td>"
                f"<td class='has-text-right'>{reg_info['w']}x{reg_info['h']}</td>"
                f"<td class='has-text-right'>{cal['freq_min']:.0f} - {cal['freq_max']:.0f} Hz</td>"
                f"<td class='has-text-right'>{cal['db_min']:.1f} - {cal['db_max']:.1f} dB</td>"
                f"</tr>\n"
            )

        # Plotly chart
        chart_div = ""
        if r["curves"]:
            traces_json = _build_traces_json(r["curves"])
            div_id = f"chart_{idx}"
            chart_div = f"""
<div id="{div_id}" style="width:100%;"></div>
<script>
Plotly.newPlot("{div_id}", {traces_json}, {{
  xaxis: {{type: "log", title: "Frequency (Hz)",
           range: [Math.log10(20), Math.log10(20000)],
           gridcolor: "#e0e0e0", gridwidth: 1}},
  yaxis: {{title: "SPL (dB)", gridcolor: "#e0e0e0", gridwidth: 1}},
  legend: {{orientation: "h", y: -0.12, x: 0.5, xanchor: "center"}},
  margin: {{t: 30, b: 70, l: 60, r: 30}},
  height: 450,
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "#fafafa",
  font: {{family: "system-ui, -apple-system, sans-serif"}},
}}, {{responsive: true}});
</script>"""

        n_curves = len(r["curves"])
        file_sections.append(f"""
<div class="box mb-5">
  <div class="level mb-3">
    <div class="level-left">
      <h3 class="title is-5 mb-0">{escaped_file}</h3>
    </div>
    <div class="level-right">
      <span class="tag is-success is-medium mr-2">{r["n_regions"]} region(s)</span>
      <span class="tag is-info is-medium">{n_curves} curve(s)</span>
    </div>
  </div>

  <div class="columns">
    <div class="column is-half">
      <figure class="image">
        <img src="{img_uri}" alt="{escaped_file}" style="border:1px solid #ddd; border-radius:4px;">
      </figure>
    </div>
    <div class="column is-half">
      {chart_div}
    </div>
  </div>

  <div class="columns">
    <div class="column is-8">
      <h4 class="title is-6">Extracted Curves</h4>
      <table class="table is-striped is-hoverable is-fullwidth is-narrow">
        <thead>
          <tr>
            <th>Curve</th>
            <th class="has-text-right">Points</th>
            <th class="has-text-right">Freq Range (Hz)</th>
            <th class="has-text-right">dB Range</th>
            <th class="has-text-right">Mean dB</th>
          </tr>
        </thead>
        <tbody>{metrics_rows}</tbody>
      </table>
    </div>
    <div class="column is-4">
      <h4 class="title is-6">Calibration</h4>
      <table class="table is-striped is-hoverable is-fullwidth is-narrow">
        <thead>
          <tr><th>Region</th><th class="has-text-right">Size</th><th class="has-text-right">Freq</th><th class="has-text-right">dB</th></tr>
        </thead>
        <tbody>{cal_rows}</tbody>
      </table>
    </div>
  </div>
</div>""")

    page = f"""<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Curve Extraction Report</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@1.0.4/css/bulma.min.css">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  body {{ background: #f5f5f5; }}
  .hero {{ background: linear-gradient(135deg, #363636 0%, #1a1a2e 100%); }}
  .hero .title {{ color: #fff; }}
  .hero .subtitle {{ color: #ccc; }}
  .summary-card {{ text-align: center; }}
  .summary-card .title {{ margin-bottom: 0.25rem; }}
  .summary-card .subtitle {{ margin-bottom: 0; }}
</style>
</head>
<body>

<section class="hero is-dark is-small">
  <div class="hero-body">
    <div class="container">
      <h1 class="title">Curve Extraction Report</h1>
      <p class="subtitle">Distortion curve extraction from measurement images</p>
    </div>
  </div>
</section>

<section class="section">
<div class="container">

  <div class="columns mb-5">
    <div class="column is-4">
      <div class="box summary-card">
        <p class="title is-3">{total}</p>
        <p class="subtitle is-6 has-text-grey">Images Processed</p>
      </div>
    </div>
    <div class="column is-4">
      <div class="box summary-card">
        <p class="title is-3 has-text-success">{success}/{total}</p>
        <p class="subtitle is-6 has-text-grey">Successful</p>
      </div>
    </div>
    <div class="column is-4">
      <div class="box summary-card">
        <p class="title is-3 has-text-info">{total_curves}</p>
        <p class="subtitle is-6 has-text-grey">Total Curves Extracted</p>
      </div>
    </div>
  </div>

  {"".join(file_sections)}

</div>
</section>

<footer class="footer">
  <div class="content has-text-centered">
    <p>Generated by <strong>spinorama</strong> extraction pipeline</p>
  </div>
</footer>

</body>
</html>
"""
    output_path.write_text(page, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract curves from PNGs and generate HTML report"
    )
    parser.add_argument("--input-dir", type=Path, required=True, help="Directory with PNG images")
    parser.add_argument(
        "--output", type=Path, default=Path("report_extraction.html"), help="Output HTML file"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.WARNING
    setup_logger(level)

    pngs = sorted(args.input_dir.glob("*.png"))
    if not pngs:
        print(f"No PNG files found in {args.input_dir}", file=sys.stderr)
        return 1

    print(f"Processing {len(pngs)} images from {args.input_dir}")

    results: list[dict] = []
    for i, png in enumerate(pngs):
        print(f"  [{i + 1}/{len(pngs)}] {png.name}")
        result = _process_image(png)
        results.append(result)
        if result["status"] == "success":
            n = len(result["curves"])
            print(f"         {result['n_regions']} region(s), {n} curve(s)")
        else:
            print(f"         ERROR: {result.get('error', '?')}")

    generate_report(results, args.output)
    print(f"\nReport written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
