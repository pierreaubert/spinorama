#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe: text-level tick/legend recovery on annotated graph images.

Compares Tesseract words vs jina-ocr-v1 transcriptions against the panel
JSON ground truth (axis anchors + series labels). No geometry is scored:
this answers "can the model read the text at all" before any integration.

Split-workflow friendly: transcribe on the CUDA box, score anywhere::

    # cuda box (or mac)
    ./scripts/jina_ocr_run.py --images src/graphextract/datas/graph-cea2034 --out /tmp/jina_txt
    # anywhere
    ./scripts/jina_ocr_probe.py --images src/graphextract/datas/graph-cea2034 \\
        --transcriptions /tmp/jina_txt --out /tmp/probe.json

Step 1 (baseline, no model download): omit --transcriptions.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from graphextract.jina_ocr import extract_legend_candidates, extract_number_tokens

NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?\s*[kK]?")


def parse_numbers(texts: list[str]) -> list[float]:
    out: list[float] = []
    for text in texts:
        for match in NUMBER_RE.findall(text):
            token = match.strip()
            mult = 1.0
            if token[-1:] in ("k", "K"):
                mult = 1000.0
                token = token[:-1].strip()
            try:
                out.append(float(token) * mult)
            except ValueError:
                continue
    return out


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def load_ground_truth(ann_path: Path) -> tuple[set[float], set[str]]:
    """Tick values and series labels from a panel-schema annotation file."""
    ticks: set[float] = set()
    labels: set[str] = set()
    try:
        doc = json.loads(ann_path.read_text())
    except (OSError, json.JSONDecodeError):
        return ticks, labels
    for panel in doc.get("panels", []):
        for axis in (panel.get("axes") or {}).values():
            if not isinstance(axis, dict):
                continue
            for anchor in axis.get("anchors_used", []):
                try:
                    ticks.add(float(anchor["value"]))
                except (KeyError, TypeError, ValueError):
                    continue
        series = panel.get("series") or []
        for entry in series:
            label = (entry.get("label") or "").strip() if isinstance(entry, dict) else ""
            if label:
                labels.add(label)
    return ticks, labels


def tesseract_words(image_path: Path) -> tuple[list[str], str]:
    """Return (word texts, status). Status is 'ok' or 'ocr_unavailable'."""
    try:
        import cv2
    except ImportError:
        return [], "no_cv2"
    from graphextract.ocr_adapters import OCRError, TesseractOCR

    provider = TesseractOCR()
    if not provider.available:
        return [], "ocr_unavailable"
    gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return [], "unreadable_image"
    try:
        words = provider.read_words(gray)
    except OCRError:
        return [], "ocr_unavailable"
    return [w.text for w in words], "ok"


def score_numbers(expected: set[float], got: list[float]) -> dict:
    hits = 0
    for value in expected:
        if any(abs(g - value) <= max(1e-9, abs(value) * 1e-3) for g in got):
            hits += 1
    return {"expected": len(expected), "hits": hits,
            "recall": hits / len(expected) if expected else 1.0}


def score_labels(expected: set[str], text_blob: str) -> dict:
    blob = norm(text_blob)
    hits = sum(1 for label in expected if norm(label) in blob)
    return {"expected": len(expected), "hits": hits,
            "recall": hits / len(expected) if expected else 1.0}


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe OCR text recovery on graphs")
    parser.add_argument("--images", type=Path, required=True,
                        help="Dir with *.png + sibling *.json annotations")
    parser.add_argument("--transcriptions", type=Path, default=None,
                        help="Dir of <stem>.md from jina_ocr_run.py --out")
    parser.add_argument("--out", type=Path, default=None, help="JSON report path")
    parser.add_argument("--limit", type=int, default=0, help="Max images (0=all)")
    args = parser.parse_args()

    pngs = sorted(p for p in args.images.glob("*.png") if p.is_file())
    if args.limit:
        pngs = pngs[: args.limit]
    results = []
    for png in pngs:
        expected_ticks, expected_labels = load_ground_truth(png.with_suffix(".json"))
        words, tess_status = tesseract_words(png)
        tess_numbers = parse_numbers(words)
        entry = {
            "image": png.name,
            "n_truth_ticks": len(expected_ticks),
            "n_truth_labels": len(expected_labels),
            "tesseract": {
                "status": tess_status,
                "n_words": len(words),
                "ticks": score_numbers(expected_ticks, tess_numbers),
                "legends": score_labels(expected_labels, " ".join(words)),
            },
        }
        if args.transcriptions is not None:
            md = args.transcriptions / f"{png.stem}.md"
            if md.is_file():
                text = md.read_text()
                entry["jina"] = {
                    "status": "ok",
                    "ticks": score_numbers(expected_ticks, extract_number_tokens(text)),
                    "legends": score_labels(expected_labels, " ".join(
                        extract_legend_candidates(text)) + " " + text),
                    "legend_names_found": extract_legend_candidates(text),
                }
            else:
                entry["jina"] = {"status": "missing_transcription"}
        results.append(entry)

    def mean(key: str, sub: str) -> float:
        vals = [r[key][sub]["recall"] for r in results
                if sub in r.get(key, {}) and r[key][sub].get("expected")]
        return sum(vals) / len(vals) if vals else float("nan")

    summary = {
        "n_images": len(results),
        "tesseract_tick_recall": mean("tesseract", "ticks"),
        "tesseract_legend_recall": mean("tesseract", "legends"),
    }
    if args.transcriptions is not None:
        summary["jina_tick_recall"] = mean("jina", "ticks")
        summary["jina_legend_recall"] = mean("jina", "legends")
    print(json.dumps(summary, indent=2))
    for entry in results:
        tess = entry["tesseract"]
        line = (f"{entry['image']}: tess[{tess['status']}] "
                f"ticks={tess['ticks']['hits']}/{tess['ticks']['expected']} "
                f"legends={tess['legends']['hits']}/{tess['legends']['expected']}")
        if "jina" in entry and entry["jina"].get("status") == "ok":
            line += (f" | jina ticks={entry['jina']['ticks']['hits']}/"
                     f"{entry['jina']['ticks']['expected']} "
                     f"legends={entry['jina']['legends']['hits']}/"
                     f"{entry['jina']['legends']['expected']}")
        print(line)
    if args.out is not None:
        args.out.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
        print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
