#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for datas.checks module."""

import pytest
from typing import Dict, Any

from datas.checks import (
    ValidationResult,
    validate_impedance,
    validate_sensitivity,
    validate_measurement,
    validate_speaker_data,
    validate_speaker_database,
    IMPEDANCE_MIN,
    IMPEDANCE_MAX,
    SENSITIVITY_MIN,
    SENSITIVITY_MAX,
)


class TestValidationResult:
    """Test ValidationResult class."""

    def test_init(self):
        """Test ValidationResult initialization."""
        result = ValidationResult()
        assert result.valid is True
        assert result.messages == []

    def test_add_error(self):
        """Test adding error messages."""
        result = ValidationResult()
        result.add_error("Test error")
        assert result.valid is False
        assert result.messages == ["ERROR: Test error"]

    def test_add_warning(self):
        """Test adding warning messages."""
        result = ValidationResult()
        result.add_warning("Test warning")
        assert result.valid is True  # Warnings don't invalidate
        assert result.messages == ["WARNING: Test warning"]

    def test_multiple_messages(self):
        """Test adding multiple messages."""
        result = ValidationResult()
        result.add_warning("Warning 1")
        result.add_error("Error 1")
        result.add_warning("Warning 2")
        
        assert result.valid is False
        assert len(result.messages) == 3
        assert "WARNING: Warning 1" in result.messages
        assert "ERROR: Error 1" in result.messages
        assert "WARNING: Warning 2" in result.messages


class TestValidateImpedance:
    """Test impedance validation."""

    def test_valid_impedance_values(self):
        """Test valid impedance values."""
        result = ValidationResult()
        
        # Test common valid values
        for impedance in [4.0, 6.0, 8.0, 16.0, 2.0]:
            validate_impedance("Test Speaker", "test_measurement", impedance, result)
        
        assert result.valid is True
        assert len(result.messages) == 0

    def test_invalid_impedance_too_low(self):
        """Test impedance values that are too low."""
        result = ValidationResult()
        validate_impedance("Test Speaker", "test_measurement", 1.0, result)
        
        assert result.valid is True  # Warnings don't invalidate
        assert len(result.messages) == 1
        assert "WARNING:" in result.messages[0]
        assert "Unlikely impedance value 1.0Ω" in result.messages[0]
        assert f"Expected range: {IMPEDANCE_MIN}-{IMPEDANCE_MAX}Ω" in result.messages[0]

    def test_invalid_impedance_too_high(self):
        """Test impedance values that are too high."""
        result = ValidationResult()
        validate_impedance("Test Speaker", "test_measurement", 32.0, result)
        
        assert result.valid is True  # Warnings don't invalidate
        assert len(result.messages) == 1
        assert "WARNING:" in result.messages[0]
        assert "Unlikely impedance value 32.0Ω" in result.messages[0]

    def test_impedance_non_numeric(self):
        """Test non-numeric impedance values."""
        result = ValidationResult()
        validate_impedance("Test Speaker", "test_measurement", "not_a_number", result)
        
        assert result.valid is False
        assert len(result.messages) == 1
        assert "ERROR:" in result.messages[0]
        assert "Impedance must be a number" in result.messages[0]

    def test_impedance_edge_cases(self):
        """Test impedance edge cases."""
        result = ValidationResult()
        
        # Test exact boundaries
        validate_impedance("Test Speaker", "test_measurement", IMPEDANCE_MIN, result)
        validate_impedance("Test Speaker", "test_measurement", IMPEDANCE_MAX, result)
        
        assert result.valid is True
        assert len(result.messages) == 0


class TestValidateSensitivity:
    """Test sensitivity validation."""

    def test_valid_sensitivity_values(self):
        """Test valid sensitivity values."""
        result = ValidationResult()
        
        # Test common valid values
        for sensitivity in [85.0, 88.0, 92.0, 95.0, 100.0]:
            validate_sensitivity("Test Speaker", "test_measurement", sensitivity, result)
        
        assert result.valid is True
        assert len(result.messages) == 0

    def test_invalid_sensitivity_too_low(self):
        """Test sensitivity values that are too low."""
        result = ValidationResult()
        validate_sensitivity("Test Speaker", "test_measurement", 60.0, result)
        
        assert result.valid is True  # Warnings don't invalidate
        assert len(result.messages) == 1
        assert "WARNING:" in result.messages[0]
        assert "Unlikely sensitivity value 60.0dB" in result.messages[0]
        assert f"Expected range: {SENSITIVITY_MIN}-{SENSITIVITY_MAX}dB" in result.messages[0]

    def test_invalid_sensitivity_too_high(self):
        """Test sensitivity values that are too high."""
        result = ValidationResult()
        validate_sensitivity("Test Speaker", "test_measurement", 130.0, result)
        
        assert result.valid is True  # Warnings don't invalidate
        assert len(result.messages) == 1
        assert "WARNING:" in result.messages[0]
        assert "Unlikely sensitivity value 130.0dB" in result.messages[0]

    def test_sensitivity_non_numeric(self):
        """Test non-numeric sensitivity values."""
        result = ValidationResult()
        validate_sensitivity("Test Speaker", "test_measurement", "not_a_number", result)
        
        assert result.valid is False
        assert len(result.messages) == 1
        assert "ERROR:" in result.messages[0]
        assert "Sensitivity must be a number" in result.messages[0]

    def test_sensitivity_edge_cases(self):
        """Test sensitivity edge cases."""
        result = ValidationResult()
        
        # Test exact boundaries
        validate_sensitivity("Test Speaker", "test_measurement", SENSITIVITY_MIN, result)
        validate_sensitivity("Test Speaker", "test_measurement", SENSITIVITY_MAX, result)
        
        assert result.valid is True
        assert len(result.messages) == 0


class TestValidateMeasurement:
    """Test measurement validation including impedance and sensitivity."""

    def test_measurement_with_valid_specifications(self):
        """Test measurement with valid impedance and sensitivity in specifications."""
        result = ValidationResult()
        measurement = {
            "origin": "Test Origin",
            "format": "klippel",
            "specifications": {
                "impedance": 8.0,
                "sensitivity": 88.0,
            }
        }
        
        validate_measurement("Test Speaker", "test_measurement", measurement, result)
        
        assert result.valid is True
        assert len(result.messages) == 0

    def test_measurement_with_invalid_specifications(self):
        """Test measurement with invalid impedance and sensitivity in specifications."""
        result = ValidationResult()
        measurement = {
            "origin": "Test Origin",
            "format": "klippel",
            "specifications": {
                "impedance": 1.0,  # Too low
                "sensitivity": 130.0,  # Too high
            }
        }
        
        validate_measurement("Test Speaker", "test_measurement", measurement, result)
        
        assert result.valid is True  # Warnings don't invalidate
        assert len(result.messages) == 2
        assert any("Unlikely impedance value 1.0Ω" in msg for msg in result.messages)
        assert any("Unlikely sensitivity value 130.0dB" in msg for msg in result.messages)

    def test_measurement_with_sensitivity_at_measurement_level(self):
        """Test measurement with sensitivity at measurement level."""
        result = ValidationResult()
        measurement = {
            "origin": "Test Origin",
            "format": "klippel",
            "sensitivity": 88.0,
        }
        
        validate_measurement("Test Speaker", "test_measurement", measurement, result)
        
        assert result.valid is True
        assert len(result.messages) == 0

    def test_measurement_with_invalid_sensitivity_at_measurement_level(self):
        """Test measurement with invalid sensitivity at measurement level."""
        result = ValidationResult()
        measurement = {
            "origin": "Test Origin",
            "format": "klippel",
            "sensitivity": 60.0,  # Too low
        }
        
        validate_measurement("Test Speaker", "test_measurement", measurement, result)
        
        assert result.valid is True  # Warnings don't invalidate
        assert len(result.messages) == 1
        assert "Unlikely sensitivity value 60.0dB" in result.messages[0]

    def test_measurement_without_specifications(self):
        """Test measurement without specifications (should not cause errors)."""
        result = ValidationResult()
        measurement = {
            "origin": "Test Origin",
            "format": "klippel",
        }
        
        validate_measurement("Test Speaker", "test_measurement", measurement, result)
        
        assert result.valid is True
        assert len(result.messages) == 0

    def test_measurement_with_non_dict_specifications(self):
        """Test measurement with non-dict specifications."""
        result = ValidationResult()
        measurement = {
            "origin": "Test Origin",
            "format": "klippel",
            "specifications": "not_a_dict",
        }
        
        validate_measurement("Test Speaker", "test_measurement", measurement, result)
        
        assert result.valid is True
        assert len(result.messages) == 0


class TestValidateSpeakerData:
    """Test complete speaker data validation."""

    def test_speaker_with_valid_impedance_and_sensitivity(self):
        """Test speaker with valid impedance and sensitivity values."""
        result = ValidationResult()
        speaker_data = {
            "brand": "Test Brand",
            "model": "Test Model",
            "type": "passive",
            "shape": "bookshelves",
            "default_measurement": "test_measurement",
            "measurements": {
                "test_measurement": {
                    "origin": "Test Origin",
                    "format": "klippel",
                    "specifications": {
                        "impedance": 8.0,
                        "sensitivity": 88.0,
                    }
                }
            }
        }
        
        result = validate_speaker_data("Test Brand Test Model", speaker_data)
        
        assert result.valid is True
        # Should have no warnings about impedance/sensitivity
        impedance_warnings = [msg for msg in result.messages if "impedance" in msg.lower()]
        sensitivity_warnings = [msg for msg in result.messages if "sensitivity" in msg.lower()]
        assert len(impedance_warnings) == 0
        assert len(sensitivity_warnings) == 0

    def test_speaker_with_invalid_impedance_and_sensitivity(self):
        """Test speaker with invalid impedance and sensitivity values."""
        result = ValidationResult()
        speaker_data = {
            "brand": "Test Brand",
            "model": "Test Model",
            "type": "passive",
            "shape": "bookshelves",
            "default_measurement": "test_measurement",
            "measurements": {
                "test_measurement": {
                    "origin": "Test Origin",
                    "format": "klippel",
                    "specifications": {
                        "impedance": 1.0,  # Too low
                        "sensitivity": 130.0,  # Too high
                    }
                }
            }
        }
        
        result = validate_speaker_data("Test Brand Test Model", speaker_data)
        
        assert result.valid is True  # Warnings don't invalidate
        impedance_warnings = [msg for msg in result.messages if "impedance" in msg.lower()]
        sensitivity_warnings = [msg for msg in result.messages if "sensitivity" in msg.lower()]
        assert len(impedance_warnings) == 1
        assert len(sensitivity_warnings) == 1


class TestValidateSpeakerDatabase:
    """Test complete speaker database validation."""

    def test_database_with_mixed_valid_invalid_values(self):
        """Test database with mix of valid and invalid impedance/sensitivity values."""
        speakers = {
            "Valid Speaker": {
                "brand": "Valid",
                "model": "Speaker",
                "type": "passive",
                "shape": "bookshelves",
                "default_measurement": "test_measurement",
                "measurements": {
                    "test_measurement": {
                        "origin": "Test Origin",
                        "format": "klippel",
                        "specifications": {
                            "impedance": 8.0,
                            "sensitivity": 88.0,
                        }
                    }
                }
            },
            "Invalid Speaker": {
                "brand": "Invalid",
                "model": "Speaker",
                "type": "passive",
                "shape": "bookshelves",
                "default_measurement": "test_measurement",
                "measurements": {
                    "test_measurement": {
                        "origin": "Test Origin",
                        "format": "klippel",
                        "specifications": {
                            "impedance": 0.5,  # Too low
                            "sensitivity": 140.0,  # Too high
                        }
                    }
                }
            }
        }
        
        result = validate_speaker_database(speakers)
        
        assert result.valid is True  # Warnings don't invalidate
        
        # Should have warnings for the invalid speaker
        impedance_warnings = [msg for msg in result.messages if "impedance" in msg.lower() and "0.5" in msg]
        sensitivity_warnings = [msg for msg in result.messages if "sensitivity" in msg.lower() and "140.0" in msg]
        assert len(impedance_warnings) == 1
        assert len(sensitivity_warnings) == 1


if __name__ == "__main__":
    pytest.main([__file__])
