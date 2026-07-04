import httpx
import config
import json


def parse_outcome_prices(market):
    outcomes = json.loads(market["outcomes"])
    prices = json.loads(market["outcomePrices"])
    return dict(zip(outcomes, prices))


def get_markets_for_city(city):
    events = get_weather_events()
    matches = []
    for event in events:
        title = (event.get("title") or event.get("question") or "")
        if city["market_keyword"].lower() in title.lower():
            for market in event.get("markets", []):
                matches.append(market)
    return matches

def get_weather_events(limit=200):
    params = {
        "active": "true",
        "closed": "false",
        "limit": limit,
        "order": "volume24hr",
        "ascending": "false",
    }
    response = httpx.get(f"{config.GAMMA_API_URL}/events", params=params, timeout=20)
    response.raise_for_status()
    events = response.json()

    weather_keywords = ("temperature", "high in", "weather", "°f", "degrees")
    weather_events = []
    for event in events:
        title = (event.get("title") or event.get("question") or "").lower()
        if any(keyword in title for keyword in weather_keywords):
            weather_events.append(event)
    return weather_events