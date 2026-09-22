# -*- coding: utf-8 -*-
"""Tests for evidence.py: depth floor and exclusion masking."""

import cv2
import numpy as np

from graphextract.evidence import StyleSpec, segment_evidence


def _gray_image(noise_val=250, core_val=230):
    """White field with one paper-noise pixel and one stroke-core pixel."""
    img = np.full((60, 80, 3), 255, np.uint8)
    img[10, 10] = (noise_val, noise_val, noise_val)
    img[40, 40] = (core_val, core_val, 205)
    img[20, 20] = (200, 200, 200)  # deep grey impostor (glyph edge)
    img[50, 50] = (180, 180, 180)  # grey stroke core
    return img


def test_depth_floor_rejects_paper_noise_for_pale_seeds():
    # Sovox-ER shape: a near-grey seed matches 5-deep paper noise through
    # both match paths; only the 20-deep stroke core may survive.
    layers = segment_evidence(_gray_image(),
                              [StyleSpec("er", "ER", (231, 231, 205))])
    mask = layers.curve_masks["er"]
    assert mask[40, 40] == 255
    assert mask[10, 10] == 0
    assert layers.union_mask is not None
    assert layers.union_mask[40, 40] == 255
    assert layers.union_mask[10, 10] == 0


def test_chroma_gate_rejects_grey_impostors_for_chromatic_seeds():
    # Sovox-SP shape: deep grey glyph edges unmix into pastel masks and
    # hijack the seed take; hue-less pixels carry nothing to attribute.
    layers = segment_evidence(_gray_image(),
                              [StyleSpec("er", "ER", (231, 231, 205))])
    assert layers.curve_masks["er"][20, 20] == 0
    # Achromatic seeds cannot use hue and keep their grey cores.
    gray = segment_evidence(_gray_image(),
                            [StyleSpec("oa", "OA", (180, 180, 180))])
    assert gray.curve_masks["oa"][50, 50] == 255


def test_exclude_zeroes_key_and_word_boxes():
    # Legend keys and words mask out of every layer: text ink is never
    # curve ink.
    layers = segment_evidence(_gray_image(),
                              [StyleSpec("er", "ER", (231, 231, 205))],
                              exclude=[(35, 35, 10, 10)])
    assert "er" not in layers.curve_masks  # sole core pixel masked out
    assert layers.union_mask[40, 40] == 0
