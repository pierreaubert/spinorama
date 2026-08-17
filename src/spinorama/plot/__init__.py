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

"""Public re-export surface for the plot package.

The original ``plot.py`` module was split into focused submodules. Importers
can pick the focused submodule they need (e.g. ``from spinorama.plot.theme
import UNIFORM_COLORS``) or keep using the top-level package surface.
"""

from spinorama.plot.theme import (
    FLAG_FEATURE_ANNOTATION,
    FLAG_FEATURE_CONFIDENCE_ZONES,
    FLAG_FEATURE_TREND_LINES,
    FLAG_FEATURE_VISIBLE,
    FONT_FAMILY,
    FONT_H1,
    FONT_H2,
    FONT_H3,
    FONT_H4,
    FONT_H5,
    FONT_H6,
    FONT_SIZE_H1,
    FONT_SIZE_H2,
    FONT_SIZE_H3,
    FONT_SIZE_H4,
    FONT_SIZE_H5,
    FONT_SIZE_H6,
    CONTOUR_COLORSCALE,
    RADAR_COLORS,
    UNIFORM_COLORS,
    colors,
    contour_params_default,
    label_short,
    legend_rank,
    plot_params_default,
    radar_params_default,
)
from spinorama.plot.axes import (
    generate_colorbar,
    generate_xaxis,
    generate_yaxis_angles,
    generate_yaxis_di,
    generate_yaxis_gd,
    generate_yaxis_phases,
    generate_yaxis_spl,
    plot_valid_freq_ranges,
)
from spinorama.plot.annotations import (
    AnnotationGeometry,
    AnnotationRequest,
    annotation_dicts,
    estimate_annotation_size,
    place_annotations,
)
from spinorama.plot.layouts import (
    common_layout,
    contour_layout,
    radar_layout,
)
from spinorama.plot.spinorama import (
    plot_spinorama,
    plot_spinorama_annotation,
    plot_spinorama_traces,
)
from spinorama.plot.spl import (
    plot_graph,
    plot_graph_flat,
    plot_graph_flat_traces,
    plot_graph_group_delay,
    plot_graph_onaxis,
    plot_graph_regression,
    plot_graph_regression_traces,
    plot_graph_spl,
    plot_graph_traces,
)
from spinorama.plot.contour import (
    flatten,
    plot_contour,
    plot_contour_3d,
)
from spinorama.plot.radar import (
    find_nearest_freq,
    plot_radar,
)
from spinorama.plot.eqs import plot_eqs

__all__ = [
    # theme
    "FLAG_FEATURE_ANNOTATION",
    "FLAG_FEATURE_CONFIDENCE_ZONES",
    "FLAG_FEATURE_TREND_LINES",
    "FLAG_FEATURE_VISIBLE",
    "FONT_FAMILY",
    "FONT_H1",
    "FONT_H2",
    "FONT_H3",
    "FONT_H4",
    "FONT_H5",
    "FONT_H6",
    "FONT_SIZE_H1",
    "FONT_SIZE_H2",
    "FONT_SIZE_H3",
    "FONT_SIZE_H4",
    "FONT_SIZE_H5",
    "FONT_SIZE_H6",
    "CONTOUR_COLORSCALE",
    "RADAR_COLORS",
    "UNIFORM_COLORS",
    "colors",
    "contour_params_default",
    "label_short",
    "legend_rank",
    "plot_params_default",
    "radar_params_default",
    # axes
    "generate_colorbar",
    "generate_xaxis",
    "generate_yaxis_angles",
    "generate_yaxis_di",
    "generate_yaxis_gd",
    "generate_yaxis_phases",
    "generate_yaxis_spl",
    "plot_valid_freq_ranges",
    # annotations
    "AnnotationGeometry",
    "AnnotationRequest",
    "annotation_dicts",
    "estimate_annotation_size",
    "place_annotations",
    # layouts
    "common_layout",
    "contour_layout",
    "radar_layout",
    # spinorama
    "plot_spinorama",
    "plot_spinorama_annotation",
    "plot_spinorama_traces",
    # spl
    "plot_graph",
    "plot_graph_flat",
    "plot_graph_flat_traces",
    "plot_graph_group_delay",
    "plot_graph_onaxis",
    "plot_graph_regression",
    "plot_graph_regression_traces",
    "plot_graph_spl",
    "plot_graph_traces",
    # contour
    "flatten",
    "plot_contour",
    "plot_contour_3d",
    # radar
    "find_nearest_freq",
    "plot_radar",
    # eqs
    "plot_eqs",
]
