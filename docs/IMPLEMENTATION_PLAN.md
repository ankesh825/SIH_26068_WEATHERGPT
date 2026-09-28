# 🌤️ WeatherGPT (SIH26068) - Complete Implementation Plan & Architecture Document

**Ministry of Earth Sciences (MoES) | India Meteorological Department (IMD)**  
**Theme: Disaster Management / Early Warning Dissemination**  
*Document Generated: September 2026*

---

## 1. Executive Summary & Problem Statement

### The Problem
India produces world-class meteorological data through the India Meteorological Department (IMD), MoES bulletins, Mausam portal, Doppler Weather Radars, and INSAT-3D satellite imagery. However, an ordinary citizen, smallholder farmer (Kisan), or highway traveler faces a severe **"last mile" technical translation gap**:
- Raw meteorological numbers (e.g., *28°C, 82% humidity, 60% probability, WMO code 65*) require domain expertise to translate into actionable decisions.
- Existing portals are one-way dashboards with no conversational follow-up or native voice querying in Hindi or Hinglish.

### The Solution: WeatherGPT
WeatherGPT introduces a **conversational, authoritative AI layer** designed on top of numerical meteorological datasets. 

Key architectural principles:
1. **Zero Hallucination (Strict Grounding)**: The AI does not invent or guess temperatures or rainfall figures; it strictly interprets verified datasets.
2. **Domain-Specific Persona Modes**: Tailored advice for Farmers (*Kisan* 🌾), Travelers (*Yatri* 🚗), Citizens (*Nagrik* 🏙️), and Disaster Management Officers (🚨).
3. **Voice-First & Multilingual**: Supports voice queries via Web Speech API in Hindi, Hinglish, and English.
4. **Disaster Readiness**: Instant evaluation of IMD/NDMA Common Alerting Protocol (CAP) severe weather thresholds.

---

## 2. End-to-End System Architecture

```
User Query (Voice/Text: Hindi / Hinglish / English)
                     │
                     ▼
  Frontend Web Console (HTML5 + Glassmorphic Dark UI)
  - Web Speech STT (Mic) & TTS (Speaker)
  - Interactive Leaflet Doppler Radar Map
  - 24-Hour Color-Coded Risk Timeline Ribbon
                     │
         [HTTP POST /api/chat]
                     ▼
          FastAPI Backend Orchestrator
                     │
       ┌─────────────┴─────────────────────────┐
       ▼                                       ▼
  AI Parser & NLU Engine              Geocoding Engine
  - Intent classification             - In-Memory Indian Cities DB
  - Entity extraction (City, Date)     - Open-Meteo Geocoding API
  - Off-topic guardrails
       │                                       │
       └──────────────────┬────────────────────┘
                          ▼
             Open-Meteo NWP & Forecast API
             - Current metrics (Temp, Humidity, Wind, UV)
             - 24h Hourly & 7-Day Forecast
             - ECMWF IFS-025 / GFS / ICON Models
                          │
       ┌──────────────────┴────────────────────┐
       ▼                                       ▼
  Alert Evaluation Engine             Advisory Intelligence Engine
  - IMD CAP Alert Rules               - Kisan: Soil, Spraying, Irrigation
  - NDMA SACHET Bulletins             - Yatri: Hydroplaning, Fog, Corridor Score
  - Heatwave/Storm Thresholds         - Nagrik: Umbrella, Heat stress, UV
                                      - Officer: SDRF, Culverts, EOC Alert
       │                                       │
       └──────────────────┬────────────────────┘
                          ▼
            Conversational Synthesis Engine
            - Gemini 1.5 Flash (if API Key present)
            - Grounded NLU Template Engine (Offline fallback)
                          │
                          ▼
               Standardized JSON Response
               + Hero Card & Timeline Sync
```

---

## 3. Technology Stack Breakdown

| Component | Technology / Library | Role & Justification |
|---|---|---|
| **Frontend UI** | HTML5, CSS3, Vanilla JS (ES6+) | Ultra-lightweight, zero bundle overhead, rapid loading on 2G/3G mobile networks. |
| **Styling** | Glassmorphic Dark Console Theme | Modern, high-contrast dashboard with responsive grid layouts. |
| **Doppler Radar** | Leaflet.js 1.9.4 + RainViewer API | Real-time precipitation radar tile overlays with dark basemaps. |
| **Voice Processing** | Web Speech API (STT + TTS) | Zero-latency browser-native voice recognition and audio speech narration in Indian English & Hindi (`hi-IN`). |
| **Backend Framework**| FastAPI (Python 3.12) | Asynchronous, high-throughput REST API with automatic OpenAPI (Swagger) documentation. |
| **Data Validation** | Pydantic v2 | Type safety and strict JSON schema validation for all inputs/outputs. |
| **HTTP Client** | HTTPX (Async) | Non-blocking asynchronous REST calls to meteorological APIs. |
| **AI / LLM** | Google Gemini API + Internal NLU | Grounded narration with fallback regex/rule engine when offline. |
| **Weather Data** | Open-Meteo Open Meteorological API | High-resolution Numerical Weather Prediction (NWP) models (ECMWF, GFS, ICON). |

---

## 4. Backend Components & Service Implementation

### 4.1 Chat Router (`backend/app/api/chat.py`)
Main conversational gateway accepting `POST /api/chat`.
- Validates input message, selected persona, and language.
- Runs the query through `parse_user_query`.
- Resolves location (coordinates, district, state).
- Fetches real-time weather metrics.
- Evaluates disaster thresholds and generates domain advisories.
- Calls the response generator and returns a complete `ChatResponse` model with suggested follow-ups and source transparency metadata.

### 4.2 AI & Grounded NLU Engine (`backend/app/services/ai_service.py`)
- **Intent Classification**: Classifies user input into `weather`, `greeting`, `identity`, or `off_topic`.
- **Off-Topic Safety Guardrail**: Prevents hallucination on non-weather queries (e.g., cricket, movies, politics) by politely steering the conversation back to verified weather parameters.
- **Entity Extraction**: Recognizes 30+ Indian cities and relative timeframes (`aaj`, `kal`, `weekend`).
- **Dynamic Persona Switching**: Auto-detects if a general visitor asks farming questions (*sinchai*, *keetnashak*, *khet*) and routes to the Farmer persona.
- **Grounded Generator**: Uses Google Gemini 1.5 Flash with strict temperature (0.2) and anti-hallucination system prompts, or uses deterministic templates if the API key is not supplied.

### 4.3 Weather Service (`backend/app/services/weather_service.py`)
- Calls Open-Meteo endpoint with parameters: `temperature_2m`, `relative_humidity_2m`, `apparent_temperature`, `precipitation`, `weather_code`, `wind_speed_10m`, `wind_direction_10m`, `uv_index`.
- Decodes WMO weather codes (0-99) into visual icons and human-readable text.
- Extracts next 24-hour precipitation probabilities and 7-day daily forecast bounds.
- Compares multi-model NWP predictions (ECMWF IFS-025, GFS, ICON) for temperature and rainfall variance.
- Provides realistic synthetic metrics in offline fallback mode.

### 4.4 Alert & Early Warning Service (`backend/app/services/alert_service.py`)
- Implements IMD / NDMA Common Alerting Protocol (CAP) logic:
  - **Red Alert (Severe Heatwave)**: Ambient temp ≥ 42°C. Triggers emergency hydration & shelter advice.
  - **Orange Alert (Heavy Precipitation & Squalls)**: Rain > 25mm or rain prob > 80% with thunderstorm codes. Advises suspending farm spraying and avoiding waterlogged roads.
  - **Wind Hazard Warning**: Gusts exceeding 45 km/h.
  - **Yellow Watch (Thunderstorm/Lightning)**: Damini network lightning activity.
- Maintains static CAP bulletins for high-priority districts (Mumbai, Indore, Delhi).

### 4.5 Domain Persona Advisory Engine (`backend/app/services/advisory_engine.py`)
Translates weather metrics into sector-specific action plans:
- **🌾 Kisan (Farmer)**:
  - Precipitation > 50%: Postpone irrigation (save water & prevent root rot) and halt chemical spraying.
  - Wind > 18 km/h: Warn against crop lodging in tall crops (maize, sugarcane).
- **🚗 Yatri (Traveler)**:
  - Wet asphalt: Warn of hydroplaning risks and advocate maintaining safe braking buffers.
  - Fog (WMO 45/48): Recommend low-beam fog lights.
- **🏙️ Nagrik (Citizen / General)**:
  - Rain > 40%: Umbrella reminder.
  - UV Index ≥ 7.0: Sun protection advisory between 12-3 PM.
- **🚨 Disaster Officer**:
  - Inundation warning for low-lying culverts; standby trigger for State Disaster Response Force (SDRF).

### 4.6 Geocoding Service (`backend/app/services/geocoding_service.py`)
- Fast in-memory lookup table of major Indian cities (Delhi, Mumbai, Indore, Bhopal, Jaipur, Bengaluru, Chennai, Kolkata, etc.).
- Open-Meteo Geocoding REST API for arbitrary tier-2 and tier-3 towns.
- In-memory dictionary cache to prevent redundant external API calls.

### 4.7 Climate History Service (`backend/app/services/climate_service.py`)
- Supplies 5-year monsoon and temperature trend datasets for regional agricultural and disaster resilience planning.

---

## 5. Frontend Dashboard Implementation

### 5.1 Chat Console (`frontend/js/chat.js` & `voice.js`)
- **Conversational Stream**: Real-time message exchange with rich markdown formatting and alert tags.
- **Voice Mic (STT)**: One-click voice recognition using browser Web Speech API.
- **Text-to-Speech (TTS)**: `🔊 Listen` button on each assistant response to speak out the response in Hindi or Indian English.
- **Why This Answer? (Grounding Transparency Inspector)**: Expandable accordion showing high-resolution met grid coordinates, verified data sources, CAP gateway details, and DPDP Act 2023 compliance notice.
- **Client-Side Direct Fallback Engine**: If the backend is loading or unreachable, the frontend seamlessly queries Open-Meteo directly and synthesizes responses client-side.

### 5.2 Real-Time Weather & Risk Console (`frontend/js/app.js` & `radar.js`)
- **Hero Weather Card**: Live temperature, feels-like temperature, humidity, wind speed, UV index, and AQI.
- **24-Hour Visual Risk Ribbon**: Color-coded danger timeline (Green = Safe, Yellow = Watch, Red = Danger) with dynamic bar fills.
- **Persona Intelligence Sub-Panels**:
  - *Kisan*: Soil moisture estimate, spraying window status, irrigation schedule, fungal disease risk.
  - *Yatri*: Highway corridor safety score (out of 10), visibility distance, crosswind hazard.
  - *Disaster Command*: Warning level, catchment population at risk, alert broadcast queue, SDRF shelter capacity.
- **Interactive Doppler Radar**: Leaflet map displaying real-time precipitation radar frames from RainViewer API.
- **NWP Multi-Model Comparison Tab**: Side-by-side comparison of ECMWF, GFS, and ICON forecasts.
- **5-Year Climate Trend Chart**: Visual bar chart showing annual precipitation variability.

---

## 6. As-Built Data Baseline (Honesty & Compliance Map)

As documented in `DATA_BASELINE.md`:

| Feature | Current Production Status | Source |
|---|---|---|
| **Live Forecast (Current, 24h, 7-Day)** | **100% Live** | Open-Meteo Realtime & Hourly API |
| **Geocoding & Location Discovery** | **100% Live** | Open-Meteo Geocoding + Offline In-Memory DB |
| **Doppler Radar Visualization** | **100% Live** | RainViewer Live Radar Tile Pipeline |
| **NWP Model Comparison** | **Live** on Models View | Open-Meteo Multi-Model Query |
| **NDMA SACHET / CAP Alerts** | **Hybrid / Simulated** | Regional simulated bulletins (Mumbai/Indore/Delhi) + Dynamic threshold engine |
| **Air Quality (AQI)** | **Placeholder (45 - Good)** | Schema default (planned for CPCB portal integration) |
| **Climate 5-Year Trends** | **Climatological Baseline** | Regional latitude-based historical formula |

---

## 7. How to Run & Deploy

### Backend Setup
```bash
cd backend
# Activate virtual environment
.\.venv\Scripts\activate   # Windows
# Start FastAPI application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation: **http://localhost:8000/docs**

### Frontend Setup
Open `frontend/index.html` directly in any modern browser, or serve statically:
```bash
cd frontend
python -m http.server 3000
```
Visit: **http://localhost:3000**

---
*WeatherGPT - Developed for Smart India Hackathon (SIH26068)*
