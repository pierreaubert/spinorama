from __future__ import annotations

# ruff: noqa: S101

from typing import List

from metaedit.models import (
    DataAcquisition,
    Measurement,
    Size,
    SpeakerMetadata,
    Specifications,
    export_speaker_metadata,
)


def _keys_in_order(keys: List[str], ordered_subset: List[str]) -> bool:
    """Return True if keys from ordered_subset appear in keys in the same relative order.

    Missing keys are ignored; only the relative order of present keys is checked.
    """
    positions = {k: i for i, k in enumerate(keys)}
    present = [k for k in ordered_subset if k in positions]
    return all(positions[present[i]] < positions[present[i + 1]] for i in range(len(present) - 1))


def test_top_level_order_min_diff() -> None:
    sm = SpeakerMetadata(
        brand="BrandX",
        model="ModelY",
        shape="bookshelves",
        type="passive",
        price="$999",
        amount="pair",
        default_measurement="m1",
        measurements={
            "m1": Measurement(origin="TestOrigin", format="klippel"),
        },
    )

    out = export_speaker_metadata(sm)
    keys = list(out.keys())

    expected_order = [
        "brand",
        "model",
        "type",
        "price",
        "amount",
        "shape",
        "default_measurement",
        "measurements",
    ]

    assert keys[: len(expected_order)] == expected_order


def test_measurement_order_and_prune() -> None:
    meas = Measurement(
        origin="Lab",
        format="klippel",
        quality="A",
        reviews={"default": "Great"},
        review_published="20220101",
        extras=None,  # should be omitted
        data_acquisition=DataAcquisition(via="Klippel"),
        specifications=Specifications(
            sensitivity=85.0,
            impedance=None,
            size=Size(height=10.0),
            weight=10.0,
        ),
    )

    sm = SpeakerMetadata(
        brand="B",
        model="M",
        default_measurement="m1",
        measurements={"m1": meas},
    )

    out = export_speaker_metadata(sm)

    m1 = out["measurements"]["m1"]
    m1_keys = list(m1.keys())

    # Ensure extras and notes are pruned if empty
    assert "extras" not in m1_keys
    assert "notes" not in m1_keys

    expected_meas_order = [
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
    assert _keys_in_order(m1_keys, expected_meas_order)

    # Check specs order
    specs = m1["specifications"]
    spec_keys = list(specs.keys())
    expected_spec_order = [
        "sensitivity",
        "impedance",
        "dispersion",
        "SPL",
        "size",
        "weight",
    ]
    assert _keys_in_order(spec_keys, expected_spec_order)
