Store reproducible experiment specs here, never API keys or paid proprietary responses.
POST a spec to /api/runs. The demo provider is synthetic. Add service-specific adapters
in providers.py; record service, plan, collection time, forecast horizon and actual
outcome before comparing accuracy, Brier score, calibration, latency and subscription cost.
The starter stores results but does not yet resolve outcomes or compute these metrics.
