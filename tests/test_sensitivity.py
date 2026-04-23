#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for sensitivity computation and display for passive speakers.

Regression tests for the bug where passive speakers show 0dB sensitivity
on the main page and no sensitivity on the detail page.
"""

import pytest

from website.utils import get_sensitivity, sensitivity_html


class TestGetSensitivity:
    """Test get_sensitivity returns correct values for passive speakers."""

    def _make_speaker(self, speaker_type, specifications=None, computed_sensitivity=None):
        """Helper to build a minimal speaker data dict."""
        measurement = {
            "origin": "ASR",
            "format": "klippel",
        }
        if specifications is not None:
            measurement["specifications"] = specifications
        if computed_sensitivity is not None:
            measurement["computed_sensitivity"] = computed_sensitivity
        return {
            "brand": "Test",
            "model": "Speaker",
            "type": speaker_type,
            "default_measurement": "asr",
            "measurements": {
                "asr": measurement,
            },
        }

    def test_active_speaker_returns_zero(self):
        """Active speakers should always return 0 (sensitivity not applicable)."""
        speaker = self._make_speaker("active", specifications={"sensitivity": 88.0})
        assert get_sensitivity(None, speaker) == 0

    def test_passive_with_spec_sensitivity(self):
        """Passive speaker with manufacturer spec sensitivity should return it."""
        speaker = self._make_speaker("passive", specifications={"sensitivity": 88.0})
        result = get_sensitivity(None, speaker)
        assert result == 88.0

    def test_passive_with_computed_sensitivity_no_spec(self):
        """Passive speaker without spec sensitivity but with computed sensitivity
        should return the computed value. This is the main regression case."""
        speaker = self._make_speaker(
            "passive",
            specifications={"size": {"height": 400, "width": 220, "depth": 260}},
            computed_sensitivity={"computed": 85.3, "distance": 1.0, "sensitivity_1m": 85.3},
        )
        result = get_sensitivity(None, speaker)
        assert result == pytest.approx(85.3, abs=0.1)

    def test_passive_with_no_spec_no_computed(self):
        """Passive speaker with no sensitivity data at all should return 0."""
        speaker = self._make_speaker("passive", specifications={})
        result = get_sensitivity(None, speaker)
        assert result == 0

    def test_passive_with_no_specifications(self):
        """Passive speaker with no specifications dict at all should return 0."""
        speaker = self._make_speaker("passive")
        result = get_sensitivity(None, speaker)
        assert result == 0

    def test_passive_with_both_spec_and_computed(self):
        """When both spec and computed sensitivity exist, spec takes priority."""
        speaker = self._make_speaker(
            "passive",
            specifications={"sensitivity": 88.0},
            computed_sensitivity={"computed": 85.3, "distance": 1.0, "sensitivity_1m": 85.3},
        )
        result = get_sensitivity(None, speaker)
        assert result == 88.0

    def test_passive_with_no_default_measurement(self):
        """Passive speaker with no default_measurement should return 0."""
        speaker = {
            "brand": "Test",
            "model": "Speaker",
            "type": "passive",
            "default_measurement": None,
            "measurements": {},
        }
        result = get_sensitivity(None, speaker)
        assert result == 0

    def test_passive_computed_sensitivity_1m_differs(self):
        """When measurement distance != 1m, the 1m estimate should be returned."""
        speaker = self._make_speaker(
            "passive",
            specifications={},
            computed_sensitivity={"computed": 79.3, "distance": 2.0, "sensitivity_1m": 85.3},
        )
        result = get_sensitivity(None, speaker)
        assert result == pytest.approx(85.3, abs=0.1)


class TestSensitivityHtml:
    """Test sensitivity_html formatting."""

    def test_active_speaker(self):
        """Active speakers should display 'Active'."""
        assert sensitivity_html(None, "active", 0) == "Active"

    def test_passive_with_sensitivity(self):
        """Passive speakers with sensitivity should show the rounded value."""
        html = sensitivity_html(None, "passive", 88.0)
        assert "88" in html
        assert "dB" in html

    def test_passive_sensitivity_rounds_down(self):
        """83.23 should display as 83."""
        html = sensitivity_html(None, "passive", 83.23)
        assert ">83<" in html

    def test_passive_sensitivity_rounds_up(self):
        """83.88 should display as 84."""
        html = sensitivity_html(None, "passive", 83.88)
        assert ">84<" in html

    def test_passive_with_zero_sensitivity(self):
        """Passive speakers with 0 sensitivity should show '?'."""
        html = sensitivity_html(None, "passive", 0)
        assert "?" in html
        assert "dB" in html

    def test_passive_with_string_zero(self):
        """Sensitivity of string '0' should show '?'."""
        html = sensitivity_html(None, "passive", "0")
        assert "?" in html
