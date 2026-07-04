import config


def kelly_fraction(p_model, price):
    price = min(max(price, 0.001), 0.999)
    b = (1 - price) / price
    q = 1 - p_model
    f = (b * p_model - q) / b
    return f

def size_position(p_model, market_price, bankroll, already_staked_today=0.0):
    edge = p_model - market_price

    if abs(edge) < config.MIN_EDGE:
        return {
            "side": "NO_TRADE",
            "stake": 0.0,
            "rationale": f"Edge {edge:+.1%} is below the {config.MIN_EDGE:.0%} threshold — skipping."
        }

    max_total_exposure = bankroll * config.MAX_POSITION_PCT
    remaining_room = max_total_exposure - already_staked_today

    if remaining_room <= 0:
        return {
            "side": "NO_TRADE",
            "stake": 0.0,
            "rationale": f"Already staked ${already_staked_today:.2f} on this city today "
                         f"(cap is ${max_total_exposure:.2f}) — skipping."
        }

    side = "YES" if edge > 0 else "NO"
    price = market_price if side == "YES" else (1 - market_price)
    p_win = p_model if side == "YES" else (1 - p_model)

    full_kelly = kelly_fraction(p_win, price)
    fractional_kelly = max(full_kelly, 0) * config.KELLY_FRACTION
    stake = round(bankroll * fractional_kelly, 2)
    stake = min(stake, remaining_room)
    stake = round(stake, 2)

    if stake < 1.0:
        return {
            "side": "NO_TRADE",
            "stake": 0.0,
            "rationale": f"Available room (${remaining_room:.2f}) too small for a meaningful trade — skipping."
        }

    return {
        "side": side,
        "stake": stake,
        "rationale": f"Model {p_model:.1%} vs market {market_price:.1%} (edge {edge:+.1%}). "
                     f"Betting {side}, full Kelly {full_kelly:.1%}, "
                     f"stake ${stake} (room left today: ${remaining_room:.2f})"
    }