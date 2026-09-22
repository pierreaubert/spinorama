# Graph extraction: validation, curves, and filled contours

Run commands from the repository root with `PYTHONPATH=src` and the project's
Python environment. Curve extraction keeps the existing backend by default.
The temporal and neural candidates are experimental: the diagnostic benchmark
shows lower error/false support, but not more strictly complete series.

## Filled contours

The discrete-colorbar extractor produces a scalar field rather than a collection
of x-monotone curves. Try the included horizontal RCF image:

```sh
PYTHONPATH=src .venv/bin/python -m graphextract \
  src/graphextract/datas/graph-contour/spl-horizontal-contour-for-rcf-kxw-4-a-m.png \
  --kind filled-contour \
  --calibration src/graphextract/datas/graph-contour/rcf-horizontal.calibration.json \
  --json /tmp/rcf-field.json --overlay /tmp/rcf-field.png
```

The JSON contains calibration, palette, units, image hash, validity fraction and
the companion NPZ filename. The NPZ contains `x`, `y`, `lower`, `upper`, `valid`,
`band_index`, and `color_residual`. Array shape is `(len(y), len(x))`; native row
order is retained, so angle commonly decreases with increasing row index.
Values are **intervals**: a -12 to -9 dB band never becomes a measured -10.5 dB.
Unknowns are NaN with `valid=False`; invalid band indices are -1. Pixels explained
by a mixture of two adjacent bands have index -2 and the union of both intervals
(they never become an interpolated scalar). Set `allow_band_mixtures=false` to
disable this conservative boundary recovery. The preview
shows unknown pixels in gray and retains the source color of mixed-band pixels. Color distance is evidence, not a calibrated
probability of correctness.

Calibration JSON requires:

* `x` and `y`: `scale` (`linear` or `log10`), `unit`, and `anchors`, each an
  image-global `[pixel, value]` pair. Supply at least three independent ticks.
* `band_edges`: strictly increasing numeric edges; `unit` describes the field.
* Optional `plot_xywh` / `colorbar_xywh`: explicit image-global rectangles.
  Otherwise detection supports one large colored rectangle and one separate
  thin colorbar. Ambiguous layouts and neutral palettes need explicit boxes.
* `reverse_colorbar`: values decrease left-to-right or top-to-bottom.
* `band_boundaries`: normalized spatial boundaries from 0 to 1 in increasing
  value direction, required for unequal physical band widths. Default: equal
  widths. This is appropriate for the supplied RCF discrete bars.
* `extend_min` / `extend_max`: end bands are open-ended if the source clips them.
  NPZ bounds use infinities; JSON palette bounds use null, with the convention
  recorded in metadata. Do not assert clipping unless supported by the source.
* Optional `exclude_xywh`: known overprints to mark unknown, even if their color
  happens to match a palette band.

Repeated/indistinguishable palette colors are rejected. Outlines, gridlines and
anti-aliased boundary pixels that do not decode confidently remain unknown.
There is no automatic inpainting. Continuous gradients, line-only contours,
photographic perspective correction, and automatic colorbar OCR are not yet
supported. Geometry detection never guesses numerical limits.

Python callers can use `extract_field(image, config)`, then
`field.resample(frequencies, angles)` to obtain interval bounds and validity.
Resampling selects nearest native cells and preserves holes. It does not create
additional spatial or amplitude resolution. `field.contours(levels)` optionally
derives open paths, disconnected components and closed loops through marching
squares on band midpoints. These paths are marked `interpolated`; they are not
observations, and no cell with an unknown corner is traversed.

## Reproducible comparisons

```sh
OMP_NUM_THREADS=2 PYTHONPATH=src .venv/bin/python -m graphextract.benchmark \
  --count 12 --learned --output /tmp/graphextract-comparison.json
```

Without `--manifest`, this is a **synthetic tracking diagnostic**, with oracle
panel geometry, series count and colors explicitly recorded. The six frozen
families cover crossings, sharp notches, dashes, nearby hues, identical hues,
and JPEG/label overprints. Input hashes and per-series measurements are included.
Training uses a different seed from evaluation; both share rendering families,
so this is not evidence of generalization to unseen real chart styles.
`--learned` needs PyTorch; classical extraction does not.

The checked-in `benchmarks/robustness-v1.json` records one comparison. Primary
metrics are strict per-series pass, visible coverage, false support and native
pixel error. The contour diagnostic also reports interval containment, interval
width, coverage and false support for clean and JPEG-compressed fields. Coverage
counts unique reference columns; repeated predictions
cannot inflate it. Missing scores, extra identities, and false support prevent
strict panel acceptance. Background pixel accuracy is not the neural metric:
`segmentation_metrics` reports per-series precision, recall, F1 and IoU.

Real evaluation uses a version-1 JSON manifest with a `cases` list:

```json
{
  "version": 1,
  "cases": [{
    "id": "unique-image-id",
    "image": "relative/path/to/image.png",
    "annotation": "relative/path/to/locked-gold.json",
    "image_sha256": "sha256-of-original-file-bytes",
    "annotation_sha256": "sha256-of-annotation-file-bytes",
    "source_group": "measurement-source-and-rendering-family",
    "split": "locked_test"
  }]
}
```

Annotations use `corpus.ImageAnnotation`, `status="locked"`, dense native
centerlines, explicit occlusion intervals, unique semantic labels, and verified
axis ticks. Multi-panel ticks must include `panel_id`. Unsupported ambiguous
gold is not counted as success. Both file hashes are checked before evaluation.
Sources and identical images cannot cross train/dev/calibration/locked-test
splits; group related products, crops, resizes and recolorings under the same
source manually. The tool cannot detect every derivative of an image.

```sh
PYTHONPATH=src .venv/bin/python -m graphextract.benchmark \
  --manifest path/to/manifest.json --split locked_test \
  --tracker temporal --output /tmp/real-results.json
```

The extractor receives only the image; gold is used afterward for geometry,
identity, visible-support and calibration scoring. Panels are matched one-to-one
by geometry, curves by semantic labels, never by best-fitting shape. Wrong axes,
units, missing/extra series or panels all fail image completeness. The repository
does not yet contain a manually verified locked real-image accuracy corpus;
existing extraction JSON and overlays must not be relabeled as ground truth.

## Temporal and learned candidates

```sh
PYTHONPATH=src .venv/bin/python -m graphextract image.png --tracker temporal
```

Temporal search carries a beam of complete trajectory hypotheses, using native
color evidence and motion/curvature costs. Later columns can disambiguate an
earlier branch. Equally supported alternatives are exported and their differing
samples marked ambiguous. Blank columns stay missing. Legacy `--assumptions`
are intentionally incompatible with this backend rather than silently ignored.
Series are searched separately; this is not yet a global multi-series identity
solver. Exactly identical series colors require an independent identity constraint
and are marked ambiguous, even if a learned shape prior favors one assignment.

`MultiLabelConvSeg` uses independent sigmoid heads with dilated convolutions.
Overlaps retain all memberships during supervision. It is a fixed-series pilot,
not a palette-independent pretrained chart reader. Train with
`train_multilabel_segmentor(panels, series_ids)` on appropriately annotated images,
and save the returned model. Visible-mask targets describe visible evidence;
geometric targets describe potentially hidden paths and must be labeled as such
in an experiment. The bundled benchmark trains on visible masks.

```sh
PYTHONPATH=src .venv/bin/python -m graphextract image.png \
  --tracker temporal --segmentor checkpoint.pt \
  --curve 'Alpha=#D20000' --curve 'Beta=#0000D2'
```

Checkpoint series IDs must match selected panel IDs (`curve_1`, `curve_2`, ...
for explicit CLI colors). Checkpoint mismatch is an error. Native evidence gates
neural probabilities, preventing the model from declaring pixels observed where
the classical evidence has none. This also limits recovery of weak evidence.
Retrain/validate per deployment domain; no general-purpose checkpoint is shipped.

## Acceptance

Fit `ConfidenceCalibrator` on training outcomes, use `select_threshold` on an
independent calibration set, then call `validate_threshold` once with the frozen
threshold on an untouched test set. Use independent source-level cases, not
pixels or duplicated crops. Threshold selection uses simultaneous one-sided
exact binomial lower bounds (Bonferroni correction); held-out validation uses a
fixed-threshold bound. At 95% confidence, a 99.5% precision target requires about
598 accepted, independent, error-free held-out cases, and more if there are
errors. One successful image cannot substantiate that claim.

Pass the held-out `AcceptancePoint` to `auto_acceptable(panel, calibrator, point)`;
raw numeric thresholds and calibration-only selection results are rejected.
The runtime gate only accepts complete, calibrated panels with observed samples,
no unresolved review reasons, and no alternatives. New confidence features include
the weakest series and longest unsupported run. Old saved calibrators are
rejected with a refit message because their feature schema differs. Explicit
left/right logarithmic y scales are now available through `AxisAnchors`.

Run the regression suite with:

```sh
OMP_NUM_THREADS=2 .venv/bin/python -m pytest src/graphextract/tests -q
```
