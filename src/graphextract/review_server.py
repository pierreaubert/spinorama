#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal local review server (stdlib only): collects posted corrections.

Usage:
    ../../.venv/bin/python review_server.py --bundle review.html --port 8321 \
        --out corrections/

Then open http://localhost:8321/ in a browser. POST /corrections appends one
JSON line per correction to <out>/<panel>.jsonl. Nothing here retrains models
or touches locked test data; promotion happens through shadow.py only.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def store_correction(out_dir: Path, corr: dict) -> Path:
    """Validate and append one correction; returns the jsonl path."""
    if not isinstance(corr, dict) or "panel_id" not in corr or "target" not in corr:
        raise ValueError("correction needs 'panel_id' and 'target'")
    panel = str(corr["panel_id"]).replace("#", "_")
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{panel}.jsonl"
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(corr) + "\n")
    return p


class Handler(BaseHTTPRequestHandler):
    bundle: Path = Path("review.html")
    out_dir: Path = Path("corrections")

    def log_message(self, *args):  # quieter logs
        pass

    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        body = self.bundle.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/corrections":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            store_correction(self.out_dir, json.loads(raw))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"recorded")
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"rejected: {exc}".encode())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--port", type=int, default=8321)
    ap.add_argument("--out", type=Path, default=Path("corrections"))
    args = ap.parse_args()
    Handler.bundle = args.bundle
    Handler.out_dir = args.out
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"serving {args.bundle} at http://127.0.0.1:{args.port}/")
    srv.serve_forever()


if __name__ == "__main__":
    main()
