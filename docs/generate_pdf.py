import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Preformatted,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute total page count."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(40, A4[1] - 30, "WeatherGPT (SIH26068) — System Implementation Plan & Architecture")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(40, A4[1] - 34, A4[0] - 40, A4[1] - 34)

        # Footer
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 40, 25, footer_text)
        self.drawString(40, 25, "Confidential — MoES / IMD Weather & Disaster Intelligence Platform")
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(40, 36, A4[0] - 40, 36)
        self.restoreState()


def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=45,
        bottomMargin=45,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#0f172a")
    accent_blue = colors.HexColor("#1d4ed8")
    accent_cyan = colors.HexColor("#0284c7")
    text_dark = colors.HexColor("#1e293b")
    text_muted = colors.HexColor("#475569")
    bg_light = colors.HexColor("#f8fafc")
    border_color = colors.HexColor("#cbd5e1")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=primary_color,
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=accent_cyan,
        spaceAfter=6,
    )

    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=text_muted,
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=accent_blue,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=text_dark,
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=text_dark,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3,
    )

    callout_style = ParagraphStyle(
        'Callout_Text',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor("#1e3a8a"),
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.2,
        leading=9.5,
        textColor=colors.HexColor("#0f172a"),
    )

    th_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )

    td_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=text_dark,
    )

    td_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=text_dark,
    )

    story = []

    # Title & Header
    story.append(Paragraph("🌤️ WeatherGPT (SIH26068)", title_style))
    story.append(Paragraph("Conversational AI for Weather Forecasting, Alerts & Climate Information", subtitle_style))
    story.append(Paragraph("<b>Ministry of Earth Sciences (MoES)</b> &bull; <b>India Meteorological Department (IMD)</b> &bull; Theme: Disaster Management<br/>Release: v1.0.0 Production Prototype &bull; Document Date: September 2026", meta_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceBefore=0, spaceAfter=10))

    # Section 1: Executive Summary
    story.append(Paragraph("1. Executive Summary & Problem Formulation", h1_style))
    story.append(Paragraph(
        "India generates abundant, high-resolution meteorological intelligence via the India Meteorological Department (IMD) "
        "and Numerical Weather Prediction (NWP) centers. However, there exists a critical <b>'last-mile translation gap'</b>: "
        "raw atmospheric metrics (e.g., 28°C, 82% humidity, WMO code 65, 14 km/h gusts) are difficult for an everyday farmer, "
        "commuter, or traveler to interpret into operational decisions.", body_style
    ))
    story.append(Paragraph(
        "<b>WeatherGPT</b> bridges this gap by deploying an authoritative conversational AI layer that interprets verified "
        "meteorological feeds into clear, native-language advice (Hindi, Hinglish, English) while strictly upholding "
        "<b>Zero-Hallucination Grounded AI</b>.", body_style
    ))

    # Callout Box
    callout_data = [[
        Paragraph("<b>Grounded AI Architecture Rule:</b> The AI model never invents, guesses, or hallucinates weather numbers. "
                  "Numerical forecasts are fetched from verified Open-Meteo & NWP APIs; the AI strictly narrates and contextualizes verified facts.", callout_style)
    ]]
    t_callout = Table(callout_data, colWidths=[doc.width])
    t_callout.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#eff6ff")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#93c5fd")),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_callout)
    story.append(Spacer(1, 8))

    # Section 2: End-to-End Pipeline
    story.append(Paragraph("2. System Architecture & End-to-End Pipeline", h1_style))
    diag_text = (
        "[User Voice / Text Query (Hindi, Hinglish, English)]\n"
        "                     │\n"
        "                     ▼\n"
        "[Frontend Web Console (HTML5 + Glassmorphic UI)]\n"
        "  • Web Speech API (STT Mic & TTS Speaker)   • Live Doppler Radar (Leaflet + RainViewer)\n"
        "  • 24-Hour Color-Coded Risk Timeline Ribbon • Dynamic Persona Sub-Dashboards\n"
        "                     │  HTTP POST /api/chat\n"
        "                     ▼\n"
        "[FastAPI Backend Engine (Python 3.12)]\n"
        "  ├─► AI Parser & NLU: Intent classification (Weather/Greeting/Off-topic), City & Timeframe\n"
        "  ├─► Geocoding Service: In-memory cache + Open-Meteo Geocoding REST API\n"
        "  ├─► Weather & NWP Engine: Live forecast (Temp, Rain Prob, Wind, UV, Hourly 24h, Daily 7d)\n"
        "  ├─► Disaster Alert Evaluator: IMD CAP thresholds (Heatwave >=42°C Red, Storms Orange)\n"
        "  ├─► Persona Advisory Engine: Actionable tips for Kisan, Yatri, Nagrik, Disaster Officer\n"
        "  └─► Grounded Response Synthesis: Gemini 1.5 Flash (low temp 0.2) or deterministic template\n"
        "                     │\n"
        "                     ▼\n"
        "[Standardized ChatResponse JSON] ──► Syncs Hero Card, Radar Map & Danger Timeline"
    )
    t_diag = Table([[Preformatted(diag_text, code_style)]], colWidths=[doc.width])
    t_diag.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 0.75, border_color),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_diag)
    story.append(Spacer(1, 10))

    # Section 3: Technology Stack
    story.append(Paragraph("3. Technology Stack & Key Specifications", h1_style))
    tech_data = [
        [Paragraph("Subsystem", th_style), Paragraph("Technology / Tool", th_style), Paragraph("Implementation Purpose", th_style)],
        [Paragraph("Backend Framework", td_bold), Paragraph("FastAPI (Python 3.12)", td_style), Paragraph("High-speed asynchronous ASGI REST service with automatic Swagger UI at /docs.", td_style)],
        [Paragraph("Data Validation", td_bold), Paragraph("Pydantic v2", td_style), Paragraph("Strict typed schemas for chat requests, weather cards, and disaster alert items.", td_style)],
        [Paragraph("Async Network", td_bold), Paragraph("HTTPX", td_style), Paragraph("Non-blocking asynchronous HTTP client for external meteorological API calls.", td_style)],
        [Paragraph("AI / LLM Layer", td_bold), Paragraph("Google Gemini 1.5 Flash + NLU", td_style), Paragraph("Dual engine: Gemini API if key is set, plus built-in rule-based grounded template generator.", td_style)],
        [Paragraph("Meteorological Feeds", td_bold), Paragraph("Open-Meteo REST & NWP", td_style), Paragraph("Live current, 24-hour hourly, 7-day outlook, and ECMWF / GFS / ICON multi-model comparisons.", td_style)],
        [Paragraph("Doppler Radar", td_bold), Paragraph("Leaflet.js + RainViewer API", td_style), Paragraph("Real-time precipitation radar tile overlays on CartoDB dark basemap.", td_style)],
        [Paragraph("Voice Processing", td_bold), Paragraph("Web Speech API (STT / TTS)", td_style), Paragraph("Zero-latency browser-native voice recognition and audio speech narration in Hindi & English.", td_style)],
        [Paragraph("Frontend UI", td_bold), Paragraph("HTML5 / CSS3 / ES6 Vanilla JS", td_style), Paragraph("Lightweight, zero-bundle overhead console designed for smooth performance on 2G/3G.", td_style)],
    ]
    t_tech = Table(tech_data, colWidths=[1.3*inch, 1.8*inch, 4.0*inch])
    t_tech.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
    ]))
    story.append(t_tech)
    story.append(Spacer(1, 10))

    # Section 4: Backend Services
    story.append(Paragraph("4. Backend Modular Service Breakdown", h1_style))

    story.append(Paragraph("4.1 Conversational Router & AI Engine (chat.py & ai_service.py)", h2_style))
    story.append(Paragraph(
        "• <b>Intent & Dialog Classification:</b> Distinguishes between <code>weather</code>, <code>greeting</code>, <code>identity</code>, and <code>off_topic</code> queries.<br/>"
        "• <b>Off-Topic Safety Guardrails:</b> Non-weather queries (cricket, films, politics, coding) are politely deflected with a live city weather snapshot to prevent hallucination.<br/>"
        "• <b>Entity & Timeframe Extraction:</b> Extracts 30+ Indian cities and timeframes (today, kal, weekend) using regex and NLP patterns.<br/>"
        "• <b>Persona Auto-Inference:</b> Automatically routes agricultural queries (khet, sinchai, fasal) to the Kisan persona even if the user has not explicitly selected it.", bullet_style
    ))

    story.append(Paragraph("4.2 Weather & Numerical Weather Prediction Service (weather_service.py)", h2_style))
    story.append(Paragraph(
        "• <b>Live Multi-Parameter Forecast:</b> Fetches temperature, apparent feels-like, humidity, precipitation, wind speed, wind direction, and UV index.<br/>"
        "• <b>WMO Code Decoding:</b> Translates 20+ WMO atmospheric codes into localized emojis and text descriptions.<br/>"
        "• <b>NWP Multi-Model Comparison:</b> Compares ECMWF IFS-025, NOAA GFS Seamless, and DWD ICON Seamless for 3-day max temperatures and rain totals.<br/>"
        "• <b>Offline Fallback Engine:</b> Supplies realistic synthetic meteorology if external networks fail, preventing crashes.", bullet_style
    ))

    story.append(Paragraph("4.3 Early Warning & Alert Service (alert_service.py)", h2_style))
    story.append(Paragraph(
        "• <b>Severe Heatwave (Red Alert):</b> Ambient temperature ≥ 42°C triggers emergency ORS hydration and direct sunlight avoidance notices.<br/>"
        "• <b>Heavy Downpour & Squall (Orange Alert):</b> Rain > 25mm or rain probability > 80% with storm codes issues pesticide halt and underpass hazard warnings.<br/>"
        "• <b>High Wind / Gale Warning:</b> Wind gusts > 45 km/h trigger crop lodging and structural hazard advisories.<br/>"
        "• <b>Regional CAP Registry:</b> Pre-configured bulletins for high-density hubs (Mumbai Orange Alert, Indore Yellow Watch, Delhi Heat Stress).", bullet_style
    ))

    story.append(Paragraph("4.4 Domain Persona Advisory Engine (advisory_engine.py)", h2_style))
    story.append(Paragraph(
        "• <b>🌾 Kisan (Farmer):</b> Advises irrigation deferral if rain probability exceeds 50%; warns against foliar spray drift if wind exceeds 18 km/h.<br/>"
        "• <b>🚗 Yatri (Traveler):</b> Evaluates asphalt hydroplaning risk; recommends low-beam fog lights under low visibility conditions.<br/>"
        "• <b>🏙️ Nagrik (Citizen):</b> Recommends carrying an umbrella; warns of UV hazards when index exceeds 7.0.<br/>"
        "• <b>🚨 Disaster Officer:</b> Formulates culvert waterlogging warnings and triggers SDRF Level-2 stand-by readiness notices.", bullet_style
    ))

    story.append(Spacer(1, 10))

    # Section 5: API Endpoints
    story.append(Paragraph("5. REST API Endpoints Specification", h1_style))
    api_data = [
        [Paragraph("Endpoint", th_style), Paragraph("Method", th_style), Paragraph("Parameters", th_style), Paragraph("Response Model & Summary", th_style)],
        [Paragraph("<code>/api/chat</code>", td_bold), Paragraph("POST", td_style), Paragraph("message, persona, language, city, lat, lon", td_style), Paragraph("ChatResponse: answer, weather_card, alert, advisories, followups, sources.", td_style)],
        [Paragraph("<code>/api/weather/forecast</code>", td_bold), Paragraph("GET", td_style), Paragraph("location, lat, lon", td_style), Paragraph("WeatherCardData: current, 24h hourly points, 7-day daily forecast.", td_style)],
        [Paragraph("<code>/api/weather/models</code>", td_bold), Paragraph("GET", td_style), Paragraph("location", td_style), Paragraph("NWPComparisonResponse: ECMWF vs GFS vs ICON comparison & consensus.", td_style)],
        [Paragraph("<code>/api/alerts/active</code>", td_bold), Paragraph("GET", td_style), Paragraph("None", td_style), Paragraph("List[AlertItem]: Active regional CAP bulletins across monitored districts.", td_style)],
        [Paragraph("<code>/api/climate/history</code>", td_bold), Paragraph("GET", td_style), Paragraph("location", td_style), Paragraph("ClimateTrendResponse: 5-year rainfall and temperature historical trend analysis.", td_style)],
        [Paragraph("<code>/health</code>", td_bold), Paragraph("GET", td_style), Paragraph("None", td_style), Paragraph("Health status: {'status': 'healthy', 'version': '1.0.0'}", td_style)],
    ]
    t_api = Table(api_data, colWidths=[1.5*inch, 0.7*inch, 1.9*inch, 3.0*inch])
    t_api.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
    ]))
    story.append(t_api)
    story.append(Spacer(1, 10))

    # Section 6: Frontend Console
    story.append(Paragraph("6. Frontend Interaction & Dashboard Console", h1_style))
    story.append(Paragraph(
        "The frontend (<code>frontend/index.html</code>) is divided into two synchronized consoles:", body_style
    ))
    story.append(Paragraph(
        "1. <b>Conversational Console (Left):</b> Features Web Speech voice mic input (STT), text-to-speech audio button (TTS), "
        "alert tags, dynamic suggestion follow-up chips, and an expandable <i>'Why This Answer?' (Grounding Transparency Inspector)</i> "
        "documenting the met grid point, verified feeds, and DPDP Act compliance. Includes a direct client-side fallback engine to query Open-Meteo if the backend is down.<br/>"
        "2. <b>Visual Weather & Risk Console (Right):</b> Provides 4 switchable tabs: <i>Live Metrics</i> (hero card, 24h visual risk ribbon, "
        "dynamic persona intelligence panels for Kisan/Yatri/Officer, hourly scroll, and 7-day outlook), <i>Doppler Radar</i> "
        "(interactive Leaflet map with RainViewer live precipitation tiles), <i>NWP Models</i> (ECMWF vs GFS vs ICON cards), and "
        "<i>Climate Trends</i> (5-year rainfall variability bar chart).", body_style
    ))
    story.append(Spacer(1, 10))

    # Section 7: Data Baseline
    story.append(Paragraph("7. As-Built Data Baseline & Compliance Map", h1_style))
    story.append(Paragraph(
        "As cataloged in <code>DATA_BASELINE.md</code>, here is the transparent status of all datasets:", body_style
    ))
    baseline_data = [
        [Paragraph("Pipeline", th_style), Paragraph("Current Status", th_style), Paragraph("Data Source", th_style), Paragraph("Production Integration Plan", th_style)],
        [Paragraph("Forecast (Current, 24h, 7d)", td_bold), Paragraph("<b>100% Live</b>", td_style), Paragraph("Open-Meteo REST API", td_style), Paragraph("Live global NWP; production ready for IMD Bharat Forecast System (BFS).", td_style)],
        [Paragraph("Location / Geocoding", td_bold), Paragraph("<b>100% Live</b>", td_style), Paragraph("Open-Meteo + In-Memory DB", td_style), Paragraph("Live geocoding with instant fallback for 25+ major Indian cities.", td_style)],
        [Paragraph("Doppler Weather Radar", td_bold), Paragraph("<b>100% Live</b>", td_style), Paragraph("RainViewer Radar Tiles", td_style), Paragraph("Live precipitation radar scan stream on dark basemap.", td_style)],
        [Paragraph("NWP Model Comparison", td_bold), Paragraph("<b>100% Live</b>", td_style), Paragraph("Open-Meteo Multi-Model", td_style), Paragraph("Live queries for ECMWF IFS-025, NOAA GFS, and DWD ICON.", td_style)],
        [Paragraph("NDMA SACHET / CAP Alerts", td_bold), Paragraph("Hybrid Prototype", td_style), Paragraph("Static CAP + Rules Engine", td_style), Paragraph("Simulated bulletins for Mumbai/Indore/Delhi + dynamic threshold evaluator.", td_style)],
        [Paragraph("Air Quality (AQI)", td_bold), Paragraph("Baseline (45)", td_style), Paragraph("Schema Default Placeholder", td_style), Paragraph("Baseline ready for direct CPCB National Air Quality Index API plug-in.", td_style)],
        [Paragraph("5-Year Climate Trends", td_bold), Paragraph("Climatology Baseline", td_style), Paragraph("Latitude Formula Baseline", td_style), Paragraph("Regional latitude climatology baseline for monsoon trend analysis.", td_style)],
    ]
    t_base = Table(baseline_data, colWidths=[1.6*inch, 1.2*inch, 1.7*inch, 2.6*inch])
    t_base.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, bg_light]),
    ]))
    story.append(t_base)
    story.append(Spacer(1, 10))

    # Section 8: Execution
    story.append(Paragraph("8. How to Execute & Deploy", h1_style))
    exec_code = (
        "# 1. Start FastAPI Backend (Port 8000)\n"
        "cd weathergpt/backend\n"
        ".\\.venv\\Scripts\\activate\n"
        "uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload\n"
        "# Swagger UI: http://localhost:8000/docs\n\n"
        "# 2. Start Frontend Static Server (Port 3000)\n"
        "cd weathergpt/frontend\n"
        "python -m http.server 3000\n"
        "# Web Console: http://localhost:3000"
    )
    t_exec = Table([[Preformatted(exec_code, code_style)]], colWidths=[doc.width])
    t_exec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 0.75, border_color),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_exec)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF: {filename}")

if __name__ == '__main__':
    target = os.path.join(r"c:\Users\satyaveer singh\OneDrive\Desktop\weathergpt\docs", "WeatherGPT_Implementation_Plan.pdf")
    build_pdf(target)
