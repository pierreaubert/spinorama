#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Regression tests for scripts/generate_meta.py

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from datas import Measurement
from spinorama.loaders.klippel import parse_graph_freq_klippel
from spinorama.measurements import Measurements

import generate_meta


class TestGenerateMetaAddMeasurement(unittest.TestCase):
    """Tests for add_measurement handling of partial (truncated) measurements."""

    @classmethod
    def setUpClass(cls):
        cls._measurements = cls._load_neumann_kh80_measurements()

    @staticmethod
    def _load_neumann_kh80_measurements():
        paths = {
            "cea2034": "datas/measurements/Neumann KH 80/asr-v3-20200711/CEA2034.txt",
            "eir": "datas/measurements/Neumann KH 80/asr-v3-20200711/Estimated In-Room Response.txt",
            "h_spl": "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Horizontal.txt",
            "v_spl": "datas/measurements/Neumann KH 80/asr-v3-20200711/SPL Vertical.txt",
        }
        frames = {}
        for key, path in paths.items():
            status, (_, df) = parse_graph_freq_klippel(path)
            if not status:
                msg = f"Failed to load {path}"
                raise RuntimeError(msg)
            frames[key] = df
        return Measurements(
            cea2034=frames["cea2034"],
            eir=frames["eir"],
            h_spl=frames["h_spl"],
            v_spl=frames["v_spl"],
        )

    @staticmethod
    def _speaker_info(min_valid_freq=None):
        measurement = Measurement(
            {
                "origin": "ASR",
                "format": "klippel",
            }
        )
        if min_valid_freq is not None:
            measurement["data_acquisition"] = {"min_valid_freq": min_valid_freq}
        return {
            "brand": "Test",
            "model": "Speaker",
            "type": "active",
            "default_measurement": "asr",
            "measurements": {"asr": measurement},
        }

    def test_full_range_measurement_computes_scores(self):
        speakers_info = {"Test Speaker Full": self._speaker_info()}
        with patch.object(generate_meta, "speakers_info", speakers_info):
            result = generate_meta.add_measurement(
                "Test Speaker Full", "ASR", "asr", self._measurements
            )
        self.assertIn("pref_rating", result)
        self.assertIn("scaled_pref_rating", result)
        self.assertIn("estimates", result)

    def test_explicit_20hz_computes_scores(self):
        speakers_info = {"Test Speaker 20Hz": self._speaker_info(min_valid_freq=20)}
        with patch.object(generate_meta, "speakers_info", speakers_info):
            result = generate_meta.add_measurement(
                "Test Speaker 20Hz", "ASR", "asr", self._measurements
            )
        self.assertIn("pref_rating", result)
        self.assertIn("scaled_pref_rating", result)
        self.assertIn("estimates", result)

    def test_partial_measurement_keeps_estimates_skips_pref_rating(self):
        speakers_info = {"Test Speaker Partial": self._speaker_info(min_valid_freq=200)}
        with patch.object(generate_meta, "speakers_info", speakers_info):
            result = generate_meta.add_measurement(
                "Test Speaker Partial", "ASR", "asr", self._measurements
            )
        self.assertIn("estimates", result)
        self.assertNotIn("pref_rating", result)

    def test_partial_eq_version_keeps_estimates_skips_pref_rating(self):
        """The _eq variant looks up the base measurement's data_acquisition."""
        speakers_info = {"Test Speaker Partial EQ": self._speaker_info(min_valid_freq=200)}
        with patch.object(generate_meta, "speakers_info", speakers_info):
            result = generate_meta.add_measurement(
                "Test Speaker Partial EQ", "ASR", "asr_eq", self._measurements
            )
        self.assertIn("estimates_eq", result)
        self.assertNotIn("pref_rating_eq", result)


class TestAudioholicsMetadata(unittest.TestCase):
    """Regression test ensuring Audioholics measurements are flagged as partial."""

    def test_all_audioholics_measurements_have_min_valid_freq(self):
        from datas.speaker import speakers_info

        audioholics_keys = {
            "misc-audioholics",
            "misc-audioholics-vertical",
            "misc-audioholics-horizontal",
        }
        missing = []
        for speaker_name, speaker_data in speakers_info.items():
            for version, measurement in speaker_data.get("measurements", {}).items():
                if version not in audioholics_keys:
                    continue
                data_acquisition = measurement.get("data_acquisition", {})
                min_valid_freq = data_acquisition.get("min_valid_freq")
                if min_valid_freq != 200:
                    missing.append((speaker_name, version, min_valid_freq))
        self.assertEqual(
            missing,
            [],
            f"Audioholics measurements missing min_valid_freq=200: {missing}",
        )


if __name__ == "__main__":
    unittest.main()
