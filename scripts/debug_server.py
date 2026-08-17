#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# https://gist.github.com/acdha/925e9ffc3d74ad59c3ea
#
"""
usage: "debug_server.py [--help] [--ip=<ip>] [--port=<port>]

Use instead of `python3 -m http.server` when you need CORS

Options:
  --help        display usage
  --ip=<ip>     ip to bind, default is localhost
  --port=<port> port to listen to, default is 8000
"""

import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
import argparse


class CORSRequestHandler(SimpleHTTPRequestHandler):
    """Generate CORS headers"""

    def do_GET(self):
        f = self.send_head()
        if f:
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        return super(CORSRequestHandler, self).end_headers()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A simple HTTP server with CORS headers.")
    parser.add_argument("--version", action="version", version="debug_server.py version 1.1")
    parser.add_argument("--ip", default="127.0.0.1", help="IP to bind, default is 127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen to, default is 8000")

    args = parser.parse_args()

    ip = args.ip
    port = args.port

    try:
        httpd = HTTPServer((ip, port), CORSRequestHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("... Bye")
        sys.exit(0)
    sys.exit(1)
