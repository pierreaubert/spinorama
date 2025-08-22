# -*- coding: utf-8 -*-
from glob import glob
import io
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Annotated
import yaml

from fastapi import FastAPI, Query, Depends
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse, FileResponse, Response

from datas.metadata import speakers_info

API_VERSION = "v1"
CURRENT_VERSION = 0
SOFTWARE_VERSION = f"{API_VERSION}.{CURRENT_VERSION}"

APIFILES = "/var/www/html/spinorama-api"
SPINFILES = "/var/www/html/spinorama-prod/speakers"
METADATA = f"{APIFILES}/assets/metadata.json"

KNOWN_MEASUREMENTS = set(
    [
        "CEA2034",
        "On Axis",
        "Estimated In-Room Response",
        "Early Reflections",
        "Horizontal Reflections",
        "Vertical Reflections",
        "SPL Horizontal",
        "SPL Horizontal Normalized",
        "SPL Vertical",
        "SPL Vertical Normalized",
        "SPL Horizontal Contour",
        "SPL Horizontal Contour Normalized",
        "SPL Vertical Contour",
        "SPL Vertical Contour Normalized",
        "SPL Horizontal Contour 3D",
        "SPL Horizontal Contour Normalized 3D",
        "SPL Vertical Contour 3D",
        "SPL Vertical Contour Normalized 3D",
        "SPL Horizontal Globe",
        "SPL Horizontal Globe Normalized",
        "SPL Vertical Globe",
        "SPL Vertical Globe Normalized",
        "SPL Horizontal Radar",
        "SPL Vertical Radar",
    ]
)

KNOWN_FORMATS = set(["jpeg", "jpg", "json", "png", "webp"])


# Global variable to store metadata
_metadata_cache = None


def load_metadata():
    """Load metadata for dependency injection."""
    global _metadata_cache
    if _metadata_cache is None:
        if not os.path.exists(METADATA):
            logging.error("Cannot find %s", METADATA)
            sys.exit(1)

        with open(METADATA, "r", encoding="utf8") as f:
            _metadata_cache = json.load(f)

    yield _metadata_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI startup/shutdown."""
    # Startup: Load metadata into cache
    global _metadata_cache
    if not os.path.exists(METADATA):
        logging.error("Cannot find %s", METADATA)
        sys.exit(1)

    with open(METADATA, "r", encoding="utf8") as f:
        _metadata_cache = json.load(f)

    yield

    # Shutdown: Clean up if needed
    _metadata_cache = None


app = FastAPI(
    debug=False,
    title="Spinorama API",
    version=SOFTWARE_VERSION,
    lifespan=lifespan,
)


@app.get(f"/{API_VERSION}/brands", tags=["speaker"])
async def get_brand_list(metadata: dict = Depends(load_metadata)):  # noqa: B008
    return sorted({v.get("brand") for _, v in metadata.items()})


@app.get(f"/{API_VERSION}/speakers", tags=["speaker"])
async def get_speaker_list(metadata: dict = Depends(load_metadata)):  # noqa: B008
    return sorted(metadata.keys())


@app.get(f"/{API_VERSION}/speaker/{{speaker_name}}/metadata", tags=["speaker"])
async def get_speaker_metadata(
    speaker_name: str,
    metadata: dict = Depends(load_metadata),  # noqa: B008
):
    content = metadata.get(speaker_name, {"error": "Speaker not found"})
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


@app.get(f"/{API_VERSION}/speaker/{{speaker_name}}/versions", tags=["speaker"])
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


@app.get(
    f"/{API_VERSION}/speaker/{{speaker_name}}/version/{{speaker_version}}/measurements",
    tags=["speaker"],
)
async def get_speaker_measurements(speaker_name: str, speaker_version: str):
    if not speaker_name:
        return {"error": "Speaker name and measurement name are mandatory"}

    if speaker_name not in speakers_info:
        return {"error": f"Speaker {speaker_name} is not in our database!"}

    if "/" in speaker_version or ".." in speaker_version:
        return {"error": f"Invalid speaker_version {speaker_version}!"}

    meta_data = speakers_info[speaker_name]

    if speaker_version not in meta_data["measurements"]:
        valid_keys = ", ".join(list(meta_data["measurements"].keys()))
        return {
            "error": f"Version {speaker_version} is not known for speaker {speaker_name}! Valid keys are ({valid_keys})."
        }

    origin = meta_data["measurements"][speaker_version]["origin"]
    if origin[0:8] == "Vendors-":
        origin = origin[8:]
    upper_dir = f"{SPINFILES}/{speaker_name}"
    dir_data = f"{upper_dir}/{origin}/{speaker_version}"

    if not os.path.exists(upper_dir):
        print(upper_dir)
        return {"error": f"Speaker {speaker_name} does not have precomputed measurements!"}

    if not os.path.exists(dir_data):
        return {
            "error": f"Speaker {speaker_name} does not have precomputed measurements for origin {origin} and version {speaker_version}!"
        }

    m1 = [s.split("/")[-1] for s in glob(f"{dir_data}/*.*")]
    return sorted(set([s.split(".")[0] for s in m1]))


@app.get(
    f"/{API_VERSION}/speaker/{{speaker_name}}/version/{{speaker_version}}/measurements/{{measurement_name}}",
    tags=["speaker"],
)
async def get_speaker_measurements_data(
    speaker_name: str,
    speaker_version: str,
    measurement_name: str,
    measurement_format: Annotated[str | None, Query(max_length=5)] = "json",
):
    if not speaker_name or not measurement_name:
        return {"error": "Speaker name and measurement name are mandatory"}

    if speaker_name not in speakers_info:
        return {"error": f"Speaker {speaker_name} is not in our database!"}

    if (
        "/" in speaker_version
        or "/" in measurement_name
        or ".." in speaker_version
        or ".." in measurement_name
    ):
        return {
            "error": f"Invalid speaker_version {speaker_version} or speaker_name {speaker_name}!"
        }

    meta_data = speakers_info[speaker_name]

    if speaker_version not in meta_data["measurements"]:
        valid_keys = ", ".join(list(meta_data["measurements"].keys()))
        return {
            "error": f"Version {speaker_version} is not known for speaker {speaker_name}! Valid keys are ({valid_keys})."
        }

    origin = meta_data["measurements"][speaker_version]["origin"]
    if origin[0:8] == "Vendors-":
        origin = origin[8:]
    upper_dir = f"{SPINFILES}/{speaker_name}"
    dir_data = f"{upper_dir}/{origin}/{speaker_version}"

    if not os.path.exists(upper_dir):
        print(upper_dir)
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

    if measurement_format and measurement_format not in KNOWN_FORMATS:
        return {
            "error": f"Version {measurement_format} is not known! Valid options are either None or({KNOWN_FORMATS})."
        }

    measurement_file = f"{dir_data}/{measurement_name}.{measurement_format}"
    if measurement_format == "png":
        measurement_file = f"{dir_data}/{measurement_name}_large.{measurement_format}"

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
