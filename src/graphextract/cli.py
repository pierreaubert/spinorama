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
from graphextract.exports import write_canonical, write_comparison_figure, write_curve_csvs
from graphextract.ocr_adapters import TesseractOCR, _box_iou, _dedup_words, _offset_words, ocr_anchor_provider, read_text_zone
from graphextract.pipeline import run_document
from graphextract.schema import DocumentResult, SegmentStatus
from graphextract.semantics import detect_legend, styles_from_legend
from graphextract.tracking import TrackConfig


_HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")


def _parse_style(value: str, index: int) -> StyleSpec:
    """Parse ``label=#RRGGBB`` (or a bare colour) into a curve style."""
    label, sep, colour = value.partition("=")
    if not sep:
        colour, label = label, f"curve_{index + 1}"
    match = _HEX.fullmatch(colour)
    if not match:
        message = (
            f"invalid curve colour {colour!r}; expected LABEL=#RRGGBB "
            f"(a '#' followed by exactly 6 hex digits), "
            f'e.g. --curve "On Axis=#265B7D"'
        )
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
                if sample.status in (SegmentStatus.OBSERVED, SegmentStatus.INTERPOLATED):
                    run.append((round(sample.u), round(sample.v)))
                    continue
                if len(run) >= 2:
                    cv2.polylines(drawing, [np.asarray(run, dtype=np.int32)], False, colour, 2, cv2.LINE_AA)
                run = []
            if len(run) >= 2:
                cv2.polylines(drawing, [np.asarray(run, dtype=np.int32)], False, colour, 2, cv2.LINE_AA)
    return cv2.addWeighted(drawing, alpha, image, 1.0 - alpha, 0)


def select_styles(
    image: npt.NDArray,
    words: Sequence | None,
    explicit: Sequence[StyleSpec] = (),
) -> list[StyleSpec]:
    """Curve styles: explicit ``--curve`` colours win; else the parsed legend
    (curve count, names, and colours); else saturated-colour discovery."""
    if list(explicit):
        return list(explicit)
    if words is not None:
        legend = detect_legend(image, words)
        if legend.has_legend and legend.entries:
            return styles_from_legend(legend)
    return discover_styles(image)


def _read_full_words(image: npt.NDArray, ocr: TesseractOCR,
                     sparse_min_words: int = 15) -> Sequence | None:
    """Full-image OCR words (image-global); None when OCR cannot deliver.

    Tesseract's page segmentation drops small type on sparse layouts, so
    a near-empty native read retries at 2x with coordinates scaled back;
    the merged set keeps whatever each scale saw. Runs only when the
    native read is sparse, so dense charts pay nothing.
    """
    if not ocr.available:
        return None
    full_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    try:
        words = ocr.read_words(full_gray)
    except Exception:  # external OCR binary: degrade to the legacy path
        return None
    if len(words) >= sparse_min_words:
        return words
    try:
        big = cv2.resize(full_gray, None, fx=2.0, fy=2.0,
                         interpolation=cv2.INTER_CUBIC)
        words2 = ocr.read_words(big)
    except Exception:
        return words
    if len(words2) <= len(words):
        return words
    from graphextract.ocr_adapters import OCRWord
    scaled = [OCRWord(w.text, w.x // 2, w.y // 2, max(1, w.w // 2),
                      max(1, w.h // 2), w.confidence) for w in words2]
    return _dedup_words(list(words) + scaled)


def _complete_legend_words(image: npt.NDArray, words: Sequence,
                           max_passes: int = 2) -> Sequence:
    """Re-read the legend zone so trailing rows join the word pool.

    Full-page OCR drops the tail of long legend stacks; the rows it
    did read locate a tight zone (entry band, extended along the row
    pitch) whose sparse-text re-read recovers the missing labels (and
    any tick digits sharing the band). Iterates until the word pool
    stops growing: each pass can only extend the zone past newly
    found rows. Needs at least two keyed entries to estimate pitch.
    """
    words = list(words)
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    for _ in range(max_passes):
        legend = detect_legend(image, words)
        if not legend.has_legend or len(legend.entries) < 2:
            return words
        cys = sorted(e.word_xywh[1] + e.word_xywh[3] / 2.0
                     for e in legend.entries)
        gaps = [b - a for a, b in zip(cys, cys[1:]) if b - a > 1.0]
        if not gaps:
            return words
        pitch = float(min(max(float(np.median(gaps)), 10.0), 100.0))
        lx, ly, lw, lh = legend.bbox_xywh or (0, 0, w, h)
        mx = int(pitch)
        my = int(4 * pitch)
        x0, y0 = max(0, lx - mx), max(0, ly - my)
        x1, y1 = min(w, lx + lw + mx), min(h, ly + lh + my)
        if x1 - x0 < 8 or y1 - y0 < 8:
            return words
        extra = read_text_zone(gray[y0:y1, x0:x1])
        if not extra:
            return words
        # Gap fill only: the zone re-read recovers missing rows, never
        # replaces words the full read already has (its errors would
        # otherwise evict correct labels on confidence).
        fresh = [wd for wd in _offset_words(extra, x0, y0)
                 if not any(_box_iou(wd, old) >= 0.5 for old in words)]
        if not fresh:
            return words
        merged = _dedup_words(words + fresh)
        if len(merged) <= len(words):
            return words
        words = merged
    return words


def extract_image(
    image_path: str | Path,
    output_json: str | Path,
    output_overlay: str | Path,
    styles: Sequence[StyleSpec] = (),
    use_ocr: bool = True,  # noqa: FBT002
    output_compare: str | Path | None = None,
    assumptions: Sequence[str] = (),
    output_csv_dir: str | Path | None = None,
    tracker: str = "legacy",
    segmentor_checkpoint: str | Path | None = None,
) -> DocumentResult:
    """Run the complete CLI workflow; exposed to make embedding straightforward."""
    image_path = Path(image_path)
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        message = f"could not read image: {image_path}"
        raise ValueError(message)
    track_config = TrackConfig.from_assumptions(assumptions, backend=tracker)
    if tracker == "temporal" and track_config.active_assumptions():
        raise ValueError("temporal backend does not implement legacy assumptions")
    ocr = TesseractOCR() if use_ocr else None
    words = _read_full_words(image, ocr) if ocr is not None else None
    if words is not None:
        words = _complete_legend_words(image, words)
    selected = select_styles(image, words, styles)
    if not selected:
        message = "no saturated curve colours found; pass --curve label=#RRGGBB"
        raise ValueError(message)
    provider = ocr_anchor_provider(ocr) if ocr is not None else None
    segmentor = None
    if segmentor_checkpoint is not None:
        from graphextract.torch_segmentor import MultiLabelConvSeg
        if tracker != "temporal":
            raise ValueError("--segmentor requires --tracker temporal")
        segmentor = MultiLabelConvSeg.load(segmentor_checkpoint)
        if set(segmentor.series_ids) != {style.series_id for style in selected}:
            raise ValueError("checkpoint series IDs differ from selected styles")
    document = run_document(image, image_path.stem, selected,
                            anchor_provider=provider, track_config=track_config,
                            words=words,
                            supplement_discovery=not list(styles), segmentor=segmentor)
    output_json = Path(output_json)
    output_overlay = Path(output_overlay)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_overlay.parent.mkdir(parents=True, exist_ok=True)
    write_canonical(document, output_json)
    if not cv2.imwrite(str(output_overlay), overlay_extracted(image, document)):
        message = f"could not write overlay: {output_overlay}"
        raise ValueError(message)
    draw_occlusion = "assume_overlap" in assumptions
    if output_compare is not None:
        output_compare = Path(output_compare)
        output_compare.parent.mkdir(parents=True, exist_ok=True)
        write_comparison_figure(image, document, list(selected), output_compare,
                                draw_occlusion=draw_occlusion)
    if output_csv_dir is not None:
        write_curve_csvs(document, output_csv_dir,
                           include_occlusion=draw_occlusion)
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="input graph image")
    parser.add_argument("--json", type=Path, help="canonical JSON output (default: <image>.json)")
    parser.add_argument("--overlay", type=Path, help="PNG overlay output (default: <image>.overlay.png)")
    parser.add_argument("--curve", action="append", default=[], metavar="LABEL=#RRGGBB", help="known curve colour; repeat for each series")
    parser.add_argument("--compare", type=Path, default=None, help="stacked original-over-reconstruction PNG output")
    parser.add_argument("--csv-dir", type=Path, default=None, help="directory receiving one freq/spl CSV per curve")
    parser.add_argument("--assumptions", action="append", default=[], metavar="NAME[,NAME...]",
                        help="tracking assumptions (comma-separated, repeatable): curve_continuous, no_jump, assume_overlap")
    parser.add_argument("--segmentor", type=Path, help="experimental multilabel checkpoint; requires temporal and matching IDs")
    parser.add_argument("--tracker", choices=("legacy", "temporal"), default="legacy")
    parser.add_argument("--kind", choices=("curves", "filled-contour"), default="curves")
    parser.add_argument("--calibration", type=Path, help="filled-contour calibration JSON")
    parser.add_argument("--no-ocr", action="store_true", help="skip OCR calibration attempt")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        styles = [_parse_style(value, index) for index, value in enumerate(args.curve)]
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    json_path = args.json or args.image.with_suffix(".json")
    overlay_path = args.overlay or args.image.with_name(f"{args.image.stem}.overlay.png")
    if args.kind == "filled-contour":
        import json
        from graphextract.calibration import CalibrationUnresolved
        from graphextract.contours import extract_field, write_field
        if args.calibration is None:
            parser.error("filled-contour requires --calibration (axes and band edges)")
        try:
            image = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError(f"could not read {args.image}")
            result = extract_field(image, json.loads(args.calibration.read_text()))
            write_field(result, image, args.image, json_path, overlay_path)
        except (ValueError, KeyError, OSError, CalibrationUnresolved) as exc:
            parser.error(str(exc))
        print(f"Scalar field: {json_path}; valid pixels: {result.valid.mean():.1%}")
        return 0
    assumptions = [name.strip() for value in args.assumptions
                   for name in value.split(",") if name.strip()]
    try:
        result = extract_image(args.image, json_path, overlay_path, styles,
                               not args.no_ocr, args.compare, assumptions,
                               args.csv_dir, args.tracker, args.segmentor)
    except ValueError as exc:
        build_parser().error(str(exc))
    print(f"wrote {json_path}")
    print(f"wrote {overlay_path}")
    if args.compare is not None:
        print(f"wrote {args.compare}")
    if args.csv_dir is not None:
        count = sum(len(p.series) for p in result.panels)
        print(f"wrote {count} curve csv files to {args.csv_dir}")
    if assumptions:
        print(f"assumptions: {', '.join(sorted(set(assumptions)))}")
    print(f"panels: {len(result.panels)}, extracted series: {sum(len(p.series) for p in result.panels)}")
    labels = [s.label for p in result.panels for s in p.series]
    if labels:
        print(f"curves: {', '.join(labels)}")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through __main__
    raise SystemExit(main())
