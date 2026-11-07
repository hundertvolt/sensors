#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Serves the website prototype for `npm run preview`: 127.0.0.1 only, and only the paths the page loads - never the
repo root, .git/ or a spilled config file (SPECIFICATION.md Part H.2)."""

# Usage: uv run scripts/preview_server.py [--port N]
# Exit 0 on Ctrl-C, 1 when the port cannot be bound (one line naming --port), 2 on a usage error.

import argparse
import contextlib
import functools
import os
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

if TYPE_CHECKING:
    from io import BytesIO

REPO_ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
DEFAULT_PORT = 8000
_MAX_PORT = 65535
# The page's own directories (html/index.html imports ../js/, fetches the definitions and the mock data); nothing else.
SERVED_DIRS = ("html", "js", "mockdata", "build/generated_src/definitions")


class _SiteHandler(SimpleHTTPRequestHandler):
    # Answers 404 for every path that does not resolve, links followed, inside one of SERVED_DIRS.
    def send_head(self) -> "BytesIO | BinaryIO | None":
        if not _is_served(Path(self.directory), self.translate_path(self.path)):
            self.send_error(HTTPStatus.NOT_FOUND)
            return None
        return super().send_head()


def _is_served(root: Path, path: str) -> bool:
    real = os.path.realpath(path)
    for served in SERVED_DIRS:
        base = os.path.realpath(root / served)
        if real == base or real.startswith(base + os.sep):
            return True
    return False


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Serves the website prototype (html/, js/, mockdata/ and the generated definitions) on 127.0.0.1.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"the port to serve on (default: {DEFAULT_PORT}; 0 picks a free one)")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= _MAX_PORT:
        parser.error(f"--port {args.port} is not a port (0-{_MAX_PORT})")
    try:
        server = make_server(args.port, REPO_ROOT)
    except OSError as e:
        print(f"error: cannot serve on {HOST}:{args.port} ({e.strerror or e}) - pass a free port with --port", file=sys.stderr)
        return 1
    with server:
        print(f"Serving the website prototype at http://{HOST}:{server.server_address[1]}/html/index.html - Ctrl-C stops it")
        with contextlib.suppress(KeyboardInterrupt):
            server.serve_forever()
    return 0


def make_server(port: int, root: Path) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((HOST, port), functools.partial(_SiteHandler, directory=str(root)))


if __name__ == "__main__":
    raise SystemExit(main())
