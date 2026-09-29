from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ..models.schemas import ChatRequest, ChatResponse, PersonaType, LanguageType
from ..services.geocoding_service import resolve_location
from ..services.weather_service import fetch_weather_forecast
from ..services.alert_service import evaluate_disaster_alerts
from ..services.advisory_engine import generate_persona_advisories
from ..services.ai_service import (
    parse_user_query,
    generate_conversational_response,
    infer_persona_from_query,
    CONVERSATION_SESSIONS
)

router = APIRouter(prefix="/chat", tags=["Conversational AI"])

@router.post("", response_model=ChatResponse)
async def chat_interaction(req: ChatRequest):
    """
    Main Conversational Weather & Disaster Intelligence Endpoint.
    Orchestrates: Multi-turn memory -> Query understanding -> Geocoding -> Weather NWP -> Alerts -> Persona Advisory -> Dynamic Conversational Synthesis.
    """
    query_text = req.message.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query message cannot be empty.")

    session_id = req.conversation_id or "default_session"
    session_data = CONVERSATION_SESSIONS.get(session_id, {})

    # 1. Parse Query (Intent, Location, Timeframe, Language) with Session Memory
    parsed = parse_user_query(query_text, session_data)
    
    # User's explicit language preference takes precedence if supplied
    effective_lang = req.language or parsed.get("detected_language", LanguageType.HINGLISH)
    effective_persona = infer_persona_from_query(
        query_text, req.persona or PersonaType.GENERAL
    )
    dialog_intent = parsed.get("dialog_intent", "weather")

    # 2. Location Resolution (parsed location takes priority, then req.city, then session memory)
    target_city = parsed.get("location") or req.city or session_data.get("last_city")
    lat, lon = req.latitude, req.longitude
    resolved_name = "Indore"
    admin1 = "Madhya Pradesh"

    if target_city:
        geo = await resolve_location(target_city)
        if geo:
            lat = geo["latitude"]
            lon = geo["longitude"]
            resolved_name = geo["name"]
            admin1 = geo.get("admin1", "")
    elif lat is not None and lon is not None:
        resolved_name = f"Coordinates ({lat:.2f}, {lon:.2f})"
    else:
        # Default to Indore
        geo = await resolve_location("Indore")
        if geo:
            lat, lon = geo["latitude"], geo["longitude"]
            resolved_name = geo["name"]
            admin1 = geo.get("admin1", "")

    # Update session state with resolved city
    if session_id not in CONVERSATION_SESSIONS:
        CONVERSATION_SESSIONS[session_id] = {}
    CONVERSATION_SESSIONS[session_id]["last_city"] = resolved_name

    # 3. Retrieve Live Weather Data & NWP Forecast
    weather_card = await fetch_weather_forecast(lat, lon, resolved_name, admin1)

    # 4. Evaluate Disaster Warning / Alerts
    alert_item = evaluate_disaster_alerts(weather_card, target_city or resolved_name)
    weather_card.severe_warning = alert_item

    # 5. Generate Domain Persona Advisories (weather questions only)
    advisories = []
    if dialog_intent == "weather":
        advisories = generate_persona_advisories(weather_card, effective_persona, effective_lang)

    # 6. Generate Dynamic Grounded AI Response
    answer_text = await generate_conversational_response(
        query=query_text,
        parsed=parsed,
        weather=weather_card,
        alert=alert_item,
        advisories=advisories,
        persona=effective_persona,
        lang=effective_lang,
        conversation_id=session_id
    )

    # 7. Generate Highly Contextual Follow-up Suggestions based on intent
    intent = parsed.get("intent", "general_forecast")
    if intent in ["rain_forecast", "rain_timing"]:
        followups = [
            f"Baarish ka exact time window kya hai?",
            f"Kya chhat par kapde sukha sakte hain?",
            f"{resolved_name} agale 3 din ka forecast?",
            f"Car wash karwana safe rahega?"
        ]
    elif intent == "clothes_drying":
        followups = [
            f"Kal baarish ke kitne percent chances hain?",
            f"Morning walk ke liye mausam kaisa hai?",
            f"Baarish kitne baje tak aayegi?",
            f"{resolved_name} 7-day outlook"
        ]
    elif intent == "crop_calendar":
        followups = [
            f"October me sarson aur matar ki buwai kaise karein?",
            f"Rabi faslon ke liye top certified varieties",
            f"Garmi (Zaid) season me konsi kheti karein?",
            f"Pure 12 mahine ka fasal calendar dikhao"
        ]
    elif intent in ["agriculture", "sinchai"]:
        followups = [
            f"Keetnashak spray kab karein?",
            f"Mitti me nami kitne din rahegi?",
            f"Is mahine me konsi kheti karein?",
            f"Fasal ko tezz hawa se khatra hai?"
        ]
    elif intent == "travel":
        followups = [
            f"Highway par fog aur visibility report",
            f"Two-wheeler ke liye crosswind hazard?",
            f"Return aate waqt baarish milegi?",
            f"Active disaster alerts check karo"
        ]
    elif intent == "car_wash":
        followups = [
            f"Kal baarish hone ke chances hain?",
            f"Chhat par kapde sukha sakte hain?",
            f"{resolved_name} agale 3 din ka mausam",
            f"Dopahar me dhoop niklegi kya?"
        ]
    elif intent == "morning_walk":
        followups = [
            f"Dopahar me garmi kitni badhegi?",
            f"Subah hawa ki speed aur AQI?",
            f"Kal walk ke liye time kaisa rahega?",
            f"Chhata le ke nikalna zaroori hai?"
        ]
    elif intent == "apparel_comfort":
        followups = [
            f"AC chalane ki zaroorat padegi kya?",
            f"Dopahar me dhoop kitni tez hogi?",
            f"Shaam ka mausam kaisa rahega?",
            f"Kal baarish hogi kya?"
        ]
    else:
        followups = [
            f"Kal {resolved_name} mein baarish hogi kya?",
            f"Chhat par kapde sukha sakta hoon?",
            f"Highway travel safe hai kya?",
            f"{resolved_name} agale 3 din ka forecast"
        ]

    return ChatResponse(
        answer=answer_text,
        persona=effective_persona,
        language=effective_lang,
        extracted_location=resolved_name,
        extracted_intent=intent,
        weather_card=weather_card,
        alert=alert_item,
        actionable_advisory=advisories,
        suggested_followups=followups,
        sources=["Open-Meteo ECMWF/GFS", "IMD Alert Criteria", "NDMA SACHET"]
    )
