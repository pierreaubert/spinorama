#!/usr/bin/env python3
"""Regression tests for the EQ image stage cache."""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import generate_peqs


class TestEqImageStageCache(unittest.TestCase):
    def test_requires_the_recorded_outputs_to_remain_present(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            output = root / "eq.json"
            output.write_text("{}", encoding="utf-8")
            manifest = root / "stage-manifest.json"
            manifest.write_text(
                json.dumps({"fingerprint": "current", "outputs": [str(output)]}),
                encoding="utf-8",
            )

            with (
                patch.object(generate_peqs, "EQ_IMAGE_STAGE_CACHE_MANIFEST", manifest),
                patch.object(generate_peqs, "eq_image_stage_fingerprint", return_value="current"),
            ):
                self.assertTrue(generate_peqs.eq_image_stage_cache_is_valid({}))
                output.unlink()
                self.assertFalse(generate_peqs.eq_image_stage_cache_is_valid({}))


if __name__ == "__main__":
    unittest.main()
