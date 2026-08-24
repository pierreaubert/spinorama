#!/usr/bin/env python3
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
from pathlib import Path
import tempfile
import unittest

from mako.template import Template

import spinorama.constant_paths as cpaths

from generate_html import (
    CACHE_VERSION,
    WEBSITE_JS_FILES,
    adapt_imports,
    copy_if_different,
    get_files,
    get_versions,
)


class JSImportTests(unittest.TestCase):
    def setUp(self):
        self.versions = get_versions("{}/update_3rdparties.sh".format(cpaths.CPATH_SCRIPTS))
        self.jsfiles = get_files(cpaths.CPATH_WEBSITE, "js")
        self.mini = ".min"

    def test_import_misc(self):
        code = "import { show } from './misc.js';"
        transformed = adapt_imports(code, self.versions, self.jsfiles, self.mini)
        self.assertIn("/js", transformed)

    def test_import_fuse(self):
        code = "import Fuse from 'fuse.js';"
        transformed = adapt_imports(code, self.versions, self.jsfiles, self.mini)
        self.assertIn("/js3rd", transformed)
        self.assertIn(self.versions["FUSE"], transformed)

    def test_import_plotly(self):
        code = "import Plotly from 'plotly.js-dist-min';"
        transformed = adapt_imports(code, self.versions, self.jsfiles, self.mini)
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

        minimized = adapt_imports(code, self.versions, self.jsfiles, self.mini)
        self.assertIn("/js3rd", minimized)
        self.assertIn("/js/download-{}.min.js".format(CACHE_VERSION), minimized)
        self.assertIn("/js/meta-{}.min.js".format(CACHE_VERSION), minimized)
        self.assertIn("/js/plot-{}.min.js".format(CACHE_VERSION), minimized)
        self.assertIn(self.versions["FUSE"], minimized)

        transformed = adapt_imports(code, self.versions, self.jsfiles, "")
        self.assertIn("/js3rd", transformed)
        self.assertIn("/js/download-{}.js".format(CACHE_VERSION), transformed)
        self.assertIn("/js/meta-{}.js".format(CACHE_VERSION), transformed)
        self.assertIn("/js/plot-{}.js".format(CACHE_VERSION), transformed)
        self.assertIn(self.versions["FUSE"], transformed)

    def test_meta_template_compiles(self):
        template = Template(filename=f"{cpaths.CPATH_WEBSITE}/meta.js")
        rendered = template.render(
            site="https://www.spinorama.org",
            metadata_filename_head="json/metadata.json",
            metadata_filename_chunks='["json/metadata-0.json"]',
            eqdata_filename="json/eqdata.json",
        )

        self.assertIn("startsWith('$' + '{')", rendered)
        self.assertIn('JSON.parse(metadataFilenameChunksValue)', rendered)

    def test_annotation_layout_is_bundled(self):
        self.assertIn("annotation-layout", WEBSITE_JS_FILES)

    def test_copy_if_different_preserves_mtime_for_identical_output(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            source = Path(temporary_dir) / "source.js"
            destination = Path(temporary_dir) / "destination.js"
            source.write_text("const value = 1;\n", encoding="utf-8")

            self.assertTrue(copy_if_different(str(source), str(destination)))
            stats = destination.stat()
            os.utime(
                destination,
                ns=(stats.st_atime_ns, stats.st_mtime_ns + 1_000_000),
            )
            unchanged_mtime = destination.stat().st_mtime_ns

            self.assertFalse(copy_if_different(str(source), str(destination)))
            self.assertEqual(destination.stat().st_mtime_ns, unchanged_mtime)

            source.write_text("const value = 2;\n", encoding="utf-8")
            self.assertTrue(copy_if_different(str(source), str(destination)))


if __name__ == "__main__":
    unittest.main()
