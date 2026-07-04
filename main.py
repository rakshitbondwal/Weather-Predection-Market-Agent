import config
from src.weather.open_meteo_client import get_point_forecast, get_consensus_forecast_high
from src.markets.polymarket_gamma import get_markets_for_city, parse_outcome_prices
from src.strategy.probability_model import parse_temperature_bucket, probability_of_bucket
from src.strategy.kelly import size_position
from src.strategy.hedging import evaluate_hedge
from src.trading.paper_broker import record_trade, init_db, get_all_trades
from src.agent.llm_agent import ask_agent_for_trade_review, parse_market_question_with_llm
from src.agent.telegram_bot import send_telegram_message
from datetime import date


def process_city(city):
    print(f"\n--- {city['name']} ---")

    markets = get_markets_for_city(city)
    if not markets:
        print("No active markets for this city right now.")
        return

    staked_today = 0.0

    for market in markets:
        question = market["question"]
        print(f"\nAnalyzing Market: \"{question}\"")
        
        # 1. Parse question structure using LLM
        parsed_q = parse_market_question_with_llm(question)
        target_date_str = None
        temp_threshold = None
        condition = None
        
        if parsed_q and "error" not in parsed_q:
            target_date_str = parsed_q.get("target_date")
            temp_threshold = parsed_q.get("temp_threshold")
            condition = parsed_q.get("condition")
            print(f"  [LLM Parse] City: {parsed_q.get('city')}, Date: {target_date_str}, Threshold: {temp_threshold}°C, Condition: {condition}")
        else:
            print("  [LLM Parse] Failed or key missing. Falling back to regex / defaults.")
            
        if not target_date_str:
            target_date_str = date.today().isoformat()
            
        # 2. Fetch consensus forecast (Global Open-Meteo + Local source/Apify)
        try:
            forecast_high = get_consensus_forecast_high(city, target_date_str)
        except Exception as e:
            print(f"  [Weather] Consensus error: {e}. Falling back to Open-Meteo legacy.")
            try:
                forecast = get_point_forecast(city)
                forecast_high = forecast["daily"]["temperature_2m_max"][0]
            except Exception as legacy_err:
                print(f"  [Weather] Legacy fallback failed: {legacy_err}. Skipping market.")
                continue
                
        print(f"  [Weather] Consensus Forecast High: {forecast_high}°C")

        # 3. Determine bucket
        bucket = None
        if temp_threshold is not None and condition is not None:
            if condition == "above":
                bucket = {"low": temp_threshold, "high": None}
            else:
                bucket = {"low": None, "high": temp_threshold}
        else:
            bucket = parse_temperature_bucket(question)
            
        if bucket is None:
            print(f"  [Strategy] Skipping: Unable to parse bucket.")
            continue

        prices = parse_outcome_prices(market)
        if "Yes" not in prices:
            continue
        market_price = float(prices["Yes"])

        model_prob = probability_of_bucket(bucket, forecast_high)
        decision = size_position(model_prob, market_price, config.STARTING_BANKROLL, staked_today)

        print(f"  [Kelly Size] Result: {decision['rationale']}")

        if decision["side"] != "NO_TRADE":
            # 4. Generate LLM critique of the trade decision
            critique = ask_agent_for_trade_review(
                city_name=city["name"],
                question=question,
                forecast_high=forecast_high,
                model_prob=model_prob,
                market_price=market_price,
                kelly_decision=decision
            )
            
            # 5. Record trade in DB
            record_trade(
                city=city["name"],
                question=question,
                side=decision["side"],
                price=market_price,
                stake=decision["stake"],
                model_probability=model_prob,
                rationale=decision["rationale"],
                trade_type="primary",
                target_date=target_date_str,
                temp_threshold=temp_threshold,
                condition=condition,
                llm_critique=critique
            )
            
            # 6. Send Telegram Notification
            msg = (
                f"<b>Weather Trade Executed</b>\n"
                f"<b>City:</b> {city['name']}\n"
                f"<b>Market:</b> {question}\n"
                f"<b>Side:</b> {decision['side']}\n"
                f"<b>Stake:</b> ${decision['stake']}\n"
                f"<b>Price:</b> {market_price:.2f}\n"
                f"<b>Model Probability:</b> {model_prob:.1%}\n\n"
                f"<b>LLM Critique:</b>\n{critique}"
            )
            send_telegram_message(msg)
            
            staked_today += decision["stake"]

        # Sleep between market iterations to prevent OpenRouter rate limits
        import time
        time.sleep(1.2)


    # Evaluate potential hedges
    check_hedge_for_city(city["name"], markets)


def check_hedge_for_city(city_name, markets):
    trades = get_all_trades()
    city_trades = [t for t in trades if t['city'] == city_name]

    total_yes = sum(t['stake'] for t in city_trades if t['side'] == 'YES')
    total_no = sum(t['stake'] for t in city_trades if t['side'] == 'NO')

    hedge_decision = evaluate_hedge(city_name, total_yes, total_no, config.STARTING_BANKROLL)
    print(f"Hedge check for {city_name}: {hedge_decision['rationale']}")

    if not hedge_decision["should_hedge"]:
        return hedge_decision

    already_held_questions = {t['question'] for t in city_trades}

    best_market = None
    best_price = 0.0
    for market in markets:
        if market["question"] in already_held_questions:
            continue
        prices = parse_outcome_prices(market)
        if "Yes" not in prices:
            continue
        price = float(prices["Yes"])
        if price > best_price:
            best_price = price
            best_market = market

    if best_market is None or best_price < 0.10:
        print(f"No meaningful hedge available for {city_name} "
              f"(best remaining option priced at {best_price:.3f}) — skipping execution.")
        return hedge_decision

    # Parse hedging question structure using LLM
    parsed_hedge = parse_market_question_with_llm(best_market["question"])
    h_date = parsed_hedge.get("target_date") if parsed_hedge else None
    h_temp = parsed_hedge.get("temp_threshold") if parsed_hedge else None
    h_cond = parsed_hedge.get("condition") if parsed_hedge else None

    # Record hedge in DB
    record_trade(
        city=city_name,
        question=best_market["question"],
        side="YES",
        price=best_price,
        stake=hedge_decision["hedge_stake"],
        model_probability=best_price,
        rationale=f"HEDGE: {hedge_decision['rationale']}",
        trade_type="hedge",
        target_date=h_date,
        temp_threshold=h_temp,
        condition=h_cond,
        llm_critique="Automatic portfolio hedge based on directional exposure."
    )
    print(f"Hedge executed: ${hedge_decision['hedge_stake']} YES on \"{best_market['question']}\" at {best_price:.3f}")

    # Send Telegram Notification for Hedge
    hedge_msg = (
        f"<b>Portfolio Hedge Executed</b>\n"
        f"<b>City:</b> {city_name}\n"
        f"<b>Market:</b> {best_market['question']}\n"
        f"<b>Hedge Stake:</b> ${hedge_decision['hedge_stake']}\n"
        f"<b>Price:</b> {best_price:.3f}\n"
        f"<b>Rationale:</b> {hedge_decision['rationale']}"
    )
    send_telegram_message(hedge_msg)

    return hedge_decision


def run_all_cities():
    init_db()
    for city in config.CITIES:
        try:
            process_city(city)
        except Exception as e:
            print(f"Error processing {city['name']}: {e}")


if __name__ == "__main__":
    run_all_cities()