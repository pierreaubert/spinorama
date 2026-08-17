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

# where the code for the website is
CPATH = "."
CPATH_SRC = f"{CPATH}/src"
CPATH_PYTHON = f"{CPATH_SRC}/spinorama"
CPATH_WEBSITE = f"{CPATH_SRC}/website"
CPATH_SCRIPTS = f"{CPATH}/scripts"

# where the metadata around the speakers are
CPATH_DATAS = f"{CPATH}/datas"
CPATH_DATAS_ICONS = f"{CPATH_DATAS}/icons"
CPATH_DATAS_PICTURES = f"{CPATH_DATAS}/pictures"
CPATH_DATAS_SPEAKERS = f"{CPATH_DATAS}/measurements"
CPATH_DATAS_EQ = f"{CPATH_DATAS}/eq"
CPATH_DATAS_HEADPHONES = f"{CPATH_DATAS}/headphones"
CPATH_DATAS_HEADPHONE_EQ = f"{CPATH_DATAS}/headphone_eq"
CPATH_DATAS_HEADPHONE_TARGETS = f"{CPATH_DATAS}/headphone_targets"

# where the temporay files go
CPATH_BUILD = f"{CPATH}/build"
CPATH_BUILD_EQ = f"{CPATH_BUILD}/eq"
CPATH_BUILD_WEBSITE = f"{CPATH_BUILD}/website"
CPATH_BUILD_MAKO = f"{CPATH_BUILD}/mako_modules"

# where the generated files go
CPATH_DIST = f"{CPATH}/dist"
CPATH_DIST_JS = f"{CPATH_DIST}/js"
CPATH_DIST_JS3RD = f"{CPATH_DIST}/js3rd"
CPATH_DIST_CSS = f"{CPATH_DIST}/css"
CPATH_DIST_JSON = f"{CPATH_DIST}/json"
CPATH_DIST_METADATA_JSON = f"{CPATH_DIST_JSON}/metadata.json"
CPATH_DIST_EQDATA_JSON = f"{CPATH_DIST_JSON}/eqdata.json"
CPATH_DIST_SPEAKERS = f"{CPATH_DIST}/speakers"
CPATH_DIST_PICTURES = f"{CPATH_DIST}/pictures"
CPATH_DIST_HEADPHONE_JSON = f"{CPATH_DIST_JSON}/headphone.json"

# headphone generated output
CPATH_DIST_HEADPHONES = f"{CPATH_DIST}/headphones"
CPATH_DIST_HEADPHONE_METADATA_JSON = f"{CPATH_DIST_JSON}/headphone_metadata.json"
CPATH_DIST_HEADPHONE_EQDATA_JSON = f"{CPATH_DIST_JSON}/headphone_eqdata.json"

# mean is computed over a range
MEAN_MIN = 300
MEAN_MAX = 3000

# midrange defintion
MIDRANGE_MIN_FREQ = 300
MIDRANGE_MAX_FREQ = 5000
MIDRANGE_FREQ = [MIDRANGE_MIN_FREQ, MIDRANGE_MAX_FREQ]

# range for directivity computations
DIRECTIVITY_MIN_FREQ = 1000
DIRECTIVITY_MAX_FREQ = 10000

# range for slope computations
SLOPE_MIN_FREQ = 100
SLOPE_MAX_FREQ = 12000

# Sensitivity definition: no agreement here but from IEC 60268-5 (the main standard):
#
# The IEC standard defines sensitivity as the sound pressure level (SPL) produced
# at 1 meter on-axis when driven with 2.83 Vrms of pink noise (or a  specified
# bandwidth), measured in an anechoic environment. The result is expressed as dB SPL / 2.83V / 1m.
# - 2.83 Vrms delivers exactly 1 watt into 8 ohms (P = V²/R). This is why you often
#   see sensitivity quoted as "dB/W/m."
# - For speakers with a different nominal impedance (e.g., 4 ohms), 2.83V delivers 2W,
# which inflates the number compared to a true 1W measurement. Some manufacturers exploit this.
#
# Key conventions and variants:
#
# +------------------------------------------------------------------------------------------------+
# │       Convention        │                             Description                              |
# +------------------------------------------------------------------------------------------------+
# │ 2.83V / 1m              │ Most common today. Voltage-referenced, impedance-independent.        |
# +------------------------------------------------------------------------------------------------+
# | 1W / 1m                 │ Power-referenced. Adjusts voltage to deliver exactly 1W regardless   |
# |                         | of impedance. More honest for cross-impedance comparisons.           |
# +------------------------------------------------------------------------------------------------+
# │ Half-space vs           │ Half-space (2π) adds ~3dB vs free-field (4π) due to the baffle/ground|
# | Full space              | reflection. Spec sheets don't always clarify which.                  │
# +------------------------------------------------------------------------------------------------+
# │ Frequency range         │ Typically averaged over 300Hz – 3 kHz (or sometimes 1 kHz only). The |
# |                         | chosen band matters a lot for the resulting number.                  |
# +------------------------------------------------------------------------------------------------+

SENSITIVITY_MIN_FREQ = 300
SENSITIVITY_MAX_FREQ = 3000

# default frequency range for plots
DEFAULT_FREQ_RANGE = (20.0, 20000.0)
# default SPL range for plots
DEFAULT_SPL_RANGE = (-40.0, 10.0)

# curve names
C_ON = "On Axis"
C_LW = "Listening Window"
C_PIR = "Estimated In-Room Response"
C_SP = "Sound Power"
C_ER = "Early Reflections"

# flags
flags_ADD_HASH = False  # noqa: N816
