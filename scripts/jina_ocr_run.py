#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Launcher: download jinaai/jina-ocr-v1 and run it on graph images.

Works on macOS (mps/cpu) and CUDA Linux. Uses the project .venv::

    source .venv/bin/activate
    ./scripts/jina_ocr_run.py --install-deps      # once: torch mirror deps
    ./scripts/jina_ocr_run.py --download-only     # once: ~6.7 GB download
    ./scripts/jina_ocr_run.py --image path/to/graph.png
    ./scripts/jina_ocr_run.py --images src/graphextract/datas/graph-cea2034 --out /tmp/jina_txt

Notes: weights are CC-BY-NC-4.0, acceptable here (open source, no business).
Needs trust_remote_code.
Model cache: default HF cache; override with HF_HOME (e.g.
HF_HOME=/Volumes/data/Binaries/hfcache on the linux box).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from graphextract.jina_ocr import GRAPH_PROMPT, MODEL_ID, JinaOCRReader, pick_device

DEPS = ["torch", "torchvision", "transformers", "huggingface_hub", "accelerate", "Pillow"]


def install_deps() -> None:
    import subprocess

    print("Installing into current environment:", " ".join(DEPS))
    subprocess.check_call([sys.executable, "-m", "pip", "install", *DEPS])


def download(model_id: str, model_dir: str | None) -> str:
    from huggingface_hub import snapshot_download

    print(f"Downloading {model_id} (~6.7 GB) ...")
    started = time.time()
    local = snapshot_download(repo_id=model_id, local_dir=model_dir or None)
    print(f"Done in {time.time() - started:.0f}s -> {local}")
    return local


def run_images(args: argparse.Namespace) -> int:
    reader = JinaOCRReader(
        model_id=args.model,
        model_dir=args.model_dir,
        device=None if args.device == "auto" else args.device,
        max_new_tokens=args.max_new_tokens,
    )
    targets: list[Path] = []
    if args.image is not None:
        targets = [args.image]
    else:
        targets = sorted(p for p in args.images.glob("*.png") if p.is_file())
    if not targets:
        print("No images found", file=sys.stderr)
        return 1
    out_dir = Path(args.out) if args.out else None
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    for img in targets:
        try:
            started = time.time()
            text = reader.transcribe(
                str(img), prompt=GRAPH_PROMPT if args.graph_prompt else None
            )
            elapsed = time.time() - started
        except Exception as exc:  # noqa: BLE001 -- report per image, keep going
            print(f"[FAIL] {img}: {exc}", file=sys.stderr)
            failures += 1
            continue
        print(f"--- {img} ({elapsed:.1f}s, device={reader.device}) ---")
        print(text)
        if out_dir is not None:
            (out_dir / f"{img.stem}.md").write_text(text + "\n")
    summary = {"model": args.model, "device": reader.device, "n": len(targets),
               "failures": failures}
    print(json.dumps(summary))
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Download + run jina-ocr-v1")
    parser.add_argument("--model", default=MODEL_ID)
    parser.add_argument("--model-dir", default=None,
                        help="Snapshot dir (default: HF cache)")
    parser.add_argument("--device", default="auto",
                        help="auto (cuda>mps>cpu), cuda, cuda:0, mps, cpu")
    parser.add_argument("--max-new-tokens", type=int, default=1024)
    parser.add_argument("--image", type=Path, default=None)
    parser.add_argument("--images", type=Path, default=None,
                        help="Directory of .png files")
    parser.add_argument("--out", default=None, help="Write .md transcriptions here")
    parser.add_argument("--graph-prompt", action="store_true",
                        help="Graph-tuned prompt (tick labels, legends, plain text)")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--install-deps", action="store_true",
                        help="pip install runtime deps into the current env")
    args = parser.parse_args()

    if args.install_deps:
        install_deps()
        if args.image is None and args.images is None and not args.download_only:
            return 0
    if args.download_only:
        download(args.model, args.model_dir)
        return 0
    if args.image is None and args.images is None:
        # Default action with no target: just fetch the weights.
        download(args.model, args.model_dir)
        return 0
    if args.model_dir is None:
        # Ensure weights are cached before torch/transformers import.
        try:
            download(args.model, None)
        except Exception as exc:  # noqa: BLE001 -- offline cache may already exist
            print(f"Download skipped/failed ({exc}); trying local cache ...")
    print(f"Device: {pick_device(None if args.device == 'auto' else args.device)}")
    return run_images(args)


if __name__ == "__main__":
    raise SystemExit(main())
