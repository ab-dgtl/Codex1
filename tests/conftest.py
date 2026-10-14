"""Tests must never reach a real provider, even if credentials exist locally."""
import httpx
import pytest


@pytest.fixture(autouse=True)
def deny_real_http(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("Real HTTP is forbidden in tests; use MockTransport or ASGITransport")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", deny)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", deny)
