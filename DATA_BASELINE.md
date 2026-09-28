# WeatherGPT data baseline (as built)

This file is the **frozen as-is map** of how data works today. Later honesty/cache/climate work should be measured against this document, not against README pitch language.

WeatherGPT is a **grounded-narration prototype**: chat loads a weather card first, then rules add alerts and persona advice, then Gemini or a template writes the sentence. The LLM is not supposed to invent forecast numbers. That claim is only true for a successful Open-Meteo forecast fetch.

## Pipeline

```
User query or city UI
        │
        ▼
frontend HTML/JS
        │  POST /api/chat
        │  GET /api/weather/forecast
        ▼
chat.py / weather.py
        │
        ├─► ai_service.parse_user_query
        ├─► geocoding_service.resolve_location
        │         ├─ Open-Meteo Geocoding API
        │         └─ INDIAN_CITY_FALLBACKS (in-memory)
        ├─► weather_service.fetch_weather_forecast
        │         ├─ Open-Meteo Forecast API  (live)
        │         └─ get_offline_weather      (synthetic)
        ├─► alert_service.evaluate_disaster_alerts
        │         ├─ REGIONAL_CAP_ALERTS      (hardcoded)
        │         └─ IMD-style thresholds on the card
        ├─► advisory_engine (persona rules)
        └─► Gemini if GEMINI_API_KEY else template NLU

frontend also:
  RainViewer tiles          → radar.js
  GET /api/climate/history  → climate_service (mostly synthetic)
  GET /api/weather/models   → Open-Meteo multi-model (not used in chat)
```

## Data sources that are actually live

| Pipeline | Source | Used by | Real vs fake |
| --- | --- | --- | --- |
| Current + hourly 24h + daily 7d | Open-Meteo `api.open-meteo.com/v1/forecast` | Chat, dashboard, `GET /api/weather/forecast` | **Live** when HTTP succeeds |
| Geocoding | Open-Meteo geocoding + ~20 Indian cities in `INDIAN_CITY_FALLBACKS` | All location resolution | **Live** for unknown cities if API works; else **Delhi fallback** |
| NWP ECMWF / GFS / ICON | Open-Meteo `models=` query | **Only** `GET /api/weather/models` (Models tab). **Not** used in chat | **Live** if 200; else canned dict |
| Radar | RainViewer timestamps + tiles | `frontend/js/radar.js` | **Live** overlay |
| Climate 5-year bars | `backend/app/services/climate_service.py` | Climate tab | Archive URL is called for **2023 only**; **response is ignored**. Bars are a **latitude formula** (20–26N → 980 mm base, else 820 mm) |
| AQI | `air_quality_index=45` in `weather_service` (schema default 45; offline fallback 52) | Weather card | **Hardcoded** |
| NDMA SACHET / IMD CAP | `REGIONAL_CAP_ALERTS` in `alert_service.py` | Chat + `GET /api/alerts/active` | **Static** Mumbai / Indore / Delhi bulletins, not a live feed |
| `CACHE_TTL_SECONDS=900` | `backend/app/config.py` | Nowhere | **Unused** (geocoding has an unbounded in-memory dict, not this TTL) |
| `conversation_id` | `ChatRequest` in `schemas.py` | Request field only | **Unused** |
| Timeframe (`kal` / 7 days) | Parsed in `ai_service.py` | Answer copy slightly | Forecast fetch is always **current + next 24h + 7d**; no day-index pick |

## Chat orchestration

`backend/app/api/chat.py`:

1. `parse_user_query` — language, city regex, intent, `dialog_intent` (weather vs greeting vs off-topic).
2. Location: request city → parsed city → lat/lon → else Delhi via `resolve_location`.
3. Always `fetch_weather_forecast` (even for greetings; weather is still attached on the card).
4. `evaluate_disaster_alerts` then `generate_persona_advisories` only if `dialog_intent == weather`.
5. `generate_conversational_response` — Gemini if `GEMINI_API_KEY` is set, else templates in `ai_service`.
6. Response `sources` always list `"Open-Meteo ECMWF/GFS"`, `"IMD Alert Criteria"`, and `"NDMA SACHET"` even when those feeds were not queried.

Frontend default city is **Indore** (`frontend/js/app.js`). Backend settings default is **New Delhi** (`config.py`). Production API base (when deployed) is Render: `https://weathergpt-sih-2026-1.onrender.com`.

## Grounding claim vs this baseline

True for live Open-Meteo current / hourly / daily.

**Not** true for:

- Offline weather (fixed 29°C, 20% rain)
- Climate history (synthetic series)
- AQI 45
- Hardcoded district CAP stories
- NWP fallback consensus text

Unknown city names fall back to **Delhi**, which can look like a wrong grounded answer.

## Baseline snapshot (do not “fix” these as part of this map)

Keep these four facts as the starting point for later phases:

1. **Open-Meteo live forecast** when the forecast HTTP call succeeds.
2. **Hardcoded CAP** (`REGIONAL_CAP_ALERTS` + `/api/alerts/active` returns those three cities).
3. **Synthetic climate and AQI** (latitude formula / ignored archive JSON; AQI always 45 on the live path).
4. **Unused cache TTL** (`CACHE_TTL_SECONDS` is defined and never read).
