import config
import httpx
import re
from datetime import datetime, date
from src.trading.paper_broker import get_all_trades, resolve_trade_in_db, init_db
from src.agent.telegram_bot import send_telegram_message


# Create coordinate lookup
CITY_MAP = {c["name"]: c for c in config.CITIES}


def fetch_historical_high_temp(city_name: str, target_date_str: str) -> float:
    """
    Fetches the actual historical high temperature for a city and date from Open-Meteo Archive API.
    """
    city = CITY_MAP.get(city_name)
    if not city:
        print(f"[ERROR] City {city_name} not found in config.")
        return None
        
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "start_date": target_date_str,
        "end_date": target_date_str,
        "daily": "temperature_2m_max",
        "timezone": "auto"
    }
    
    try:
        response = httpx.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        temps = data.get("daily", {}).get("temperature_2m_max", [])
        if temps and temps[0] is not None:
            return float(temps[0])
    except Exception as e:
        print(f"[OpenMeteo Archive] Error fetching temp for {city_name} on {target_date_str}: {e}")
        
    # Emergency fallback: try legacy forecast API (which contains past few days)
    try:
        url_forecast = "https://api.open-meteo.com/v1/forecast"
        params_f = {
            "latitude": city["lat"],
            "longitude": city["lon"],
            "daily": "temperature_2m_max",
            "timezone": "auto",
            "past_days": 7,
            "forecast_days": 1
        }
        res = httpx.get(url_forecast, params=params_f, timeout=20)
        if res.status_code == 200:
            data = res.json()
            dates = data.get("daily", {}).get("time", [])
            temps = data.get("daily", {}).get("temperature_2m_max", [])
            for i, d in enumerate(dates):
                if d == target_date_str and temps[i] is not None:
                    return float(temps[i])
    except Exception as fallback_err:
        print(f"[OpenMeteo Forecast] Fallback historical fetch failed: {fallback_err}")
        
    return None


def evaluate_all_trades():
    init_db()
    trades = get_all_trades()
    
    unresolved_trades = [t for t in trades if not t.get("resolved")]
    
    print(f"\n--- Resolving Trades ---")
    print(f"Found {len(unresolved_trades)} unresolved trades total.")
    
    today_str = date.today().isoformat()
    resolved_count = 0
    
    for t in unresolved_trades:
        trade_id = t["id"]
        city = t["city"]
        question = t["question"]
        side = t["side"]
        price = t["price"]
        stake = t["stake"]
        model_prob = t["model_probability"]
        target_date_str = t.get("target_date")
        threshold = t.get("temp_threshold")
        condition = t.get("condition")
        trade_type = t.get("trade_type", "primary")
        
        # Skip if target_date is not set or is in the future
        if not target_date_str:
            print(f"Skipping Trade #{trade_id}: No target date defined.")
            continue
            
        if target_date_str > today_str:
            print(f"Skipping Trade #{trade_id} (City: {city}, Date: {target_date_str}): Date is in the future.")
            continue
            
        print(f"\nResolving Trade #{trade_id}: {city} ({target_date_str}) - \"{question}\"")
        
        actual_temp = fetch_historical_high_temp(city, target_date_str)
        if actual_temp is None:
            print(f"  Failed to fetch historical temperature. Skipping resolution.")
            continue
            
        # Determine actual YES outcome
        if condition == "above":
            is_yes = actual_temp >= threshold
        elif condition == "below":
            is_yes = actual_temp <= threshold
        else:
            # Fallback regex check if condition was not saved
            q_lower = question.lower()
            if "or below" in q_lower or "below" in q_lower:
                is_yes = actual_temp <= threshold if threshold is not None else False
            else:
                is_yes = actual_temp >= threshold if threshold is not None else False
                
        actual_outcome = 1 if is_yes else 0
        outcome_str = "YES" if is_yes else "NO"
        print(f"  Actual Temp: {actual_temp}°C vs Threshold: {threshold}°C -> Market Outcome: {outcome_str}")
        
        # Calculate PnL
        # YES trade:
        # Payout = (stake / price) if YES occurs, else 0
        # NO trade:
        # Payout = (stake / (1 - price)) if NO occurs, else 0
        pnl = 0.0
        if side == "YES":
            if actual_outcome == 1:
                payout = stake / price
                pnl = payout - stake
            else:
                pnl = -stake
        elif side == "NO":
            if actual_outcome == 0:
                payout = stake / (1 - price)
                pnl = payout - stake
            else:
                pnl = -stake
                
        pnl = round(pnl, 2)
        print(f"  Position: {side} @ {price:.2f} (Stake: ${stake:.2f}) -> PnL: ${pnl:+.2f}")
        
        # Update in database
        resolve_trade_in_db(trade_id, actual_temp, pnl)
        resolved_count += 1
        
    print(f"\nSuccessfully resolved {resolved_count} trades.")
    
    # Calculate global statistics
    all_trades_updated = get_all_trades()
    resolved_all = [t for t in all_trades_updated if t.get("resolved")]
    
    if not resolved_all:
        print("\nNo resolved trades to compile statistics for.")
        return
        
    print(f"\n======================================")
    print(f"     WEATHER AGENT PERFORMANCE REPORT")
    print(f"======================================")
    
    total_trades = len(resolved_all)
    total_pnl = sum(t["pnl"] for t in resolved_all)
    total_staked = sum(t["stake"] for t in resolved_all)
    win_trades = [t for t in resolved_all if t["pnl"] > 0]
    win_rate = len(win_trades) / total_trades if total_trades > 0 else 0.0
    
    # Brier Scores
    model_errors = []
    market_errors = []
    
    for t in resolved_all:
        # Determine actual YES outcome
        # If yes is the outcome, actual_yes = 1, else 0
        actual_yes = 0
        cond = t.get("condition")
        actual_t = t.get("actual_temp")
        thresh = t.get("temp_threshold")
        
        if cond == "above" and actual_t is not None and thresh is not None:
            actual_yes = 1 if actual_t >= thresh else 0
        elif cond == "below" and actual_t is not None and thresh is not None:
            actual_yes = 1 if actual_t <= thresh else 0
        else:
            # Check db side and pnl to reconstruct outcome
            # If bet on YES and won -> outcome is YES (1)
            # If bet on NO and won -> outcome is NO (0)
            # If bet on YES and lost -> outcome is NO (0)
            # If bet on NO and lost -> outcome is YES (1)
            if t["side"] == "YES":
                actual_yes = 1 if t["pnl"] > 0 else 0
            else:
                actual_yes = 0 if t["pnl"] > 0 else 1
                
        # Primary trades only for model vs market evaluation
        if t.get("trade_type", "primary") == "primary":
            # predicted probability of YES
            model_pred = t["model_probability"]
            # market probability of YES
            market_pred = t["price"]
            
            model_errors.append((model_pred - actual_yes) ** 2)
            market_errors.append((market_pred - actual_yes) ** 2)
            
    brier_model = sum(model_errors) / len(model_errors) if model_errors else 0.0
    brier_market = sum(market_errors) / len(market_errors) if market_errors else 0.0
    
    print(f"Total Resolved Trades: {total_trades}")
    print(f"Total Staked Capital:  ${total_staked:.2f}")
    print(f"Total Portfolio PnL:   ${total_pnl:+.2f}")
    print(f"Portfolio Win Rate:    {win_rate:.1%}")
    print(f"Model Brier Score:     {brier_model:.4f}")
    print(f"Market Brier Score:    {brier_market:.4f}")
    
    better_flag = "BETTER than" if brier_model < brier_market else "WORSE than"
    if brier_model == brier_market:
        better_flag = "EQUAL to"
    print(f"Model forecasting is {better_flag} the market.")
    print(f"======================================\n")
    
    # Send Telegram Update
    tel_msg = (
        f"<b>Weather Agent Performance Report</b>\n\n"
        f"<b>Total Resolved Trades:</b> {total_trades}\n"
        f"<b>Net Portfolio PnL:</b> {total_pnl:+.2f} USD\n"
        f"<b>Win Rate:</b> {win_rate:.1%}\n"
        f"<b>Model Brier Score:</b> {brier_model:.4f}\n"
        f"<b>Market Brier Score:</b> {brier_market:.4f}\n\n"
        f"<i>Model accuracy is {better_flag} the Polymarket consensus!</i>"
    )
    send_telegram_message(tel_msg)


if __name__ == "__main__":
    evaluate_all_trades()
