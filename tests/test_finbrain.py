from copy import deepcopy

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from prediction_agent.api import app
from prediction_agent.config import Settings
from prediction_agent.db import enqueue, list_runs
from prediction_agent.providers import predict
from prediction_agent.worker import process_one

REAL_CLIENT = httpx.Client


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, app_token="test-token-with-at-least-24-characters",
                    database_path=str(tmp_path / "test.db"),
                    finbrain_enabled=True, finbrain_api_key="mock-secret")


@pytest.fixture
def payload():
    # Synthetic fixture shaped like the official v2 success example.
    return {"success": True, "data": {
        "symbol": "AAPL", "name": "Apple Inc.", "type": "daily",
        "predictions": [{"date": "2026-10-15", "mid": 250.0, "lower": 240.0, "upper": 260.0}],
        "metadata": {"expectedShortTerm": 1.0, "expectedMidTerm": 2.0,
                     "expectedLongTerm": 3.0, "lowerBoundChange": -4.0, "upperBoundChange": 5.0},
        "lastUpdated": "2026-10-14T08:00:00Z"}}


def mock_client(monkeypatch, handler):
    def client(**kwargs):
        assert kwargs["follow_redirects"] is False
        assert kwargs["timeout"] == 45
        return REAL_CLIENT(transport=httpx.MockTransport(handler), **kwargs)
    monkeypatch.setattr("prediction_agent.finbrain.httpx.Client", client)


def spec(**kwargs):
    return {"provider": "finbrain", "question": "Capture forecast", "symbol": "AAPL", **kwargs}


@pytest.mark.parametrize("horizon", ["daily", "monthly"])
def test_contract_and_persistence(monkeypatch, settings, payload, horizon):
    payload["data"]["type"] = horizon
    calls = []
    def handler(request):
        calls.append(request)
        assert request.method == "GET"
        assert str(request.url) == f"https://api.finbrain.tech/v2/predictions/{horizon}/AAPL"
        assert request.headers["Authorization"] == "Bearer mock-secret"
        return httpx.Response(200, json=payload)
    mock_client(monkeypatch, handler)
    enqueue(settings.database_path, spec(forecast_type=horizon))
    assert process_one(settings)
    row = list_runs(settings.database_path)[0]
    assert row["status"] == "completed"
    result = row["result"]
    assert result["forecast"]["predictions"][0]["mid"] == 250
    assert result["forecast"]["lastUpdated"] == payload["data"]["lastUpdated"]
    assert result["retrieved_at"]
    assert "probability" not in result
    assert result["cost_usd"] is None
    assert len(calls) == 1


@pytest.mark.parametrize("overrides", [
    {"finbrain_enabled": False}, {"finbrain_api_key": ""},
])
def test_disabled_or_missing_key_never_opens_client(monkeypatch, settings, overrides):
    for key, value in overrides.items():
        setattr(settings, key, value)
    mock_client(monkeypatch, lambda request: pytest.fail("Unexpected HTTP request"))
    with pytest.raises(ValueError):
        predict(spec(), settings)


@pytest.mark.parametrize("changes", [{"symbol": "../secret"}, {"symbol": None},
                                    {"forecast_type": "hourly"}])
def test_invalid_request_never_calls_api(monkeypatch, settings, changes):
    mock_client(monkeypatch, lambda request: pytest.fail("Unexpected HTTP request"))
    with pytest.raises(ValidationError):
        predict(spec(**changes), settings)


@pytest.mark.parametrize("status", [302, 400, 401, 403, 404, 429, 500])
def test_http_failure_single_call_and_redaction(monkeypatch, settings, status):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": "mock-secret"},
                              headers={"Location": "https://other.example", "Retry-After": "10"})
    mock_client(monkeypatch, handler)
    enqueue(settings.database_path, spec())
    assert process_one(settings)
    row = list_runs(settings.database_path)[0]
    assert row["status"] == "failed"
    assert row["error"] == "HTTPStatusError"
    assert "mock-secret" not in str(row)
    assert len(calls) == 1


@pytest.mark.parametrize("case", ["empty", "bounds", "nan", "wrong_symbol", "wrong_type",
                                 "failure", "missing", "duplicate", "no_timezone"])
def test_rejects_invalid_payload(monkeypatch, settings, payload, case):
    payload = deepcopy(payload)
    data = payload["data"]
    if case == "empty":
        data["predictions"] = []
    elif case == "bounds":
        data["predictions"][0]["lower"] = 300
    elif case == "nan":
        data["predictions"][0]["mid"] = "NaN"
    elif case == "wrong_symbol":
        data["symbol"] = "MSFT"
    elif case == "wrong_type":
        data["type"] = "monthly"
    elif case == "failure":
        payload["success"] = False
    elif case == "missing":
        del data["lastUpdated"]
    elif case == "duplicate":
        data["predictions"] *= 2
    elif case == "no_timezone":
        data["lastUpdated"] = "2026-10-14T08:00:00"
    mock_client(monkeypatch, lambda request: httpx.Response(200, json=payload))
    with pytest.raises(ValueError):
        predict(spec(), settings)


def test_timeout_and_invalid_json(monkeypatch, settings):
    def timeout(request):
        raise httpx.ReadTimeout("mock-secret", request=request)
    mock_client(monkeypatch, timeout)
    with pytest.raises(httpx.ReadTimeout):
        predict(spec(), settings)
    mock_client(monkeypatch, lambda request: httpx.Response(200, text="invalid-json"))
    with pytest.raises(ValueError):
        predict(spec(), settings)


def test_api_accepts_finbrain_and_validates_symbol(monkeypatch):
    monkeypatch.setenv("APP_TOKEN", "test-token-with-at-least-24-characters")
    # Avoid enqueue and any interaction with the real worker.
    monkeypatch.setattr("prediction_agent.api.enqueue", lambda path, value: "test-id")
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token-with-at-least-24-characters"}
    assert client.post("/api/runs", json=spec(), headers=headers).status_code == 202
    assert client.post("/api/runs", json=spec(symbol=None), headers=headers).status_code == 422


def test_unknown_provider_rejected(settings):
    with pytest.raises(ValueError, match="Unknown provider"):
        predict({"provider": "typo"}, settings)
