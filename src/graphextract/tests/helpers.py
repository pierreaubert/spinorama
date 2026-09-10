# -*- coding: utf-8 -*-
"""Shared synthetic builders for the canonical-pipeline tests."""

import math

import cv2
import numpy as np
import numpy.typing as npt

from graphextract.calibration import ScaleType
from graphextract.evidence import StyleSpec
from graphextract.render import RenderPanel, RenderSeries, render_panel
from graphextract.schema import AxisRole, TickAnchor


def log_sine_panel(
    width: int = 640,
    height: int = 480,
    crossing: bool = False,
) -> tuple[npt.NDArray, RenderPanel, object]:
    """Render one log-x panel with two coloured curves; return (img, panel, truth)."""
    xs = np.geomspace(20, 20000, 120).tolist()
    y_a = [60.0 + 8.0 * math.sin(math.log10(f) * 4.0) for f in xs]
    if crossing:
        y_b = [60.0 - 8.0 * math.sin(math.log10(f) * 4.0) for f in xs]
    else:
        y_b = [40.0 + 4.0 * math.sin(math.log10(f) * 4.0) for f in xs]
    panel = RenderPanel(
        rect_xywh=(70, 30, width - 100, height - 80),
        series=[
            RenderSeries("a", (0, 0, 255), xs, y_a, width_px=1),
            RenderSeries("b", (255, 0, 0), xs, y_b, width_px=2),
        ],
    )
    # Supersampled + area-downscaled rendering keeps rasterization
    # quantization an order of magnitude below the 1px contract, so the test
    # measures the pipeline rather than vertex rounding.
    truth = render_panel((width, height), panel, supersample=3)
    return truth.image, panel, truth


def styles_ab() -> list[StyleSpec]:
    return [
        StyleSpec("a", "A", (0, 0, 255), (40, 40, 40)),
        StyleSpec("b", "B", (255, 0, 0), (40, 40, 40)),
    ]


def renderer_anchors(panel: RenderPanel, truth: object, offset: tuple[int, int],
                     source: str) -> object:
    """Exact anchors in interior-crop coordinates, labelled with their source."""
    from graphextract.pipeline import AxisAnchors

    ox, oy = offset
    x_anchors = [TickAnchor(truth.x_fit.transform(f) - ox, f, 1.0, source)
                 for f in (20, 100, 1000, 10000, 20000)]
    y_anchors = [TickAnchor(truth.y_fit.transform(v) - oy, v, 1.0, source)
                 for v in (20, 40, 60, 80, 100)]
    return AxisAnchors(x=x_anchors, y_left=y_anchors, x_scale=ScaleType.LOG10,
                       x_unit="Hz", y_unit="dB", source=source)


def dense_reference(truth: object, series_id: str,
                    u_lo: float | None = None, u_hi: float | None = None,
                    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Dense (u, v, visible) reference in full-image native coordinates.

    The scoring domain is the evaluated support (e.g. panel interior columns);
    reference columns outside [u_lo, u_hi] are excluded rather than counted as
    missed coverage.
    """
    poly = truth.native_polylines[series_id]
    pu = np.array([p[0] for p in poly])
    pv = np.array([p[1] for p in poly])
    lo = int(math.floor(pu.min()))
    hi = int(math.ceil(pu.max()))
    if u_lo is not None:
        lo = max(lo, int(math.ceil(u_lo)))
    if u_hi is not None:
        hi = min(hi, int(math.floor(u_hi)))
    uu = np.arange(lo, hi + 1, dtype=float)
    vv = np.interp(uu, pu, pv)
    vis = np.zeros_like(uu, dtype=bool)
    mask = truth.visible_masks[series_id]
    for i, u in enumerate(uu):
        xi = int(round(u))
        if 0 <= xi < mask.shape[1]:
            vis[i] = bool((mask[:, xi] > 0).any())
    return uu, vv, vis


def gray_of(img: npt.NDArray) -> npt.NDArray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
