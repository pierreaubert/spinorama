#!/usr/bin/env python3
"""Regression tests for EQ comparison incremental output handling."""

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import generate_eq_compare


class TestEqCompareCaching(unittest.TestCase):
    def test_rewrites_existing_output_when_a_dependency_is_newer(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            output = root / "eq_compare.json"
            dependency = root / "filter.txt"
            output.write_text("old", encoding="utf-8")
            dependency.write_text("new", encoding="utf-8")
            output_stats = output.stat()
            os.utime(output, ns=(output_stats.st_atime_ns, output_stats.st_mtime_ns - 1_000_000))

            figure = Mock()
            figure.to_json.return_value = "new"
            speaker = {"brand": "Test", "model": "Speaker"}
            with (
                patch.object(generate_eq_compare, "eq_compare_filename", return_value=str(output)),
                patch.object(generate_eq_compare, "eq_compare_dependencies", return_value=[str(dependency)]),
                patch.object(
                    generate_eq_compare,
                    "build_eq_figure_and_filename",
                    return_value=(figure, str(output), [str(dependency)]),
                ),
            ):
                generate_eq_compare._eq_compare_worker(speaker, force=False)

            self.assertEqual(output.read_text(encoding="utf-8"), "new")
            figure.to_json.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
