#!/usr/bin/env python3
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

import unittest

import spinorama.constant_paths as cpaths

from generate_html import adapt_imports, get_versions, get_files, CACHE_VERSION


class JSImportTests(unittest.TestCase):
    def setUp(self):
        self.versions = get_versions("{}/update_3rdparties.sh".format(cpaths.CPATH_SCRIPTS))
        self.jsfiles = get_files(cpaths.CPATH_WEBSITE, "js")

    def test_import_misc(self):
        code = "import { show } from './misc.js';"
        transformed = adapt_imports(code, self.versions, self.jsfiles)
        self.assertIn("/js", transformed)

    def test_import_fuse(self):
        code = "import Fuse from 'fuse.js';"
        transformed = adapt_imports(code, self.versions, self.jsfiles)
        self.assertIn("/js3rd", transformed)
        self.assertIn(self.versions["FUSE"], transformed)

    def test_import_plotly(self):
        code = "import Plotly from 'plotly-dist-min';"
        transformed = adapt_imports(code, self.versions, self.jsfiles)
        self.assertNotIn("/js3rd", transformed)
        self.assertNotIn("/js", transformed)
        self.assertNotIn("Plotly", transformed)

    def test_import_multi(self):
        code = """
// import Fuse from 'fuse.js';

import {
    urlSite
} from './meta.js';
import {
    getMetadata,
    assignOptions,
    getAllSpeakers,
    getSpeakerData
} from './download.js';
import {
    knownMeasurements,
    setContour,
    setGlobe,
    setGraph,
    setCEA2034,
    setRadar,
    setSurface,
} from './plot.js';
        """
        transformed = adapt_imports(code, self.versions, self.jsfiles)
        self.assertIn("/js3rd", transformed)
        self.assertIn("/js/download-{}.min.js".format(CACHE_VERSION), transformed)
        self.assertIn("/js/meta-{}.min.js".format(CACHE_VERSION), transformed)
        self.assertIn("/js/plot-{}.min.js".format(CACHE_VERSION), transformed)
        self.assertIn(self.versions["FUSE"], transformed)


if __name__ == "__main__":
    unittest.main()
