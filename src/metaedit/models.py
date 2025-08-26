from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, cast
import copy

from pydantic import BaseModel, Field  # type: ignore[reportMissingImports]


class Size(BaseModel):
    height: Optional[float] = None
    width: Optional[float] = None
    depth: Optional[float] = None


class Dispersion(BaseModel):
    horizontal: Optional[float] = None
    vertical: Optional[float] = None


class SPL(BaseModel):
    peak: Optional[float] = None
    continuous: Optional[float] = None
    max: Optional[float] = None
    m_noise: Optional[float] = None
    b_noise: Optional[float] = None
    pink_noise: Optional[float] = None


class Specifications(BaseModel):
    sensitivity: Optional[float] = None
    impedance: Optional[float] = None
    weight: Optional[float] = None
    size: Optional[Size] = None
    spl_peak: Optional[float] = None
    spl_long_term: Optional[float] = None
    # Expanded fields to align with datas.Specifications
    dispersion: Optional[Dispersion] = None
    spl: Optional[SPL] = Field(default=None, alias="SPL")


class DataAcquisition(BaseModel):
    via: Optional[str] = None
    distance: Optional[float] = None
    signal: Optional[str] = None
    resolution: Optional[float] = None
    min_valid_freq: Optional[float] = None
    max_valid_freq: Optional[float] = None
    air_absorbtion: Optional[bool] = Field(default=None, alias="air_absorbtion")
    notes: Optional[str] = None


class Extras(BaseModel):
    is_equed: Optional[bool] = Field(default=None, alias="is_equed")
    score_penalty: Optional[float] = None


class Measurement(BaseModel):
    origin: Optional[str] = None
    format: Optional[str] = None
    quality: Optional[str] = None
    reviews: Dict[str, str] = Field(default_factory=dict)
    review_published: Optional[str] = None  # YYYYMMDD
    symmetry: Optional[str] = None
    data_acquisition: Optional[DataAcquisition] = None
    extras: Optional[Extras] = None
    notes: Optional[str] = None
    specifications: Optional[Specifications] = None


class SpeakerMetadata(BaseModel):
    brand: str
    model: str
    type: Optional[str] = None
    shape: Optional[str] = None
    price: Optional[str] = None
    amount: Optional[str] = None
    # Optional picture path (e.g., datas/icons/Brand Model.png)
    picture: Optional[str] = None
    measurements: Dict[str, Measurement] = Field(default_factory=dict)
    default_measurement: Optional[str] = None

    @staticmethod
    def convert_legacy_reviews(data: dict) -> dict:
        # Deep copy-like behavior
        converted = copy.deepcopy(data)
        measurements = converted.get("measurements")
        if isinstance(measurements, dict):
            for _key, meas in list(measurements.items()):
                if isinstance(meas, dict) and "review" in meas and "reviews" not in meas:
                    meas_reviews = {"default": meas["review"]}
                    meas.pop("review", None)
                    meas["reviews"] = meas_reviews
        return converted

    @staticmethod
    def format_date_for_python(date_str: str) -> str:
        # YYYY-MM-DD -> YYYYMMDD
        if not date_str or len(date_str) != 10:
            return ""
        return date_str.replace("-", "")

    @staticmethod
    def format_date_for_input(date_str: str) -> str:
        # YYYYMMDD -> YYYY-MM-DD
        if not date_str or len(date_str) != 8:
            return ""
        return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"


# ---- Export helpers -------------------------------------------------------


def _is_empty_value(v: Any) -> bool:
    """Return True for values that should be pruned from the exported dict.

    - None and empty strings are removed
    - Empty dicts and lists are removed
    - 0, 0.0 and False are kept (not considered empty)
    """
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    if isinstance(v, (list, tuple)) and len(v) == 0:
        return True
    return bool(isinstance(v, dict) and len(v) == 0)


def prune_empty(obj: Any) -> Any:
    """Recursively prune empty fields and blocks from a nested structure.

    This removes keys whose values are None, empty string, empty dict or empty list.
    Non-empty scalars like 0, 0.0, and False are retained.
    """
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            pruned_v = prune_empty(v)
            if not _is_empty_value(pruned_v):
                out[k] = pruned_v
        return out
    if isinstance(obj, list):
        pruned_list = [prune_empty(v) for v in obj]
        pruned_list = [v for v in pruned_list if not _is_empty_value(v)]
        return pruned_list
    return obj


def export_speaker_metadata(sm: SpeakerMetadata) -> Dict[str, Any]:
    """Serialize a SpeakerMetadata to a dict with specific key ordering and pruned empties.

    Top-level key order:
    brand, model, type, price, amount, shape, default_measurement, measurements, then other keys.

    For each measurement, key order:
    origin, format, quality, reviews, review_published, extras, notes, data_acquisition, specifications, then other keys.

    For specifications, key order:
    sensitivity, impedance, dispersion, SPL, size, weight, then other keys.

    Empty values/blocks are pruned. Unknown keys are appended at the end to minimize diffs.
    """
    raw = sm.model_dump(exclude_none=True, by_alias=True)

    # Helper to order dict by a preferred list of keys and then append remaining keys in original order
    def order_keys(src: Dict[str, Any], preferred: list[str]) -> Dict[str, Any]:
        dst: Dict[str, Any] = {}
        for k in preferred:
            if k in src and not _is_empty_value(src[k]):
                dst[k] = src[k]
        for k, v in src.items():
            if k not in dst:
                dst[k] = v
        return dst

    # Reorder specifications if present
    def reorder_spec(spec: Any) -> Any:
        if not isinstance(spec, dict):
            return spec
        pref = ["sensitivity", "impedance", "dispersion", "SPL", "size", "weight"]
        return order_keys(spec, pref)

    # Reorder a single measurement dict
    def reorder_measurement(meas: Any) -> Any:
        if not isinstance(meas, dict):
            return meas
        # Reorder nested specifications first if present
        if "specifications" in meas and isinstance(meas["specifications"], dict):
            meas = dict(meas)
            meas["specifications"] = reorder_spec(meas["specifications"])
        pref = [
            "origin",
            "format",
            "quality",
            "reviews",
            "review_published",
            "extras",
            "notes",
            "data_acquisition",
            "specifications",
        ]
        return order_keys(meas, pref)

    # Build top-level with desired order
    out: Dict[str, Any] = {}
    top_pref = [
        "brand",
        "model",
        "type",
        "price",
        "amount",
        "shape",
        "default_measurement",
        "measurements",
    ]

    # Prepare measurements block in-place respecting measurement key order
    if isinstance(raw.get("measurements"), dict):
        ordered_meas: Dict[str, Any] = {}
        for mkey, mval in cast(Dict[str, Any], raw["measurements"]).items():
            ordered_meas[mkey] = prune_empty(reorder_measurement(mval))
        raw = dict(raw)
        raw["measurements"] = ordered_meas

    # Apply top-level ordering
    out = order_keys(raw, top_pref)

    # Final prune to remove any empty blocks inserted during ordering
    return prune_empty(out)
