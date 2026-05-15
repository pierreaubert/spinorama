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

"""Plotly theme: fonts, colors, feature flags, default canvas sizes."""

import plotly.io as pio

FLAG_FEATURE_TREND_LINES = True
FLAG_FEATURE_CONFIDENCE_ZONES = True
FLAG_FEATURE_ANNOTATION = True
FLAG_FEATURE_VISIBLE = False

pio.templates.default = "plotly_white"

FONT_SIZE_H1 = 16
FONT_SIZE_H2 = 14
FONT_SIZE_H3 = 12
FONT_SIZE_H4 = 11
FONT_SIZE_H5 = 10
FONT_SIZE_H6 = 9

FONT_FAMILY = "Arial"

FONT_H1 = dict(size=FONT_SIZE_H1, family=FONT_FAMILY)
FONT_H2 = dict(size=FONT_SIZE_H2, family=FONT_FAMILY)
FONT_H3 = dict(size=FONT_SIZE_H3, family=FONT_FAMILY)
FONT_H4 = dict(size=FONT_SIZE_H4, family=FONT_FAMILY)
FONT_H5 = dict(size=FONT_SIZE_H5, family=FONT_FAMILY)
FONT_H6 = dict(size=FONT_SIZE_H6, family=FONT_FAMILY)

# ratio is 4x3
plot_params_default: dict[str, int | str] = {
    "xmin": 20,
    "xmax": 20000,
    "ymin": -40,
    "ymax": 10,
    "width": 1200,
    "height": 800,
}

# ratio is 2x1
contour_params_default: dict[str, int | str] = {
    "xmin": 100,
    "xmax": 20000,
    "width": 1200,
    "height": 800,
}

# ratio is 4x5
radar_params_default: dict[str, int | str] = {
    "xmin": 400,
    "xmax": 20000,
    "width": 1000,
    "height": 1200,
}

colors: list[str] = [
    "#5c77a5",
    "#dc842a",
    "#c85857",
    "#89b5b1",
    "#71a152",
    "#bab0ac",
    "#e15759",
    "#b07aa1",
    "#76b7b2",
    "#ff9da7",
]

UNIFORM_COLORS: dict[str, str] = {
    # regression
    "Linear Regression": colors[0],
    "Band ±1.5dB": colors[1],
    "Band ±3dB": colors[1],
    # PIR
    "Estimated In-Room Response": colors[0],
    # spin
    "On Axis": colors[0],
    "Listening Window": colors[1],
    "Early Reflections": colors[2],
    "Sound Power": colors[3],
    "Early Reflections DI": colors[4],
    "Sound Power DI": colors[5],
    # reflections
    "Ceiling Bounce": colors[1],
    "Floor Bounce": colors[2],
    "Front Wall Bounce": colors[3],
    "Rear Wall Bounce": colors[4],
    "Side Wall Bounce": colors[5],
    #
    "Ceiling Reflection": colors[1],
    "Floor Reflection": colors[2],
    #
    "Front": colors[1],
    "Rear": colors[2],
    "Side": colors[3],
    #
    "Total Early Reflection": colors[7],
    "Total Horizontal Reflection": colors[8],
    "Total Vertical Reflection": colors[9],
    # SPL
    "10°": colors[1],
    "20°": colors[2],
    "30°": colors[3],
    "40°": colors[4],
    "50°": colors[5],
    "60°": colors[6],
    "70°": colors[7],
    #
    "500 Hz": colors[1],
    "1000 Hz": colors[2],
    "2000 Hz": colors[3],
    "10000 Hz": colors[4],
    "15000 Hz": colors[5],
}

label_short = {
    # regression
    "Linear Regression": "Reg",
    "Band ±1.5dB": "±1.5dB",
    "Band ±3dB": "±3dB",
    # PIR
    "Estimated In-Room Response": "PIR",
    # spin
    "On Axis": "ON",
    "Listening Window": "LW",
    "Early Reflections": "ER",
    "Sound Power": "SP",
    "Early Reflections DI": "ERDI",
    "Sound Power DI": "SPDI",
    # reflections
    "Ceiling Bounce": "CB",
    "Floor Bounce": "FB",
    "Front Wall Bounce": "FWB",
    "Rear Wall Bounce": "RWB",
    "Side Wall Bounce": "SWB",
    #
    "Ceiling Reflection": "CR",
    "Floor Reflection": "FR",
    #
    "Front": "F",
    "Rear": "R",
    "Side": "S",
    #
    "Total Early Reflection": "TER",
    "Total Horizontal Reflection": "THR",
    "Total Vertical Reflection": "TVR",
}


legend_rank = {
    "On Axis": 0,
    "10°": 10,
    "20°": 20,
    "30°": 30,
    "40°": 40,
    "50°": 50,
    "60°": 60,
    "70°": 70,
    "80°": 80,
    "90°": 90,
    "-10°": -10,
    "-20°": -20,
    "-30°": -30,
    "-40°": -40,
    "-50°": -50,
    "-60°": -60,
    "-70°": -70,
    "-80°": -80,
    "-90°": -90,
}


CONTOUR_COLORSCALE = [
    [0, "rgb(0,0,168)"],
    [0.1, "rgb(0,0,200)"],
    [0.2, "rgb(0,74,255)"],
    [0.3, "rgb(0,152,255)"],
    [0.4, "rgb(74,255,161)"],
    [0.5, "rgb(161,255,74)"],
    [0.6, "rgb(255,255,0)"],
    [0.7, "rgb(234,159,0)"],
    [0.8, "rgb(255,74,0)"],
    [0.9, "rgb(222,74,0)"],
    [1, "rgb(253,14,13)"],
]

RADAR_COLORS: dict[str, str] = {
    "100 Hz": colors[0],
    "125 Hz": colors[1],
    "160 Hz": colors[2],
    "200 Hz": colors[3],
    "250 Hz": colors[4],
    "315 Hz": colors[5],
    "400 Hz": colors[6],
    "500 Hz": colors[7],
    "1600 Hz": colors[8],
    "2000 Hz": colors[9],
    "2500 Hz": colors[0],
    "3150 Hz": colors[1],
    "4000 Hz": colors[2],
    "5000 Hz": colors[3],
    "6000 Hz": colors[4],
    "8000 Hz": colors[5],
}
