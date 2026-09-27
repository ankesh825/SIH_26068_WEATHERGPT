import re
import os
from typing import Dict, Any, Tuple, Optional
from ..models.schemas import (
    WeatherCardData,
    AlertItem,
    PersonaType,
    LanguageType,
)
from ..config import settings

# Supported Indian cities regex
KNOWN_LOCATIONS = [
    "indore", "bhopal", "delhi", "new delhi", "mumbai", "pune", "jaipur",
    "lucknow", "patna", "kolkata", "bengaluru", "bangalore", "chennai",
    "hyderabad", "ahmedabad", "chandigarh", "varanasi", "kanpur", "nagpur",
    "surat", "visakhapatnam", "shimla", "dehradun", "srinagar", "goa", "udaipur",
    "jodhpur", "amritsar", "agra", "gwalior", "jabalpur", "ujjain"
]

WEATHER_KEYWORDS = [
    "weather", "mausam", "baarish", "barish", "rain", "raining", "barsat",
    "temperature", "temp", "garmi", "sardi", "cold", "heat", "humid", "humidity",
    "wind", "hawa", "forecast", "alert", "warning", "cyclone", "toofan", "flood",
    "baad", "tsunami", "lightning", "bijli", "thunder", "hail", "fog",
    "kohra", "kohara", "aqi", "uv", "umbrella", "chhata", "sinchai", "irrigate",
    "irrigation", "khet", "fasal", "crop", "spray", "pesticide", "travel", "safar",
    "highway", "flight", "road", "drive", "visibility", "heatwave", "loo",
    "drought", "sukha", "storm", "andhi", "nwp", "imd", "radar", "climate",
    "snow", "barf", "cloud", "badal", "sunny", "dhoop", "overcast",
    "os", "monsoon", "barish", "precip", "windchill", "feels like"
]

GREETING_PATTERNS = [
    r"^\s*(hi|hii|hey|hello|helo|yo|hola|namaste|namaskar|salam|salaam)\b",
    r"^\s*(good\s+(morning|afternoon|evening|night)|shubh\s+prabhat|suprabhat)\b",
    r"^\s*(kaise\s+ho|kya\s+haal|whats?\s*up|how\s+are\s+you|kya\s+haaal)\b",
    r"^\s*(ok|okay|thanks|thank you|dhanyavad|shukriya|bye|goodbye|ok thanks)\s*[.!]?\s*$",
]

IDENTITY_PATTERNS = [
    r"\b(who are you|what are you|tum kaun|aap kaun|what can you do|kya kar sakte|help me|your name|introduce)\b",
    r"\b(kya ho tum|tum kya ho|weather ?gpt kaun|lix kaun)\b",
]

OFF_TOPIC_HINTS = [
    "cricket", "football", "ipl", "movie", "film", "song", "gaana", "recipe",
    "cooking", "khana", "homework", "math", "coding", "python", "javascript",
    "bitcoin", "stock", "share market", "politics", "election", "joke", "shayari",
    "love", "girlfriend", "boyfriend", "dating", "exam result", "whatsapp",
    "instagram", "youtube", "game", "pubg", "free fire", "capital of", "who is pm",
    "prime minister", "modi", "story", "poem", "translate", "homework",
]


def _contains_any(text: str, words) -> bool:
    return any(w in text for w in words)


def infer_persona_from_query(message: str, fallback: PersonaType) -> PersonaType:
    """If a general visitor talks like a kisan/yatri/officer, switch advisory role."""
    lower = message.lower()
    if _contains_any(lower, ["irrigate", "sinchai", "crop", "fasal", "khet", "kisan", "spray", "pesticide", "farmer"]):
        return PersonaType.FARMER
    if _contains_any(lower, ["travel", "safar", "drive", "road", "flight", "highway", "yatri", "visibility"]):
        return PersonaType.TRAVELER
    if _contains_any(lower, ["sdrf", "ndma", "evacuation", "shelter", "disaster officer", "eoc"]):
        return PersonaType.DISASTER_OFFICER
    return fallback


def classify_dialog_intent(message: str) -> str:
    """greeting | identity | off_topic | weather"""
    lower = message.lower().strip()
    weather_hit = _contains_any(lower, WEATHER_KEYWORDS)
    city_hit = any(re.search(rf"\b{re.escape(city)}\b", lower) for city in KNOWN_LOCATIONS)
    if weather_hit or city_hit:
        return "weather"
    for pat in IDENTITY_PATTERNS:
        if re.search(pat, lower):
            return "identity"
    for pat in GREETING_PATTERNS:
        if re.search(pat, lower):
            return "greeting"
    if _contains_any(lower, OFF_TOPIC_HINTS):
        return "off_topic"
    # Short casual chat without weather words
    if len(lower.split()) <= 8:
        return "off_topic"
    return "off_topic"


def parse_user_query(message: str) -> Dict[str, Any]:
    """
    Parses intent, location, time, and language from the user query.
    """
    lower = message.lower()
    dialog_intent = classify_dialog_intent(message)
    
    # Detect language
    lang = LanguageType.HINGLISH
    # Check Devanagari script for pure Hindi
    if re.search(r'[\u0900-\u097F]', message):
        lang = LanguageType.HINDI
    elif any(w in lower for w in ["will it", "what is", "temperature in", "forecast for", "should i", "heavy rain in"]):
        lang = LanguageType.ENGLISH

    # Detect Location
    detected_location = None
    for city in KNOWN_LOCATIONS:
        if re.search(rf"\b{city}\b", lower):
            detected_location = city.title()
            break

    # If not found, look for patterns like "in <word>", "me <word>", "ka <word>"
    if not detected_location:
        m = re.search(r"(?:in|at|me|mein|sheher|city)\s+([a-zA-Z]+)", lower)
        if m and m.group(1) not in ["kal", "aaj", "rain", "baarish", "weather", "delhi"]:
            detected_location = m.group(1).title()

    # Detect Time
    timeframe = "today"
    if any(w in lower for w in ["kal", "tomorrow", "agli subah", "next day"]):
        timeframe = "tomorrow"
    elif any(w in lower for w in ["weekend", "sunday", "hafta", "week", "7 days", "agale din"]):
        timeframe = "7_days"

    # Detect Intent
    intent = "general_forecast"
    if dialog_intent != "weather":
        intent = dialog_intent
    elif any(w in lower for w in ["alert", "warning", "khatra", "cyclone", "toofan", "tsunami", "flood", "baad"]):
        intent = "disaster_alert"
    elif any(w in lower for w in ["irrigate", "sinchai", "crop", "fasal", "khet", "kisan", "spray", "pesticide"]):
        intent = "agriculture"
    elif any(w in lower for w in ["travel", "safar", "jaana", "drive", "road", "flight", "highway"]):
        intent = "travel"
    elif any(w in lower for w in ["baarish", "rain", "raining", "barsat"]):
        intent = "rain_forecast"
    elif any(w in lower for w in ["garmi", "heat", "temperature", "temp", "cold", "sardi", "humid"]):
        intent = "temperature"
    elif any(w in lower for w in ["history", "trend", "climate", "pichle saal", "average"]):
        intent = "climate_history"

    return {
        "location": detected_location,
        "timeframe": timeframe,
        "intent": intent,
        "dialog_intent": dialog_intent,
        "detected_language": lang
    }

async def generate_conversational_response(
    query: str,
    parsed: Dict[str, Any],
    weather: WeatherCardData,
    alert: Optional[AlertItem],
    advisories: list,
    persona: PersonaType,
    lang: LanguageType
) -> str:
    """
    Synthesizes a human-friendly, authoritative explanation.
    Uses Gemini API if key is provided, or the built-in grounded NLU engine.
    """
    dialog = parsed.get("dialog_intent") or parsed.get("intent")
    if dialog in ("greeting", "identity", "off_topic"):
        return _generate_grounded_fallback(
            query, parsed, weather, alert, advisories, persona, lang
        )

    # 1. Try Google Gemini if configured
    gemini_key = settings.GEMINI_API_KEY.strip()
    if gemini_key:
        try:
            return await _call_gemini_llm(
                query, parsed, weather, alert, advisories, persona, lang, gemini_key
            )
        except Exception as e:
            print(f"Gemini API call failed ({e}), falling back to internal NLU generator.")

    # 2. Built-in Grounded Meteorological NLU Engine
    return _generate_grounded_fallback(
        query, parsed, weather, alert, advisories, persona, lang
    )

def _generate_grounded_fallback(
    query: str,
    parsed: Dict[str, Any],
    weather: WeatherCardData,
    alert: Optional[AlertItem],
    advisories: list,
    persona: PersonaType,
    lang: LanguageType
) -> str:
    loc = weather.location
    timeframe = parsed.get("timeframe", "today")
    rain_prob = weather.precipitation_probability
    temp = weather.temperature
    condition = weather.condition
    time_label = "Kal" if timeframe == "tomorrow" else "Aaj"
    time_label_en = "Tomorrow" if timeframe == "tomorrow" else "Today"
    dialog = parsed.get("dialog_intent") or parsed.get("intent")

    scope_reply = _scope_conversation_reply(query, dialog, weather, lang)
    if scope_reply:
        return scope_reply

    # Alert context
    alert_prefix = ""
    if alert and alert.severity.value in ["warning", "severe"]:
        if lang == LanguageType.HINDI:
            alert_prefix = f"🚨 **चेतावनी ({alert.category}):** {alert.headline}!\n\n"
        elif lang == LanguageType.HINGLISH:
            alert_prefix = f"🚨 **ALERT ({alert.category}):** {alert.headline}!\n\n"
        else:
            alert_prefix = f"🚨 **OFFICIAL ALERT ({alert.category}):** {alert.headline}!\n\n"

    # Specific responses based on language
    if lang == LanguageType.HINDI:
        if parsed["intent"] == "rain_forecast":
            if rain_prob > 60:
                body = f"हाँ, {loc} में {time_label.lower()} बारिश होने की **प्रबल संभावना ({rain_prob}%)** है। वर्तमान मौसम {condition} है और तापमान लगभग {temp}°C बना हुआ है।"
            elif rain_prob > 30:
                body = f"{loc} में {time_label.lower()} हल्की बूंदाबांदी या छिटपुट बारिश की संभावना ({rain_prob}%) है। तापमान {temp}°C के आसपास रहेगा।"
            else:
                body = f"{loc} में {time_label.lower()} बारिश की संभावना काफी कम ({rain_prob}%) है। मौसम मुख्य रूप से {condition} रहेगा और तापमान लगभग {temp}°C रहेगा।"
        elif parsed["intent"] == "disaster_alert":
            if alert:
                body = f"{loc} के लिए {alert.headline} सक्रिय है। {alert.description}"
            else:
                body = f"{loc} के लिए वर्तमान में कोई गंभीर मौसम चेतावनी सक्रिय नहीं है। स्थितियां सामान्य और नियंत्रण में हैं।"
        else:
            body = f"{loc} में {time_label.lower()} का मौसम {condition} बना हुआ है। वर्तमान तापमान {temp}°C (अनुभूत: {weather.apparent_temperature}°C), आर्द्रता {weather.humidity}% और हवा की गति {weather.wind_speed} km/h है।"

    elif lang == LanguageType.HINGLISH:
        if parsed["intent"] == "rain_forecast":
            if rain_prob > 60:
                body = f"Haan, {loc} mein {time_label.lower()} baarish hone ke **kaafi acche chances ({rain_prob}%)** hain! Current condition {condition} hai aur temperature {temp}°C ke aas-paas hai."
            elif rain_prob > 30:
                body = f"{loc} mein {time_label.lower()} thodi bahut boonda-baandi ya light shower ki possibility ({rain_prob}%) hai. Mausam {condition} rahega aur temperature around {temp}°C rahega."
            else:
                body = f"{loc} mein {time_label.lower()} baarish ki possibility kaafi kam ({rain_prob}%) hai. Aasman mostly {condition} rahega aur maximum temperature {temp}°C tak jayega."
        elif parsed["intent"] == "disaster_alert":
            if alert:
                body = f"{loc} ke liye **{alert.headline}** active hai. {alert.description}"
            else:
                body = f"{loc} ke liye abhi koi severe disaster alert ya emergency warning active nahi hai. Weather condition normal hai."
        else:
            body = f"{loc} mein {time_label.lower()} mausam {condition} rahega. Current temperature **{temp}°C** (feels like {weather.apparent_temperature}°C), humidity {weather.humidity}% aur wind speed {weather.wind_speed} km/h hai."

    else: # ENGLISH
        if parsed["intent"] == "rain_forecast":
            if rain_prob > 60:
                body = f"Yes, there is a **high probability of rain ({rain_prob}%)** in {loc} {time_label_en.lower()}. Expect {condition} with temperatures around {temp}°C."
            elif rain_prob > 30:
                body = f"There is a moderate chance of isolated light showers ({rain_prob}%) in {loc} {time_label_en.lower()}. The sky condition will remain {condition} with a temperature of {temp}°C."
            else:
                body = f"Rainfall is unlikely in {loc} {time_label_en.lower()} with only a {rain_prob}% probability. Skies will be {condition} with temperatures around {temp}°C."
        elif parsed["intent"] == "disaster_alert":
            if alert:
                body = f"Active weather warning for {loc}: **{alert.headline}**. {alert.description}"
            else:
                body = f"No severe weather warnings or disaster alerts are currently active for {loc}. Meteorological indices remain in the green zone."
        else:
            body = f"The weather in {loc} {time_label_en.lower()} is {condition}. Currently, the temperature is **{temp}°C** (apparent {weather.apparent_temperature}°C), relative humidity is {weather.humidity}%, and winds are blowing at {weather.wind_speed} km/h."

    # Append persona tip if present
    tip_str = ""
    if advisories:
        tip_str = "\n\n💡 **Actionable Tip:**\n• " + "\n• ".join(advisories[:2])

    return f"{alert_prefix}{body}{tip_str}"


def _scope_conversation_reply(query: str, dialog: str, weather: WeatherCardData, lang: LanguageType) -> Optional[str]:
    """Handle greetings, identity, and non-weather chat without failing the session."""
    loc = weather.location
    temp = weather.temperature
    condition = weather.condition
    rain = weather.precipitation_probability

    if dialog == "greeting":
        if lang == LanguageType.HINDI:
            return (
                f"नमस्ते! मैं **WeatherGPT** हूँ — मौसम, आपदा चेतावनी और यात्रा/खेती सलाह के लिए आपका सहायक।\n\n"
                f"अभी **{loc}** में तापमान **{temp}°C** है और मौसम {condition} है। "
                f"बारिश की संभावना लगभग {rain}% है।\n\n"
                "आप मुझसे पूछ सकते हैं: बारिश, तापमान, अलर्ट, सिंचाई या सफर की सेफ्टी।"
            )
        if lang == LanguageType.ENGLISH:
            return (
                f"Hello! I am **WeatherGPT**, your weather and disaster assistant.\n\n"
                f"Right now in **{loc}** it is **{temp}°C** and {condition}, with about {rain}% chance of rain.\n\n"
                "Ask me about rain, temperature, alerts, farming, or travel safety — I stay in that lane so answers stay reliable."
            )
        return (
            f"Namaste! Main **WeatherGPT** hoon — mausam, disaster alerts, kheti aur travel safety ka assistant.\n\n"
            f"Abhi **{loc}** mein temperature **{temp}°C** hai, condition {condition} hai, baarish ~{rain}%. \n\n"
            "Aap kisi bhi persona se pooch sakte ho (general user bhi). Weather se related sawal poochiye — main handle kar lunga."
        )

    if dialog == "identity":
        if lang == LanguageType.HINDI:
            return (
                "मैं **WeatherGPT (SIH26068)** हूँ — MoES / IMD शैली का conversational मौसम प्लेटफ़ॉर्म।\n"
                "मैं किसान, यात्री, नागरिक, आपदा अधिकारी **और सामान्य विज़िटर** तीनों की मदद करता हूँ।\n\n"
                f"अभी {loc} का लाइव रीडिंग: **{temp}°C**, {condition}।"
            )
        if lang == LanguageType.ENGLISH:
            return (
                "I am **WeatherGPT (SIH26068)** — a conversational weather and disaster intelligence assistant.\n"
                "I help farmers, travelers, citizens, disaster officers, and general visitors who have not picked a role.\n\n"
                f"Live snapshot for {loc}: **{temp}°C**, {condition}."
            )
        return (
            "Main **WeatherGPT (SIH26068)** hoon — conversational weather + disaster assistant.\n"
            "Persona select kiye bina bhi baat kar sakte ho. Main kisan, yatri, nagrik aur general user sabko guide karta hoon.\n\n"
            f"{loc} live: **{temp}°C**, {condition}."
        )

    if dialog == "off_topic":
        if lang == LanguageType.HINDI:
            return (
                f"यह सवाल मौसम / आपदा सुरक्षा से जुड़ा नहीं लगता। मैं क्रिकेट स्कोर, फिल्म या सामान्य चैट का जवाब नहीं देता — "
                f"ताकि गलत मौसम जानकारी न फैले।\n\n"
                f"मैं **{loc}** का मौसम बता सकता हूँ: अभी **{temp}°C**, {condition}, बारिश ~{rain}%. "
                "बारिश, अलर्ट, सिंचाई या यात्रा के बारे में पूछें।"
            )
        if lang == LanguageType.ENGLISH:
            return (
                "That looks outside weather and disaster safety, so I will not invent an answer there.\n\n"
                f"I can still help with **{loc}**: it is **{temp}°C**, {condition}, rain chance ~{rain}%. "
                "Ask about rain, alerts, farming, or travel and I will answer from live data."
            )
        return (
            f"Yeh sawal weather / disaster se related nahi lagta, isliye main ispe guess nahi karunga.\n\n"
            f"Lekin **{loc}** ka mausam ready hai: **{temp}°C**, {condition}, baarish ~{rain}%. "
            "Baarish, alert, kheti ya travel poochiye — main deal karunga. General user ho to bhi chalega."
        )

    return None

async def _call_gemini_llm(
    query: str,
    parsed: Dict[str, Any],
    weather: WeatherCardData,
    alert: Optional[AlertItem],
    advisories: list,
    persona: PersonaType,
    lang: LanguageType,
    api_key: str
) -> str:
    """Invokes Google Gemini API with grounded constraints."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    system_prompt = (
        "You are WeatherGPT, an authoritative conversational meteorological AI platform developed for "
        "Smart India Hackathon (SIH26068) under the Ministry of Earth Sciences (MoES) and IMD.\n"
        "STRICT GROUNDING RULE: You must ONLY communicate the verified meteorological and alert facts provided in the prompt. "
        "NEVER hallucinate, invent, or speculate any temperature, rain percentage, or wind metrics.\n"
        f"Target Persona: {persona.value.upper()}\n"
        f"Language requested: {lang.value.upper()} (Respond naturally in Hindi, Hinglish, or English as requested).\n"
        "Keep answers concise, direct, empathetic, and actionable.\n"
        "If the user greets you, introduce WeatherGPT and offer the live city snapshot.\n"
        "If the query is NOT about weather, climate, farming weather, travel weather, or disaster alerts, "
        "politely refuse to go off-topic, then still share the current city weather and invite a weather question. "
        "Never crash, never stay silent, never invent cricket/movie/politics answers."
    )

    data_payload = {
        "location": weather.location,
        "temperature_celsius": weather.temperature,
        "apparent_temperature": weather.apparent_temperature,
        "weather_condition": weather.condition,
        "precipitation_probability": weather.precipitation_probability,
        "humidity_percent": weather.humidity,
        "wind_speed_kmh": weather.wind_speed,
        "active_alert": alert.model_dump() if alert else None,
        "advisories": advisories
    }

    prompt = (
        f"User Query: \"{query}\"\n\n"
        f"Verified Meteorological Data:\n{data_payload}\n\n"
        f"Provide a natural, helpful, grounded response in {lang.value} with clear actionable advice."
    )

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
        )
    )
    return response.text
