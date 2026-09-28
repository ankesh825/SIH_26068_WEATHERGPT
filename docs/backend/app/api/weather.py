from fastapi import APIRouter, Query
from typing import Optional
from ..models.schemas import WeatherCardData, NWPComparisonResponse
from ..services.geocoding_service import resolve_location
from ..services.weather_service import fetch_weather_forecast, fetch_nwp_comparison
from ..services.alert_service import evaluate_disaster_alerts

router = APIRouter(prefix="/weather", tags=["Weather Intelligence"])

@router.get("/forecast", response_model=WeatherCardData)
async def get_forecast(
    location: Optional[str] = Query(None, description="City or district name"),
    lat: Optional[float] = Query(None, description="Latitude"),
    lon: Optional[float] = Query(None, description="Longitude")
):
    """Retrieves live weather conditions, hourly and 7-day forecasts."""
    resolved_name = "New Delhi"
    admin1 = "Delhi"

    if location:
        geo = await resolve_location(location)
        if geo:
            lat = geo["latitude"]
            lon = geo["longitude"]
            resolved_name = geo["name"]
            admin1 = geo.get("admin1", "")
    elif lat is None or lon is None:
        lat, lon = 28.6139, 77.2090

    weather = await fetch_weather_forecast(lat, lon, resolved_name, admin1)
    weather.severe_warning = evaluate_disaster_alerts(weather, location or resolved_name)
    return weather

@router.get("/models", response_model=NWPComparisonResponse)
async def get_nwp_comparison(
    location: Optional[str] = Query("Indore", description="City or district name")
):
    """Compares ECMWF, GFS, and ICON Numerical Weather Prediction models side-by-side."""
    geo = await resolve_location(location)
    lat = geo["latitude"] if geo else 22.7196
    lon = geo["longitude"] if geo else 75.8577
    name = geo["name"] if geo else location

    comp = await fetch_nwp_comparison(lat, lon, name)
    return NWPComparisonResponse(**comp)

MAJOR_INDIAN_CITIES = [
    {"name": "New Delhi", "state": "Delhi", "lat": 28.6139, "lon": 77.2090, "region": "North"},
    {"name": "Mumbai", "state": "Maharashtra", "lat": 19.0760, "lon": 72.8777, "region": "West"},
    {"name": "Bengaluru", "state": "Karnataka", "lat": 12.9716, "lon": 77.5946, "region": "South"},
    {"name": "Kolkata", "state": "West Bengal", "lat": 22.5726, "lon": 88.3639, "region": "East"},
    {"name": "Chennai", "state": "Tamil Nadu", "lat": 13.0827, "lon": 80.2707, "region": "South"},
    {"name": "Indore", "state": "Madhya Pradesh", "lat": 22.7196, "lon": 75.8577, "region": "Central"},
    {"name": "Bhopal", "state": "Madhya Pradesh", "lat": 23.2599, "lon": 77.4126, "region": "Central"},
    {"name": "Jaipur", "state": "Rajasthan", "lat": 26.9124, "lon": 75.7873, "region": "North-West"},
    {"name": "Hyderabad", "state": "Telangana", "lat": 17.3850, "lon": 78.4867, "region": "South-Central"},
    {"name": "Ahmedabad", "state": "Gujarat", "lat": 23.0225, "lon": 72.5714, "region": "West"},
    {"name": "Lucknow", "state": "Uttar Pradesh", "lat": 26.8467, "lon": 80.9462, "region": "North"},
    {"name": "Patna", "state": "Bihar", "lat": 25.5941, "lon": 85.1376, "region": "East"},
    {"name": "Pune", "state": "Maharashtra", "lat": 18.5204, "lon": 73.8567, "region": "West"},
    {"name": "Shimla", "state": "Himachal Pradesh", "lat": 31.1048, "lon": 77.1734, "region": "Himalayan"},
    {"name": "Srinagar", "state": "Jammu & Kashmir", "lat": 34.0837, "lon": 74.7973, "region": "North"},
    {"name": "Guwahati", "state": "Assam", "lat": 26.1445, "lon": 91.7362, "region": "North-East"},
    {"name": "Kochi", "state": "Kerala", "lat": 9.9312, "lon": 76.2673, "region": "Coastal South"},
]

@router.get("/all-india")
async def get_all_india_weather():
    """Fetches real-time weather summary across all major regions of India for the live ticker and map."""
    import httpx
    from ..services.weather_service import decode_wmo_code
    
    lats = ",".join(str(c["lat"]) for c in MAJOR_INDIAN_CITIES)
    lons = ",".join(str(c["lon"]) for c in MAJOR_INDIAN_CITIES)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lats}&longitude={lons}&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m&timezone=auto"
    
    items = []
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                data_list = data if isinstance(data, list) else [data]
                for idx, city in enumerate(MAJOR_INDIAN_CITIES):
                    c_data = data_list[idx].get("current", {}) if idx < len(data_list) else {}
                    code = int(c_data.get("weather_code", 1))
                    cond = decode_wmo_code(code)
                    items.append({
                        "name": city["name"],
                        "state": city["state"],
                        "region": city["region"],
                        "lat": city["lat"],
                        "lon": city["lon"],
                        "temperature": round(float(c_data.get("temperature_2m", 28.0))),
                        "humidity": int(c_data.get("relative_humidity_2m", 55)),
                        "wind": round(float(c_data.get("wind_speed_10m", 12.0))),
                        "precipitation": float(c_data.get("precipitation", 0.0)),
                        "condition": cond,
                        "weather_code": code
                    })
                return {"status": "success", "count": len(items), "cities": items}
    except Exception as e:
        print(f"All-India batch fetch fallback: {e}")

    # Fallback default values
    for city in MAJOR_INDIAN_CITIES:
        items.append({
            "name": city["name"],
            "state": city["state"],
            "region": city["region"],
            "lat": city["lat"],
            "lon": city["lon"],
            "temperature": 29,
            "humidity": 60,
            "wind": 12,
            "precipitation": 0.0,
            "condition": "⛅ Partly cloudy",
            "weather_code": 2
        })
    return {"status": "fallback", "count": len(items), "cities": items}
