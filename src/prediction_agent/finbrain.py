"""FinBrain v2 price forecasts; no fabricated event probabilities.

Contract: https://finbrain.tech/api-reference/ticker-predictions/
"""
from datetime import date, datetime, timezone
from typing import Annotated, Literal

import httpx
from pydantic import BaseModel, Field, model_validator

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class FinBrainRequest(BaseModel):
    symbol: str = Field(pattern=r"^[A-Z0-9][A-Z0-9.\-]{0,19}$")
    forecast_type: Literal["daily", "monthly"] = "daily"


class PricePoint(BaseModel):
    date: date
    mid: Number
    lower: Number
    upper: Number

    @model_validator(mode="after")
    def ordered_bounds(self):
        if not self.lower <= self.mid <= self.upper:
            raise ValueError("Invalid forecast bounds")
        return self


class Moves(BaseModel):
    expectedShortTerm: Number
    expectedMidTerm: Number
    expectedLongTerm: Number
    lowerBoundChange: Number
    upperBoundChange: Number


class ForecastData(BaseModel):
    symbol: str
    name: str
    type: Literal["daily", "monthly"]
    predictions: list[PricePoint] = Field(min_length=1, max_length=366)
    metadata: Moves
    lastUpdated: datetime

    @model_validator(mode="after")
    def validate_dates(self):
        dates = [point.date for point in self.predictions]
        if dates != sorted(set(dates)):
            raise ValueError("Forecast dates must be unique and increasing")
        if self.lastUpdated.tzinfo is None:
            raise ValueError("lastUpdated must include a timezone")
        return self


class ForecastResponse(BaseModel):
    success: Literal[True]
    data: ForecastData


def predict_finbrain(spec, settings):
    # This guard also applies to jobs enqueued before configuration changed.
    if not settings.finbrain_enabled:
        raise ValueError("FinBrain access is disabled")
    if not settings.finbrain_api_key.strip():
        raise ValueError("FINBRAIN_API_KEY is required")
    request = FinBrainRequest.model_validate(spec)
    url = f"https://api.finbrain.tech/v2/predictions/{request.forecast_type}/{request.symbol}"
    # Fixed origin; key only in header; one request, no redirects or retries.
    with httpx.Client(timeout=45, follow_redirects=False) as client:
        response = client.get(url, headers={"Authorization": f"Bearer {settings.finbrain_api_key}"})
        response.raise_for_status()
        forecast = ForecastResponse.model_validate(response.json()).data
    if forecast.symbol != request.symbol or forecast.type != request.forecast_type:
        raise ValueError("Response does not match the requested forecast")
    return {
        "provider": "finbrain", "kind": "price_forecast",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "forecast": forecast.model_dump(mode="json"),
        # Subscription allocation is unknown; never report this as free.
        "cost_usd": None,
    }
