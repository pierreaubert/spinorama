#!/usr/bin/env python
# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-21 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
CPATH_SRC = "{}/{}".format(CPATH, "src")
CPATH_PYTHON = "{}/{}".format(CPATH_SRC, "spinorama")
CPATH_WEBSITE = "{}/{}".format(CPATH_SRC, "website")
CPATH_WEBSITE_ASSETS = "{}/{}".format(CPATH_WEBSITE, "assets")
CPATH_WEBSITE_ASSETS_CSS = "{}/{}".format(CPATH_WEBSITE_ASSETS, "")
CPATH_WEBSITE_ASSETS_JS = "{}/{}".format(CPATH_WEBSITE_ASSETS, "")

# where the metadata around the speakers are
CPATH_DATAS = "{}/{}".format(CPATH, "datas")
CPATH_DATAS_LOGOS = "{}/{}".format(CPATH_DATAS, "logos")
CPATH_DATAS_PICTURES = "{}/{}".format(CPATH_DATAS, "pictures")
CPATH_DATAS_SPEAKERS = "{}/{}".format(CPATH_DATAS, "measurements")

# where the generated files go
CPATH_DOCS = "{}/{}".format(CPATH, "docs")
CPATH_DOCS_ASSETS = "{}/{}".format(CPATH_DOCS, "assets")
CPATH_DOCS_ASSETS_JS = "{}/{}".format(CPATH_DOCS_ASSETS, "")
CPATH_DOCS_ASSETS_CSS = "{}/{}".format(CPATH_DOCS_ASSETS, "")
CPATH_METADATA_JSON = "{}/{}".format(CPATH_DOCS_ASSETS, "metadata.json")
CPATH_DOCS_SPEAKERS = "{}/{}".format(CPATH_DOCS, "speakers")
CPATH_DOCS_PICTURES = "{}/{}".format(CPATH_DOCS, "pictures")
