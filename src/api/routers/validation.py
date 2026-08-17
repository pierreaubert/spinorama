# -*- coding: utf-8 -*-
"""Speaker-metadata validation endpoint."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request

from ..state import API_VERSION

from datas.checks import validate_speaker_data


router = APIRouter(prefix=f"/{API_VERSION}", tags=["validation"])


@router.post("/validate")
async def validate_speaker_metadata(request: Request):
    """Validate speaker metadata according to Spinorama standards."""
    try:
        speaker_data = await request.json()

        brand = speaker_data.get("brand", "Unknown")
        model = speaker_data.get("model", "Unknown")
        speaker_name = f"{brand} {model}"

        validation_result = validate_speaker_data(speaker_name, speaker_data)

        return {
            "valid": validation_result.valid,
            "messages": validation_result.messages,
            "speaker_name": speaker_name,
        }

    except json.JSONDecodeError:
        return {
            "valid": False,
            "messages": ["ERROR: Invalid JSON format"],
            "speaker_name": "Unknown",
        }
    except Exception as e:
        return {
            "valid": False,
            "messages": [f"ERROR: Validation failed - {e!s}"],
            "speaker_name": "Unknown",
        }
