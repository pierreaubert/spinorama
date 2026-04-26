#!/usr/bin/env python3
"""Dump the headphone database to JSON for the TypeScript editor app.

Reads ``datas.headphones.headphones_info`` and writes a flat list to
``data/headphones.json`` next to this script (resolved relative to the app
root, ``tools/headphone-image-editor``).

Each entry is::

    {
      "key": "ABYSS Headphones AB-1266 Phi TC",
      "brand": "ABYSS Headphones",
      "model": "AB-1266 Phi TC",
      "shape": "over-ear",
      "price": "4995.00",          # optional
      "picture": "ABYSS Headphones AB-1266 Phi TC.jpg"  # filename if found, else null
    }
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
APP_ROOT = HERE.parent
REPO_ROOT = APP_ROOT.parent.parent

# Make `import datas` resolve to <repo>/datas without requiring the user to
# install the package.
sys.path.insert(0, str(REPO_ROOT))

from datas.headphones import headphones_info  # noqa: E402  (after sys.path tweak)


PICTURES_DIR = REPO_ROOT / "datas" / "pictures"
OUT_PATH = APP_ROOT / "data" / "headphones.json"


def find_picture(key: str) -> str | None:
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        candidate = PICTURES_DIR / f"{key}{ext}"
        if candidate.is_file():
            return candidate.name
    return None


def main() -> int:
    entries = []
    for key, hp in headphones_info.items():
        if hp.get("skip"):
            continue
        entry = {
            "key": key,
            "brand": hp.get("brand", ""),
            "model": hp.get("model", ""),
            "shape": hp.get("shape", ""),
            "picture": find_picture(key),
        }
        if "price" in hp:
            entry["price"] = hp["price"]
        entries.append(entry)

    entries.sort(key=lambda e: (e["brand"].lower(), e["model"].lower()))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with_picture = sum(1 for e in entries if e["picture"])
    print(
        f"Wrote {len(entries)} headphones to {OUT_PATH.relative_to(APP_ROOT)} "
        f"({with_picture} with picture, {len(entries) - with_picture} missing)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
