import httpx
import config
from src.weather.apify_client import get_apify_weather_forecast

def get_point_forecast(city, days=3):
    """
    Standard forecast fetch for today/tomorrow (legacy compatibility).
    """
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "celsius",
        "timezone": "auto",
        "forecast_days": days,
    }
    response = httpx.get(config.OPEN_METEO_URL, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def get_open_meteo_forecast_for_date(city, target_date_str: str) -> float:
    """
    Fetches the Open-Meteo forecast high for a specific date (YYYY-MM-DD).
    """
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "daily": "temperature_2m_max",
        "temperature_unit": "celsius",
        "timezone": "auto",
        "forecast_days": 7,
    }
    try:
        response = httpx.get(config.OPEN_METEO_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        dates = data.get("daily", {}).get("time", [])
        temps = data.get("daily", {}).get("temperature_2m_max", [])
        
        for idx, date_val in enumerate(dates):
            if date_val == target_date_str:
                return float(temps[idx])
                
        # Default fallback: return first day if target date not found
        if temps:
            return float(temps[0])
    except Exception as e:
        print(f"[OpenMeteo] Error fetching forecast for {city['name']}: {e}")
    return None


def get_consensus_forecast_high(city, target_date_str: str) -> float:
    """
    Computes a consensus forecast high temperature for a city and target date
    by averaging the global Open-Meteo forecast and the local country API forecast.
    """
    # 1. Fetch Open-Meteo forecast (Global)
    om_temp = get_open_meteo_forecast_for_date(city, target_date_str)
    
    # 2. Fetch Local source (per-country / Apify)
    local_temp = get_apify_weather_forecast(city["name"], target_date_str)
    
    # 3. Consensus Logic
    if om_temp is not None and local_temp is not None:
        consensus = round((om_temp + local_temp) / 2.0, 2)
        print(f"[CONSENSUS] {city['name']} ({target_date_str}) -> Global: {om_temp}°C, Local: {local_temp}°C -> Consensus: {consensus}°C")
        return consensus
    elif om_temp is not None:
        print(f"[CONSENSUS] {city['name']} ({target_date_str}) -> Global Only: {om_temp}°C")
        return om_temp
    elif local_temp is not None:
        print(f"[CONSENSUS] {city['name']} ({target_date_str}) -> Local Only: {local_temp}°C")
        return local_temp
    else:
        # Emergency fallback: try legacy forecast endpoint
        try:
            forecast = get_point_forecast(city, days=3)
            fallback_temp = float(forecast["daily"]["temperature_2m_max"][0])
            print(f"[CONSENSUS] {city['name']} ({target_date_str}) -> Emergency Fallback to today: {fallback_temp}°C")
            return fallback_temp
        except Exception as e:
            raise ValueError(f"Failed to fetch any forecast high for {city['name']}: {e}")