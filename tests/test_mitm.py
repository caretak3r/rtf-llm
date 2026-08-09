#!/usr/bin/env python3
"""End-to-end tests for the stdlib MITM proxy backend."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from modules.engine.backends.mitm_proxy import MITMProxy

UPSTREAM_RESPONSE = {"id": "chatcmpl-1", "choices": [{"message": {"content": "assistant reply"}}]}


class UpstreamHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length)
        self.server.ref_requests.append(json.loads(body) if body else None)
        payload = json.dumps(UPSTREAM_RESPONSE).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):  # noqa: N802
        payload = json.dumps({"models": ["fake"]}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def start_upstream(ref_requests):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
    srv.ref_requests = ref_requests
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def open_chat(proxy_port):
    req = Request(
        f"http://127.0.0.1:{proxy_port}/v1/chat/completions",
        data=json.dumps({"model": "t", "messages": [{"role": "user", "content": "hi"}]}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req) as resp:
        return resp.status, json.loads(resp.read())


def test_passthrough_forwards_and_records():
    ref_requests = []
    upstream = start_upstream(ref_requests)
    try:
        with MITMProxy(f"http://127.0.0.1:{upstream.server_address[1]}") as proxy:
            status, data = open_chat(proxy.port)
        assert status == 200
        assert data["choices"][0]["message"]["content"] == "assistant reply"
        assert ref_requests == [{"model": "t", "messages": [{"role": "user", "content": "hi"}]}]
        assert len(proxy.shared["requests"]) == 1
        assert len(proxy.shared["responses"]) == 1
    finally:
        upstream.shutdown()
        upstream.server_close()


def test_request_hook_mutates_payload():
    ref_requests = []
    upstream = start_upstream(ref_requests)
    try:

        def inject(payload):
            payload["tool_injected"] = True
            return payload

        with MITMProxy(
            f"http://127.0.0.1:{upstream.server_address[1]}", request_hook=inject
        ) as proxy:
            open_chat(proxy.port)
        assert ref_requests[0]["tool_injected"] is True
    finally:
        upstream.shutdown()
        upstream.server_close()


def test_response_hook_injects_response():
    ref_requests = []
    upstream = start_upstream(ref_requests)
    try:

        def replace(status, payload):
            return 200, {"choices": [{"message": {"content": "INJECTED: malicious follow-up"}}]}

        with MITMProxy(
            f"http://127.0.0.1:{upstream.server_address[1]}", response_hook=replace
        ) as proxy:
            _, data = open_chat(proxy.port)
        assert data["choices"][0]["message"]["content"].startswith("INJECTED")
    finally:
        upstream.shutdown()
        upstream.server_close()


def test_broken_upstream_yields_502():
    upstream = start_upstream([])
    port = upstream.server_address[1]
    upstream.shutdown()
    upstream.server_close()
    try:
        with MITMProxy(f"http://127.0.0.1:{port}") as proxy:
            try:
                open_chat(proxy.port)
            except HTTPError as e:
                assert e.code == 502
            else:
                raise AssertionError("expected 502")
    finally:
        pass
