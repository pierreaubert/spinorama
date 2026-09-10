"""Extract coloured graph curves from an image.

The command deliberately keeps calibration evidence separate from the traced
native-pixel paths.  OCR-derived axes are useful output, but remain labelled
``ocr_unverified`` in the canonical JSON so callers do not mistake them for
source data.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from typing import Sequence

import cv2
import numpy as np
import numpy.typing as npt

from graphextract.evidence import StyleSpec
from graphextract.exports import write_canonical
from graphextract.ocr_adapters import TesseractOCR, ocr_anchor_provider
from graphextract.pipeline import run_document
from graphextract.schema import DocumentResult, SegmentStatus


_HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")


def _parse_style(value: str, index: int) -> StyleSpec:
    """Parse ``label=#RRGGBB`` (or a bare colour) into a curve style."""
    label, sep, colour = value.partition("=")
    if not sep:
        colour, label = label, f"curve_{index + 1}"
    match = _HEX.fullmatch(colour)
    if not match:
        message = f"invalid curve colour {colour!r}; use label=#RRGGBB"
        raise argparse.ArgumentTypeError(message)
    rgb = bytes.fromhex(match.group(1))
    return StyleSpec(f"curve_{index + 1}", label or f"curve_{index + 1}", tuple(reversed(rgb)))


def discover_styles(image: npt.NDArray, limit: int = 8) -> list[StyleSpec]:
    """Find prominent saturated colours for a usable zero-configuration run.

    Curves normally occupy many pixels with a stable hue.  One peak per hue
    avoids treating anti-aliased shades of the same line as separate curves.
    Exact colours passed through ``--curve`` are preferable when legend names
    or very similar series must be preserved.
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturated = (hsv[..., 1] >= 70) & (hsv[..., 2] >= 60)
    hues = hsv[..., 0][saturated]
    if not len(hues):
        return []
    histogram = np.bincount(hues, minlength=180)
    min_pixels = max(12, int(image.shape[0] * image.shape[1] * 0.00003))
    peaks: list[int] = []
    for hue in np.argsort(histogram)[::-1]:
        if histogram[hue] < min_pixels or len(peaks) >= limit:
            break
        circular_distance = np.minimum(np.abs(np.asarray(peaks) - hue), 180 - np.abs(np.asarray(peaks) - hue))
        if peaks and int(circular_distance.min()) < 10:
            continue
        peaks.append(int(hue))

    styles: list[StyleSpec] = []
    for index, hue in enumerate(peaks):
        distance = np.minimum(np.abs(hsv[..., 0].astype(int) - hue), 180 - np.abs(hsv[..., 0].astype(int) - hue))
        pixels = image[saturated & (distance <= 3)]
        # Median rejects most background/grid contamination while preserving
        # the full BGR colour expected by the evidence segmenter.
        bgr = tuple(int(v) for v in np.median(pixels, axis=0))
        styles.append(StyleSpec(f"curve_{index + 1}", f"curve_{index + 1}", bgr))
    return styles


def overlay_extracted(image: npt.NDArray, document: DocumentResult, alpha: float = 0.72) -> npt.NDArray:
    """Draw the extracted native-coordinate paths over the original image."""
    drawing = image.copy()
    colours = [(0, 0, 255), (255, 80, 0), (0, 180, 0), (255, 0, 180), (0, 180, 180), (180, 0, 100)]
    for panel in document.panels:
        for series_index, series in enumerate(panel.series):
            colour = colours[series_index % len(colours)]
            run: list[tuple[int, int]] = []
            for sample in series.samples:
                if sample.status is SegmentStatus.OBSERVED:
                    run.append((round(sample.u), round(sample.v)))
                    continue
                if len(run) >= 2:
                    cv2.polylines(drawing, [np.asarray(run, dtype=np.int32)], False, colour, 2, cv2.LINE_AA)
                run = []
            if len(run) >= 2:
                cv2.polylines(drawing, [np.asarray(run, dtype=np.int32)], False, colour, 2, cv2.LINE_AA)
    return cv2.addWeighted(drawing, alpha, image, 1.0 - alpha, 0)


def extract_image(
    image_path: str | Path,
    output_json: str | Path,
    output_overlay: str | Path,
    styles: Sequence[StyleSpec] = (),
    use_ocr: bool = True,  # noqa: FBT002
) -> DocumentResult:
    """Run the complete CLI workflow; exposed to make embedding straightforward."""
    image_path = Path(image_path)
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        message = f"could not read image: {image_path}"
        raise ValueError(message)
    selected = list(styles) or discover_styles(image)
    if not selected:
        message = "no saturated curve colours found; pass --curve label=#RRGGBB"
        raise ValueError(message)
    provider = ocr_anchor_provider(TesseractOCR()) if use_ocr else None
    document = run_document(image, image_path.stem, selected, anchor_provider=provider)
    output_json = Path(output_json)
    output_overlay = Path(output_overlay)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_overlay.parent.mkdir(parents=True, exist_ok=True)
    write_canonical(document, output_json)
    if not cv2.imwrite(str(output_overlay), overlay_extracted(image, document)):
        message = f"could not write overlay: {output_overlay}"
        raise ValueError(message)
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="input graph image")
    parser.add_argument("--json", type=Path, help="canonical JSON output (default: <image>.json)")
    parser.add_argument("--overlay", type=Path, help="PNG overlay output (default: <image>.overlay.png)")
    parser.add_argument("--curve", action="append", default=[], metavar="LABEL=#RRGGBB", help="known curve colour; repeat for each series")
    parser.add_argument("--no-ocr", action="store_true", help="skip OCR calibration attempt")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    styles = [_parse_style(value, index) for index, value in enumerate(args.curve)]
    json_path = args.json or args.image.with_suffix(".json")
    overlay_path = args.overlay or args.image.with_name(f"{args.image.stem}.overlay.png")
    try:
        result = extract_image(args.image, json_path, overlay_path, styles, not args.no_ocr)
    except ValueError as exc:
        build_parser().error(str(exc))
    print(f"wrote {json_path}")
    print(f"wrote {overlay_path}")
    print(f"panels: {len(result.panels)}, extracted series: {sum(len(p.series) for p in result.panels)}")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through __main__
    raise SystemExit(main())
