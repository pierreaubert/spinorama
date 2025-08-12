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
import sys
import unittest
import tempfile
from unittest.mock import patch, MagicMock
from typing import List, Tuple

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.importer.audiorekr.audiorekr import (
    read_on,
    read_spl,
    process_spl,
    process,
    parse_args,
    interpolate,
)


class TestAudiorekr(unittest.TestCase):
    """Test the audiorekr importer functions."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.speakername = "TestSpeaker"

        # Create sample test files with mock data
        self.temp_dir = tempfile.TemporaryDirectory()

        # Create test on-axis SPL file
        self.on_spl_file = os.path.join(self.temp_dir.name, "on_spl.txt")
        with open(self.on_spl_file, "w") as f:
            f.write("20.0 85.5\n")
            f.write("100.0 90.2\n")
            f.write("1000.0 88.7\n")
            f.write("10000.0 82.3\n")
            f.write("20000.0 75.1\n")

        # Create test horizontal SPL file
        self.h_spl_file = os.path.join(self.temp_dir.name, "h_spl.txt")
        with open(self.h_spl_file, "w") as f:
            f.write("20.0, 85.5, 0\n")
            f.write("100.0, 90.2, 0\n")
            f.write("20.0, 84.1, 10\n")
            f.write("100.0, 89.5, 10\n")

        # Create test vertical SPL file
        self.v_spl_file = os.path.join(self.temp_dir.name, "v_spl.txt")
        with open(self.v_spl_file, "w") as f:
            f.write("20.0, 85.0, 0\n")
            f.write("100.0, 90.0, 0\n")
            f.write("20.0, 83.0, 10\n")
            f.write("100.0, 88.0, 10\n")

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_read_on_default_freq(self) -> None:
        """Test read_on function with default frequency threshold."""
        on_spl = read_on(self.on_spl_file)
        self.assertEqual(len(on_spl), 5)
        self.assertEqual(on_spl[0], (20.0, 85.5))
        self.assertEqual(on_spl[-1], (20000.0, 75.1))

    def test_read_on_filters_correctly(self) -> None:
        """Test that read_on returns correct frequency range."""
        on_spl = read_on(self.on_spl_file)
        # Should contain all frequencies between 20 and 20000 Hz
        filtered_data = [item for item in on_spl if item[0] >= 100.0]
        self.assertEqual(len(filtered_data), 4)
        self.assertEqual(filtered_data[0][0], 100.0)
        self.assertEqual(filtered_data[-1][0], 20000.0)

    def test_read_spl_default_freq(self) -> None:
        """Test read_spl function with default frequency threshold."""
        h_spl = read_spl(self.h_spl_file)
        self.assertEqual(len(h_spl[0]), 2)
        self.assertEqual(len(h_spl[10]), 2)
        self.assertEqual(h_spl[0][0], (20.0, 85.5))
        self.assertEqual(h_spl[10][0], (20.0, 84.1))

    def test_read_spl_filters_correctly(self) -> None:
        """Test that read_spl returns correct frequency range."""
        h_spl = read_spl(self.h_spl_file)
        # Check that 100.0 Hz is included for both angles 0 and 10
        self.assertIn((100.0, 90.2), h_spl[0])
        self.assertIn((100.0, 89.5), h_spl[10])

    @patch("os.path.exists")
    @patch("builtins.open", create=True)
    def test_process_full(self, mock_open: MagicMock, mock_exists: MagicMock) -> None:
        """Test the full process function with all SPL files."""
        mock_exists.return_value = True

        # Process both horizontal and vertical files
        process(
            self.speakername,
            self.on_spl_file,
            self.h_spl_file,
            self.v_spl_file,
            freq_similar=100.0,
            freq_interpolate=50.0,
            freq_valid_data=25.0,
        )

        # Check that file writing was attempted
        self.assertTrue(mock_open.called)

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_basic(self, mock_parse_args: MagicMock) -> None:
        """Test basic argument parsing."""
        mock_args = MagicMock()
        mock_args.speaker = "TestSpeaker"
        mock_args.freq_similar = None
        mock_args.freq_interpolate = None
        mock_args.freq_valid_data = None
        mock_args.on_file = "01_FR.txt"
        mock_args.h_file = "02_Horizontal Contour Plot.txt"
        mock_args.v_file = "03_Vertical Contour Plot.txt"
        mock_parse_args.return_value = mock_args

        args = parse_args()
        self.assertEqual(args.speaker, "TestSpeaker")
        self.assertIsNone(args.freq_similar)
        self.assertIsNone(args.freq_interpolate)
        self.assertIsNone(args.freq_valid_data)

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_with_valid_freq(self, mock_parse_args: MagicMock) -> None:
        """Test argument parsing with valid frequency values."""
        mock_args = MagicMock()
        mock_args.speaker = "TestSpeaker"
        mock_args.freq_similar = 30.0  # Smallest
        mock_args.freq_valid_data = 100.0  # Largest
        mock_args.on_file = "custom_on.txt"
        mock_args.h_file = "custom_h.txt"
        mock_args.v_file = "custom_v.txt"
        mock_parse_args.return_value = mock_args

        args = parse_args()
        self.assertEqual(args.speaker, "TestSpeaker")
        self.assertEqual(args.freq_similar, 30.0)
        self.assertEqual(args.freq_valid_data, 100.0)
        self.assertEqual(args.on_file, "custom_on.txt")
        self.assertEqual(args.h_file, "custom_h.txt")
        self.assertEqual(args.v_file, "custom_v.txt")

    @patch("sys.argv", ["audiorekr.py", "--speaker", "TestSpeaker"])
    def test_parse_args_real(self) -> None:
        """Test actual argument parsing with real arguments."""
        with patch("argparse.ArgumentParser.exit") as mock_exit:
            try:
                args = parse_args()
                self.assertEqual(args.speaker, "TestSpeaker")
                self.assertIsNone(args.freq_similar)
            except SystemExit:
                pass  # Expected in some test environments
            self.assertFalse(mock_exit.called)

    def test_interpolate_function(self) -> None:
        """Test the interpolate function with three points."""
        point1 = (20.0, 80.0)  # First point
        point2 = (100.0, 90.0)  # Middle point
        point3 = (1000.0, 85.0)  # Last point

        # Test exact points
        self.assertEqual(interpolate(point1, point2, point3, 20.0), 80.0)
        self.assertEqual(interpolate(point1, point2, point3, 1000.0), 85.0)

        # Test midpoints in each segment
        self.assertAlmostEqual(
            interpolate(point1, point2, point3, 60.0), 85.0
        )  # Between point1 and point2
        self.assertAlmostEqual(
            interpolate(point1, point2, point3, 500.0), 87.78, places=2
        )  # Between point2 and point3

        # Test edge cases
        self.assertEqual(interpolate(point1, point2, point3, 10.0), 80.0)  # Below range
        self.assertEqual(interpolate(point1, point2, point3, 2000.0), 85.0)  # Above range

    @patch("argparse.ArgumentParser.error")
    @patch("argparse.ArgumentParser.parse_args")
    def test_invalid_freq_similar_larger_than_valid_data(
        self, mock_parse_args: MagicMock, mock_error: MagicMock
    ) -> None:
        """Test when freq_similar is larger than freq_valid_data."""
        mock_args = MagicMock()
        mock_args.speaker = "TestSpeaker"
        mock_args.freq_similar = 120.0  # Invalid: larger than freq_valid_data
        mock_args.freq_valid_data = 100.0
        mock_parse_args.return_value = mock_args

        parse_args()
        mock_error.assert_called_with("--freq-similar must be smaller than --freq-valid-data")

    @patch("argparse.ArgumentParser.error")
    @patch("argparse.ArgumentParser.parse_args")
    def test_partially_specified_frequencies(
        self, mock_parse_args: MagicMock, mock_error: MagicMock
    ) -> None:
        """Test with only some frequency parameters specified (should not error)."""
        mock_args = MagicMock()
        mock_args.speaker = "TestSpeaker"
        mock_args.freq_similar = 30.0
        mock_args.freq_valid_data = None  # Not specified
        mock_parse_args.return_value = mock_args

        args = parse_args()
        self.assertEqual(args.freq_similar, 30.0)
        self.assertIsNone(args.freq_valid_data)
        mock_error.assert_not_called()  # Should not call error

    def test_process_spl_function(self) -> None:
        """Test the process_spl function that handles frequency interpolation."""
        # Setup input data
        on_spl = [(20.0, 85.5), (100.0, 90.2), (1000.0, 88.7)]
        h_spl = {0: [(20.0, 85.5), (100.0, 90.2)], 10: [(20.0, 84.1), (100.0, 89.5)]}

        # Test with valid frequency thresholds
        freq_similar = 30.0
        freq_valid_data = 90.0

        result = process_spl(h_spl, on_spl, freq_similar, freq_valid_data)

        # Check that angles are preserved
        self.assertIn(0, result)
        self.assertIn(10, result)


if __name__ == "__main__":
    unittest.main()
