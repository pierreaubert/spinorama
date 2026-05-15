# -*- coding: utf-8 -*-
"""Headphone-resource routes."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from starlette.responses import FileResponse, JSONResponse

from ..state import (
    API_VERSION,
    HEADPHONE_FILES,
    load_headphone_metadata,
    safe_segment,
)


router = APIRouter(prefix=f"/{API_VERSION}", tags=["headphone"])


@router.get("/headphones")
async def get_headphone_list(
    brand: Annotated[str | None, Query(description="Filter by brand")] = None,
    shape: Annotated[
        str | None, Query(description="Filter by shape (over-ear, on-ear, in-ear)")
    ] = None,
    recommendation: Annotated[
        str | None, Query(description="Filter by recommendation (Yes/No)")
    ] = None,
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
            if any(
                m.get("recommendation", "").lower() == rec_lower
                for m in v.get("measurements", {}).values()
            )
        }
    return sorted(results.keys())


@router.get("/headphone/brands")
async def get_headphone_brand_list(
    metadata: dict = Depends(load_headphone_metadata),  # noqa: B008
):
    return sorted({v.get("brand") for _, v in metadata.items()})


@router.get("/headphone/shapes")
async def get_headphone_shape_list(
    metadata: dict = Depends(load_headphone_metadata),  # noqa: B008
):
    return sorted({v.get("shape") for _, v in metadata.items()})


@router.get("/headphone/{headphone_name}/metadata")
async def get_headphone_metadata(
    headphone_name: str,
    metadata: dict = Depends(load_headphone_metadata),  # noqa: B008
):
    content = metadata.get(headphone_name, {"error": "Headphone not found"})
    return JSONResponse(content=jsonable_encoder(content))


@router.get("/headphone/{headphone_name}/versions")
async def get_headphone_versions(
    headphone_name: str,
    metadata: dict = Depends(load_headphone_metadata),  # noqa: B008
):
    if headphone_name not in metadata:
        return {"error": f"Headphone {headphone_name} is not in our database!"}

    return list(metadata[headphone_name].get("measurements", {}).keys())


@router.get("/headphone/{headphone_name}/frequency_response")
async def get_headphone_frequency_response(
    headphone_name: str,
    version: Annotated[
        str | None,
        Query(description="Measurement version (defaults to default_measurement)"),
    ] = None,
    metadata: dict = Depends(load_headphone_metadata),  # noqa: B008
):
    if headphone_name not in metadata:
        return {"error": f"Headphone {headphone_name} is not in our database!"}

    if not safe_segment(headphone_name):
        return {"error": f"Invalid headphone_name {headphone_name}!"}

    hp = metadata[headphone_name]
    meas_key = version or hp.get("default_measurement", "")

    if not meas_key or meas_key not in hp.get("measurements", {}):
        valid = list(hp.get("measurements", {}).keys())
        return {"error": f"Unknown version {meas_key!r} for {headphone_name}. Valid: {valid}"}

    if not safe_segment(meas_key):
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
