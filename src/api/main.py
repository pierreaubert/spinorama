# -*- coding: utf-8 -*-
import json
import logging
import os
import sys
from typing import Annotated

from fastapi import FastAPI, Query, Depends
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse, FileResponse

from datas.metadata import speakers_info

API_VERSION = "v0"
CURRENT_VERSION = 2
SOFTWARE_VERSION = f"{API_VERSION}.{CURRENT_VERSION}"

FILES = "/var/www/html/spinorama-dev"
METADATA = f"{FILES}/assets/metadata.json"
CACHE = f"{FILES}/cache"


def load_metadata():
    if not os.path.exists(METADATA):
        logging.error("Cannot find %s", METADATA)
        sys.exit(1)

    with open(METADATA, "r", encoding="utf8") as f:
        metadata = json.load(f)
        yield metadata


app = FastAPI(
    debug=False,
    title="Spinorama API",
    version=SOFTWARE_VERSION,
    on_startup=[load_metadata],
)


@app.get(f"/{API_VERSION}/brands", tags=["speaker"])
async def get_brand_list(metadata: dict = Depends(load_metadata)):
    return sorted(set([v.get("brand") for _, v in metadata.items()]))


@app.get(f"/{API_VERSION}/speaker", tags=["speaker"])
async def get_speaker_list(metadata: dict = Depends(load_metadata)):
    return sorted(metadata.keys())


@app.get(f"/{API_VERSION}/speaker/{{speaker_name}}/metadata", tags=["speaker"])
async def get_speaker_metadata(speaker_name: str, metadata: dict = Depends(load_metadata)):
    content = metadata.get(speaker_name, {"error": "Speaker not found"})
    json = jsonable_encoder(content)
    return JSONResponse(content=json)


@app.get(
    f"/{API_VERSION}/speaker/{{speaker_name}}/version/{{speaker_version}}/measurements/{{measurement_name}}",
    tags=["speaker"],
)
async def get_speaker_measurements(
    speaker_name: str,
    speaker_version: str,
    measurement_name: str,
    measurement_format: Annotated[str | None, Query(max_length=5)] = "json",
):
    if not speaker_name or not measurement_name:
        return {"error": "Speaker name and measurement name are mandatory"}

    if speaker_name not in speakers_info:
        return {"error": f"Speaker {speaker_name} is not in our database!"}

    meta_data = speakers_info[speaker_name]
    version = meta_data["default_measurement"]
    origin = meta_data["measurements"][version]["origin"]
    upper_dir = f"{FILES}/speakers/{speaker_name}"
    dir_data = f"{upper_dir}/{origin}/{version}"

    if not os.path.exists(upper_dir):
        print(upper_dir)
        return {"error": f"Speaker {speaker_name} does not have precomputed measurements!"}

    if not os.path.exists(dir_data):
        return {
            "error": f"Speaker {speaker_name} does not have precomputed measurements for origin {origin} and version {version}!"
        }

    measurement_file = f"{dir_data}/{measurement_name}.{measurement_format}"
    if measurement_format == "png":
        measurement_file = f"{dir_data}/{measurement_name}_large.{measurement_format}"

    if not os.path.exists(measurement_file):
        return {
            "error": f"Speaker {speaker_name} does not have precomputed {measurement_name} in format {measurement_format} for origin {origin} and version {version}!"
        }

    if measurement_format == "json":
        with open(measurement_file, "r", encoding="utf8") as fd:
            return fd.readlines()

    if measurement_format in ("webp", "jpg", "png"):
        return FileResponse(measurement_file)

    return {"error": "fetching measurements failed format {measurement_format} is unknown!"}