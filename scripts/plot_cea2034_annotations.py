#!/usr/bin/env python3
"""Render annotated CEA-2034 plots for a list of speakers.

This is intentionally a small iteration harness around the same loader and
plotting code used by ``compute_spin.py``.  It makes the annotations visible
in the exported image without changing the default website/plot behaviour.

Examples:

    python scripts/plot_cea2034_annotations.py "Adam A5X" "Adam T5V" --force
    python scripts/plot_cea2034_annotations.py \
        "Bowers & Wilkins 607 S2 Anniversary Edition" \
        --output-dir /tmp/cea2034 --width 1200 --height 800 --force
    python scripts/plot_cea2034_annotations.py /path/to/speaker/directory
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import plotly.io as pio


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SRC_DIR))

from compute_spin import detect_format, load_speaker_data
from spinorama import logger, setup_logger
from spinorama.constant_paths import DEFAULT_FREQ_RANGE
from spinorama.misc import sanitize_filename
from spinorama.plot import plot_params_default
from spinorama.speaker import display_spinorama


FORMAT_CHOICES = (
    "auto",
    "klippel",
    "princeton",
    "spl_hv_txt",
    "gll_hv_txt",
    "rew_text_dump",
    "webplotdigitizer",
)


def resolve_speaker(speaker: str, data_root: Path) -> tuple[Path, str]:
    """Resolve a CLI speaker name or directory to ``(directory, name)``."""
    direct = Path(speaker).expanduser()
    if direct.is_dir():
        directory = direct.resolve()
        return directory, directory.name

    rooted = (data_root / speaker).expanduser()
    if rooted.is_dir():
        directory = rooted.resolve()
        return directory, directory.name

    message = f"Speaker directory not found for {speaker!r}; checked {direct} and {rooted}"
    raise FileNotFoundError(message)


def detect_format_and_version(
    speaker_dir: Path, speaker_name: str, requested_format: str
) -> tuple[str, str]:
    """Return the loader format and version for one speaker directory."""
    if requested_format == "auto":
        detected = detect_format(str(speaker_dir), speaker_name)
        if detected is None:
            message = f"Could not detect a measurement format for {speaker_dir}"
            raise ValueError(message)
        return detected

    subdirectories = sorted(
        path for path in speaker_dir.iterdir() if path.is_dir() and not path.name.startswith(".")
    )
    version = subdirectories[0].name if subdirectories else "default"
    return requested_format, version


def valid_frequency_range(measurements) -> tuple[float, float]:
    """Match the raw-measurement range used by the existing graph generator."""
    minimum, maximum = DEFAULT_FREQ_RANGE
    for frame in (measurements.h_spl, measurements.v_spl):
        if frame is None or "Freq" not in frame or frame.empty:
            continue
        minimum = max(minimum, float(frame.Freq.min()))
        maximum = min(maximum, float(frame.Freq.max()))
    return minimum, maximum


def make_plot_parameters(width: int, height: int) -> dict:
    """Build plot parameters without mutating the shared defaults."""
    parameters = plot_params_default.copy()
    parameters.update(width=width, height=height, layout="compact")
    return parameters


def show_annotations(figure) -> int:
    """Show placed annotations while preserving solver-hidden annotations."""
    annotations = list(figure.layout.annotations or ())
    visible_count = 0
    for annotation in annotations:
        hidden_by_solver = str(annotation.name or "").startswith("layout-hidden:")
        annotation.visible = not hidden_by_solver
        if not hidden_by_solver:
            visible_count += 1
    return visible_count


def render_speaker(
    speaker: str,
    *,
    data_root: Path,
    output_dir: Path,
    requested_format: str,
    symmetry: str | None,
    width: int,
    height: int,
    force: bool,
) -> Path:
    """Load and render one speaker, returning the PNG path."""
    speaker_dir, speaker_name = resolve_speaker(speaker, data_root)
    fmt, version = detect_format_and_version(speaker_dir, speaker_name, requested_format)

    success, measurements, _parameters = load_speaker_data(
        str(speaker_dir), speaker_name, fmt, version, symmetry
    )
    if not success:
        message = f"Could not load measurements from {speaker_dir}"
        raise RuntimeError(message)

    figure = display_spinorama(
        measurements,
        make_plot_parameters(width, height),
        valid_frequency_range(measurements),
    )
    if figure is None:
        message = f"No CEA-2034 plot could be generated for {speaker_name}"
        raise RuntimeError(message)

    annotation_count = show_annotations(figure)
    if annotation_count == 0:
        message = f"CEA-2034 plot for {speaker_name} contains no annotations"
        raise RuntimeError(message)

    figure.update_layout(title=speaker_name)
    output_path = output_dir / f"{sanitize_filename(speaker_name)}_CEA2034_annotations.png"
    if output_path.exists() and not force:
        logger.info("Skipping existing %s (use --force to overwrite)", output_path)
        return output_path

    pio.write_image(figure, str(output_path), width=width, height=height)
    logger.info("Saved %s (%d annotations)", output_path, annotation_count)
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render one annotated CEA-2034 PNG per speaker.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "speakers",
        nargs="+",
        help="Speaker names below --data-root, or direct speaker measurement directories",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=PROJECT_ROOT / "datas" / "measurements",
        help="Root containing speaker directories (default: datas/measurements)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "build" / "cea2034-annotations",
        help="Directory for generated PNGs (default: build/cea2034-annotations)",
    )
    parser.add_argument(
        "--format",
        choices=FORMAT_CHOICES,
        default="auto",
        help="Measurement format, or auto-detect per speaker (default: auto)",
    )
    parser.add_argument("--width", type=int, default=1200, help="PNG width (default: 1200)")
    parser.add_argument("--height", type=int, default=800, help="PNG height (default: 800)")
    parser.add_argument(
        "--symmetry",
        choices=["auto", "mirror", "shift", "none"],
        default="auto",
        help="Horizontal-angle symmetry mode (default: auto)",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing PNGs")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.width <= 0 or args.height <= 0:
        parser.error("--width and --height must be positive")

    setup_logger(level=logging.DEBUG if args.verbose else logging.INFO)
    data_root = args.data_root.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    symmetry = None if args.symmetry == "auto" else args.symmetry
    failures = 0
    for speaker in args.speakers:
        try:
            render_speaker(
                speaker,
                data_root=data_root,
                output_dir=output_dir,
                requested_format=args.format,
                symmetry=symmetry,
                width=args.width,
                height=args.height,
                force=args.force,
            )
        except Exception as error:  # keep processing the rest of a speaker list
            failures += 1
            if args.verbose:
                logger.exception("Failed to render %s", speaker)
            else:
                print(f"ERROR: {speaker}: {error}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
