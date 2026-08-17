# -*- coding: utf-8 -*-
"""Speaker-resource routes."""

from __future__ import annotations

import os
from glob import glob
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from starlette.responses import FileResponse, JSONResponse

from ..state import (
    API_VERSION,
    KNOWN_MEASUREMENTS,
    SPINFILES,
    load_metadata,
    safe_path,
    safe_segment,
)


router = APIRouter(prefix=f"/{API_VERSION}", tags=["speaker"])


def _vendor_stripped(origin: str) -> str:
    """Drop the ``Vendors-`` prefix that lives in metadata but not on disk."""
    return origin[8:] if origin.startswith("Vendors-") else origin


@router.get("/brands")
async def get_brand_list(metadata: dict = Depends(load_metadata)):  # noqa: B008
    return sorted({v.get("brand") for _, v in metadata.items()})


@router.get("/speakers")
async def get_speaker_list(metadata: dict = Depends(load_metadata)):  # noqa: B008
    return sorted(metadata.keys())


@router.get("/speaker/{speaker_name}/metadata")
async def get_speaker_metadata(
    speaker_name: str,
    metadata: dict = Depends(load_metadata),  # noqa: B008
):
    content = metadata.get(speaker_name, {"error": "Speaker not found"})
    return JSONResponse(content=jsonable_encoder(content))


@router.get("/speaker/{speaker_name}/versions")
async def get_speaker_versions(
    speaker_name: str,
    metadata: dict = Depends(load_metadata),  # noqa: B008
):
    if not speaker_name:
        return {"error": "Speaker name is mandatory"}

    if speaker_name not in metadata:
        return {"error": f"Speaker {speaker_name} is not in our database!"}

    if not isinstance(metadata[speaker_name]["measurements"], dict):
        return {"error": "No measurement found for speaker {speaker_name}!"}

    return list(metadata[speaker_name]["measurements"].keys())


@router.get("/speaker/{speaker_name}/version/{speaker_version}/measurements")
async def get_speaker_measurements(
    speaker_name: str,
    speaker_version: str,
    metadata: dict = Depends(load_metadata),  # noqa: B008
):
    if not speaker_name:
        return {"error": "Speaker name and measurement name are mandatory"}

    if not (safe_segment(speaker_name) and safe_segment(speaker_version)):
        return {
            "error": f"Invalid speaker_name {speaker_name} or speaker_version {speaker_version}!"
        }

    if speaker_name not in metadata:
        return {"error": f"Speaker {speaker_name} is not in our database!"}

    meta_data = metadata[speaker_name]

    if speaker_version not in meta_data["measurements"]:
        valid_keys = ", ".join(list(meta_data["measurements"].keys()))
        return {
            "error": f"Version {speaker_version} is not known for speaker {speaker_name}! Valid keys are ({valid_keys})."
        }

    origin = _vendor_stripped(meta_data["measurements"][speaker_version]["origin"])
    if not safe_segment(origin):
        return {"error": f"Invalid origin {origin}!"}

    upper_dir = safe_path(SPINFILES, speaker_name)
    if upper_dir is None:
        return {"error": f"Invalid path for speaker {speaker_name}!"}

    dir_data = safe_path(upper_dir, origin, speaker_version)
    if dir_data is None:
        return {
            "error": f"Speaker {speaker_name} does not have precomputed measurements for origin {origin} and version {speaker_version}!"
        }

    if not os.path.exists(upper_dir):
        return {"error": f"Speaker {speaker_name} does not have precomputed measurements!"}

    if not os.path.exists(dir_data):
        return {
            "error": f"Speaker {speaker_name} does not have precomputed measurements for origin {origin} and version {speaker_version}!"
        }

    m1 = [s.split("/")[-1] for s in glob(f"{dir_data}/*.*")]
    return sorted(set([s.split(".")[0] for s in m1]))


@router.get("/speaker/{speaker_name}/version/{speaker_version}/measurements/{measurement_name}")
async def get_speaker_measurements_data(
    speaker_name: str,
    speaker_version: str,
    measurement_name: str,
    measurement_format: Annotated[str | None, Query(max_length=5)] = "json",
    metadata: dict = Depends(load_metadata),  # noqa: B008
):
    if not speaker_name or not measurement_name:
        return {"error": "Speaker name and measurement name are mandatory"}

    if not (
        safe_segment(speaker_name)
        and safe_segment(speaker_version)
        and safe_segment(measurement_name)
    ):
        return {
            "error": f"Invalid speaker_name {speaker_name}, speaker_version {speaker_version} or measurement_name {measurement_name}!"
        }

    if speaker_name not in metadata:
        return {"error": f"Speaker {speaker_name} is not in our database!"}

    meta_data = metadata[speaker_name]

    if speaker_version not in meta_data["measurements"]:
        valid_keys = ", ".join(list(meta_data["measurements"].keys()))
        return {
            "error": f"Version {speaker_version} is not known for speaker {speaker_name}! Valid keys are ({valid_keys})."
        }

    origin = _vendor_stripped(meta_data["measurements"][speaker_version]["origin"])
    if not safe_segment(origin):
        return {"error": f"Invalid origin {origin}!"}

    upper_dir = safe_path(SPINFILES, speaker_name)
    if upper_dir is None:
        return {"error": f"Invalid path for speaker {speaker_name}!"}

    dir_data = safe_path(upper_dir, origin, speaker_version)
    if dir_data is None:
        return {
            "error": f"Speaker {speaker_name} does not have precomputed measurements for origin {origin} and version {speaker_version}!"
        }

    if not os.path.exists(upper_dir):
        return {"error": f"Speaker {speaker_name} does not have precomputed measurements!"}

    if not os.path.exists(dir_data):
        return {
            "error": f"Speaker {speaker_name} does not have precomputed measurements for origin {origin} and version {speaker_version}!"
        }

    if "_unmelted" in measurement_name:
        measurement_name = measurement_name[0:-9]

    if measurement_name not in KNOWN_MEASUREMENTS:
        return {
            "error": f"Version {measurement_name} is not known! Valid options are ({KNOWN_MEASUREMENTS})."
        }

    if measurement_format and measurement_format != "json":
        return {
            "error": f"Version {measurement_format} is not known! Only valid options is None or json."
        }

    file_name = f"{measurement_name}.{measurement_format}"
    if measurement_format == "png":
        file_name = f"{measurement_name}_large.{measurement_format}"

    measurement_file = safe_path(dir_data, file_name)
    if measurement_file is None:
        return {
            "error": f"Speaker {speaker_name} does not have precomputed {measurement_name} in format {measurement_format} for origin {origin} and version {speaker_version}!"
        }

    if not os.path.exists(measurement_file):
        return {
            "error": f"Speaker {speaker_name} does not have precomputed {measurement_name} in format {measurement_format} for origin {origin} and version {speaker_version}!"
        }

    if measurement_format == "json":
        with open(measurement_file, "r", encoding="utf8") as fd:
            return fd.readlines()

    if measurement_format in ("webp", "jpg", "png"):
        return FileResponse(measurement_file)

    return {"error": "fetching measurements failed format {measurement_format} is unknown!"}
