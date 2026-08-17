# -*- coding: utf-8 -*-
"""Tests for the Spinorama API endpoints."""

import json
from unittest.mock import Mock, patch, mock_open

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, load_metadata


MOCK_METADATA = {
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
def client() -> TestClient:
    """Create a test client with metadata dependency overridden."""
    app.dependency_overrides[load_metadata] = lambda: MOCK_METADATA
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestBrands:
    def test_get_brand_list(self, client: TestClient) -> None:
        response = client.get("/v1/brands")
        assert response.status_code == 200
        brands = response.json()
        assert isinstance(brands, list)
        assert "Test Brand" in brands
        assert "Another Brand" in brands
        assert brands == sorted(brands)


class TestSpeakers:
    def test_get_speaker_list(self, client: TestClient) -> None:
        response = client.get("/v1/speakers")
        assert response.status_code == 200
        speakers = response.json()
        assert isinstance(speakers, list)
        assert "Test Speaker 1" in speakers
        assert "Test Speaker 2" in speakers
        assert speakers == sorted(speakers)

    def test_get_speaker_list_returns_all(self, client: TestClient) -> None:
        """Every speaker in metadata must appear in /speakers."""
        response = client.get("/v1/speakers")
        speakers = response.json()
        for name in MOCK_METADATA:
            assert name in speakers


class TestSpeakerMetadata:
    def test_success(self, client: TestClient) -> None:
        response = client.get("/v1/speaker/Test Speaker 1/metadata")
        assert response.status_code == 200
        data = response.json()
        assert data["brand"] == "Test Brand"
        assert "measurements" in data

    def test_not_found(self, client: TestClient) -> None:
        response = client.get("/v1/speaker/Non Existent Speaker/metadata")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"] == "Speaker not found"


class TestSpeakerVersions:
    def test_success(self, client: TestClient) -> None:
        response = client.get("/v1/speaker/Test Speaker 1/versions")
        assert response.status_code == 200
        versions = response.json()
        assert isinstance(versions, list)
        assert "version1" in versions
        assert "version2" in versions

    def test_not_found(self, client: TestClient) -> None:
        response = client.get("/v1/speaker/Non Existent/versions")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "is not in our database" in data["error"]

    def test_no_measurements_dict(self) -> None:
        """Measurements field is not a dict."""
        bad_metadata = {"Bad Speaker": {"brand": "X", "measurements": "not_a_dict"}}
        app.dependency_overrides[load_metadata] = lambda: bad_metadata
        client = TestClient(app)
        response = client.get("/v1/speaker/Bad Speaker/versions")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "No measurement found" in data["error"]
        app.dependency_overrides.clear()


class TestSpeakerMeasurements:
    """Tests for GET /v1/speaker/{name}/version/{version}/measurements.

    This endpoint now uses the same metadata source as /speakers and /versions,
    ensuring a speaker listed in /speakers is always findable here.
    """

    @patch("src.api.routers.speaker.glob")
    @patch("os.path.exists", return_value=True)
    def test_success(self, mock_exists: Mock, mock_glob: Mock, client: TestClient) -> None:
        mock_glob.return_value = [
            "/path/CEA2034.json",
            "/path/On Axis.png",
            "/path/SPL Horizontal.webp",
        ]
        response = client.get("/v1/speaker/Test Speaker 1/version/version1/measurements")
        assert response.status_code == 200
        measurements = response.json()
        assert isinstance(measurements, list)
        assert "CEA2034" in measurements
        assert "On Axis" in measurements
        assert "SPL Horizontal" in measurements

    def test_speaker_not_found(self, client: TestClient) -> None:
        response = client.get("/v1/speaker/Unknown Speaker/version/v1/measurements")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "is not in our database" in data["error"]

    def test_version_not_found(self, client: TestClient) -> None:
        """Known speaker but unknown version returns an error with valid keys."""
        response = client.get("/v1/speaker/Test Speaker 1/version/bad_version/measurements")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "is not known" in data["error"]
        assert "version1" in data["error"]

    @patch("os.path.exists", return_value=False)
    def test_no_precomputed_dir(self, mock_exists: Mock, client: TestClient) -> None:
        response = client.get("/v1/speaker/Test Speaker 1/version/version1/measurements")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "does not have precomputed" in data["error"]

    def test_vendor_origin_prefix_stripped(self, client: TestClient) -> None:
        """Version with 'Vendors-' origin prefix should strip it for path lookup."""
        with (
            patch("os.path.exists") as mock_exists,
            patch("src.api.routers.speaker.glob", return_value=["/path/CEA2034.json"]),
        ):
            mock_exists.return_value = True
            response = client.get("/v1/speaker/Test Speaker 1/version/version2/measurements")
            assert response.status_code == 200
            # Verify the glob was called with stripped origin
            from src.api.main import SPINFILES

            mock_exists.assert_any_call(f"{SPINFILES}/Test Speaker 1/TestVendor/version2")


class TestSpeakerMeasurementsData:
    """Tests for GET /v1/speaker/{name}/version/{version}/measurements/{measurement}."""

    @patch("os.path.exists", return_value=True)
    def test_json_success(self, mock_exists: Mock, client: TestClient) -> None:
        with patch("builtins.open", mock_open(read_data='[{"freq": 100, "dB": -3.0}]')):
            response = client.get(
                "/v1/speaker/Test Speaker 1/version/version1/measurements/CEA2034"
            )
            assert response.status_code == 200

    def test_speaker_not_found(self, client: TestClient) -> None:
        response = client.get("/v1/speaker/Unknown/version/v1/measurements/CEA2034")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "is not in our database" in data["error"]

    def test_version_not_found(self, client: TestClient) -> None:
        response = client.get("/v1/speaker/Test Speaker 1/version/bad/measurements/CEA2034")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "is not known" in data["error"]

    @patch("os.path.exists", return_value=True)
    def test_invalid_measurement_name(self, mock_exists: Mock, client: TestClient) -> None:
        response = client.get(
            "/v1/speaker/Test Speaker 1/version/version1/measurements/Bogus Measurement"
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "is not known" in data["error"]

    @patch("os.path.exists", return_value=True)
    def test_invalid_format(self, mock_exists: Mock, client: TestClient) -> None:
        response = client.get(
            "/v1/speaker/Test Speaker 1/version/version1/measurements/CEA2034?measurement_format=invalid"
        )
        # FastAPI validates max_length=5, "invalid" is 7 chars → 422
        assert response.status_code == 422

    @patch("os.path.exists")
    def test_file_not_found(self, mock_exists: Mock, client: TestClient) -> None:
        # Directory exists but measurement file doesn't
        mock_exists.side_effect = lambda path: not path.endswith(".json") and "speakers" in path
        response = client.get("/v1/speaker/Test Speaker 1/version/version1/measurements/CEA2034")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "does not have precomputed" in data["error"]


class TestConsistency:
    """All endpoints must use the same metadata source.

    A speaker returned by /speakers must be recognized by /versions and
    /measurements — this was the bug where /measurements used a stale
    speakers_info dict while /speakers used metadata.json.
    """

    def test_speakers_found_in_versions(self, client: TestClient) -> None:
        """Every speaker from /speakers must be recognized by /versions."""
        speakers = client.get("/v1/speakers").json()
        for name in speakers:
            resp = client.get(f"/v1/speaker/{name}/versions")
            data = resp.json()
            assert isinstance(data, list), (
                f"Speaker '{name}' listed in /speakers but /versions returned error: {data}"
            )

    @patch("src.api.routers.speaker.glob", return_value=["/path/CEA2034.json"])
    @patch("os.path.exists", return_value=True)
    def test_speakers_found_in_measurements(
        self, mock_exists: Mock, mock_glob: Mock, client: TestClient
    ) -> None:
        """Every speaker+version from /versions must be recognized by /measurements."""
        speakers = client.get("/v1/speakers").json()
        for name in speakers:
            versions = client.get(f"/v1/speaker/{name}/versions").json()
            assert isinstance(versions, list)
            for version in versions:
                resp = client.get(f"/v1/speaker/{name}/version/{version}/measurements")
                data = resp.json()
                assert isinstance(data, list), (
                    f"Speaker '{name}' version '{version}' returned error from "
                    f"/measurements: {data}"
                )


class TestSpeakerMeasurementsPathTraversal:
    """Path-injection defences for the measurements list endpoint."""

    def test_speaker_name_with_dotdot_rejected(self, client: TestClient) -> None:
        # %2E%2E is decoded to '..' inside the path parameter.
        response = client.get("/v1/speaker/Evil%2E%2ESpeaker/version/v1/measurements")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Invalid" in data["error"]


class TestSpeakerMeasurementsDataPathTraversal:
    """Path-injection defences for the measurement data endpoint."""

    def test_speaker_name_with_dotdot_rejected(self, client: TestClient) -> None:
        response = client.get("/v1/speaker/Evil%2E%2ESpeaker/version/v1/measurements/CEA2034")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Invalid" in data["error"]

    def test_version_with_dotdot_rejected(self, client: TestClient) -> None:
        response = client.get("/v1/speaker/Test Speaker 1/version/%2E%2Ev1/measurements/CEA2034")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Invalid" in data["error"]

    def test_measurement_with_dotdot_rejected(self, client: TestClient) -> None:
        response = client.get(
            "/v1/speaker/Test Speaker 1/version/version1/measurements/%2E%2ECEA2034"
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Invalid" in data["error"]


class TestSafeSegment:
    """Unit tests for ``src.api.state.safe_segment``."""

    def test_valid_segments(self) -> None:
        from src.api.state import safe_segment

        assert safe_segment("Test Speaker 1") is True
        assert safe_segment("version1") is True
        assert safe_segment("CEA2034") is True
        assert safe_segment(".hidden") is True

    def test_rejects_empty(self) -> None:
        from src.api.state import safe_segment

        assert safe_segment("") is False

    def test_rejects_dot_and_dotdot(self) -> None:
        from src.api.state import safe_segment

        assert safe_segment(".") is False
        assert safe_segment("..") is False

    def test_rejects_separators(self) -> None:
        from src.api.state import safe_segment

        assert safe_segment("a/b") is False
        assert safe_segment("a\\b") is False

    def test_rejects_dotdot_anywhere(self) -> None:
        from src.api.state import safe_segment

        assert safe_segment("a..b") is False

    def test_rejects_null_byte(self) -> None:
        from src.api.state import safe_segment

        assert safe_segment("a\x00b") is False


class TestSafePath:
    """Unit tests for ``src.api.state.safe_path``."""

    def test_valid_path_inside_base(self) -> None:
        from src.api.state import safe_path

        result = safe_path("/var/www/html", "speakers", "Test Speaker 1")
        assert result == "/var/www/html/speakers/Test Speaker 1"

    def test_rejects_traversal(self) -> None:
        from src.api.state import safe_path

        assert safe_path("/var/www/html", "..", "etc") is None
        assert safe_path("/var/www/html", "speakers", "..", "etc") is None

    def test_rejects_absolute_path(self) -> None:
        from src.api.state import safe_path

        assert safe_path("/var/www/html", "/etc/passwd") is None

    def test_base_alone_is_valid(self) -> None:
        from src.api.state import safe_path

        assert safe_path("/var/www/html") == "/var/www/html"


class TestLoadMetadata:
    @patch("src.api.state.METADATA", "/tmp/test_metadata.json")
    @patch("os.path.exists", return_value=False)
    def test_file_not_found(self, mock_exists: Mock) -> None:
        with pytest.raises(SystemExit):
            list(load_metadata())

    @patch("src.api.state.METADATA", "/tmp/test_metadata.json")
    @patch("os.path.exists", return_value=True)
    def test_success(self, mock_exists: Mock) -> None:
        test_data = {"test": "data"}
        with patch("builtins.open", mock_open(read_data=json.dumps(test_data))):
            result = list(load_metadata())
            assert len(result) == 1
            assert result[0] == test_data
