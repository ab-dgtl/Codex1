import httpx
from fastapi.testclient import TestClient

from prediction_agent.api import app
from prediction_agent.config import Settings
from prediction_agent.db import enqueue, list_runs
from prediction_agent.providers import predict
from prediction_agent.telegram import command
from prediction_agent.worker import process_one


def setup(monkeypatch, tmp_path):
    monkeypatch.setenv('APP_TOKEN', 'test-token-with-at-least-24-characters')
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'agent.db'))
    return Settings(_env_file=None)


def test_api_worker_pipeline(monkeypatch, tmp_path):
    settings = setup(monkeypatch, tmp_path)
    client = TestClient(app)
    assert client.get('/api/runs').status_code == 403
    assert client.get('/api/runs', headers={'Authorization': 'Bearer wrong'}).status_code == 401
    headers = {'Authorization': 'Bearer ' + settings.app_token}
    assert client.post('/api/runs', json={'question': 'Will it happen?'}, headers=headers).status_code == 202
    assert process_one(settings)
    row = client.get('/api/runs', headers=headers).json()[0]
    assert row['status'] == 'completed'
    assert row['result']['probability'] == 0.5
    assert not process_one(settings)
    assert client.post('/api/runs', json={'question': 'x'}, headers=headers).status_code == 422
    assert client.get('/').status_code == 200


def test_failures_are_redacted(monkeypatch, tmp_path):
    settings = setup(monkeypatch, tmp_path)
    enqueue(settings.database_path, {'question': 'Will it happen?', 'provider': 'http'})
    assert process_one(settings)
    row = list_runs(settings.database_path)[0]
    assert row['status'] == 'failed'
    assert row['error'] == 'ValueError'


def test_http_contract(monkeypatch, tmp_path):
    settings = setup(monkeypatch, tmp_path)
    settings.provider_url = 'https://service.example/predict'
    settings.provider_allowed_hosts = 'service.example'
    def handler(request):
        assert request.method == 'POST'
        return httpx.Response(200, json={'probability': 0.7, 'rationale': 'Evidence'})
    real_client = httpx.Client
    monkeypatch.setattr('prediction_agent.providers.httpx.Client',
                        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    assert predict({'question': 'Will it happen?', 'provider': 'http'}, settings)['probability'] == 0.7


def test_telegram_commands(monkeypatch, tmp_path):
    settings = setup(monkeypatch, tmp_path)
    assert command('/run Will it happen?', settings.database_path).startswith('Queued:')
    assert 'queued' in command('/runs', settings.database_path)
