"""Tests for graph-cache shard recovery."""

import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import generate_common


class CacheShardRecoveryTests(unittest.TestCase):
    def test_corrupt_shard_is_quarantined_instead_of_raising(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            shard = Path(temporary_dir) / "b0.h5"
            shard.write_bytes(b"broken cache")

            with patch.object(generate_common.fl, "load", side_effect=KeyError("missing node")):
                result = generate_common._cache_fetch_worker((str(shard), logging.INFO))

            self.assertIsNone(result)
            self.assertFalse(shard.exists())
            self.assertEqual((Path(temporary_dir) / "b0.h5.corrupt").read_bytes(), b"broken cache")

    def test_quarantine_keeps_an_existing_backup(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            shard = Path(temporary_dir) / "b0.h5"
            first_backup = Path(temporary_dir) / "b0.h5.corrupt"
            shard.write_bytes(b"new failure")
            first_backup.write_bytes(b"old failure")

            quarantined = generate_common._quarantine_corrupt_cache(str(shard))

            self.assertEqual(quarantined, Path(temporary_dir) / "b0.h5.corrupt.1")
            self.assertEqual(first_backup.read_bytes(), b"old failure")
            self.assertEqual(quarantined.read_bytes(), b"new failure")


if __name__ == "__main__":
    unittest.main()
