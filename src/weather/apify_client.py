import os
import config
from apify_client import ApifyClient
from src.weather.local_sources import get_local_source_high_temp

def get_apify_weather_forecast(city_name: str, target_date_str: str) -> float:
    """
    Fetches the forecast high temperature for a city and target date using Apify's
    oneary/weather-database-scraper.
    Falls back to local country-specific weather APIs if APIFY_TOKEN is missing,
    or if the Apify run fails.
    """
    if not config.APIFY_TOKEN:
        print(f"[APIFY] No token configured. Falling back to local per-country API for {city_name}.")
        return get_local_source_high_temp(city_name, target_date_str)
        
    print(f"[APIFY] Triggering oneary/weather-database-scraper for {city_name} on {target_date_str}...")
    try:
        client = ApifyClient(config.APIFY_TOKEN)
        
        # Configure input for the weather scraper
        run_input = {
            "locations": [city_name],
            "units": "metric",
            "timeFrame": "ten_day",
            "proxyConfiguration": {
                "useApifyProxy": True
            }
        }
        
        # Execute the actor (timeout set to 120 seconds to prevent blocking)
        run = client.actor("oneary/weather-database-scraper").call(run_input=run_input, timeout_secs=120)
        
        # Retrieve results from dataset
        dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
        print(f"[APIFY] Successfully retrieved {len(dataset_items)} items from dataset.")
        
        # Search dataset items for matching date
        for item in dataset_items:
            item_date = item.get("date") or item.get("datetime") or item.get("ymd") or ""
            # Match date (handling different ISO formats or substring matches)
            if target_date_str in item_date or item_date in target_date_str:
                max_temp = item.get("maxTemp") or item.get("tempMax") or item.get("highTemp") or item.get("temperatureMax") or item.get("temp")
                if max_temp is not None:
                    print(f"[APIFY] Found matching forecast high temp: {max_temp}°C")
                    return float(max_temp)
                    
        # If no matching date, try to get the first available forecast item
        if dataset_items:
            first_item = dataset_items[0]
            max_temp = first_item.get("maxTemp") or first_item.get("tempMax") or first_item.get("highTemp") or first_item.get("temperatureMax") or first_item.get("temp")
            if max_temp is not None:
                print(f"[APIFY] Date match failed. Using first forecast high: {max_temp}°C")
                return float(max_temp)
                
        print(f"[APIFY] Could not extract temperature from dataset. Falling back to local source.")
    except Exception as e:
        print(f"[APIFY] Error executing scraper or fetching results: {e}. Falling back to local source.")
        
    return get_local_source_high_temp(city_name, target_date_str)
