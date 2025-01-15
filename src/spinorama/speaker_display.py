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

from spinorama import logger
from spinorama.load_misc import graph_unmelt
from spinorama.compute_misc import compute_minmax_slopes
from spinorama.plot import (
    plot_params_default,
    contour_params_default,
    radar_params_default,
    plot_spinorama,
    plot_graph,
    #     plot_graph_flat,
    plot_graph_spl,
    plot_graph_regression,
    plot_contour,
    plot_radar,
    plot_contour_3d,
)


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


def display_inroom(df, graph_params=plot_params_default):
    spin = df.get("CEA2034 Normalized_unmelted")
    if spin is None:
        spin_melted = df.get("CEA2034 Normalized")
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
            slopes = compute_minmax_slopes(spin, is_normalized=True)
        return plot_graph_regression(df, "Estimated In-Room Response", graph_params, slopes, False)


# ----------------------------------------------------------------------
# provide "as measured" graphs
# ----------------------------------------------------------------------
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
