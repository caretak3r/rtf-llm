#!/usr/bin/env python3
"""Plan 052 Step 1: MITM proxy refuses cleartext downgrades of https requests
and speaks TLS to https upstreams unless allow_insecure_upstream=True."""

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from modules.engine.backends.mitm_proxy import MITMProxy


class UpstreamHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0) or 0)
        self.rfile.read(length)
        payload = json.dumps({"ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def post(proxy_port, headers=None):
    req = Request(
        f"http://127.0.0.1:{proxy_port}/v1/chat/completions",
        data=json.dumps({"messages": []}).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        resp = urlopen(req, timeout=5)
        return resp.status, resp.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def test_https_request_to_http_upstream_gets_502():
    upstream = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    try:
        with MITMProxy(f"http://127.0.0.1:{upstream.server_address[1]}") as proxy:
            status, body = post(proxy.port, {"X-Forwarded-Proto": "https"})
        assert status == 502
        assert b"allow_insecure_upstream" in body
    finally:
        upstream.shutdown()
        upstream.server_close()


def test_downgrade_allowed_with_explicit_flag():
    upstream = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    try:
        with MITMProxy(
            f"http://127.0.0.1:{upstream.server_address[1]}",
            allow_insecure_upstream=True,
        ) as proxy:
            status, body = post(proxy.port, {"X-Forwarded-Proto": "https"})
        assert status == 200
        assert json.loads(body) == {"ok": True}
    finally:
        upstream.shutdown()
        upstream.server_close()


def test_https_upstream_uses_tls_connection(monkeypatch):
    created = []

    class FakeTLSConn:
        def __init__(self, host, timeout=None):
            created.append(host)

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            body = b"{}"

            class Resp:
                status = 200

                @staticmethod
                def getheaders():
                    return [("Content-Type", "application/json")]

                @staticmethod
                def read():
                    return body

            return Resp()

        @staticmethod
        def close():
            pass

    monkeypatch.setattr(http.client, "HTTPSConnection", FakeTLSConn)
    with MITMProxy("https://tls.example/v1") as proxy:
        status, _ = post(proxy.port)
    assert status == 200
    assert created == ["tls.example"]
