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

import os
import pathlib
import copy
import math
from typing import Callable

import plotly.io

from spinorama import logger, setup_logger
from spinorama.constant_paths import CPATH_DIST_SPEAKERS, DEFAULT_FREQ_RANGE
from spinorama.measurements import Measurements
from spinorama.misc import measurements_valid_freq_range, sanitize_filename, write_multiformat
from spinorama.filter_peq import Peq, peq_preamp_gain
from spinorama.compute_misc import compute_minmax_slopes
from spinorama.plot import (
    plot_params_default,
    contour_params_default,
    radar_params_default,
    plot_spinorama,
    plot_graph,
    plot_graph_spl,
    plot_graph_regression,
    plot_graph_onaxis,
    plot_graph_group_delay,
    plot_contour,
    plot_radar,
    plot_contour_3d,
    FONT_H1,
)


SPACING = 20
LEGEND = 60


def scale_params(params, factor):
    new_params = copy.deepcopy(params)
    width = params["width"]
    height = params["height"]
    if factor == 3:
        new_width = math.floor(width - 6 * SPACING) / 3
        new_height = math.floor(height - 6 * SPACING) / 3
        new_params["height"] = new_height
    else:
        new_width = math.floor(width - 3 * SPACING) / 2
    new_params["width"] = new_width
    for check in ("xmin", "xmax"):
        if check not in new_params:
            logger.error("scale_param %s is not a key", check)
    if new_params["xmin"] == new_params["xmax"]:
        logger.error("scale_param x-range is empty")
    if "ymin" in new_params and "ymax" in new_params and new_params["ymin"] == new_params["ymax"]:
        logger.error("scale_param y-range is empty")
    return new_params


def _spin_for(m: Measurements, is_normalized: bool):
    """Return the wide CEA2034 frame for ``is_normalized``, or ``None``."""
    spin = m.cea2034_normalized if is_normalized else m.cea2034
    if spin is None or spin.Freq.shape[0] == 0:
        return None
    return spin


def _slopes_for(m: Measurements, is_normalized: bool):
    """Return (spin, slopes) for the requested normalisation, ``(None, None)`` if missing."""
    spin = _spin_for(m, is_normalized)
    if spin is None:
        return None, None
    slopes = compute_minmax_slopes(spin=spin.copy(), is_normalized=is_normalized)
    return spin, slopes


# ----------------------------------------------------------------------
# Spinorama (CEA2034) line plots — "as measured" and "normalized"
# ----------------------------------------------------------------------
def _display_spinorama_common(
    m: Measurements, graph_params, is_normalized, valid_freq_range: tuple[float, float]
):
    spin, slopes = _slopes_for(m, is_normalized=is_normalized)
    if spin is None:
        logger.debug("plot_spinorama: no CEA2034 (is_normalized=%s)", is_normalized)
        return None

    fig = plot_spinorama(
        spin, graph_params, slopes, is_normalized=is_normalized, valid_freq_range=valid_freq_range
    )
    if fig is None:
        logger.info("plot_spinorama failed")
    return fig


def display_spinorama(
    m: Measurements,
    graph_params=plot_params_default,
    valid_freq_range: tuple[float, float] = DEFAULT_FREQ_RANGE,
):
    return _display_spinorama_common(m, graph_params, False, valid_freq_range)


def display_spinorama_normalized(
    m: Measurements,
    graph_params=plot_params_default,
    valid_freq_range: tuple[float, float] = DEFAULT_FREQ_RANGE,
):
    return _display_spinorama_common(m, graph_params, True, valid_freq_range)


def _display_inroom_common(
    m: Measurements,
    graph_params: dict,
    is_normalized: bool,
    valid_freq_range: tuple[float, float],
):
    spin, slopes = _slopes_for(m, is_normalized=is_normalized)
    if spin is None:
        logger.debug("plot_inroom: no CEA2034 (is_normalized=%s)", is_normalized)
        return None

    eir = m.eir_normalized if is_normalized else m.eir
    if eir is None:
        logger.debug("plot_inroom: no EIR (partial measurements)")
        return None

    return plot_graph_regression(
        eir,
        "Estimated In-Room Response",
        spin,
        graph_params,
        slopes,
        is_normalized,
        valid_freq_range,
    )


def display_inroom(m: Measurements, graph_params=plot_params_default, valid_freq_range=DEFAULT_FREQ_RANGE):
    return _display_inroom_common(m, graph_params, False, valid_freq_range)


def display_inroom_normalized(
    m: Measurements, graph_params=plot_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    return _display_inroom_common(m, graph_params, True, valid_freq_range)


# ----------------------------------------------------------------------
# Per-curve plots
# ----------------------------------------------------------------------
def display_onaxis(
    m: Measurements, graph_params=plot_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    # Prefer the dedicated on-axis frame; fall back to the on-axis column of
    # the CEA2034 spin (partial measurements path).
    onaxis = m.on_axis if m.on_axis is not None else m.cea2034
    if onaxis is None or "On Axis" not in onaxis:
        logger.debug("display_onaxis: no on-axis curve available")
        return None
    return plot_graph_onaxis(onaxis, m.h_spl, graph_params, valid_freq_range)


def display_group_delay(
    m: Measurements, graph_params=plot_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    if m.h_spl is None or "Phase On Axis" not in m.h_spl:
        logger.debug("display_group_delay: no horizontal-SPL phase available")
        return None
    return plot_graph_group_delay(m.h_spl, graph_params, valid_freq_range)


def display_reflection_early(
    m: Measurements, graph_params=plot_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    if m.early_reflections is None:
        return None
    return plot_graph(m.early_reflections, graph_params, valid_freq_range)


def display_reflection_horizontal(
    m: Measurements, graph_params=plot_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    if m.horizontal_reflections is None:
        return None
    return plot_graph(m.horizontal_reflections, graph_params, valid_freq_range)


def display_reflection_vertical(
    m: Measurements, graph_params=plot_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    if m.vertical_reflections is None:
        return None
    return plot_graph(m.vertical_reflections, graph_params, valid_freq_range)


# (axis, normalized) → field-name lookup. Drives the four SPL line plots and
# the four contour/contour-3D variants below.
_SPL_FIELD = {
    ("horizontal", False): "h_spl",
    ("horizontal", True): "h_spl_normalized",
    ("vertical", False): "v_spl",
    ("vertical", True): "v_spl_normalized",
}


def _spl_frame(m: Measurements, axis: str, normalized: bool):
    return getattr(m, _SPL_FIELD[(axis, normalized)])


def display_spl(
    m: Measurements,
    axis: str,
    graph_params=plot_params_default,
    valid_freq_range=DEFAULT_FREQ_RANGE,
    include_all_angles: bool = False,
    normalized: bool = False,
):
    frame = _spl_frame(m, axis, normalized)
    if frame is None:
        return None
    return plot_graph_spl(frame, graph_params, valid_freq_range, include_all_angles)


def display_spl_horizontal(
    m: Measurements,
    graph_params=plot_params_default,
    valid_freq_range=DEFAULT_FREQ_RANGE,
    include_all_angles: bool = False,
):
    return display_spl(m, "horizontal", graph_params, valid_freq_range, include_all_angles)


def display_spl_vertical(
    m: Measurements,
    graph_params=plot_params_default,
    valid_freq_range=DEFAULT_FREQ_RANGE,
    include_all_angles: bool = False,
):
    return display_spl(m, "vertical", graph_params, valid_freq_range, include_all_angles)


def display_spl_horizontal_normalized(
    m: Measurements,
    graph_params=plot_params_default,
    valid_freq_range=DEFAULT_FREQ_RANGE,
    include_all_angles: bool = False,
):
    return display_spl(
        m, "horizontal", graph_params, valid_freq_range, include_all_angles, normalized=True
    )


def display_spl_vertical_normalized(
    m: Measurements,
    graph_params=plot_params_default,
    valid_freq_range=DEFAULT_FREQ_RANGE,
    include_all_angles: bool = False,
):
    return display_spl(
        m, "vertical", graph_params, valid_freq_range, include_all_angles, normalized=True
    )


def display_contour(
    m: Measurements,
    axis: str,
    graph_params=contour_params_default,
    valid_freq_range=DEFAULT_FREQ_RANGE,
    normalized: bool = False,
):
    frame = _spl_frame(m, axis, normalized)
    if frame is None:
        return None
    return plot_contour(frame, graph_params, valid_freq_range)


def display_contour_horizontal(
    m: Measurements, graph_params=contour_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    return display_contour(m, "horizontal", graph_params, valid_freq_range)


def display_contour_vertical(
    m: Measurements, graph_params=contour_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    return display_contour(m, "vertical", graph_params, valid_freq_range)


def display_contour_horizontal_normalized(
    m: Measurements, graph_params=contour_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    return display_contour(m, "horizontal", graph_params, valid_freq_range, normalized=True)


def display_contour_vertical_normalized(
    m: Measurements, graph_params=contour_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    return display_contour(m, "vertical", graph_params, valid_freq_range, normalized=True)


def display_contour_3d(
    m: Measurements,
    axis: str,
    graph_params=contour_params_default,
    valid_freq_range=DEFAULT_FREQ_RANGE,
    normalized: bool = False,
):
    frame = _spl_frame(m, axis, normalized)
    if frame is None:
        return None
    return plot_contour_3d(frame, graph_params, valid_freq_range)


def display_contour_horizontal_3d(
    m: Measurements, graph_params=contour_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    return display_contour_3d(m, "horizontal", graph_params, valid_freq_range)


def display_contour_vertical_3d(
    m: Measurements, graph_params=contour_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    return display_contour_3d(m, "vertical", graph_params, valid_freq_range)


def display_contour_horizontal_normalized_3d(
    m: Measurements, graph_params=contour_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    return display_contour_3d(m, "horizontal", graph_params, valid_freq_range, normalized=True)


def display_contour_vertical_normalized_3d(
    m: Measurements, graph_params=contour_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    return display_contour_3d(m, "vertical", graph_params, valid_freq_range, normalized=True)


def display_radar(
    m: Measurements,
    axis: str,
    graph_params,
    valid_freq_range=DEFAULT_FREQ_RANGE,
):
    frame = _spl_frame(m, axis, False)
    if frame is None:
        return None
    return plot_radar(frame, graph_params, valid_freq_range)


def display_radar_horizontal(
    m: Measurements, graph_params=radar_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    return display_radar(m, "horizontal", graph_params, valid_freq_range)


def display_radar_vertical(
    m: Measurements, graph_params=radar_params_default, valid_freq_range=DEFAULT_FREQ_RANGE
):
    return display_radar(m, "vertical", graph_params, valid_freq_range)


def build_filename(speaker, origin, version, graph_name, file_ext) -> str:
    filedir = (
        CPATH_DIST_SPEAKERS + "/" + sanitize_filename(speaker) + "/" + origin.replace("Vendors-", "") + "/" + version
    )
    pathlib.Path(filedir).mkdir(parents=True, exist_ok=True)
    filename = filedir + "/" + graph_name.replace("_smoothed", "")
    if file_ext == "png":
        filename += "_large"
    filename += "." + file_ext
    return filename


def build_title(origin: str, version: str, speaker: str, title: str, iir: Peq) -> str:
    whom = origin
    if origin[0:8] == "Vendors-":
        whom = origin.replace("Vendors-", "")
    elif origin == "Misc":
        if version[-3:] == "-sr":
            whom = "Sound & Recording (data scanned)"
        elif version[-3:] == "-pp":
            whom = "Production Partners (data scanned)"
        else:
            dash_pos = version.find("-")
            if dash_pos != -1 and dash_pos < len(version) - 1:
                whom = version[dash_pos + 1 :].capitalize()
    elif origin == "ASR":
        whom = "Audio Science Review"
    preamp = peq_preamp_gain(iir) if len(iir) > 0 else 0.0
    gain = ""
    if preamp != 0.0:
        gain = " (eq gain {:+1.1f}dB)".format(preamp)
    return "{2} for {0} measured by {1}{3}".format(speaker, whom, title, gain)


def print_a_graph(filename, chart, ext, force) -> int:
    updated = 0

    check = (
        force
        or not os.path.exists(filename)
        or (os.path.exists(filename) and os.path.getsize(filename) == 0)
    )
    if not check:
        return updated

    try:
        if ext == "json":
            content = chart.to_json()
            with open(filename, "w", encoding="utf-8") as f_d:
                f_d.write(content)
        updated += 1
    except Exception:
        logger.exception("Got unkown error for %s", filename)

    return updated


# Formats that produce per-axis (H/V) SPL sweeps. Drives the extra view rows
# in ``build_figures`` (reflections, SPL, contour, radar).
_HV_MFORMATS = frozenset({"klippel", "spl_hv_txt", "gll_hv_txt", "princeton"})

# Always-on views: (graph name, display function). Each display function takes
# ``(df_speaker, graph_params, valid_freq_range)``.
_COMMON_VIEWS: tuple[tuple[str, Callable], ...] = (
    ("CEA2034", display_spinorama),
    ("CEA2034 Normalized", display_spinorama_normalized),
    ("On Axis", display_onaxis),
    ("Estimated In-Room Response", display_inroom),
    ("Estimated In-Room Response Normalized", display_inroom_normalized),
)

_REFLECTION_VIEWS: tuple[tuple[str, Callable], ...] = (
    ("Early Reflections", display_reflection_early),
    ("Horizontal Reflections", display_reflection_horizontal),
    ("Vertical Reflections", display_reflection_vertical),
)

_SPL_VIEWS: tuple[tuple[str, Callable], ...] = (
    ("SPL Horizontal", display_spl_horizontal),
    ("SPL Vertical", display_spl_vertical),
    ("SPL Horizontal Normalized", display_spl_horizontal_normalized),
    ("SPL Vertical Normalized", display_spl_vertical_normalized),
)

_CONTOUR_VIEWS: tuple[tuple[str, Callable], ...] = (
    ("SPL Horizontal Contour", display_contour_horizontal),
    ("SPL Vertical Contour", display_contour_vertical),
    ("SPL Horizontal Contour Normalized", display_contour_horizontal_normalized),
    ("SPL Vertical Contour Normalized", display_contour_vertical_normalized),
    ("SPL Horizontal Contour 3D", display_contour_horizontal_3d),
    ("SPL Vertical Contour 3D", display_contour_vertical_3d),
    ("SPL Horizontal Contour Normalized 3D", display_contour_horizontal_normalized_3d),
    ("SPL Vertical Contour Normalized 3D", display_contour_vertical_normalized_3d),
)

_RADAR_VIEWS: tuple[tuple[str, Callable], ...] = (
    ("SPL Horizontal Radar", display_radar_horizontal),
    ("SPL Vertical Radar", display_radar_vertical),
)


def _safe_display(
    op_title: str,
    op_call,
    m: Measurements,
    *args,
    speaker: str = "",
    version: str = "",
    origin: str = "",
    **kwargs,
):
    """Invoke a ``display_*`` function and convert ``KeyError`` into a logged ``None``."""
    try:
        graph = op_call(m, *args, **kwargs)
    except KeyError as ke:
        logger.error(
            "display %s failed with a key error (%s) for %s %s %s",
            op_title,
            ke,
            speaker,
            version,
            origin,
        )
        return None
    if graph is None:
        logger.info("display %s failed for %s %s %s", op_title, speaker, version, origin)
    return graph


def _make_graph_params(width: int, height: int, origins_info: dict, origin: str) -> dict:
    params = copy.deepcopy(plot_params_default)
    params["width"] = width
    params["height"] = height
    params["layout"] = "compact"
    params["xmin"] = origins_info[origin]["min hz"]
    params["xmax"] = origins_info[origin]["max hz"]
    params["ymin"] = origins_info[origin]["min dB"]
    params["ymax"] = origins_info[origin]["max dB"]
    return params


def _make_contour_params(width: int, height: int, origins_info: dict, origin: str) -> dict:
    params = copy.deepcopy(contour_params_default)
    params["width"] = width
    params["height"] = height
    params["layout"] = "compact"
    params["xmin"] = origins_info[origin]["min hz"]
    params["xmax"] = origins_info[origin]["max hz"]
    return params


def _make_radar_params(width: int, height: int, origins_info: dict, origin: str) -> dict:
    params = copy.deepcopy(radar_params_default)
    params["width"] = int(height * 4 / 5)
    params["height"] = height
    params["layout"] = "compact"
    params["xmin"] = origins_info[origin]["min hz"]
    params["xmax"] = origins_info[origin]["max hz"]
    return params


def build_figures(
    m: Measurements,
    speaker: str,
    parameters: dict,
    origins_info: dict,
    iir: Peq,
) -> dict:
    """Build every figure for one speaker. Pure: no filesystem access.

    Returns a ``{graph_name: plotly.Figure}`` dict. Entries are dropped (not
    set to ``None``) when the corresponding display call fails, except for
    contour/radar which match the legacy behaviour of always returning a
    figure or ``None``.
    """
    mformat = parameters["mformat"]
    version = parameters["mversion"]
    origin = parameters["morigin"]
    width = parameters["width"]
    height = parameters["height"]

    if width // height != 4 // 3:
        logger.error("ratio width / height must be 4/3")
        height = int(width * 3 / 4)

    graph_params = _make_graph_params(width, height, origins_info, origin)
    valid_freq_range = measurements_valid_freq_range(
        speaker,
        version,
        m.h_spl,
        m.v_spl,
    )

    ctx = dict(speaker=speaker, version=version, origin=origin)
    graphs: dict = {}

    for op_title, op_call in _COMMON_VIEWS:
        graph = _safe_display(op_title, op_call, m, graph_params, valid_freq_range, **ctx)
        if graph is not None:
            graphs[op_title] = graph

    graph = _safe_display(
        "Group Delay", display_group_delay, m, graph_params, valid_freq_range, **ctx
    )
    if graph is not None:
        graphs["Group Delay"] = graph

    if mformat in _HV_MFORMATS:
        for op_title, op_call in _REFLECTION_VIEWS:
            graph = _safe_display(op_title, op_call, m, graph_params, valid_freq_range, **ctx)
            if graph is not None:
                graphs[op_title] = graph

        for op_title, op_call in _SPL_VIEWS:
            graph = _safe_display(
                op_title,
                op_call,
                m,
                graph_params,
                valid_freq_range,
                include_all_angles=True,
                **ctx,
            )
            if graph is not None:
                graphs[op_title] = graph

        contour_params = _make_contour_params(width, height, origins_info, origin)
        for op_title, op_call in _CONTOUR_VIEWS:
            graphs[op_title] = op_call(m, contour_params, valid_freq_range)

        radar_params = _make_radar_params(width, height, origins_info, origin)
        for op_title, op_call in _RADAR_VIEWS:
            graphs[op_title] = op_call(m, radar_params, valid_freq_range)

    for key, graph in graphs.items():
        if graph is None:
            continue
        title = key.replace("_smoothed", "")
        graph.update_layout(
            title=dict(
                text=build_title(origin, version, speaker, title, iir),
                font=FONT_H1,
            ),
        )

    return graphs


def emit_figures(
    graphs: dict,
    speaker: str,
    origin: str,
    version_key: str,
    force_print: bool,
) -> int:
    """Write each non-empty figure to its JSON sidecar. IO only.

    Returns the number of JSON files actually written.
    """
    updated = 0
    for key, graph in graphs.items():
        if graph is None:
            continue

        filename_json = build_filename(speaker, origin, version_key, key, "json")
        if not (
            force_print
            or not os.path.exists(filename_json)
            or os.path.getsize(filename_json) == 0
        ):
            continue

        try:
            content = graph.to_json()
            with open(filename_json, "w", encoding="utf-8") as f_d:
                f_d.write(content)
                updated += 1
        except Exception:
            logger.exception("Got unkown error for %s: %s", speaker, filename_json)

    return updated


def print_graphs(
    data: Measurements | tuple[Peq, Measurements],
    speaker: str,
    parameters: dict,
    origins_info: dict,
    force_print: bool,
    log_level: int,
) -> int:
    """Build and emit every figure for one speaker."""
    setup_logger(level=log_level)
    version = parameters["mversion"]
    origin = parameters["morigin"]
    version_key = parameters.get("mversion_key", version)

    if isinstance(data, tuple):
        iir, m = data
    else:
        iir, m = [], data

    if m is None or m.is_empty():
        logger.info("measurements empty for %s %s %s", speaker, version, origin)
        return 0

    graphs = build_figures(m, speaker, parameters, origins_info, iir)
    return emit_figures(graphs, speaker, origin, version_key, force_print)
