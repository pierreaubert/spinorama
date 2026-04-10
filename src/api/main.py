# -*- coding: utf-8 -*-
from glob import glob
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Query, Depends, Request
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse, FileResponse

from datas.checks import validate_speaker_data

API_VERSION = "v1"
CURRENT_VERSION = 0
SOFTWARE_VERSION = f"{API_VERSION}.{CURRENT_VERSION}"

APIFILES = "/var/www/html/spinorama-api"
SPINFILES = "/var/www/html/spinorama-prod/speakers"
METADATA = f"{APIFILES}/assets/metadata.json"
HEADPHONE_METADATA = f"{APIFILES}/assets/headphone.json"

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

ALIAS_MEASUREMENTS = {
    "ON": "On Axis",
    "On-Axis": "On Axis",
    "LW": "Listening Window",
    "ER": "Early Reflections",
    "PIR": "Estimated In-Room Response",
    "Predicted In-Room Response": "Estimated In-Room Response",
}

# Global variable to store metadata
_metadata_cache = None
_headphone_metadata_cache = None


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


def load_headphone_metadata():
    """Load headphone metadata for dependency injection."""
    global _headphone_metadata_cache
    if _headphone_metadata_cache is None:
        if not os.path.exists(HEADPHONE_METADATA):
            logging.warning("Cannot find %s, headphone endpoints disabled", HEADPHONE_METADATA)
            _headphone_metadata_cache = {}
        else:
            with open(HEADPHONE_METADATA, "r", encoding="utf8") as f:
                _headphone_metadata_cache = json.load(f)

    yield _headphone_metadata_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI startup/shutdown."""
    # Startup: Load metadata into cache
    global _metadata_cache, _headphone_metadata_cache
    if not os.path.exists(METADATA):
        logging.error("Cannot find %s", METADATA)
        sys.exit(1)

    with open(METADATA, "r", encoding="utf8") as f:
        _metadata_cache = json.load(f)

    if os.path.exists(HEADPHONE_METADATA):
        with open(HEADPHONE_METADATA, "r", encoding="utf8") as f:
            _headphone_metadata_cache = json.load(f)
    else:
        _headphone_metadata_cache = {}

    yield

    # Shutdown: Clean up if needed
    _metadata_cache = None
    _headphone_metadata_cache = None


openapi_tags = [
    {
        "name": "speaker",
        "description": "Speaker measurements and metadata",
    },
    {
        "name": "headphone",
        "description": "Headphone measurements and metadata",
    },
    {
        "name": "validation",
        "description": "Data validation endpoints",
    },
]

app = FastAPI(
    debug=False,
    title="Spinorama API",
    version=SOFTWARE_VERSION,
    lifespan=lifespan,
    openapi_tags=openapi_tags,
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
async def get_speaker_measurements(
    speaker_name: str,
    speaker_version: str,
    metadata: dict = Depends(load_metadata),  # noqa: B008
):
    if not speaker_name:
        return {"error": "Speaker name and measurement name are mandatory"}

    if speaker_name not in metadata:
        return {"error": f"Speaker {speaker_name} is not in our database!"}

    if "/" in speaker_version or ".." in speaker_version:
        return {"error": f"Invalid speaker_version {speaker_version}!"}

    meta_data = metadata[speaker_name]

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
    metadata: dict = Depends(load_metadata),  # noqa: B008
):
    if not speaker_name or not measurement_name:
        return {"error": "Speaker name and measurement name are mandatory"}

    if speaker_name not in metadata:
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

    meta_data = metadata[speaker_name]

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

    if measurement_format and measurement_format != "json":
        return {
            "error": f"Version {measurement_format} is not known! Only valid options is None or json."
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


@app.post(f"/{API_VERSION}/validate", tags=["validation"])
async def validate_speaker_metadata(request: Request):
    """Validate speaker metadata according to Spinorama standards."""
    try:
        speaker_data = await request.json()

        # Extract speaker name from the data or generate one
        brand = speaker_data.get("brand", "Unknown")
        model = speaker_data.get("model", "Unknown")
        speaker_name = f"{brand} {model}"

        # Validate the speaker data
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
            "messages": [f"ERROR: Validation failed - {str(e)}"],
            "speaker_name": "Unknown",
        }


# --- Headphone endpoints ---


HEADPHONE_FILES = "/var/www/html/spinorama-api/assets/headphones"


@app.get(f"/{API_VERSION}/headphones", tags=["headphone"])
async def get_headphone_list(
    brand: Annotated[str | None, Query(description="Filter by brand")] = None,
    shape: Annotated[str | None, Query(description="Filter by shape (over-ear, on-ear, in-ear)")] = None,
    recommendation: Annotated[str | None, Query(description="Filter by recommendation (Yes/No)")] = None,
    metadata: dict = Depends(load_headphone_metadata),  # noqa: B008
):
    results = metadata
    if brand:
        brand_lower = brand.lower()
        results = {k: v for k, v in results.items() if v.get("brand", "").lower() == brand_lower}
    if shape:
        shape_lower = shape.lower()
        results = {k: v for k, v in results.items() if v.get("shape", "").lower() == shape_lower}
    if recommendation:
        rec_lower = recommendation.lower()
        results = {
            k: v
            for k, v in results.items()
            if any(m.get("recommendation", "").lower() == rec_lower for m in v.get("measurements", {}).values())
        }
    return sorted(results.keys())


@app.get(f"/{API_VERSION}/headphone/brands", tags=["headphone"])
async def get_headphone_brand_list(metadata: dict = Depends(load_headphone_metadata)):  # noqa: B008
    return sorted({v.get("brand") for _, v in metadata.items()})


@app.get(f"/{API_VERSION}/headphone/shapes", tags=["headphone"])
async def get_headphone_shape_list(metadata: dict = Depends(load_headphone_metadata)):  # noqa: B008
    return sorted({v.get("shape") for _, v in metadata.items()})


@app.get(f"/{API_VERSION}/headphone/{{headphone_name}}/metadata", tags=["headphone"])
async def get_headphone_metadata(
    headphone_name: str,
    metadata: dict = Depends(load_headphone_metadata),  # noqa: B008
):
    content = metadata.get(headphone_name, {"error": "Headphone not found"})
    encoded = jsonable_encoder(content)
    return JSONResponse(content=encoded)


@app.get(f"/{API_VERSION}/headphone/{{headphone_name}}/versions", tags=["headphone"])
async def get_headphone_versions(
    headphone_name: str,
    metadata: dict = Depends(load_headphone_metadata),  # noqa: B008
):
    if headphone_name not in metadata:
        return {"error": f"Headphone {headphone_name} is not in our database!"}

    return list(metadata[headphone_name].get("measurements", {}).keys())


@app.get(
    f"/{API_VERSION}/headphone/{{headphone_name}}/frequency_response",
    tags=["headphone"],
)
async def get_headphone_frequency_response(
    headphone_name: str,
    version: Annotated[str | None, Query(description="Measurement version (defaults to default_measurement)")] = None,
    metadata: dict = Depends(load_headphone_metadata),  # noqa: B008
):
    if headphone_name not in metadata:
        return {"error": f"Headphone {headphone_name} is not in our database!"}

    if "/" in headphone_name or ".." in headphone_name:
        return {"error": f"Invalid headphone_name {headphone_name}!"}

    hp = metadata[headphone_name]
    meas_key = version or hp.get("default_measurement", "")

    if not meas_key or meas_key not in hp.get("measurements", {}):
        valid = list(hp.get("measurements", {}).keys())
        return {"error": f"Unknown version {meas_key!r} for {headphone_name}. Valid: {valid}"}

    if "/" in meas_key or ".." in meas_key:
        return {"error": f"Invalid version {meas_key}!"}

    csv_path = f"{HEADPHONE_FILES}/{headphone_name}/{meas_key}/frequency_response.csv"

    # Defense-in-depth: ensure the resolved path stays inside HEADPHONE_FILES
    real_base = os.path.realpath(HEADPHONE_FILES)
    real_csv = os.path.realpath(csv_path)
    if os.path.commonpath([real_base, real_csv]) != real_base:
        return {"error": f"Invalid path for {headphone_name} ({meas_key})"}

    if not os.path.exists(real_csv):
        return {"error": f"No frequency response data for {headphone_name} ({meas_key})"}

    return FileResponse(real_csv, media_type="text/csv")
