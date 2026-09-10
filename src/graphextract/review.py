# -*- coding: utf-8 -*-
"""Review workflow (plan-20260810, section 9): corrections, re-run, regression.

The reviewer corrects the smallest uncertain item. Corrections are stored as
JSON, re-applied deterministically, and failing panels export as regression
bundles. ``build_html_bundle`` produces a self-contained visual review page
(nearest-neighbour zoom, toggleable layers); ``review_server.py`` collects
posted corrections without extra dependencies.
"""

from __future__ import annotations

import base64
import html as html_mod
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np
import numpy.typing as npt

from graphextract.pipeline import AxisAnchors, run_panel
from graphextract.schema import PanelOutcome, PanelResult, TickAnchor

CORRECTION_TARGETS = ("tick", "scale_unit", "panel_boundary", "legend",
                      "junction", "interval", "unresolvable")


@dataclass
class Correction:
    target: str  # one of CORRECTION_TARGETS
    panel_id: str
    payload: dict = field(default_factory=dict)
    author: str = ""
    timestamp: float = 0.0
    rationale: str = ""

    def __post_init__(self) -> None:
        if self.target not in CORRECTION_TARGETS:
            raise ValueError(f"unknown correction target: {self.target!r}")

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> Correction:
        return Correction(**d)


def apply_corrections(anchors: AxisAnchors,
                      corrections: list[Correction]) -> tuple[AxisAnchors, list[str]]:
    """Fold reviewer corrections into anchors; source becomes user_verified.

    - tick: payload {axis, pixel, value} replaces/adds one anchor (source manual).
    - scale_unit: payload {axis, scale?, unit?} overrides AxisAnchors fields.
    - panel_boundary/legend/junction/interval/unresolvable: recorded as notes;
      junction/interval/unresolvable also force reviewer re-inspection downstream.
    """
    from graphextract.calibration import ScaleType

    notes: list[str] = []
    x = list(anchors.x)
    y = list(anchors.y_left)
    yr = list(anchors.y_right)
    x_scale, x_unit, y_unit, yru = anchors.x_scale, anchors.x_unit, anchors.y_unit, anchors.y_right_unit
    for c in corrections:
        p = c.payload
        if c.target == "tick":
            t = TickAnchor(float(p["pixel"]), float(p["value"]), 1.0, "manual")
            {"x": x, "y_left": y, "y_right": yr}[p.get("axis", "x")].append(t)
            notes.append(f"manual tick {p.get('axis', 'x')}={t.value}@{t.pixel}")
        elif c.target == "scale_unit":
            if p.get("axis", "x") == "x":
                if "scale" in p:
                    x_scale = ScaleType(p["scale"])
                if "unit" in p:
                    x_unit = str(p["unit"])
            else:
                if "unit" in p:
                    y_unit = str(p["unit"])
            notes.append(f"scale/unit override: {p}")
        else:
            notes.append(f"{c.target}: {p} ({c.rationale})")
    return (AxisAnchors(x=x, y_left=y, y_right=yr, x_scale=x_scale, x_unit=x_unit,
                        y_unit=y_unit, y_right_unit=yru, source="user_verified"), notes)


def rerun_with_corrections(img: npt.NDArray, panel_id: str, interior: npt.NDArray,
                           offset: tuple[int, int], base: AxisAnchors,
                           styles, corrections: list[Correction],
                           track_config=None) -> tuple[PanelResult, list[str]]:
    """Apply corrections and re-run one panel; provenance records the loop."""
    anchors, notes = apply_corrections(base, corrections)
    if not corrections:
        notes.append("no corrections supplied")
    res = run_panel(img, panel_id, interior, offset, anchors, styles, track_config)
    res.provenance["corrections"] = [c.to_dict() for c in corrections]
    res.provenance["correction_notes"] = notes
    return res, notes


def export_regression_case(out_dir: str | Path, image_id: str, panel_id: str,
                           interior: npt.NDArray, anchors: AxisAnchors,
                           style_specs, corrections: list[Correction],
                           notes: str = "") -> Path:
    """Write a self-contained regression bundle loadable by tests/CI."""
    d = Path(out_dir) / f"{image_id}_{panel_id.replace('#', '_')}"
    d.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(d / "interior.png"), interior)
    def anchor_dict(a: AxisAnchors) -> dict:
        return {"x": [asdict(t) for t in a.x], "y_left": [asdict(t) for t in a.y_left],
                "y_right": [asdict(t) for t in a.y_right],
                "x_scale": a.x_scale.value if a.x_scale else None,
                "x_unit": a.x_unit, "y_unit": a.y_unit,
                "y_right_unit": a.y_right_unit, "source": a.source}
    (d / "anchors.json").write_text(json.dumps(anchor_dict(anchors), indent=2) + "\n")
    (d / "styles.json").write_text(json.dumps(
        [{"series_id": s.series_id, "label": s.label, "bgr": list(s.bgr)} for s in style_specs],
        indent=2) + "\n")
    (d / "corrections.json").write_text(json.dumps(
        [c.to_dict() for c in corrections], indent=2) + "\n")
    (d / "README.txt").write_text(
        f"Regression case for {image_id} {panel_id}\nnotes: {notes}\n"
        "Reproduce: load interior.png + anchors.json + styles.json, run_panel, "
        "apply corrections.json, compare against the locked expectation in CI.\n")
    return d


def _img_uri(img: npt.NDArray) -> str:
    _, buf = cv2.imencode(".png", img)
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def build_html_bundle(doc, images: dict[str, npt.NDArray],
                      out_path: str | Path) -> Path:
    """Self-contained review page: pixelated zoom, layer toggles, correction forms."""
    out_path = Path(out_path)
    sections = []
    for p in doc.panels:
        pid = html_mod.escape(p.panel.panel_id)
        img = images.get(p.panel.panel_id)
        img_tag = f'<img src="{_img_uri(img)}" class="pix" alt="{pid}">' if img is not None else "<p>no image</p>"
        samples = {s.series_id: [[s.u, s.v, s.status.value] for s in s.samples]
                   for s in p.series for s in [s]}
        queue = "".join(f"<li>{html_mod.escape(r)}</li>" for r in p.review_reasons) or "<li>none</li>"
        template = json.dumps({"target": "tick", "panel_id": p.panel.panel_id,
                               "payload": {"axis": "x", "pixel": 0, "value": 0.0},
                               "author": "", "rationale": ""}, indent=2)
        sections.append(f"""
<section><h2>{pid} — {p.outcome.value}</h2>
<div class="row"><div>{img_tag}</div>
<div><canvas id="c_{pid}" width="560" height="360"></canvas><br>
<label><input type="checkbox" id="t_{pid}" checked> predictions</label></div></div>
<h3>Review queue</h3><ul>{queue}</ul>
<h3>Correction (JSON)</h3>
<textarea id="x_{pid}" rows="8" cols="70">{html_mod.escape(template)}</textarea><br>
<button onclick="dlCorr('{pid}')">Download correction</button>
<button onclick="postCorr('{pid}')">Post to local server</button>
<script>
const S_{pid} = {json.dumps(samples)};
(function() {{
  const cv = document.getElementById('c_{pid}');
  const ctx = cv.getContext('2d');
  function draw() {{
    ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, cv.width, cv.height);
    if (!document.getElementById('t_{pid}').checked) return;
    for (const [sid, pts] of Object.entries(S_{pid})) {{
      ctx.fillStyle = sid.endsWith('0') ? '#c00' : '#00c';
      for (const [u, v, st] of pts) {{
        if (st !== 'observed') continue;
        ctx.fillRect((u % cv.width), (v % cv.height), 2, 2);
      }}
    }}
  }}
  document.getElementById('t_{pid}').onchange = draw; draw();
}})();
</script></section>""")
    page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Review bundle {html_mod.escape(doc.image_id)}</title>
<style>.pix {{ image-rendering: pixelated; max-width: 560px; border: 1px solid #888; }}
canvas {{ border: 1px solid #888; }} section {{ border-top: 2px solid #333; margin-top: 1em; }}</style>
</head><body><h1>Review: {html_mod.escape(doc.image_id)}</h1>
{''.join(sections)}
<script>
function corrText(pid) {{ return document.getElementById('x_' + pid).value; }}
function dlCorr(pid) {{
  const b = new Blob([corrText(pid)], {{type: 'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(b); a.download = pid.replace('#', '_') + '.correction.json'; a.click();
}}
function postCorr(pid) {{
  fetch('/corrections', {{method: 'POST', body: corrText(pid)}}).then(r => alert(r.status));
}}
</script></body></html>"""
    out_path.write_text(page, encoding="utf-8")
    return out_path
