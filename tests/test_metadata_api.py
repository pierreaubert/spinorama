# -*- coding: utf-8 -*-
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import sys

# Add the datas directory to the path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "datas"))

from metadata.api import MetadataAPI


class TestMetadataAPI(unittest.TestCase):
    """Test suite for MetadataAPI class"""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(self.test_dir)

        self.sample_speaker = {
            "brand": "Test Brand",
            "model": "Test Model",
            "type": "active",
            "shape": "bookshelves",
            "default_measurement": "test-measurement",
            "measurements": {
                "test-measurement": {
                    "origin": "Test Origin",
                    "format": "klippel",
                    "quality": "high",
                }
            },
        }

        self.mock_speakers_info = {
            "Test Speaker 1": {
                "brand": "Brand A",
                "model": "Model X",
                "type": "passive",
                "shape": "floorstanders",
                "default_measurement": "asr",
                "measurements": {"asr": {"origin": "ASR", "format": "klippel"}},
            }
        }

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.test_dir)

    @patch("datas.metadata_api.speakers_info")
    def test_init_loads_speakers(self, mock_speakers_info):
        """Test that MetadataAPI initializes correctly."""
        mock_speakers_info.items.return_value = self.mock_speakers_info.items()

        api = MetadataAPI(self.test_data_dir)
        self.assertGreater(len(api.speakers_cache), 0)

    @patch("datas.metadata_api.speakers_info")
    def test_generate_speaker_id(self, mock_speakers_info):
        """Test speaker ID generation."""
        mock_speakers_info.items.return_value = []

        api = MetadataAPI(self.test_data_dir)
        speaker_id = api._generate_speaker_id("Test Brand", "Test Model")
        self.assertEqual(speaker_id, "test-brand-test-model")

    @patch("datas.metadata_api.speakers_info")
    def test_get_all_speakers(self, mock_speakers_info):
        """Test getting all speakers."""
        mock_speakers_info.items.return_value = self.mock_speakers_info.items()

        api = MetadataAPI(self.test_data_dir)
        speakers = api.get_all_speakers()

        self.assertEqual(len(speakers), 1)
        self.assertIn("id", speakers[0])

    @patch("datas.metadata_api.speakers_info")
    def test_add_speaker_success(self, mock_speakers_info):
        """Test adding a new speaker."""
        mock_speakers_info.items.return_value = []

        api = MetadataAPI(self.test_data_dir)
        result = api.add_speaker(self.sample_speaker)

        self.assertIn("id", result)
        self.assertIn("message", result)

    @patch("datas.metadata_api.speakers_info")
    def test_add_speaker_missing_fields(self, mock_speakers_info):
        """Test adding speaker with missing fields."""
        mock_speakers_info.items.return_value = []

        api = MetadataAPI(self.test_data_dir)
        incomplete_speaker = {"model": "Test Model"}

        with self.assertRaises(ValueError):
            api.add_speaker(incomplete_speaker)

    @patch("datas.metadata_api.speakers_info")
    def test_validate_speaker_data(self, mock_speakers_info):
        """Test speaker data validation."""
        mock_speakers_info.items.return_value = []

        api = MetadataAPI(self.test_data_dir)

        # Valid data
        errors = api.validate_speaker_data(self.sample_speaker)
        self.assertEqual(len(errors), 0)

        # Invalid data
        invalid_speaker = {
            "brand": "",
            "type": "invalid_type",
            "shape": "invalid_shape",
            "measurements": {},
        }
        errors = api.validate_speaker_data(invalid_speaker)
        self.assertGreater(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
