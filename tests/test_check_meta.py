"""Tests for the metadata checker script."""

from types import SimpleNamespace

from scripts.check_meta import validate_measurement_files
from spinorama._logging import logger, setup_logger


def _speaker() -> dict:
    return {
        "brand": "Test",
        "model": "Speaker",
        "shape": "bookshelves",
        "measurements": {
            "asr": {
                "origin": "ASR",
                "format": "klippel",
            }
        },
    }


def test_measurement_files_are_loaded(tmp_path) -> None:
    measurement_dir = tmp_path / "Test_Speaker" / "asr"
    measurement_dir.mkdir(parents=True)
    calls = []

    def loader(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(is_empty=lambda: False)

    result = validate_measurement_files({"Test|Speaker": _speaker()}, str(tmp_path), loader)

    assert result.valid is True
    assert result.messages == []
    assert calls[0]["speaker_name"] == "Test_Speaker"
    assert calls[0]["speaker_parameters"]["mversion"] == "asr"


def test_missing_measurement_directory_is_an_error(tmp_path) -> None:
    def loader(**kwargs):
        raise AssertionError("the loader must not run for a missing directory")

    result = validate_measurement_files({"Test Speaker": _speaker()}, str(tmp_path), loader)

    assert result.valid is False
    assert "Measurement directory is missing" in result.messages[0]


def test_skipped_speaker_does_not_require_measurement_files(tmp_path) -> None:
    speaker = _speaker()
    speaker["skip"] = True

    def loader(**kwargs):
        raise AssertionError("the loader must not run for a skipped speaker")

    result = validate_measurement_files({"Test Speaker": speaker}, str(tmp_path), loader)

    assert result.valid is True
    assert result.messages == []


def test_unloadable_measurement_is_an_error(tmp_path) -> None:
    (tmp_path / "Test Speaker" / "asr").mkdir(parents=True)

    def loader(**kwargs):
        setup_logger(path=str(tmp_path / "spinorama.log"))
        return SimpleNamespace(is_empty=lambda: True)

    result = validate_measurement_files({"Test Speaker": _speaker()}, str(tmp_path), loader)

    assert result.valid is False
    assert "could not be loaded" in result.messages[0]
    assert not [
        handler for handler in logger.handlers if getattr(handler, "_spinorama_handler", False)
    ]
