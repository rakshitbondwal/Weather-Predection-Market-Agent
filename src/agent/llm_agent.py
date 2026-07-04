import httpx
import json
import config
import time


def post_with_backoff(url, headers, json_payload, max_retries=4, initial_delay=3.0):
    """
    Wrapper for httpx.post with exponential backoff on 429 Rate Limits.
    """
    delay = initial_delay
    for i in range(max_retries):
        try:
            response = httpx.post(url, headers=headers, json=json_payload, timeout=30)
            if response.status_code == 429:
                print(f"[LLM] Rate limited (429). Retrying in {delay:.1f}s (Attempt {i+1}/{max_retries})...")
                time.sleep(delay)
                delay *= 2.0
                continue
            response.raise_for_status()
            return response
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            # Check if it was a 429 response
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                print(f"[LLM] Rate limited (429 exception). Retrying in {delay:.1f}s (Attempt {i+1}/{max_retries})...")
                time.sleep(delay)
                delay *= 2.0
                continue
            raise e
            
    # Last ditch attempt
    return httpx.post(url, headers=headers, json=json_payload, timeout=30)


def ask_agent_for_trade_review(city_name, question, forecast_high, model_prob, market_price, kelly_decision):
    """
    Asks the OpenRouter LLM to review a proposed trade and provide a critical analysis.
    """
    if not config.OPENROUTER_API_KEY:
        print("[LLM] OPENROUTER_API_KEY not configured. Skipping trade review.")
        return "No critique (API key missing)."

    prompt = f"""You are a risk analyst reviewing a proposed prediction-market trade.

City: {city_name}
Market question: {question}
Weather forecast (consensus model): {forecast_high}°C high
Our probability model estimate: {model_prob:.1%}
Current market price (implied probability): {market_price:.1%}
Proposed trade: {kelly_decision['side']} for ${kelly_decision['stake']}

In 2-3 sentences, assess whether this trade makes sense given the numbers, and flag
any obvious risk (e.g. thin edge, forecast uncertainty, market may have better information).
Be direct and skeptical, not just agreeable."""

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        response = post_with_backoff(config.OPENROUTER_URL, headers=headers, json_payload=payload)
        response.raise_for_status()
        res_json = response.json()
        critique = res_json['choices'][0]['message']['content'].strip()
        print(f"[LLM] Trade review obtained for {city_name}: {critique}")
        return critique
    except Exception as e:
        print(f"[LLM] Error calling OpenRouter for trade review: {e}")
        return f"Critique unavailable (error: {e})."


def parse_market_question_with_llm(question):
    """
    Uses OpenRouter LLM to parse a prediction market question into structured target details:
    city, target_date (YYYY-MM-DD), temperature threshold (in Celsius), and condition ("above"/"below").
    """
    if not config.OPENROUTER_API_KEY:
        print("[LLM] OPENROUTER_API_KEY not configured. Cannot parse market question.")
        return None

    prompt = f"""Analyze the following prediction market question and extract the structured weather-related target criteria.
    
    Question: "{question}"
    
    Return a JSON object with these keys:
    - "city": The name of the city (string, e.g. "Seoul").
    - "target_date": The specific date of the weather event in YYYY-MM-DD format (string). If the year is not specified, assume 2026.
    - "temp_threshold": The temperature threshold in degrees Celsius (float). If the question is in Fahrenheit, convert it to Celsius.
    - "condition": Either "above" (for "or higher", "above", "at least", "reach X") or "below" (for "or below", "below", "less than").
    
    Respond with ONLY the JSON object, no markdown formatting, no comments."""

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        response = post_with_backoff(config.OPENROUTER_URL, headers=headers, json_payload=payload)
        response.raise_for_status()
        res_json = response.json()
        content = res_json['choices'][0]['message']['content'].strip()
        
        # Clean potential markdown block wrappers
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
            
        parsed = json.loads(content)
        return parsed
    except Exception as e:
        print(f"[LLM] Error parsing question \"{question}\" with LLM: {e}")
        return None