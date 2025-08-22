# -*- coding: utf-8 -*-
"""Tests for the Spinorama API endpoints."""

import json
import os
import tempfile
from unittest.mock import Mock, patch, mock_open
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, load_metadata


class TestAPI:
    """Test class for API endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_metadata(self) -> Dict[str, Any]:
        """Mock metadata for testing."""
        return {
            "Test Speaker 1": {
                "brand": "Test Brand",
                "measurements": {
                    "version1": {"origin": "TestOrigin"},
                    "version2": {"origin": "Vendors-TestVendor"},
                },
            },
            "Test Speaker 2": {
                "brand": "Another Brand",
                "measurements": {"v1": {"origin": "Origin2"}},
            },
        }

    @pytest.fixture
    def mock_speakers_info(self) -> Dict[str, Any]:
        """Mock speakers_info for testing."""
        return {
            "Test Speaker 1": {
                "brand": "Test Brand",
                "measurements": {"version1": {"origin": "TestOrigin"}},
            }
        }

    def test_get_brand_list_success(
        self, client: TestClient, mock_metadata: Dict[str, Any]
    ) -> None:
        """Test successful brand list retrieval."""
        with patch("src.api.main.load_metadata") as mock_load:
            mock_load.return_value = mock_metadata

            # Override the dependency
            app.dependency_overrides[load_metadata] = lambda: mock_metadata

            response = client.get("/v1/brands")

            assert response.status_code == 200
            brands = response.json()
            assert isinstance(brands, list)
            assert "Test Brand" in brands
            assert "Another Brand" in brands
            assert brands == sorted(brands)  # Should be sorted

            # Clean up
            app.dependency_overrides.clear()

    def test_get_speaker_list_success(
        self, client: TestClient, mock_metadata: Dict[str, Any]
    ) -> None:
        """Test successful speaker list retrieval."""
        with patch("src.api.main.load_metadata") as mock_load:
            mock_load.return_value = mock_metadata

            app.dependency_overrides[load_metadata] = lambda: mock_metadata

            response = client.get("/v1/speakers")

            assert response.status_code == 200
            speakers = response.json()
            assert isinstance(speakers, list)
            assert "Test Speaker 1" in speakers
            assert "Test Speaker 2" in speakers
            assert speakers == sorted(speakers)  # Should be sorted

            app.dependency_overrides.clear()

    def test_get_speaker_metadata_success(
        self, client: TestClient, mock_metadata: Dict[str, Any]
    ) -> None:
        """Test successful speaker metadata retrieval."""
        with patch("src.api.main.load_metadata") as mock_load:
            mock_load.return_value = mock_metadata

            app.dependency_overrides[load_metadata] = lambda: mock_metadata

            response = client.get("/v1/speaker/Test Speaker 1/metadata")

            assert response.status_code == 200
            data = response.json()
            assert data["brand"] == "Test Brand"
            assert "measurements" in data

            app.dependency_overrides.clear()

    def test_get_speaker_metadata_not_found(
        self, client: TestClient, mock_metadata: Dict[str, Any]
    ) -> None:
        """Test speaker metadata retrieval for non-existent speaker."""
        with patch("src.api.main.load_metadata") as mock_load:
            mock_load.return_value = mock_metadata

            app.dependency_overrides[load_metadata] = lambda: mock_metadata

            response = client.get("/v1/speaker/Non Existent Speaker/metadata")

            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert data["error"] == "Speaker not found"

            app.dependency_overrides.clear()

    def test_get_speaker_versions_success(
        self, client: TestClient, mock_metadata: Dict[str, Any]
    ) -> None:
        """Test successful speaker versions retrieval."""
        with patch("src.api.main.load_metadata") as mock_load:
            mock_load.return_value = mock_metadata

            app.dependency_overrides[load_metadata] = lambda: mock_metadata

            response = client.get("/v1/speaker/Test Speaker 1/versions")

            assert response.status_code == 200
            versions = response.json()
            assert isinstance(versions, list)
            assert "version1" in versions
            assert "version2" in versions

            app.dependency_overrides.clear()

    def test_get_speaker_versions_empty_name(
        self, client: TestClient, mock_metadata: Dict[str, Any]
    ) -> None:
        """Test speaker versions with empty speaker name."""
        with patch("src.api.main.load_metadata") as mock_load:
            mock_load.return_value = mock_metadata

            app.dependency_overrides[load_metadata] = lambda: mock_metadata

            response = client.get("/v1/speaker/ /versions")

            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            # The actual API checks if speaker is in database first, so it returns "not in our database"
            assert "is not in our database" in data["error"]

            app.dependency_overrides.clear()

    def test_get_speaker_versions_not_found(
        self, client: TestClient, mock_metadata: Dict[str, Any]
    ) -> None:
        """Test speaker versions for non-existent speaker."""
        with patch("src.api.main.load_metadata") as mock_load:
            mock_load.return_value = mock_metadata

            app.dependency_overrides[load_metadata] = lambda: mock_metadata

            response = client.get("/v1/speaker/Non Existent/versions")

            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert "is not in our database" in data["error"]

            app.dependency_overrides.clear()

    def test_get_speaker_versions_no_measurements(self, client: TestClient) -> None:
        """Test speaker versions when measurements is not a dict."""
        bad_metadata = {"Test Speaker": {"brand": "Test Brand", "measurements": "not_a_dict"}}

        with patch("src.api.main.load_metadata") as mock_load:
            mock_load.return_value = bad_metadata

            app.dependency_overrides[load_metadata] = lambda: bad_metadata

            response = client.get("/v1/speaker/Test Speaker/versions")

            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert "No measurement found" in data["error"]

            app.dependency_overrides.clear()

    @patch("src.api.main.speakers_info")
    @patch("os.path.exists")
    @patch("src.api.main.glob")
    def test_get_speaker_measurements_success(
        self, mock_glob: Mock, mock_exists: Mock, mock_speakers_info: Mock, client: TestClient
    ) -> None:
        """Test successful speaker measurements retrieval."""
        mock_speakers_info.__contains__ = Mock(return_value=True)
        mock_speakers_info.__getitem__ = Mock(
            return_value={"measurements": {"version1": {"origin": "TestOrigin"}}}
        )

        mock_exists.return_value = True
        mock_glob.return_value = [
            "/path/CEA2034.json",
            "/path/On Axis.png",
            "/path/SPL Horizontal.webp",
        ]

        response = client.get("/v1/speaker/Test Speaker/version/version1/measurements")

        assert response.status_code == 200
        measurements = response.json()
        assert isinstance(measurements, list)
        assert "CEA2034" in measurements
        assert "On Axis" in measurements
        assert "SPL Horizontal" in measurements

    @patch("src.api.main.speakers_info")
    def test_get_speaker_measurements_empty_name(
        self, mock_speakers_info: Mock, client: TestClient
    ) -> None:
        """Test speaker measurements with empty speaker name."""
        mock_speakers_info.__contains__ = Mock(return_value=False)

        response = client.get("/v1/speaker/ /version/v1/measurements")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        # The actual API checks if speaker is in database first
        assert "is not in our database" in data["error"]

    @patch("src.api.main.speakers_info")
    def test_get_speaker_measurements_not_in_db(
        self, mock_speakers_info: Mock, client: TestClient
    ) -> None:
        """Test speaker measurements for speaker not in database."""
        mock_speakers_info.__contains__ = Mock(return_value=False)

        response = client.get("/v1/speaker/Unknown Speaker/version/v1/measurements")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "is not in our database" in data["error"]

    @patch("src.api.main.speakers_info")
    def test_get_speaker_measurements_invalid_version(
        self, mock_speakers_info: Mock, client: TestClient
    ) -> None:
        """Test speaker measurements with invalid version containing slash."""
        mock_speakers_info.__contains__ = Mock(return_value=True)

        # This URL path will result in a 404 because FastAPI routing doesn't match
        response = client.get("/v1/speaker/Test Speaker/version/v1/invalid/measurements")

        assert response.status_code == 404

    @patch("src.api.main.speakers_info")
    @patch("os.path.exists")
    @patch("src.api.main.open", new_callable=mock_open, read_data='["test", "data"]')
    def test_get_speaker_measurements_data_json(
        self, mock_file: Mock, mock_exists: Mock, mock_speakers_info: Mock, client: TestClient
    ) -> None:
        """Test successful speaker measurement data retrieval in JSON format."""
        mock_speakers_info.__contains__ = Mock(return_value=True)
        mock_speakers_info.__getitem__ = Mock(
            return_value={"measurements": {"version1": {"origin": "TestOrigin"}}}
        )

        mock_exists.return_value = True

        response = client.get(
            "/v1/speaker/Test Speaker/version/version1/measurements/CEA2034?measurement_format=json"
        )

        assert response.status_code == 200

    @patch("src.api.main.speakers_info")
    @patch("os.path.exists")
    def test_get_speaker_measurements_data_file_not_found(
        self, mock_exists: Mock, mock_speakers_info: Mock, client: TestClient
    ) -> None:
        """Test speaker measurement data when file doesn't exist."""
        mock_speakers_info.__contains__ = Mock(return_value=True)
        mock_speakers_info.__getitem__ = Mock(
            return_value={"measurements": {"version1": {"origin": "TestOrigin"}}}
        )

        # Directory exists but file doesn't
        mock_exists.side_effect = lambda path: "speakers" in path and not path.endswith(".json")

        response = client.get(
            "/v1/speaker/Test Speaker/version/version1/measurements/CEA2034?measurement_format=json"
        )

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "does not have precomputed" in data["error"]

    def test_get_speaker_measurements_data_invalid_measurement(self, client: TestClient) -> None:
        """Test speaker measurement data with invalid measurement name."""
        with patch("src.api.main.speakers_info") as mock_speakers_info:
            mock_speakers_info.__contains__ = Mock(return_value=True)
            mock_speakers_info.__getitem__ = Mock(
                return_value={"measurements": {"version1": {"origin": "TestOrigin"}}}
            )

            with patch("os.path.exists", return_value=True):
                response = client.get(
                    "/v1/speaker/Test Speaker/version/version1/measurements/Invalid Measurement?measurement_format=json"
                )

                assert response.status_code == 200
                data = response.json()
                assert "error" in data
                assert "is not known" in data["error"]

    def test_get_speaker_measurements_data_invalid_format(self, client: TestClient) -> None:
        """Test speaker measurement data with invalid format."""
        with patch("src.api.main.speakers_info") as mock_speakers_info:
            mock_speakers_info.__contains__ = Mock(return_value=True)
            mock_speakers_info.__getitem__ = Mock(
                return_value={"measurements": {"version1": {"origin": "TestOrigin"}}}
            )

            with patch("os.path.exists", return_value=True):
                # FastAPI validates query parameters and returns 422 for invalid values
                response = client.get(
                    "/v1/speaker/Test Speaker/version/version1/measurements/CEA2034?measurement_format=invalid"
                )

                assert response.status_code == 422

    @patch("src.api.main.METADATA", "/tmp/test_metadata.json")
    @patch("os.path.exists")
    def test_load_metadata_file_not_found(self, mock_exists: Mock) -> None:
        """Test load_metadata when file doesn't exist."""
        mock_exists.return_value = False

        with pytest.raises(SystemExit):
            list(load_metadata())

    @patch("src.api.main.METADATA", "/tmp/test_metadata.json")
    @patch("os.path.exists")
    def test_load_metadata_success(self, mock_exists: Mock) -> None:
        """Test successful metadata loading."""
        mock_exists.return_value = True
        test_data = {"test": "data"}

        with patch("builtins.open", mock_open(read_data=json.dumps(test_data))):
            result = list(load_metadata())
            assert len(result) == 1
            assert result[0] == test_data
