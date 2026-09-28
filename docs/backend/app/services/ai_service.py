import re
import os
import random
from typing import Dict, Any, Tuple, Optional, List
from ..models.schemas import (
    WeatherCardData,
    AlertItem,
    PersonaType,
    LanguageType,
    HourlyPoint,
    DailyForecast,
)
from ..config import settings

# In-memory multi-turn session memory: conversation_id -> session state
CONVERSATION_SESSIONS: Dict[str, Dict[str, Any]] = {}

# Supported Indian cities regex
KNOWN_LOCATIONS = [
    "indore", "bhopal", "delhi", "new delhi", "mumbai", "pune", "jaipur",
    "lucknow", "patna", "kolkata", "bengaluru", "bangalore", "chennai",
    "hyderabad", "ahmedabad", "chandigarh", "varanasi", "kanpur", "nagpur",
    "surat", "visakhapatnam", "shimla", "dehradun", "srinagar", "goa", "udaipur",
    "jodhpur", "amritsar", "agra", "gwalior", "jabalpur", "ujjain", "kochi", "guwahati"
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
    "os", "monsoon", "precip", "windchill", "feels like", "kapde", "sukha",
    "car wash", "dhona", "walk", "jogging", "cricket", "match", "khel", "kitne baje",
    "kab", "parso", "weekend", "ac", "fan", "pehne", "gaadi"
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

PURE_OFF_TOPIC = [
    "recipe", "cooking", "khana banana", "homework", "math", "coding", "python",
    "javascript", "bitcoin", "crypto", "stock price", "share market", "politics",
    "election", "joke", "shayari", "love", "girlfriend", "boyfriend", "dating",
    "pubg", "free fire", "who is pm", "prime minister", "modi", "story", "poem"
]

def _contains_any(text: str, words) -> bool:
    return any(w in text for w in words)

def infer_persona_from_query(message: str, fallback: PersonaType) -> PersonaType:
    """Auto-infers persona from query terms."""
    lower = message.lower()
    if _contains_any(lower, ["irrigate", "sinchai", "crop", "fasal", "khet", "kisan", "spray", "pesticide", "farmer"]):
        return PersonaType.FARMER
    if _contains_any(lower, ["travel", "safar", "drive", "road", "flight", "highway", "yatri", "visibility", "bike"]):
        return PersonaType.TRAVELER
    if _contains_any(lower, ["sdrf", "ndma", "evacuation", "shelter", "disaster officer", "eoc", "alert status"]):
        return PersonaType.DISASTER_OFFICER
    return fallback

def classify_dialog_intent(message: str) -> str:
    """Classifies user dialog into weather, greeting, identity, or off_topic."""
    lower = message.lower().strip()
    
    # Check if pure greeting
    for pat in GREETING_PATTERNS:
        if re.search(pat, lower):
            # If weather keywords also present (e.g. "Hi, Indore weather?"), treat as weather
            if not _contains_any(lower, WEATHER_KEYWORDS):
                return "greeting"
            
    for pat in IDENTITY_PATTERNS:
        if re.search(pat, lower):
            return "identity"

    weather_hit = _contains_any(lower, WEATHER_KEYWORDS)
    city_hit = any(re.search(rf"\b{re.escape(city)}\b", lower) for city in KNOWN_LOCATIONS)
    
    if weather_hit or city_hit:
        return "weather"

    # Contextual check for short follow-ups
    if any(lower.startswith(w) for w in ["aur ", "kitne ", "kab ", "kyu", "kya ", "is it ", "can i "]):
        return "weather"

    if _contains_any(lower, PURE_OFF_TOPIC):
        return "off_topic"

    if len(lower.split()) <= 4:
        return "off_topic"

    return "weather"

def parse_user_query(message: str, session_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Parses intent, activity, location, timeframe, and language from the user query.
    Takes into account session memory for follow-up questions.
    """
    lower = message.lower()
    dialog_intent = classify_dialog_intent(message)
    
    # 1. Natural Language Auto-Detection
    lang = LanguageType.HINGLISH
    if re.search(r'[\u0900-\u097F]', message):
        lang = LanguageType.HINDI
    else:
        hinglish_markers = [
            "kya", "hai", "hoga", "hogi", "batao", "kaise", "kaisa", "mein", "aaj",
            "kal", "baarish", "barish", "mausam", "khet", "sinchai", "safar", "jaana",
            "chahiye", "rahega", "kitna", "kitni", "bataiye", "hona", "dhoop", "garmi",
            "thand", "karein", "karu", "karoon", "khatra", "toofan", "sunte", "namaste",
            "kapde", "sukha", "dhona", "chhat", "gaadi"
        ]
        words = re.findall(r'[a-zA-Z]+', lower)
        has_hinglish = any(w in hinglish_markers for w in words)
        
        english_indicators = [
            "what", "will", "how", "is", "the", "weather", "temperature", "forecast",
            "should", "can", "heavy", "rain", "today", "tomorrow", "check", "tell",
            "alert", "humidity", "wind", "storm", "chance", "show", "radar", "clothes", "dry"
        ]
        has_english = any(w in english_indicators for w in words)

        if has_hinglish:
            lang = LanguageType.HINGLISH
        elif has_english and not has_hinglish:
            lang = LanguageType.ENGLISH
        else:
            lang = LanguageType.HINGLISH

    # 2. Location Detection with Session Memory Inheritence
    detected_location = None
    for city in KNOWN_LOCATIONS:
        if re.search(rf"\b{city}\b", lower):
            detected_location = city.title()
            break

    if not detected_location:
        m = re.search(r"\b(?:in|at|me|mein|sheher|city)\b\s+([a-zA-Z]+)", lower)
        if m and m.group(1) not in ["kal", "aaj", "rain", "baarish", "weather", "chhat", "khet", "par", "subah", "shaam"]:
            detected_location = m.group(1).title()

    # If user is asking a follow-up and didn't mention a city, inherit from session
    if not detected_location and session_data and session_data.get("last_city"):
        detected_location = session_data["last_city"]

    # 3. Timeframe Resolution
    timeframe = "today"
    if any(w in lower for w in ["parso", "day after tomorrow", "परसों"]):
        timeframe = "day_after_tomorrow"
    elif any(w in lower for w in ["kal", "tomorrow", "agli subah", "next day", "कल"]):
        timeframe = "tomorrow"
    elif any(w in lower for w in ["weekend", "sunday", "hafta", "week", "7 days", "agale din", "next 3 days", "3 din", "हफ्ते", "सप्ताहांत"]):
        timeframe = "7_days"

    # 4. Deep Activity & Lifestyle Intent Detection
    intent = "general_forecast"
    if dialog_intent != "weather":
        intent = dialog_intent
    # Specific Life Activities (Roman + Devanagari Script):
    elif any(w in lower for w in ["kapde", "dry clothes", "drying", "chhat par", "sukha", "कपड़े", "सुखा", "छत"]):
        intent = "clothes_drying"
    elif any(w in lower for w in ["car wash", "gaadi dhona", "bike wash", "dhulwa", "wash", "कार वॉश", "गाड़ी धो", "धुलवा"]):
        intent = "car_wash"
    elif any(w in lower for w in ["walk", "morning walk", "jogging", "exercise", "running", "tahalne", "sair", "मॉर्निंग वॉक", "टहलने", "दौड़"]):
        intent = "morning_walk"
    elif any(w in lower for w in ["cricket", "match", "khel", "football", "sports", "ground", "क्रिकेट", "मैच", "खेल"]):
        intent = "outdoor_sports"
    elif any(w in lower for w in ["kitne baje", "kab hogi", "kab aayegi", "what time", "when will it rain", "subah hogi", "shaam ko", "कितने बजे", "कब होगी", "कब आएगी", "कब तक आएगी", "कब तक"]):
        intent = "rain_timing"
    elif any(w in lower for w in ["kya pehne", "garmi lagegi", "thand lagegi", "ac chalaye", "fan", "sweater", "jacket", "hoodie", "feels like", "क्या पहनें", "गर्मी लगेगी", "ठंड", "स्वेटर"]):
        intent = "apparel_comfort"
    elif any(w in lower for w in ["parso", "weekend", "hafta", "7 din", "agale din", "next few days", "परसों", "सप्ताहांत", "हफ्ते"]):
        intent = "multi_day"
    elif any(w in lower for w in ["alert", "warning", "khatra", "cyclone", "toofan", "tsunami", "flood", "baad", "चेतावनी", "अलर्ट", "तूफान", "बाढ़"]):
        intent = "disaster_alert"
    elif any(w in lower for w in ["irrigate", "sinchai", "crop", "fasal", "khet", "kisan", "spray", "pesticide", "सिंचाई", "फसल", "खेत", "किसान", "कीटनाशक"]):
        intent = "agriculture"
    elif any(w in lower for w in ["travel", "safar", "jaana", "drive", "road", "flight", "highway", "bike se", "car se", "यात्रा", "सफर", "हाईवे", "सड़क"]):
        intent = "travel"
    elif any(w in lower for w in ["baarish", "rain", "raining", "barsat", "pani girega", "बारिश", "बरसात", "पानी गिरेगा", "वर्षा"]):
        intent = "rain_forecast"
    elif any(w in lower for w in ["garmi", "heat", "temperature", "temp", "cold", "sardi", "dhoop", "humid", "गर्मी", "तापमान", "सर्दी", "धूप"]):
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

# ==============================================================================
# Dynamic Meteorological Analysis Helpers
# ==============================================================================

def analyze_hourly_rain_window(hourly: List[HourlyPoint]) -> Tuple[bool, str, int]:
    """Finds peak precipitation hours and danger windows from 24h hourly points."""
    if not hourly:
        return False, "Din bhar normal", 0
        
    rain_hours = [h for h in hourly if h.precipitation_probability >= 35]
    if not rain_hours:
        return False, "Agale 24 ghante aasmaan mostly dry rahega", max((h.precipitation_probability for h in hourly), default=10)
        
    start_time = rain_hours[0].time
    end_time = rain_hours[-1].time
    peak_prob = max(h.precipitation_probability for h in rain_hours)
    window_str = f"{start_time} se {end_time}"
    return True, window_str, peak_prob

def format_multi_day_summary(daily: List[DailyForecast], lang: LanguageType) -> str:
    """Constructs dynamic day-by-day forecast overview."""
    if not daily:
        return ""
    lines = []
    days_to_show = daily[:3]
    for d in days_to_show:
        if lang == LanguageType.HINDI:
            lines.append(f"• **{d.date}:** {d.condition}, तापमान {round(d.max_temp)}°/{round(d.min_temp)}°C, बारिश की संभावना {d.precipitation_probability}%")
        elif lang == LanguageType.ENGLISH:
            lines.append(f"• **{d.date}:** {d.condition}, Temp {round(d.max_temp)}°/{round(d.min_temp)}°C, Rain Risk {d.precipitation_probability}%")
        else:
            lines.append(f"• **{d.date}:** {d.condition}, Temp {round(d.max_temp)}°/{round(d.min_temp)}°C, Baarish risk ~{d.precipitation_probability}%")
    return "\n".join(lines)

# ==============================================================================
# Conversational Synthesis
# ==============================================================================

async def generate_conversational_response(
    query: str,
    parsed: Dict[str, Any],
    weather: WeatherCardData,
    alert: Optional[AlertItem],
    advisories: list,
    persona: PersonaType,
    lang: LanguageType,
    conversation_id: Optional[str] = None
) -> str:
    """
    Synthesizes a human-like, non-repetitive, authoritative meteorological response.
    Supports multi-turn memory and lifestyle-specific context.
    """
    dialog = parsed.get("dialog_intent") or parsed.get("intent")
    if dialog in ("greeting", "identity", "off_topic"):
        return _scope_conversation_reply(query, dialog, weather, lang)

    # 1. Update session memory
    if conversation_id:
        if conversation_id not in CONVERSATION_SESSIONS:
            CONVERSATION_SESSIONS[conversation_id] = {}
        CONVERSATION_SESSIONS[conversation_id]["last_city"] = weather.location
        CONVERSATION_SESSIONS[conversation_id]["last_intent"] = parsed.get("intent")
        CONVERSATION_SESSIONS[conversation_id]["last_weather"] = weather

    # 2. Try Google Gemini if configured
    gemini_key = settings.GEMINI_API_KEY.strip()
    if gemini_key:
        try:
            return await _call_gemini_llm(
                query, parsed, weather, alert, advisories, persona, lang, gemini_key, conversation_id
            )
        except Exception as e:
            print(f"Gemini API note ({e}), using dynamic built-in NLU intelligence.")

    # 3. Built-in Dynamic Grounded Meteorological Intelligence Engine
    return _generate_dynamic_nlu_response(
        query, parsed, weather, alert, advisories, persona, lang
    )

def _generate_dynamic_nlu_response(
    query: str,
    parsed: Dict[str, Any],
    weather: WeatherCardData,
    alert: Optional[AlertItem],
    advisories: list,
    persona: PersonaType,
    lang: LanguageType
) -> str:
    loc = weather.location
    intent = parsed.get("intent", "general_forecast")
    timeframe = parsed.get("timeframe", "today")
    rain_prob = weather.precipitation_probability
    temp = round(weather.temperature)
    app_temp = round(weather.apparent_temperature)
    condition = weather.condition
    wind = round(weather.wind_speed)
    humidity = weather.humidity
    uv = weather.uv_index

    time_label_hi = "परसों" if timeframe == "day_after_tomorrow" else ("कल" if timeframe == "tomorrow" else "आज")
    time_label_hg = "Parso" if timeframe == "day_after_tomorrow" else ("Kal" if timeframe == "tomorrow" else "Aaj")
    time_label_en = "Day after tomorrow" if timeframe == "day_after_tomorrow" else ("Tomorrow" if timeframe == "tomorrow" else "Today")

    has_rain_window, rain_window, peak_rain = analyze_hourly_rain_window(weather.hourly)

    # Alert prefix if severe
    alert_prefix = ""
    if alert and alert.severity.value in ["warning", "severe"]:
        if lang == LanguageType.HINDI:
            alert_prefix = f"🚨 **चेतावनी ({alert.category}):** {alert.headline}!\n\n"
        elif lang == LanguageType.ENGLISH:
            alert_prefix = f"🚨 **OFFICIAL ALERT ({alert.category}):** {alert.headline}!\n\n"
        else:
            alert_prefix = f"🚨 **ALERT ({alert.category}):** {alert.headline}!\n\n"

    # Conversational Openings (Varied and Natural)
    openers_hg = [
        f"Maine **{loc}** ka live forecast check kiya hai — ",
        f"Dekhiye, **{loc}** ke meteorological parameters yeh batate hain ki ",
        f"**{loc}** ke live data ke mutabiq: ",
        f"Bilkul! **{loc}** ka updated mausam situation yeh hai: "
    ]
    openers_hi = [
        f"मैंने **{loc}** का मौसम विश्लेषण देखा है — ",
        f"**{loc}** के वर्तमान मौसम आंकड़ों के अनुसार: ",
        f"देखिए, **{loc}** के हालात यह बताते हैं कि "
    ]
    openers_en = [
        f"Based on real-time meteorological observations for **{loc}**: ",
        f"Here is the verified weather breakdown for **{loc}**: ",
        f"Looking at the current atmospheric readings in **{loc}**: "
    ]

    op_hg = random.choice(openers_hg)
    op_hi = random.choice(openers_hi)
    op_en = random.choice(openers_en)

    body = ""

    # ==========================================================================
    # 1. Clothes Drying Intent
    # ==========================================================================
    if intent == "clothes_drying":
        if rain_prob > 35 or humidity > 75:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}**नहीं**, {time_label_hi} छत पर कपड़े सुखाना जोखिम भरा हो सकता है। बारिश की संभावना लगभग **{rain_prob}%** है और हवा में नमी **{humidity}%** है। कपड़े सूखने में काफी समय लगेगा और भीगने का डर है। बेहतर होगा कपड़े बालकनी या अंदर सुखाएं।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}**Not recommended.** Drying clothes outside {time_label_en.lower()} is risky due to a **{rain_prob}% chance of rain** and high relative humidity ({humidity}%). It is safer to dry clothes indoors or under a covered balcony."
            else:
                body = f"{op_hg}**Nahi**, {time_label_hg.lower()} chhat par kapde sukhana safe nahi rahega. Baarish ki probability **{rain_prob}%** hai aur humidity **{humidity}%** hone ki wajah se kapde jaldi nahi sukhenge aur bheegne ka risk rahega. Behtar hai balcony ya indoor dry karein."
        else:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}**हाँ, बिल्कुल!** {time_label_hi} छत पर कपड़े आसानी से सूख जाएंगे। धूप अच्छी रहेगी, बारिश की संभावना मात्र **{rain_prob}%** है और तापमान लगभग **{temp}°C** बना रहेगा।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}**Yes, absolutely!** Weather conditions {time_label_en.lower()} are favorable for drying laundry outside. Rain risk is minimal ({rain_prob}%) with sunshine and temperatures around **{temp}°C**."
            else:
                body = f"{op_hg}**Haan, bilkul!** {time_label_hg.lower()} chhat par kapde aaram se sukha sakte ho. Baarish ke chances na ke barabar ({rain_prob}%) hain, aasmaan mostly {condition.lower()} rahega aur temperature **{temp}°C** tak jayega."

    # ==========================================================================
    # 2. Car / Bike Wash Intent
    # ==========================================================================
    elif intent == "car_wash":
        if rain_prob > 30 or has_rain_window:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}गाड़ी वॉश कराना **अभी स्थगित (postpone) करना बेहतर होगा**। {time_label_hi} बारिश की संभावना **{rain_prob}%** है ({rain_window} के दौरान बौछारें पड़ सकती हैं)। सड़क पर कीचड़ और पानी से गाड़ी दोबारा गंदी हो सकती है।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}It is better to **hold off on washing your vehicle**. Rain probability is at **{rain_prob}%** {time_label_en.lower()} (potential showers expected around {rain_window}). Road spray and wet dirt will likely soil it right away."
            else:
                body = f"{op_hg}Abhi car/bike wash karwana **postpone karna hi samajhdari hogi**. {time_label_hg.lower()} baarish ke **{rain_prob}% chances** hain ({rain_window} ke aas-paas shower aa sakti hai). Geeli sadak aur keechad se gaadi fir gandi ho jayegi."
        else:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}**हाँ, गाड़ी धुलवा सकते हैं!** अगले 48 घंटों में मौसम साफ और शुष्क (dry) रहने की संभावना है। बारिश का खतरा केवल {rain_prob}% है।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}**Go ahead with the car wash!** Conditions remain clear and dry for the next 48 hours with rain risk at just {rain_prob}%."
            else:
                body = f"{op_hg}**Haan, gaadi wash karwa sakte hain!** Agle 2-3 din tak mausam dry aur clear rehne ka anumaan hai. Baarish ka risk sirf **{rain_prob}%** hai."

    # ==========================================================================
    # 3. Rain Timing Window Intent
    # ==========================================================================
    elif intent == "rain_timing":
        if has_rain_window:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}{loc} में मुख्य रूप से **{rain_window}** के बीच बारिश या बौछारें पड़ने की प्रबल संभावना (अधिकतम **{peak_rain}%**) दिख रही है। बाकी समय मौसम {condition.lower()} रहने का अनुमान है।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}In {loc}, the primary rain window is expected between **{rain_window}**, with peak probability reaching **{peak_rain}%**. Skies will otherwise remain {condition.lower()}."
            else:
                body = f"{op_hg}{loc} mein baarish ka main danger window **{rain_window}** ke beech dikh raha hai (peak probability ~**{peak_rain}%**). Baaki samay aasmaan mostly {condition.lower()} bana rahega."
        else:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}अगले 24 घंटों में किसी विशिष्ट समय भारी बारिश की संभावना नहीं है। हल्की-फुल्की छिटपुट नमी हो सकती है लेकिन कोई बड़ा बारिश का दौर सक्रिय नहीं है।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}No concentrated downpour window is visible in the next 24 hours. Precipitation risk stays low at {rain_prob}%."
            else:
                body = f"{op_hg}Agale 24 ghante me specific continuous baarish ka window nahi hai. Baarish ki probability sirf **{rain_prob}%** hai, isliye din mostly safe aur khula rahega."

    # ==========================================================================
    # 4. Morning Walk & Outdoor Exercise Intent
    # ==========================================================================
    elif intent == "morning_walk":
        if rain_prob > 50:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}सुबह की वॉक के समय **सावधानी रखें या घर पर ही व्यायाम करें**। सुबह बूंदाबांदी की संभावना (~{rain_prob}%) है। तापमान लगभग {temp}°C रहेगा।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}Consider **indoor workouts or keeping an umbrella ready** for your morning walk. Rain probability is elevated around {rain_prob}% with morning temperatures near {temp}°C."
            else:
                body = f"{op_hg}Subah ki walk ke dauran chhatri sath rakhein ya indoor exercise karein. Subah ke waqt boonda-baandi ke chances (~{rain_prob}%) hain. Temperature {temp}°C rahega."
        elif humidity > 85:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}वॉक पर जा सकते हैं, लेकिन हवा में नमी ({humidity}%) काफी ज्यादा है जिससे उमस और पसीना महसूस होगा। सुबह 6:00 से 7:30 बजे के बीच वॉक पूरी कर लेना सबसे बेहतर रहेगा।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}Walking conditions are possible, but high relative humidity ({humidity}%) may cause noticeable stuffiness. Planning your walk between 6:00 AM and 7:30 AM is recommended."
            else:
                body = f"{op_hg}Walk par ja sakte hain, lekin hawa me humidity ({humidity}%) kafi zyada hai jisse thoda paseena aur suffocating feel ho sakta hai. Subah 6:00 AM se 7:30 AM ke beech walk complete karna best rahega."
        else:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}**मॉर्निंग वॉक के लिए मौसम एकदम अनुकूल और सुहावना है!** ताजी हवा ({wind} km/h), सुखद तापमान (~{temp}°C) और खुला आसमान रहेगा। सुबह 6:30 से 8:30 बजे का समय सबसे उत्तम है।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}**Excellent conditions for a morning walk!** Fresh breezes ({wind} km/h), pleasant temperatures around {temp}°C, and clear skies make 6:30 AM to 8:30 AM ideal."
            else:
                body = f"{op_hg}**Morning walk ke liye mausam bilkul shandaar hai!** Taaza hawa ({wind} km/h), sukhad temperature (~{temp}°C), aur aasmaan saaf rahega. 6:30 AM se 8:30 AM ka time sabse optimal rahega."

    # ==========================================================================
    # 5. Outdoor Sports (Cricket, Football, Matches)
    # ==========================================================================
    elif intent == "outdoor_sports":
        if rain_prob > 40:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}मैच या खेल आयोजन में **बारिश से रुकावट आ सकती है**। बारिश की संभावना {rain_prob}% है और आउटफील्ड गीली रहने की आशंका है।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}Outdoor sports or cricket matches face a **fair risk of weather interruption** ({rain_prob}% rain probability) with potential wet outfield conditions."
            else:
                body = f"{op_hg}Ground par match ya sports me **baarish ki wajah se interruption aa sakta hai**. Baarish ka risk **{rain_prob}%** hai aur outfield geeli ho sakti hai."
        else:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}**खेलने के लिए मौसम बहुत बढ़िया है!** बारिश का कोई खतरा नहीं है ({rain_prob}%), हवा की गति {wind} km/h है और दृश्यता पूरी तरह साफ है।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}**Conditions are great for outdoor sports!** Rain risk is negligible ({rain_prob}%), wind is manageable at {wind} km/h, and visibility is crystal clear."
            else:
                body = f"{op_hg}**Ground par khelne ke liye mausam ekdam solid hai!** Baarish ka koi darr nahi hai (sirf {rain_prob}%), hawa ki raftaar {wind} km/h hai aur pitch condition dry rahegi."

    # ==========================================================================
    # 6. Apparel, AC & Comfort Intent
    # ==========================================================================
    elif intent == "apparel_comfort":
        if temp >= 34 or app_temp >= 36:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}काफी गर्मी और उमस रहेगी! तापमान **{temp}°C** है लेकिन महसूस **{app_temp}°C** जैसा हो रहा है (आर्द्रता: {humidity}%)। हल्के सूती (कॉटन) कपड़े पहनें और पंखे/कूलर की जरूरत पड़ेगी।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}Expect intense heat and humidity! Temperature reads **{temp}°C** but feels like **{app_temp}°C** with {humidity}% humidity. Lightweight cotton clothing and indoor cooling are advisable."
            else:
                body = f"{op_hg}Kaafi garmi aur humidity mehsoos hogi! Actual temperature **{temp}°C** hai lekin **Feels Like {app_temp}°C** tak ja raha hai (Humidity: {humidity}%). Halka sooti (cotton) kapda pehnein aur indoor AC/cooler ki zaroorat pad sakti hai."
        elif temp <= 18:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}हल्की ठंड महसूस होगी! तापमान **{temp}°C** है। सुबह और शाम के समय हल्की जैकेट, शॉल या फुल स्लीव्स के कपड़े पहनना आरामदायक रहेगा।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}Mild chill expected with temperatures around **{temp}°C**. A light sweater, hoodie, or jacket is recommended during morning and evening hours."
            else:
                body = f"{op_hg}Halki thand mehsoos hogi! Temperature **{temp}°C** hai. Subah aur shaam ke waqt halki jacket, hoodie ya full sleeves pehenna aaramdayak rahega."
        else:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}मौसम काफी संतुलित और आरामदायक बना हुआ है। तापमान **{temp}°C** (महसूस: {app_temp}°C) है। सामान्य नियमित कपड़े पहन सकते हैं।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}Atmospheric comfort is well-balanced. Temperature is **{temp}°C** (feels like {app_temp}°C). Normal day-to-day apparel is optimal."
            else:
                body = f"{op_hg}Mausam kaafi balanced aur comfortable hai! Temperature **{temp}°C** (feels like {app_temp}°C) hai. Normal regular kapde pehan sakte hain, na zyada thand lagegi na extreme garmi."

    # ==========================================================================
    # 7. Multi-Day & Weekend Outlook
    # ==========================================================================
    elif intent == "multi_day":
        daily_breakdown = format_multi_day_summary(weather.daily, lang)
        if lang == LanguageType.HINDI:
            body = f"{op_hi}**{loc} के आगामी दिनों का मौसम विवरण:**\n\n{daily_breakdown}\n\nसमग्र रूप से स्थितियां स्थिर हैं और सप्ताहांत के दौरान हल्की धूप-छांव बनी रहेगी।"
        elif lang == LanguageType.ENGLISH:
            body = f"{op_en}**Upcoming multi-day forecast for {loc}:**\n\n{daily_breakdown}\n\nOverall, atmospheric conditions remain relatively stable with intermittent cloud cover."
        else:
            body = f"{op_hg}**{loc} ke aane wale dino ka haal:**\n\n{daily_breakdown}\n\nAgle 2-3 din temperature lagbhag **{temp}°C** ke aas-paas float karega."

    # ==========================================================================
    # 8. Agriculture / Irrigation Intent
    # ==========================================================================
    elif intent == "agriculture":
        if rain_prob > 45 or weather.precipitation > 2.0:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}**सिंचाई फिलहाल स्थगित रखें!** बारिश की संभावना **{rain_prob}%** है जिससे मिट्टी में पर्याप्त नमी आ जाएगी। हवा की गति {wind} km/h रहने से कीटनाशक स्प्रे करने से बचें ताकि छिड़काव धुल न जाए।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}**Postpone field irrigation.** Rain probability is high at **{rain_prob}%**, which will naturally replenish soil moisture. Hold off on agrochemical spraying due to wind speeds of {wind} km/h."
            else:
                body = f"{op_hg}**Sinchai filhal taal dein (Postpone Irrigation)!** Baarish ke chances **{rain_prob}%** hain jisse khet me pehle se paryapt nami aa sakti hai. Saath hi hawa ki raftaar {wind} km/h hai, isliye keetnashak spray na karein taaki chemical wash-off na ho."
        else:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}**सिंचाई के लिए अनुकूल समय है।** अगले 24-48 घंटों में भारी बारिश का कोई संकेत नहीं है ({rain_prob}% संभावना)। सुबह या शाम के समय हल्की सिंचाई कर सकते हैं।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}**Favorable window for field irrigation.** No heavy precipitation expected over the next 24-48 hours ({rain_prob}% risk). Early morning or late evening watering is optimal."
            else:
                body = f"{op_hg}**Sinchai ke liye anukool samay hai.** Agale 24-48 ghanto me bhaari baarish ka koi sanket nahi hai ({rain_prob}% chance). Subah ya shaam ke waqt light irrigation kar sakte hain."

    # ==========================================================================
    # 9. Travel & Transit Intent
    # ==========================================================================
    elif intent == "travel":
        if rain_prob > 40:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}हाईवे यात्रा पर **थोड़ी सावधानी बरतें**। गीली सड़क पर फिसलने का जोखिम हो सकता है, वाहन की गति नियंत्रित रखें और दोपहिया वाहन के स्थान पर 4-पहिया वाहन को प्राथमिकता दें।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}Exercise **caution during highway travel**. Wet road surfaces may reduce tire traction. Maintain a safe braking distance and consider four-wheelers over two-wheelers."
            else:
                body = f"{op_hg}Highway travel par **thodi savdhani baratne ki zaroorat hai**. Sadak par hydroplaning aur geelapan ho sakta hai, gaadi ki braking buffer badhayein. Bike ke bajay 4-wheeler prefer karein."
        elif wind > 25:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}यात्रा सुरक्षित है, लेकिन खुले फ्लाईओवरों पर तेज हवा ({wind} km/h) का दबाव महसूस हो सकता है। दोपहिया वाहन की गति 50-60 km/h के भीतर रखें।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}Road travel is generally safe, though crosswinds up to {wind} km/h may be encountered on open bypasses and bridges. Keep speeds moderate."
            else:
                body = f"{op_hg}Travel safe hai, lekin flyovers aur open stretches par crosswind ({wind} km/h) mehsoos ho sakti hai. Two-wheeler riders speed 50-60 km/h ke andar rakhein."
        else:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}**यात्रा के लिए स्थितियां पूरी तरह अनुकूल और सुरक्षित हैं!** दृश्यता 8 किमी से अधिक है, सड़क की पकड़ बेहतर है और सुगम यात्रा रहेगी।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}**Excellent conditions for highway travel!** Clear visibility over 8 km, dry roads, and calm winds ensure a safe, comfortable journey."
            else:
                body = f"{op_hg}**Travel ke liye conditions bilkul clear aur green hain!** Highway corridor par visibility >8 km hai, road grip behtar hai aur mausam safar ke liye aasan rahega."

    # ==========================================================================
    # 10. Rain Forecast Intent
    # ==========================================================================
    elif intent == "rain_forecast":
        if rain_prob > 60:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}हाँ, {loc} में {time_label_hi} बारिश होने की **प्रबल संभावना ({rain_prob}%)** है! {('खासकर ' + rain_window + ' के दौरान तेज बौछारें आ सकती हैं।') if has_rain_window else ''} बाहर निकलते समय छाता जरूर साथ रखें।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}Yes, there is a **high probability of rain ({rain_prob}%)** in {loc} {time_label_en.lower()}! {('Particularly active window around ' + rain_window + '.') if has_rain_window else ''} Carrying rain gear is strongly advised."
            else:
                body = f"{op_hg}Haan, {loc} mein {time_label_hg.lower()} baarish hone ke **kaafi acche chances ({rain_prob}%)** hain! {('Khaaskar ' + rain_window + ' ke dauran boonda-baandi ya downpour ho sakti hai.') if has_rain_window else ''} Baahar nikalte samay umbrella sath zaroor rakhein."
        elif rain_prob > 30:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}{loc} में {time_label_hi} छिटपुट बौछारें पड़ने की संभावना (**{rain_prob}%**) है। दिन में आसमान {condition.lower()} रहेगा और तापमान लगभग **{temp}°C** रहेगा।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}Scattered showers or passing rain are possible in {loc} {time_label_en.lower()} (**{rain_prob}%** chance). Skies will remain {condition.lower()} with temperatures around **{temp}°C**."
            else:
                body = f"{op_hg}{loc} mein {time_label_hg.lower()} thodi bahut chhitput boonda-baandi ya passing showers ki possibility (**{rain_prob}%**) hai. Din me aasmaan {condition.lower()} rahega aur temperature **{temp}°C** rahega."
        else:
            if lang == LanguageType.HINDI:
                body = f"{op_hi}{loc} में {time_label_hi} बारिश की संभावना बहुत कम (**{rain_prob}%**) है। दिन भर आसमान ज्यादातर {condition.lower()} और साफ रहेगा, अधिकतम तापमान **{temp}°C** तक पहुंचेगा।"
            elif lang == LanguageType.ENGLISH:
                body = f"{op_en}Precipitation risk is minimal in {loc} {time_label_en.lower()} (**{rain_prob}%**). The day will remain mostly {condition.lower()} and sunny, with highs around **{temp}°C**."
            else:
                body = f"{op_hg}{loc} mein {time_label_hg.lower()} baarish ki possibility kaafi kam (**{rain_prob}%**) hai. Aasmaan zyadatar {condition.lower()} rahega aur dhoop ke sath maximum temperature **{temp}°C** tak jayega."

    # ==========================================================================
    # 11. Default General Forecast
    # ==========================================================================
    else:
        if lang == LanguageType.HINDI:
            body = f"{op_hi}{loc} में {time_label_hi} मौसम **{condition}** बना हुआ है। वर्तमान तापमान **{temp}°C** (महसूस: **{app_temp}°C**) है। हवा की गति **{wind} km/h** और बारिश की संभावना लगभग **{rain_prob}%** है।"
        elif lang == LanguageType.ENGLISH:
            body = f"{op_en}In {loc}, conditions {time_label_en.lower()} are **{condition}**. Current temperature is **{temp}°C** (feels like **{app_temp}°C**). Wind speed is **{wind} km/h** with rain probability around **{rain_prob}%**."
        else:
            body = f"{op_hg}{loc} mein {time_label_hg.lower()} mausam **{condition}** bana hua hai. Current temperature **{temp}°C** hai (lekin humidity {humidity}% hone ki wajah se feels-like **{app_temp}°C** lag raha hai). Hawa ki raftaar **{wind} km/h** hai aur baarish ka risk lagbhag **{rain_prob}%** hai."

    # Append actionable persona tip if relevant
    tip_str = ""
    if advisories:
        tip_str = "\n\n💡 **Actionable Tip:**\n• " + "\n• ".join(advisories[:2])

    return f"{alert_prefix}{body}{tip_str}"

# ==============================================================================
# Non-Weather Conversation Handling
# ==============================================================================

def _scope_conversation_reply(query: str, dialog: str, weather: WeatherCardData, lang: LanguageType) -> Optional[str]:
    loc = weather.location
    temp = round(weather.temperature)
    condition = weather.condition
    rain = weather.precipitation_probability

    if dialog == "greeting":
        if lang == LanguageType.HINDI:
            return (
                f"नमस्ते! मैं **WeatherGPT** हूँ — मौसम, आपदा चेतावनी, यात्रा और खेती सलाह के लिए आपका सहायक।\n\n"
                f"अभी **{loc}** में तापमान **{temp}°C** है और मौसम {condition} है (बारिश की संभावना ~{rain}%)।\n\n"
                "आप मुझसे कुछ भी पूछ सकते हैं — जैसे 'कल बारिश होगी?', 'कपड़े सुखा सकते हैं?', 'कार वॉश कराएं?' या 'हाईवे सेफ है?'"
            )
        if lang == LanguageType.ENGLISH:
            return (
                f"Hello! I am **WeatherGPT**, your meteorological copilot.\n\n"
                f"Currently in **{loc}**, it is **{temp}°C** and {condition}, with approximately {rain}% chance of rain.\n\n"
                "Ask me anything — rain forecasts, laundry drying, morning walk conditions, or travel safety!"
            )
        return (
            f"Namaste! Main **WeatherGPT** hoon — aapka weather, disaster alert aur lifestyle safety copilot.\n\n"
            f"Abhi **{loc}** mein temperature **{temp}°C** hai, aasmaan {condition.lower()} hai aur baarish ~{rain}%.\n\n"
            "Aap freely pooch sakte hain — jaise 'Kal baarish kitne baje hogi?', 'Chhat par kapde sukha lu?', 'Morning walk ka mausam kaisa hai?' ya 'Kheti me paani kab du?'"
        )

    if dialog == "identity":
        return (
            "Main **WeatherGPT (SIH26068)** hoon — Ministry of Earth Sciences (MoES) aur IMD ke theme par aadharit conversational weather AI.\n"
            "Main verified datasets (Open-Meteo, ECMWF, GFS, NDMA CAP) se data lekar common sense lifestyle aur farming decisions me madad karta hoon.\n\n"
            f"Abhi **{loc}** ka live reading: **{temp}°C**, {condition}."
        )

    if dialog == "off_topic":
        if lang == LanguageType.HINDI:
            return (
                f"यह सवाल मौसम या आपदा सुरक्षा से संबंधित नहीं लगता। गलत जानकारी से बचने के लिए मैं केवल मौसम और सुरक्षा से जुड़े विषयों पर जवाब देता हूँ।\n\n"
                f"वैसे **{loc}** में अभी तापमान **{temp}°C**, मौसम {condition}, और बारिश की संभावना ~{rain}% है। आप मौसम या यात्रा संबंधी सवाल पूछ सकते हैं।"
            )
        return (
            f"Yeh sawal weather ya safety se related nahi lagta, isliye main ispe guess nahi karunga.\n\n"
            f"Lekin **{loc}** ka mausam mere paas live ready hai: **{temp}°C**, {condition}, baarish ~{rain}%. "
            "Aap baarish, kapde sukhane, car wash, farming ya travel safety ke baare me poochiye!"
        )

    return None

# ==============================================================================
# Google Gemini LLM Integration
# ==============================================================================

async def _call_gemini_llm(
    query: str,
    parsed: Dict[str, Any],
    weather: WeatherCardData,
    alert: Optional[AlertItem],
    advisories: list,
    persona: PersonaType,
    lang: LanguageType,
    api_key: str,
    conversation_id: Optional[str] = None
) -> str:
    """Invokes Google Gemini with verified meteorological facts and conversational persona."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    system_prompt = (
        "You are WeatherGPT, a highly intelligent, authoritative, and friendly conversational meteorological AI platform developed for "
        "Smart India Hackathon (SIH26068) under the Ministry of Earth Sciences (MoES) and IMD.\n\n"
        "STRICT GROUNDING RULE: You must ONLY communicate the verified meteorological and alert facts provided in the prompt. "
        "NEVER hallucinate, invent, or speculate any temperature, rain percentage, or wind metrics.\n\n"
        "NATURAL CONVERSATION & INTELLIGENCE:\n"
        "• Be conversational, warm, and natural — never robotic or repetitive.\n"
        "• If the user asks real-world lifestyle questions (e.g., drying clothes, washing cars, morning walk, outdoor cricket, carrying umbrellas, clothes to wear, AC/fan), directly answer with practical yes/no advice backed by the verified weather metrics (rain chance, humidity, UV, wind).\n"
        "• If the user asks about rain timing, analyze the hourly forecast provided and state the exact window.\n"
        "• Automatically mirror the user's language and dialect (Devanagari Hindi -> pure Hindi, Hinglish/Roman script -> fluent Hinglish, English -> English).\n"
        "• Target Persona: " + persona.value.upper() + "\n"
        "• Keep answers direct, empathetic, and actionable."
    )

    data_payload = {
        "location": weather.location,
        "temperature_celsius": weather.temperature,
        "apparent_temperature": weather.apparent_temperature,
        "weather_condition": weather.condition,
        "precipitation_probability": weather.precipitation_probability,
        "humidity_percent": weather.humidity,
        "wind_speed_kmh": weather.wind_speed,
        "uv_index": weather.uv_index,
        "hourly_next_12_hours": [{"time": h.time, "temp": h.temperature, "rain_prob": h.precipitation_probability, "cond": h.condition} for h in weather.hourly[:12]],
        "daily_next_3_days": [{"date": d.date, "max_temp": d.max_temp, "min_temp": d.min_temp, "rain_prob": d.precipitation_probability, "cond": d.condition} for d in weather.daily[:3]],
        "active_alert": alert.model_dump() if alert else None,
        "domain_advisories": advisories
    }

    prompt = (
        f"User Query: \"{query}\"\n\n"
        f"Verified Meteorological Facts:\n{data_payload}\n\n"
        f"Synthesize an intelligent, conversational, direct response addressing the user's specific question."
    )

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.3,
        )
    )
    return response.text
