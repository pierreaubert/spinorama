# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2024 Pierre Aubert pierre(at)spinorama(dot)org
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

# where the temporay files go
CPATH_BUILD = f"{CPATH}/build"
CPATH_BUILD_WEBSITE = f"{CPATH_BUILD}/website"
CPATH_BUILD_MAKO = f"{CPATH_BUILD}/mako_modules"

# where the generated files go
CPATH_DOCS = f"{CPATH}/docs"
CPATH_DOCS_JS = f"{CPATH_DOCS}/js"
CPATH_DOCS_JS3RD = f"{CPATH_DOCS}/js3rd"
CPATH_DOCS_CSS = f"{CPATH_DOCS}/css"
CPATH_DOCS_JSON = f"{CPATH_DOCS}/json"
CPATH_DOCS_METADATA_JSON = f"{CPATH_DOCS_JSON}/metadata.json"
CPATH_DOCS_EQDATA_JSON = f"{CPATH_DOCS_JSON}/eqdata.json"
CPATH_DOCS_SPEAKERS = f"{CPATH_DOCS}/speakers"
CPATH_DOCS_PICTURES = f"{CPATH_DOCS}/pictures"

# mean is computed over a range
MEAN_MIN = 300
MEAN_MAX = 3000

# midrange defintion
MIDRANGE_MIN_FREQ = 300
MIDRANGE_MAX_FREQ = 5000
MIDRANGE_FREQ = [MIDRANGE_MIN_FREQ, MIDRANGE_MAX_FREQ]

# sensitivity defintion (no agreement here)
SENSITIVITY_MIN_FREQ = 100
SENSITIVITY_MAX_FREQ = 1000

# curve names
C_ON = "On Axis"
C_LW = "Listening Window"
C_PIR = "Estimeated In-Room Response"
C_SP = "Sound Power"
C_ER = "Early Reflections"

U_ON = f"{C_ON}_unmelted"
U_LW = f"{C_LW}_unmelted"
U_PIR = f"{C_PIR}_unmelted"
U_SP = f"{C_SP}_unmelted"
U_ER = f"{C_ER}_unmelted"

# flags
flags_ADD_HASH = False
