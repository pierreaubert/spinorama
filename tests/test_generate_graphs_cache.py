#!/usr/bin/env python3
"""Regression tests for incremental speaker-graph fingerprints."""

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import generate_graphs


class TestGraphFingerprint(unittest.TestCase):
    def test_isolated_from_unrelated_metadata_but_tracks_its_own_inputs(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            data_root = Path(temporary_dir)
            measurement = data_root / "datas" / "measurements" / "Test Speaker" / "spin.txt"
            measurement.parent.mkdir(parents=True)
            measurement.write_text("first\n", encoding="utf-8")

            speakers = {
                "Test Speaker": {"model": "Test Speaker", "value": 1},
                "Other Speaker": {"model": "Other Speaker", "value": 1},
            }
            with patch.object(generate_graphs.metadata, "speakers_info", speakers):
                shared = generate_graphs.graph_generator_fingerprint(str(data_root), 600, 400)
                first = generate_graphs.speaker_graph_fingerprint(
                    str(data_root), "Test Speaker", 600, 400, shared
                )

                speakers["Other Speaker"]["value"] = 2
                self.assertEqual(
                    first,
                    generate_graphs.speaker_graph_fingerprint(
                        str(data_root), "Test Speaker", 600, 400, shared
                    ),
                )

                speakers["Test Speaker"]["value"] = 2
                self.assertNotEqual(
                    first,
                    generate_graphs.speaker_graph_fingerprint(
                        str(data_root), "Test Speaker", 600, 400, shared
                    ),
                )

                speakers["Test Speaker"]["value"] = 1
                measurement.write_text("second\n", encoding="utf-8")
                stats = measurement.stat()
                os.utime(measurement, ns=(stats.st_atime_ns, stats.st_mtime_ns + 1_000_000))
                self.assertNotEqual(
                    first,
                    generate_graphs.speaker_graph_fingerprint(
                        str(data_root), "Test Speaker", 600, 400, shared
                    ),
                )


class TestGraphCacheCompleteness(unittest.TestCase):
    def test_requires_every_measurement_and_eq_variant(self):
        speakers = {
            "Test Speaker": {
                "measurements": {
                    "eac": {"origin": "ErinsAudioCorner"},
                    "vendor": {"origin": "Vendor"},
                }
            }
        }
        with patch.object(generate_graphs.metadata, "speakers_info", speakers):
            self.assertFalse(
                generate_graphs.speaker_cache_complete(
                    "Test Speaker", {"ErinsAudioCorner": {"eac": object()}}
                )
            )
            self.assertTrue(
                generate_graphs.speaker_cache_complete(
                    "Test Speaker",
                    {
                        "ErinsAudioCorner": {"eac": object(), "eac_eq": object()},
                        "Vendor": {"vendor": object(), "vendor_eq": object()},
                    },
                )
            )


if __name__ == "__main__":
    unittest.main()
