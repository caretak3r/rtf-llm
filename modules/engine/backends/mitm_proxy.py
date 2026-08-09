"""Stdlib MIT(MITM) proxy backend for OpenAI-compatible traffic.

Small HTTP server that sits between a client and an upstream API and runs
mutation hooks over both the request and the response JSON payloads. Used
for response-injection evaluation and delayed-tool-use testing. Patten
source: LLM-itM. No third-party dependencies.
"""

from __future__ import annotations

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


class MITMProxy:
    """Intercepts OpenAI-compatible traffic with pluggable mutation hooks."""

    def __init__(
        self,
        upstream_url: str,
        host: str = "127.0.0.1",
        port: int = 0,
        request_hook=None,
        response_hook=None,
    ) -> None:
        self._upstream = urlparse(upstream_url)
        self._request_hook = request_hook
        self._response_hook = response_hook
        self._shared = {"requests": [], "responses": []}
        self._server = ThreadingHTTPServer((host, port), self._handler_factory())
        self.port = self._server.server_address[1]

    def _handler_factory(self):
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):  # silent
                pass

            def do_POST(self):  # noqa: N802
                self._route("POST")

            def do_GET(self):  # noqa: N802
                self._route("GET")

            def _route(self, method: str):
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length) if length else b""

                # Surface to hooks (JSON when possible).
                try:
                    payload = json.loads(body) if body else None
                except ValueError:
                    payload = None

                if payload is not None and proxy._request_hook:
                    payload = proxy._request_hook(payload)
                    body = json.dumps(payload).encode()

                upstream = proxy._upstream
                conn = http.client.HTTPConnection(upstream.netloc, timeout=30)
                path = upstream.path or "/"
                headers = {
                    k: v
                    for k, v in self.headers.items()
                    if k.lower() not in ("host", "content-length")
                }
                try:
                    conn.request(
                        method,
                        path + ("?" + upstream.query if upstream.query else ""),
                        body=body,
                        headers=headers,
                    )
                    resp = conn.getresponse()
                    rbody = resp.read()
                except (OSError, http.client.HTTPException) as exc:
                    self.send_response(502)
                    self.end_headers()
                    self.wfile.write(str(exc).encode())
                    return
                finally:
                    conn.close()

                status, rbody = proxy._apply_response_hook(
                    resp.status, dict(resp.getheaders()), rbody
                )
                proxy._shared["requests"].append(
                    {"method": method, "path": self.path, "body": payload}
                )
                proxy._shared["responses"].append({"status": status, "body": rbody[:51200]})

                self.send_response(status)
                for k, v in resp.getheaders():
                    if k.lower() not in ("content-length", "transfer-encoding", "connection"):
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(rbody)))
                self.end_headers()
                self.wfile.write(rbody)

        return Handler

    def _apply_response_hook(self, status, headers, raw: bytes) -> tuple[int, bytes]:
        if not self._response_hook:
            return status, raw
        try:
            payload = json.loads(raw) if raw else None
        except ValueError:
            payload = None
        result = self._response_hook(status, payload)
        if result is None:
            return status, raw
        new_status, new_payload = result
        if isinstance(new_payload, (dict, list)):
            return new_status, json.dumps(new_payload).encode()
        return new_status, (
            new_payload if isinstance(new_payload, bytes) else str(new_payload).encode()
        )

    @property
    def shared(self) -> dict:
        """Captured (request, response) pairs for assertions and transcripts."""
        return self._shared

    def __enter__(self):
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()
