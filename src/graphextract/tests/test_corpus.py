# -*- coding: utf-8 -*-
"""Tests for corpus.py: inventory, duplicates, grouped splits, sidecars, gold."""

import hashlib
from pathlib import Path

from graphextract.corpus import (
    ImageAnnotation,
    PanelAnnotation,
    SeriesAnnotation,
    TickAnnotation,
    assign_splits,
    build_inventory,
    family_for,
    generate_synthetic_gold,
    load_annotation,
    save_annotation,
    source_group_for,
    validate_annotation,
)

DATAS = Path(__file__).resolve().parents[1] / "datas"


def test_group_and_family_heuristics():
    assert source_group_for("AsciLab C8C speakers measurement.png") == "ascilab"
    assert source_group_for("PSI Swiss Made Monitor THD distortion Measurement (1).png") == "psi"
    assert family_for("x step response dsp measurement.png") == "step_response"
    assert family_for("y THD distortion percent Measurement.png") == "distortion_percent"
    assert family_for("z distortion measurement.png") == "distortion_db"
    assert family_for("w frequency response driver measurement.png") == "frequency_response"


def test_inventory_skips_overlay_sidecars(tmp_path):
    """Derived *.overlay.png visualisations are not corpus source images."""
    import cv2
    import numpy as np
    img = np.full((40, 60, 3), 255, np.uint8)
    img[10:30, 5:55] = (0, 0, 0)
    assert cv2.imwrite(str(tmp_path / "a measurement.png"), img)
    assert cv2.imwrite(str(tmp_path / "a measurement.overlay.png"), img)
    items = build_inventory(tmp_path)
    assert [it.path for it in items] == ["a measurement.png"]


def test_inventory_finds_duplicates_and_groups():
    items = build_inventory(DATAS / "graph-distorsion")
    assert len(items) == 10
    groups = {it.source_group for it in items}
    assert groups == {"ascilab", "psi"}
    n_dup_groups = len({it.duplicate_group for it in items})
    assert n_dup_groups < len(items)  # the "(1)" copies are detected


def test_splits_keep_source_groups_together():
    items = build_inventory(DATAS / "graph-distorsion")
    splits = assign_splits(items, seed=0)
    covered = sorted(p for paths in splits.values() for p in paths)
    assert covered == sorted(it.path for it in items)
    assert splits["locked_test"]  # non-empty locked holdout
    owner: dict[str, str] = {}
    for split, paths in splits.items():
        for p in paths:
            grp = next(it.source_group for it in items if it.path == p)
            assert grp not in owner or owner[grp] == split
            owner[grp] = split


def test_annotation_round_trip_and_validation(tmp_path):
    annot = ImageAnnotation(
        image_id="x.png", sha256="abc", width=100, height=80,
        panels=[PanelAnnotation("x#p0", [0, 0, 100, 80], [10, 10, 80, 60])],
        series=[SeriesAnnotation("s0", "x#p0", "THD")],
        ticks=[TickAnnotation("x", 10.0, 20.0, "Hz")],
        annotator="tester", status="reviewed",
    )
    p = save_annotation(tmp_path, annot)
    assert load_annotation(p).series[0].label == "THD"
    assert validate_annotation(annot) == []
    assert validate_annotation(annot, image_bytes_sha="other") != []
    bad = ImageAnnotation(image_id="x.png", sha256="abc", width=100, height=80,
                          panels=[PanelAnnotation("x#p0", [0, 0, 100, 80], [90, 70, 80, 60])],
                          series=[SeriesAnnotation("s0", "x#nope", "THD")],
                          ticks=[TickAnnotation("z", 0.0, float("nan"), "?")])
    errs = validate_annotation(bad)
    assert len(errs) >= 3


def test_synthetic_gold_is_valid_and_locked(tmp_path):
    mp = generate_synthetic_gold(tmp_path, n_panels=2, seed=0)
    assert mp.exists()
    for sidecar in sorted(tmp_path.glob("synth_*.json")):
        if sidecar.name == "manifest.json":
            continue
        annot = load_annotation(sidecar)
        assert annot.status == "locked"
        img_sha = hashlib.sha256((tmp_path / annot.image_id).read_bytes()).hexdigest()
        assert validate_annotation(annot, image_bytes_sha=img_sha) == []
        assert annot.series and annot.ticks
