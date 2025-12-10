# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
from typing import Any, Dict, Tuple

from ..schema import ConfidenceValue, Range, SpeakerSpecs
from .rules import canonicalize

_NUM_RE = re.compile(r"-?\d+(?:[\.,]\d+)?")
_RANGE_RE = re.compile(r"(\d+(?:[\.,]\d+)?)\s*[a-z]*\s*(?:-|to|–|—)\s*(\d+(?:[\.,]\d+)?)", re.I)


def _to_float(s: str) -> float:
    s2 = s.replace(",", ".")
    return float(s2)


def _parse_db(value: str) -> float:
    m = _NUM_RE.search(value)
    return _to_float(m.group()) if m else float("nan")


def _parse_range_hz(value: str) -> Range | None:
    # e.g. "30Hz - 50kHz", "38Hz - 38kHz"
    m = _RANGE_RE.search(value)
    if not m:
        return None
    lo, hi = _to_float(m.group(1)), _to_float(m.group(2))
    # detect kHz
    # take last unit tokens
    val_lower = value.lower()
    if "khz" in val_lower:
        # if only one side has kHz, assume hi is kHz; if both, kHz for both
        # low side might have Hz, keep as Hz
        if "khz" in val_lower.split("-")[-1]:
            hi *= 1000
    return Range(min=lo, max=hi)


def _parse_dims(value: str) -> Dict[str, ConfidenceValue]:
    # Expect patterns like: "320.7 x 1143.8 x 428.3mm  / 12.6 x 45 x 16.9 in"
    # or "320.7 x 1143.8 x 428.3mm 12.6 x 45 x 16.9 in" (after HTML cleaning)
    out: Dict[str, ConfidenceValue] = {}

    # Look for mm dimensions
    mm_pattern = r"([\d.,]+)\s*x\s*([\d.,]+)\s*x\s*([\d.,]+)\s*mm"
    mm_match = re.search(mm_pattern, value, re.I)
    if mm_match:
        w, h, d = map(_to_float, mm_match.groups())
        out["mm"] = ConfidenceValue(
            value={"w": w, "h": h, "d": d}, confidence="high", source_hint="specs_html"
        )

    # Look for inch dimensions
    in_pattern = r"([\d.,]+)\s*x\s*([\d.,]+)\s*x\s*([\d.,]+)\s*in"
    in_match = re.search(in_pattern, value, re.I)
    if in_match:
        w, h, d = map(_to_float, in_match.groups())
        out["in"] = ConfidenceValue(
            value={"w": w, "h": h, "d": d}, confidence="high", source_hint="specs_html"
        )

    return out


def _parse_weight(value: str) -> Dict[str, ConfidenceValue]:
    # e.g. "79.1 lbs/35.9 kg"
    out: Dict[str, ConfidenceValue] = {}
    lbs_m = re.search(r"(\d+(?:[\.,]\d+)?)\s*lb", value, re.I)
    kg_m = re.search(r"(\d+(?:[\.,]\d+)?)\s*kg", value, re.I)
    if lbs_m:
        out["lb"] = ConfidenceValue(
            value=_to_float(lbs_m.group(1)), confidence="high", source_hint="specs_html"
        )
    if kg_m:
        out["kg"] = ConfidenceValue(
            value=_to_float(kg_m.group(1)), confidence="high", source_hint="specs_html"
        )
    return out


def normalize_raw_map(raw: Dict[str, str]) -> Dict[str, Any]:
    """Map raw label/value strings to canonical fields with parsed values."""
    norm: Dict[str, Any] = {}
    for label, value in raw.items():
        can = canonicalize(label)
        if not can:
            continue
        v = value
        if can == "sensitivity_db_2p83v_1m":
            norm[can] = ConfidenceValue(
                value=_parse_db(v), confidence="high", source_hint="specs_html"
            )
        elif can == "min_impedance_ohms":
            num = _NUM_RE.search(v)
            if num:
                norm[can] = ConfidenceValue(
                    value=_to_float(num.group()), confidence="high", source_hint="specs_html"
                )
        elif can == "overall_freq_hz":
            r = _parse_range_hz(v)
            if r:
                norm[can] = ConfidenceValue(value=r, confidence="high", source_hint="specs_html")
        elif can == "minus3db_freq_hz":
            r = _parse_range_hz(v)
            if r:
                norm[can] = ConfidenceValue(value=r, confidence="high", source_hint="specs_html")
        elif can == "amplifier_power_recommended_w":
            r = _RANGE_RE.search(v)
            if r:
                rng = Range(min=_to_float(r.group(1)), max=_to_float(r.group(2)))
                norm[can] = ConfidenceValue(value=rng, confidence="high", source_hint="specs_html")
        elif can == "dims":
            dims = _parse_dims(v)
            if dims:
                norm["dimensions"] = dims
        elif can == "weight_each":
            wt = _parse_weight(v)
            if wt:
                norm.setdefault("weight", {})["each"] = ConfidenceValue(
                    value=wt, confidence="high", source_hint="specs_html"
                )
        elif can == "uom_sold_as":
            norm[can] = ConfidenceValue(value=v, confidence="high", source_hint="specs_html")
    return norm


def assemble_specs(norm: Dict[str, Any], source_url: str | None = None) -> SpeakerSpecs:
    # Build a minimal valid SpeakerSpecs; unknowns default to low/null
    def cv(value: Any = None, conf: str = "low", hint: str | None = None) -> ConfidenceValue:
        return ConfidenceValue(value=value, confidence=conf, source_hint=hint)

    return SpeakerSpecs(
        brand=cv(None, "low"),
        model=cv(None, "low"),
        type=cv(None, "low"),
        sensitivity_db_2p83v_1m=norm.get("sensitivity_db_2p83v_1m", cv()),
        impedance={
            "min_ohms": norm.get("min_impedance_ohms", cv()),
        },
        amplifier_power_recommended_w=norm.get("amplifier_power_recommended_w", cv()),
        frequency_response_hz={
            "overall": norm.get("overall_freq_hz", cv()),
            "-3db_limits": norm.get("minus3db_freq_hz", cv()),
        },
        drivers={},
        crossover_hz={},
        dispersion_horizontal_deg=cv(),
        dispersion_vertical_deg=cv(),
        max_spl_db=cv(),
        dimensions=norm.get("dimensions", {}),
        weight=norm.get("weight", {}),
        cabinet={},
        uom_sold_as=norm.get("uom_sold_as", cv()),
        certifications={},
        source_url=source_url,
        last_verified=None,
    )
