"""
Tiny static server for auditioning the Sunnah Seed loop in a browser.

Serves the repository root so the preview page can fetch the WAV masters by
relative path, and redirects "/" to the preview page.

    python preview_server.py [port]
"""

from __future__ import annotations

import functools
import http.server
import os
import socketserver
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
HOME = "/assets/audio/sunnah-seed/index.html"


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", HOME)
            self.end_headers()
            return
        super().do_GET()

    def end_headers(self):
        # never block being embedded in the preview iframe, never cache audio
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):    # keep the console readable
        if "404" in (fmt % args) or "500" in (fmt % args):
            super().log_message(fmt, *args)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    handler = functools.partial(Handler, directory=ROOT)
    with Server(("0.0.0.0", port), handler) as httpd:
        print(f"Sunnah Seed preview  ->  http://0.0.0.0:{port}{HOME}")
        print(f"serving {ROOT}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
