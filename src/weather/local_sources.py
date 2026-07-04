import httpx
import re
from datetime import datetime

# City codes for China (sojson API)
CHINA_CITY_CODES = {
    "Beijing": "101010100",
    "Shanghai": "101020100",
    "Guangzhou": "101280101"
}

def get_hong_kong_local_forecast(target_date_str: str) -> float:
    """
    Fetches the local forecast for Hong Kong from the Hong Kong Observatory API.
    target_date_str format: YYYY-MM-DD
    """
    url = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php?dataType=fnd&lang=en"
    # Convert YYYY-MM-DD to YYYYMMDD
    target_date_clean = target_date_str.replace("-", "")
    
    response = httpx.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    for f in data.get("weatherForecast", []):
        if f.get("forecastDate") == target_date_clean:
            temp_info = f.get("forecastMaxtemp", {})
            return float(temp_info.get("value"))
            
    # Default to first forecast if target date is not found
    if data.get("weatherForecast"):
        return float(data["weatherForecast"][0].get("forecastMaxtemp", {}).get("value", 0.0))
    raise ValueError("No forecast found in HKO response.")


def get_tokyo_local_forecast(target_date_str: str) -> float:
    """
    Fetches Tokyo local forecast from the Japan Meteorological Agency (JMA) API.
    target_date_str format: YYYY-MM-DD
    """
    url = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"
    response = httpx.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    # Weekly forecast is typically the second item in the list
    if len(data) > 1:
        weekly = data[1]
        for ts in weekly.get("timeSeries", []):
            time_defines = ts.get("timeDefines", [])
            for area in ts.get("areas", []):
                # Tokyo area code is 130000/130010
                if area.get("area", {}).get("name") in ["東京", "東京地方"] and "tempsMax" in area:
                    temps_max = area["tempsMax"]
                    # Search for matching date in time_defines
                    for i, td in enumerate(time_defines):
                        # td is e.g. "2026-07-05T00:00:00+09:00"
                        if td.startswith(target_date_str):
                            val = temps_max[i]
                            if val:
                                return float(val)
                            
    # Fallback: check short term forecast in data[0]
    if len(data) > 0:
        short_term = data[0]
        for ts in short_term.get("timeSeries", []):
            for area in ts.get("areas", []):
                if area.get("area", {}).get("name") in ["東京", "東京地方"] and "temps" in area:
                    temps = [float(t) for t in area["temps"] if t]
                    if temps:
                        return max(temps)
                        
    raise ValueError("No Tokyo temperature forecast found in JMA response.")


def get_seoul_local_forecast(target_date_str: str) -> float:
    """
    Fetches Seoul local forecast from wttr.in JSON format.
    target_date_str format: YYYY-MM-DD
    """
    url = "https://wttr.in/Seoul?format=j1"
    response = httpx.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    for day in data.get("weather", []):
        if day.get("date") == target_date_str:
            return float(day.get("maxtempC"))
            
    # Default to first day if target date is not found
    if data.get("weather"):
        return float(data["weather"][0].get("maxtempC", 0.0))
    raise ValueError("No forecast found in wttr.in Seoul response.")


def get_china_local_forecast(city_name: str, target_date_str: str) -> float:
    """
    Fetches forecast for Beijing, Shanghai, or Guangzhou from the sojson local weather API.
    target_date_str format: YYYY-MM-DD
    """
    city_code = CHINA_CITY_CODES.get(city_name)
    if not city_code:
        raise ValueError(f"Unknown China city: {city_name}")
        
    url = f"http://t.weather.sojson.com/api/weather/city/{city_code}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = httpx.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()
    
    if data.get("status") == 200:
        forecast = data.get("data", {}).get("forecast", [])
        for f in forecast:
            if f.get("ymd") == target_date_str:
                high_str = f.get("high", "") # e.g. "高温 34℃"
                match = re.search(r"(\d+)", high_str)
                if match:
                    return float(match.group(1))
        # Default to first forecast if target date is not found
        if forecast:
            high_str = forecast[0].get("high", "")
            match = re.search(r"(\d+)", high_str)
            if match:
                return float(match.group(1))
    raise ValueError(f"No forecast found for {city_name} in sojson response.")


def get_local_source_high_temp(city_name: str, target_date_str: str) -> float:
    """
    Unified entry point to fetch weather forecast from local sources based on city name.
    """
    try:
        if city_name == "Hong Kong":
            return get_hong_kong_local_forecast(target_date_str)
        elif city_name == "Tokyo":
            return get_tokyo_local_forecast(target_date_str)
        elif city_name == "Seoul":
            return get_seoul_local_forecast(target_date_str)
        elif city_name in CHINA_CITY_CODES:
            return get_china_local_forecast(city_name, target_date_str)
        else:
            raise ValueError(f"No local source implemented for city: {city_name}")
    except Exception as e:
        print(f"Error fetching from local source for {city_name} on {target_date_str}: {e}")
        return None
