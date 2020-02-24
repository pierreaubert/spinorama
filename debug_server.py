#!/usr/bin/env python3
# encoding: utf-8
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
from docopt import docopt
from http.server import HTTPServer, SimpleHTTPRequestHandler


class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super(CORSRequestHandler, self).end_headers()


if __name__ == '__main__':

    args = docopt(__doc__,
                  version='debug_servers.py version 1.1',
                  options_first=True)

    ip = '127.0.0.1'
    port = 8000

    if args['--ip'] is not None:
        ip = args['--ip']

    if args['--port'] is not None:
        port = int(args['--port'])
    
    httpd = HTTPServer((ip, port), CORSRequestHandler)
    httpd.serve_forever()
