# -*- coding: utf-8 -*-
"""Validation functions for speaker metadata."""

import logging
from typing import List, Dict, Any
from datas import Speaker, Measurement

# Valid values for validation
VALID_AMOUNTS = ("each", "pair")
VALID_TYPES = ("active", "passive")
VALID_SHAPES = (
    "floorstanders",
    "bookshelves",
    "center",
    "surround",
    "omnidirectional",
    "columns",
    "cbt",
    "outdoor",
    "panel",
    "inwall",
    "soundbar",
    "liveportable",
    "toursound",
    "cinema",
)
VALID_FORMATS = (
    "klippel",
    "webplotdigitizer",
    "spl_hv_txt",
    "gll_hv_txt",
    "princeton",
    "rew_text_dump",
)
VALID_QUALITIES = ("low", "medium", "high", "unknown")


class ValidationResult:
    """Container for validation results."""

    def __init__(self):
        self.valid = True
        self.messages: List[str] = []

    def add_error(self, message: str):
        """Add an error message."""
        self.valid = False
        self.messages.append(f"ERROR: {message}")

    def add_warning(self, message: str):
        """Add a warning message."""
        self.messages.append(f"WARNING: {message}")


def validate_brand(name: str, speaker: Dict[str, Any], result: ValidationResult) -> None:
    """Validate speaker brand."""
    if "brand" not in speaker:
        result.add_error(f"Brand is missing for {name}")
        return

    brand = speaker["brand"]
    if not brand:
        result.add_error(f"Brand is empty for {name}")
        return

    if not name.startswith(brand):
        result.add_error(f"{name} doesn't start with brand {brand}")

    if brand.endswith(" "):
        result.add_warning(f"Suspicious space at the end of brand '{brand}' for {name}")


def validate_model(name: str, speaker: Dict[str, Any], result: ValidationResult) -> None:
    """Validate speaker model."""
    if "model" not in speaker:
        result.add_error(f"Model is missing for {name}")
        return

    brand = speaker.get("brand", "")
    model = speaker["model"]

    if not model:
        result.add_error(f"Model is empty for {name}")
        return

    # Check if model starts with brand (usually not desired)
    model_parts = model.split(" ")
    if len(model_parts) > 0 and model_parts[0] == brand:
        result.add_warning(f"Model '{model}' starts with brand '{brand}' for {name}")

    # Check if name ends with model
    if not name.endswith(model):
        result.add_error(f"{name} doesn't end with model {model}")

    if model.startswith(" "):
        result.add_warning(f"Suspicious space at the beginning of model '{model}' for {name}")


def validate_type(name: str, speaker: Dict[str, Any], result: ValidationResult) -> None:
    """Validate speaker type."""
    if "type" not in speaker:
        result.add_error(f"Type is missing for {name}")
        return

    speaker_type = speaker["type"]
    if speaker_type not in VALID_TYPES:
        result.add_error(
            f"Invalid type '{speaker_type}' for {name}. Valid types: {', '.join(VALID_TYPES)}"
        )


def validate_shape(name: str, speaker: Dict[str, Any], result: ValidationResult) -> None:
    """Validate speaker shape."""
    if "shape" not in speaker:
        result.add_error(f"Shape is missing for {name}")
        return

    shape = speaker["shape"]
    if shape not in VALID_SHAPES:
        result.add_error(
            f"Invalid shape '{shape}' for {name}. Valid shapes: {', '.join(VALID_SHAPES)}"
        )


def validate_amount(name: str, speaker: Dict[str, Any], result: ValidationResult) -> None:
    """Validate speaker amount."""
    if "amount" in speaker:
        amount = speaker["amount"]
        if amount not in VALID_AMOUNTS:
            result.add_error(
                f"Invalid amount '{amount}' for {name}. Valid amounts: {', '.join(VALID_AMOUNTS)}"
            )


def validate_measurements(name: str, speaker: Dict[str, Any], result: ValidationResult) -> None:
    """Validate speaker measurements."""
    if "measurements" not in speaker:
        result.add_error(f"Measurements are missing for {name}")
        return

    measurements = speaker["measurements"]
    if not isinstance(measurements, dict):
        result.add_error(f"Measurements must be a dictionary for {name}")
        return

    if not measurements:
        result.add_error(f"At least one measurement is required for {name}")
        return

    # Validate default measurement
    default_measurement = speaker.get("default_measurement")
    if not default_measurement:
        result.add_error(f"Default measurement is missing for {name}")
    elif default_measurement not in measurements:
        result.add_error(
            f"Default measurement '{default_measurement}' not found in measurements for {name}"
        )

    # Validate each measurement
    for measurement_key, measurement_data in measurements.items():
        validate_measurement(name, measurement_key, measurement_data, result)


def validate_measurement(
    name: str, measurement_key: str, measurement: Dict[str, Any], result: ValidationResult
) -> None:
    """Validate a single measurement."""
    # Required fields
    if "origin" not in measurement:
        result.add_error(f"Origin is missing for measurement '{measurement_key}' in {name}")
    elif not measurement["origin"]:
        result.add_error(f"Origin is empty for measurement '{measurement_key}' in {name}")

    if "format" not in measurement:
        result.add_error(f"Format is missing for measurement '{measurement_key}' in {name}")
    elif measurement["format"] not in VALID_FORMATS:
        result.add_error(
            f"Invalid format '{measurement['format']}' for measurement '{measurement_key}' in {name}. Valid formats: {', '.join(VALID_FORMATS)}"
        )

    # Optional fields validation
    if "quality" in measurement and measurement["quality"] not in VALID_QUALITIES:
        result.add_error(
            f"Invalid quality '{measurement['quality']}' for measurement '{measurement_key}' in {name}. Valid qualities: {', '.join(VALID_QUALITIES)}"
        )


def validate_speaker_data(speaker_name: str, speaker_data: Dict[str, Any]) -> ValidationResult:
    """
    Validate complete speaker data.

    Args:
        speaker_name: The name/key of the speaker
        speaker_data: The speaker data dictionary

    Returns:
        ValidationResult with validation status and messages
    """
    result = ValidationResult()

    try:
        # Basic structure validation
        if not isinstance(speaker_data, dict):
            result.add_error("Speaker data must be a dictionary")
            return result

        # Validate required fields
        validate_brand(speaker_name, speaker_data, result)
        validate_model(speaker_name, speaker_data, result)
        validate_type(speaker_name, speaker_data, result)
        validate_shape(speaker_name, speaker_data, result)

        # Validate optional fields
        validate_amount(speaker_name, speaker_data, result)
        validate_measurements(speaker_name, speaker_data, result)

    except Exception as e:
        result.add_error(f"Validation error: {str(e)}")

    return result


def validate_speaker_database(speakers: Dict[str, Dict[str, Any]]) -> ValidationResult:
    """
    Validate an entire speaker database.

    Args:
        speakers: Dictionary of speaker data

    Returns:
        ValidationResult with validation status and messages
    """
    result = ValidationResult()

    for speaker_name, speaker_data in speakers.items():
        speaker_result = validate_speaker_data(speaker_name, speaker_data)

        # Merge results
        if not speaker_result.valid:
            result.valid = False

        result.messages.extend(speaker_result.messages)

    return result
