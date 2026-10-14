# Prediction API pilot — 14 October 2026

Official documentation and published access terms only. No account was created,
no subscription purchased and no provider API request made. API presence does
not establish predictive quality. Website subscriptions and API plans differ.

| Service | Forecast/product | Official API and credentials | Access cost | Constraints and pilot fit |
| --- | --- | --- | --- | --- |
| FinBrain | ARIMA price forecasts with bounds; equities, FX, crypto, commodities | REST v2; Bearer API key | Enterprise quote, no public dollar amount; scoped 30-day free institutional evaluation | Trial 2,000 requests/hour; production limits negotiated. Daily refresh. Daily forecast ~10 days, monthly ~12 months. No historical forecast archive. Best first cross-asset technical pilot, conditional on trial approval. |
| Danelfin | AI stock scores, trade ideas and price forecasts; US stocks/ETFs and main European stocks | REST, x-api-key; /ranking and /v3/price-forecast | Free: 500 calls/month. Basic $52/month equivalent paid $624/year; Expert $149/month equivalent paid $1,788/year; Max $449/month equivalent paid $5,388/year | Free 10/min, Basic 60/min, Expert 120/min, Max 180/min. API plans separate from website. Scores have history, but v3 forecast endpoints return latest snapshot only. Best inexpensive equities-only fallback. |
| AltIndex | Alternative-data stock scores and research signals | REST v2, X-API-Key (v2_ prefix) | Hobbyist $19/month; Developer $79/month; Research $199/month; Enterprise quote | Hobbyist 250/day, 20/min, 30-day history, 1 ticker/call, evaluation/personal use. Developer 1,000/day, 300/min, 2-year history. Research 10,000/day, 50 tickers/call, internal commercial use. Scores are not calibrated event probabilities. API docs describe seven families while pricing says six: confirm entitlements. |
| Token Metrics | Crypto grades, AI trading signals and research | Official developer API documentation exists; API key required | Official launch material advertised paid access from $99/month and a free tier; CURRENT checkout price not verified | Official older comparison advertised free 5,000/month and 1/min; other launch material says limited free endpoints. Current quota/endpoint entitlement needs confirmation. Pricing URL returned 404 and selected docs were inaccessible. Crypto-specific second-stage candidate, not selected on unverified terms. |

## Sources

- FinBrain contract: https://finbrain.tech/api-reference/ticker-predictions/
- FinBrain current methodology and coverage: https://finbrain.tech/datasets/ai-forecasts/
- FinBrain licensing, evaluation and limits: https://finbrain.tech/pricing/
- Danelfin annual API pricing: https://danelfin.com/pricing/api/annual
- Danelfin contracts: https://danelfin.com/docs/api
- AltIndex pricing: https://altindex.com/pricing
- AltIndex API access/limits: https://developers.altindex.com/v2
- Token Metrics documentation: https://developers.tokenmetrics.com/
- Token Metrics launch (May 2025; not current checkout): https://research.tokenmetrics.com/p/the-token-metrics-api-is-live-build-smarter-trade-smarter-72ba
- Token Metrics older quota comparison: https://www.tokenmetrics.com/blog/token-metrics-api-vs-coingecko-api-which-crypto-api-should-you-choose-in-2025

## Decision and real connection

Select FinBrain for its cross-asset coverage, explicit dated price path and short
evaluation horizon. This is a technical selection, not evidence that its forecasts
are accurate. Although older API text calls these AI-powered, the current dataset
page specifies ARIMA. It is useful as a statistical paid-service benchmark.

Before activation obtain a scoped trial/Enterprise API key with price-forecast
entitlements, confirm supported equities and crypto ticker identifiers through
the official available-markets/tickers contract, quote currency, update timezone,
interval confidence level, limits, price, archive retention rights and internal
research license. No outreach was sent. Trial eligibility is not guaranteed.
If access is unavailable, use Danelfin Free for an equities-only pilot rather than
paying for an unscoped contract.

Only FINBRAIN_API_KEY is needed for provider authentication; no brokerage key,
wallet, seed phrase or exchange credentials. Keep it in the VPS .env/secret manager,
not in Git or browser code. APP_TOKEN protects this application's API. Telegram
and LLM credentials remain optional and independent.

FINBRAIN_ENABLED=false prevents requests even with a configured key. Set true
only after the owner approves actual API use and its budget. One experiment
performs one GET, without redirects or automatic retries, including HTTP 429.
Cost is stored as null because subscription allocation is unknown, not zero.
The flag is an administrative safeguard, not a dollar budget or rate limiter.

## Forward evaluation plan (not yet executed)

1. Freeze an instrument list (e.g. 5 liquid US equities and 2 crypto pairs), exact
   quote currencies, and daily collection time after the provider update. Obtain
   actual crypto symbols from the covered ticker list; do not assume BTCUSD.
2. Collect daily snapshots for 30 days after permission. Seven calls/day is 210
   calls over 30 days; do not poll at the worker's two-second queue interval.
   The project has no scheduler: enqueue manually or add a reviewed scheduler.
3. Persist retrieved_at, lastUpdated and the full documented forecast data.
   Deduplicate evaluations on provider/symbol/type/lastUpdated/forecast date.
   Fetch realized prices separately from a licensed market-data source; fix the
   equity closing-price and crypto UTC cutoff conventions before collecting.
4. Compare MAE/RMSE and directional accuracy against a no-change price baseline.
   Measure interval coverage/width only after confirming the confidence level.
   Never convert score/price into probability or apply Brier score to it.
5. Avoid look-ahead: score only dates after collection; exclude already elapsed
   forecast dates and document stale forecasts. Allow the final forecast horizon
   to mature after collection ends. Thirty days checks integration and early
   signals; overlapping forecast windows are not independent observations.

Outcome collection, scoring, scheduled sampling, persistent archive export and
monetary budgets are future work. The adapter and tests implement acquisition
only. Database keeps runs, but the API lists only the latest 100: seven snapshots
per day will exceed that display window during a 30-day trial, so use a DB backup
or add export before the experiment. Do not publish licensed provider responses.
