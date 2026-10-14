import secrets
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, model_validator

from .config import Settings
from .db import enqueue, list_runs

app = FastAPI(title="Prediction Agent", docs_url=None, redoc_url=None, openapi_url=None)
bearer = HTTPBearer()


class Experiment(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    provider: Literal["demo", "http", "finbrain"] = "demo"
    analyze: bool = False
    symbol: str | None = Field(default=None, pattern=r"^[A-Z0-9][A-Z0-9.\-]{0,19}$")
    forecast_type: Literal["daily", "monthly"] = "daily"

    @model_validator(mode="after")
    def require_symbol(self):
        if self.provider == "finbrain" and not self.symbol:
            raise ValueError("FinBrain requires a symbol")
        return self


def auth(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    settings = Settings()
    if not secrets.compare_digest(credentials.credentials, settings.app_token):
        raise HTTPException(401, "Invalid token")
    return settings


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return (Path(__file__).parent / "templates/dashboard.html").read_text()


@app.get("/api/runs")
def runs(settings=Depends(auth)):
    return list_runs(settings.database_path)


@app.post("/api/runs", status_code=202)
def create_run(spec: Experiment, settings=Depends(auth)):
    return {"id": enqueue(settings.database_path, spec.model_dump()), "status": "queued"}

