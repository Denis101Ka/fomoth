"""Tiny stdlib backend for the site. Serves the frontend and one JSON endpoint.

    GET /                      the page
    GET /api/report?wallet=X   the fumble report, cached per wallet on disk

The Solana Tracker key lives only here, server side, read from SOLANATRACKER_KEY. The browser
never sees it. Reports are cached so a repeat lookup and the free-tier limit are both respected.

    SOLANATRACKER_KEY=... python -m fomoth.server 8080
"""
from __future__ import annotations

import json
import pathlib
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .api import SolanaTracker
from .report import build, to_dict

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
CACHE = ROOT / "_scratch" / "reports"
CACHE.mkdir(parents=True, exist_ok=True)
WALLET_RE = __import__("re").compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/report":
            wallet = (parse_qs(u.query).get("wallet") or [""])[0].strip()
            if not WALLET_RE.match(wallet):
                return self._send(400, json.dumps({"error": "invalid wallet"}))
            cf = CACHE / f"{wallet}.json"
            if cf.exists():
                return self._send(200, cf.read_bytes())
            try:
                data = to_dict(build(wallet, SolanaTracker()))
            except Exception as e:
                return self._send(502, json.dumps({"error": str(e)}))
            cf.write_text(json.dumps(data), encoding="utf-8")
            return self._send(200, json.dumps(data))

        path = "index.html" if u.path in ("/", "") else u.path.lstrip("/")
        f = WEB / path
        if f.is_file() and WEB in f.resolve().parents:
            ct = "text/html" if f.suffix == ".html" else "text/plain"
            return self._send(200, f.read_bytes(), ct)
        return self._send(404, "not found", "text/plain")


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"fomoth on http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
