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

try:
    import ray
except ModuleNotFoundError:
    import src.miniray as ray

from wand.image import Image as Wim
from wand.exceptions import CoderError

from spinorama import logger, ray_setup_logger
from spinorama.constant_paths import CPATH_DOCS_SPEAKERS
from spinorama.ltype import DataSpeaker
from spinorama.filter_peq import Peq, peq_preamp_gain
from spinorama.misc import graph_unmelt
from spinorama.compute_misc import compute_minmax_slopes
from spinorama.plot import (
    plot_params_default,
    contour_params_default,
    radar_params_default,
    plot_spinorama,
    plot_graph,
    plot_graph_spl,
    plot_graph_regression,
    plot_contour,
    plot_radar,
    plot_contour_3d,
    FONT_H1,
)


def write_multiformat(chart, filename, force):
    """Write a png file and then convert and save to jpg and webp"""
    filepath = pathlib.Path(filename)
    if not filepath.parent.exists():
        logger.warning("%s does not exists!", filename)
        return
    if not filepath.is_file() or force:
        try:
            chart.write_image(filename)
        except RuntimeError as rt:
            logger.error("writing image %s crashed! %s", filename, rt)
            return
    if os.path.getsize(filename) == 0:
        logger.warning("Saving %s failed!", filename)
        return
    logger.info("Saving %s", filename)

    try:
        with Wim(filename=filename) as pict:
            filename = filename.replace("_large", "")
            webp = "{}.webp".format(filename[:-4])
            if not pathlib.Path(webp).is_file() or force:
                pict.convert("webp").save(filename=webp)
            pict.compression_quality = 75
            jpg = "{}.jpg".format(filename[:-4])
            if not pathlib.Path(jpg).is_file() or force:
                pict.convert("jpg").save(filename=jpg)
    except CoderError as ce:
        logger.exception("Saving picture %s failed with %s", filename, ce)


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


def get_spin_unmelted(df, is_normalized):
    print(df.keys())
    spin = (
        df.get("CEA2034_unmelted") if not is_normalized else df.get("CEA2034 Normalized_unmelted")
    )
    if spin is None:
        spin_melted = df.get("CEA2034") if not is_normalized else df.get("CEA2034 Normalized")
        if spin_melted is not None:
            spin = graph_unmelt(spin_melted)
            if is_normalized:
                df["CEA2034 Normalized_unmelted"] = spin
            else:
                df["CEA2034_unmelted"] = spin
        if spin is None:
            logger.info(
                "Display CEA2034 not in dataframe (%s) is_normalized=%s",
                ", ".join(df.keys()),
                str(is_normalized),
            )
            return None
    return spin


def get_minmax_slopes(df, is_normalized):
    spin = get_spin_unmelted(df, is_normalized)
    if spin is not None:
        return spin, compute_minmax_slopes(spin=spin, is_normalized=is_normalized)
    return None, None


# ----------------------------------------------------------------------
# provide "as measured" and "normalized" versions
# ----------------------------------------------------------------------
def display_spinorama_common(df, graph_params, is_normalized):
    spin, slopes = get_minmax_slopes(df, is_normalized=is_normalized)
    if spin is None:
        logger.error(
            "plot_spinorama failed, cannot get Spin (is_normalized=%s)", str(is_normalized)
        )
        return None

    fig = plot_spinorama(spin, graph_params, slopes, is_normalized=is_normalized)
    if fig is None:
        logger.error("plot_spinorama failed")
        return None
    return fig


def display_spinorama(df, graph_params=plot_params_default):
    return display_spinorama_common(df, graph_params, is_normalized=False)


def display_spinorama_normalized(df, graph_params=plot_params_default):
    return display_spinorama_common(df, graph_params, is_normalized=True)


def display_inroom(df, graph_params=plot_params_default):
    spin = df.get("CEA2034_unmelted")
    if spin is None:
        spin_melted = df.get("CEA2034")
        if spin_melted is not None:
            spin = graph_unmelt(spin_melted)

    try:
        if "Estimated In-Room Response_unmelted" not in df:
            return None
    except KeyError as ke:
        logger.warning("Display In Room failed with %s", ke)
        return None
    else:
        slopes = None
        if spin is not None:
            slopes = compute_minmax_slopes(spin, is_normalized=False)
        return plot_graph_regression(df, "Estimated In-Room Response", graph_params, slopes, False)


def display_inroom_normalized(df, graph_params=plot_params_default):
    spin = df.get("CEA2034 Normalized_unmelted")
    if spin is None:
        spin_melted = df.get("CEA2034 Normalized")
        if spin_melted is not None:
            spin = graph_unmelt(spin_melted)

    try:
        if "Estimated In-Room Response Normalized_unmelted" not in df:
            return None
    except KeyError as ke:
        logger.warning("Display In Room failed with %s", ke)
        return None
    else:
        slopes = None
        if spin is not None:
            slopes = compute_minmax_slopes(spin, is_normalized=True)
        return plot_graph_regression(
            df, "Estimated In-Room Response Normalized", graph_params, slopes, True
        )


# ----------------------------------------------------------------------
# provide "as measured" graphs
# ----------------------------------------------------------------------
def display_onaxis(df, graph_params=plot_params_default):
    onaxis = df.get("CEA2034_unmelted")
    if onaxis is None:
        onaxis = df.get("On Axis_unmelted")

    if onaxis is None:
        logger.debug("Display On Axis failed")
        return None

    if "On Axis" not in onaxis:
        logger.debug("Display On Axis failed, known keys are (%s)", ", ".join(onaxis.keys()))
        return None

    _, slopes = get_minmax_slopes(df, False)
    fig = plot_graph_regression(df, "On Axis", graph_params, slopes, False)
    return fig


def display_reflection_early(df, graph_params=plot_params_default):
    try:
        if "Early Reflections_unmelted" not in df:
            return None
    except KeyError as ke:
        logger.warning("Display Early Reflections failed with %s", ke)
        return None
    else:
        return plot_graph(df["Early Reflections_unmelted"], graph_params)


def display_reflection_horizontal(df, graph_params=plot_params_default):
    try:
        if "Horizontal Reflections_unmelted" not in df:
            return None
    except KeyError as ke:
        logger.warning("Display Horizontal Reflections failed with %s", ke)
        return None
    else:
        return plot_graph(df["Horizontal Reflections_unmelted"], graph_params)


def display_reflection_vertical(df, graph_params=plot_params_default):
    try:
        if "Vertical Reflections_unmelted" not in df:
            return None
    except KeyError:
        return None
    else:
        return plot_graph(df["Vertical Reflections_unmelted"], graph_params)


def display_spl(df, axis, graph_params=plot_params_default):
    try:
        if axis not in df:
            return None
    except KeyError as ke:
        logger.warning("Display SPL failed with %s", ke)
        return None
    else:
        return plot_graph_spl(df[axis], graph_params)


def display_spl_horizontal(df, graph_params=plot_params_default):
    return display_spl(df, "SPL Horizontal_unmelted", graph_params)


def display_spl_vertical(df, graph_params=plot_params_default):
    return display_spl(df, "SPL Vertical_unmelted", graph_params)


def display_spl_horizontal_normalized(df, graph_params=plot_params_default):
    return display_spl(df, "SPL Horizontal_normalized_unmelted", graph_params)


def display_spl_vertical_normalized(df, graph_params=plot_params_default):
    return display_spl(df, "SPL Vertical_normalized_unmelted", graph_params)


def display_contour(df, direction, graph_params=contour_params_default):
    if direction not in df:
        return None
    return plot_contour(df[direction], graph_params)


def display_contour_horizontal(df, graph_params=contour_params_default):
    return display_contour(df, "SPL Horizontal_unmelted", graph_params)


def display_contour_vertical(df, graph_params=contour_params_default):
    return display_contour(df, "SPL Vertical_unmelted", graph_params)


def display_contour_horizontal_normalized(df, graph_params=contour_params_default):
    return display_contour(df, "SPL Horizontal_normalized_unmelted", graph_params)


def display_contour_vertical_normalized(df, graph_params=contour_params_default):
    return display_contour(df, "SPL Vertical_normalized_unmelted", graph_params)


def display_contour_3d(df, direction, graph_params=contour_params_default):
    if direction not in df:
        return None
    return plot_contour_3d(df[direction], graph_params)


def display_contour_horizontal_3d(df, graph_params=contour_params_default):
    return display_contour_3d(df, "SPL Horizontal_unmelted", graph_params)


def display_contour_vertical_3d(df, graph_params=contour_params_default):
    return display_contour_3d(df, "SPL Vertical_unmelted", graph_params)


def display_contour_horizontal_normalized_3d(df, graph_params=contour_params_default):
    return display_contour_3d(df, "SPL Horizontal_normalized_unmelted", graph_params)


def display_contour_vertical_normalized_3d(df, graph_params=contour_params_default):
    return display_contour_3d(df, "SPL Vertical_normalized_unmelted", graph_params)


def display_radar(df, direction, graph_params):
    dfs = df.get(direction)
    if dfs is None:
        return None
    return plot_radar(dfs, graph_params)


def display_radar_horizontal(df, graph_params=radar_params_default):
    return display_radar(df, "SPL Horizontal_unmelted", graph_params)


def display_radar_vertical(df, graph_params=radar_params_default):
    return display_radar(df, "SPL Vertical_unmelted", graph_params)


def build_filename(speaker, origin, version, graph_name, file_ext) -> str:
    filedir = (
        CPATH_DOCS_SPEAKERS + "/" + speaker + "/" + origin.replace("Vendors-", "") + "/" + version
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
        else:
            write_multiformat(chart, filename, force)
        updated += 1
    except Exception:
        logger.exception("Got unkown error for %s", filename)

    return updated


@ray.remote
def print_graphs(
    data: DataSpeaker | tuple[Peq, DataSpeaker],
    speaker: str,
    version: str,
    origin: str,
    origins_info: dict,
    version_key: str,
    width: int,
    height: int,
    force_print: bool,
    level: int,
) -> int:
    ray_setup_logger(level)
    #
    df_speaker = {}
    iir = []
    if isinstance(data, dict):
        df_speaker = data
    else:
        iir, df_speaker = data
    # may happens at development time or for partial measurements
    # or when the cache is confused (typically when you change the metadata)
    if df_speaker is None:
        logger.debug("df_speaker is None for %s %s %s", speaker, version, origin)
        return 0

    if len(df_speaker.keys()) == 0:
        # if print_a_graph is called before df_speaker is ready
        # fix: ray call above
        return 0

    graph_params = copy.deepcopy(plot_params_default)
    if width // height != 4 // 3:
        logger.error("ratio width / height must be 4/3")
        height = int(width * 3 / 4)
    graph_params["width"] = width
    graph_params["height"] = height
    graph_params["layout"] = "compact"
    graph_params["xmin"] = origins_info[origin]["min hz"]
    graph_params["xmax"] = origins_info[origin]["max hz"]
    graph_params["ymin"] = origins_info[origin]["min dB"]
    graph_params["ymax"] = origins_info[origin]["max dB"]

    graphs = {}
    for op_title, op_call in (
        ("CEA2034", display_spinorama),
        ("CEA2034 Normalized", display_spinorama_normalized),
        ("On Axis", display_onaxis),
        ("Estimated In-Room Response", display_inroom),
        ("Estimated In-Room Response Normalized", display_inroom_normalized),
        ("Early Reflections", display_reflection_early),
        ("Horizontal Reflections", display_reflection_horizontal),
        ("Vertical Reflections", display_reflection_vertical),
        ("SPL Horizontal", display_spl_horizontal),
        ("SPL Vertical", display_spl_vertical),
        ("SPL Horizontal Normalized", display_spl_horizontal_normalized),
        ("SPL Vertical Normalized", display_spl_vertical_normalized),
    ):
        # logger.debug("%s %s %s %s", speaker, version, origin, ",".join(list(df_speaker.keys())))
        graph = op_call(df_speaker, graph_params)
        if graph is None:
            if op_title in ("CEA2034", "CEA2034 Normalized"):
                logger.warning("display %s failed for %s %s %s", op_title, speaker, version, origin)
            else:
                logger.info("display %s failed for %s %s %s", op_title, speaker, version, origin)
            continue
        graphs[op_title] = graph

    # change params for contour
    contour_params = copy.deepcopy(contour_params_default)
    contour_params["width"] = width
    contour_params["height"] = height
    contour_params["layout"] = "compact"
    contour_params["xmin"] = origins_info[origin]["min hz"]
    contour_params["xmax"] = origins_info[origin]["max hz"]

    graphs["SPL Horizontal Contour"] = display_contour_horizontal(df_speaker, contour_params)
    graphs["SPL Vertical Contour"] = display_contour_vertical(df_speaker, contour_params)
    graphs["SPL Horizontal Contour Normalized"] = display_contour_horizontal_normalized(
        df_speaker, contour_params
    )
    graphs["SPL Vertical Contour Normalized"] = display_contour_vertical_normalized(
        df_speaker, contour_params
    )

    graphs["SPL Horizontal Contour 3D"] = display_contour_horizontal_3d(df_speaker, contour_params)
    graphs["SPL Vertical Contour 3D"] = display_contour_vertical_3d(df_speaker, contour_params)
    graphs["SPL Horizontal Contour Normalized 3D"] = display_contour_horizontal_normalized_3d(
        df_speaker, contour_params
    )
    graphs["SPL Vertical Contour Normalized 3D"] = display_contour_vertical_normalized_3d(
        df_speaker, contour_params
    )

    # better square
    radar_params = copy.deepcopy(radar_params_default)
    radar_params["width"] = int(height * 4 / 5)
    radar_params["height"] = height
    radar_params["layout"] = "compact"
    radar_params["xmin"] = origins_info[origin]["min hz"]
    radar_params["xmax"] = origins_info[origin]["max hz"]

    graphs["SPL Horizontal Radar"] = display_radar_horizontal(df_speaker, radar_params)
    graphs["SPL Vertical Radar"] = display_radar_vertical(df_speaker, radar_params)

    # add a title if needed
    for key, graph in graphs.items():
        title = key.replace("_smoothed", "")
        # optimised for small screens / vertical orientation
        if graph is None:
            continue
        text = build_title(origin, version, speaker, title, iir)
        graphs[key].update_layout(
            title=dict(
                text=text,
                font=FONT_H1,
            ),
        )

    updated = 0
    for key, graph in graphs.items():
        if graph is None:
            continue
        # force_update = need_update()
        force_update = False
        for ext in ("png", "json"):
            filename = build_filename(speaker, origin, version_key, key, ext)
            updated += print_a_graph(filename, graph, ext, force_print or force_update)
    return updated
