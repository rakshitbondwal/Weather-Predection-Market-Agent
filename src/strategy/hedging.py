import config


def evaluate_hedge(city_name, total_yes_stake, total_no_stake, bankroll):
    trigger = bankroll * config.HEDGE_TRIGGER_PCT

    if total_yes_stake < trigger:
        return {
            "should_hedge": False,
            "rationale": f"{city_name} exposure (${total_yes_stake:.2f}) is under the "
                         f"{config.HEDGE_TRIGGER_PCT:.0%} trigger (${trigger:.2f}) — no hedge needed."
        }

    no_ratio = total_no_stake / total_yes_stake if total_yes_stake > 0 else 0

    if no_ratio >= 0.15:
        return {
            "should_hedge": False,
            "rationale": f"{city_name} already has ${total_no_stake:.2f} NO exposure "
                         f"({no_ratio:.0%} of YES side) — sufficient downside cover, no hedge needed."
        }

    hedge_stake = round(min(total_yes_stake * 0.15, bankroll * config.MAX_POSITION_PCT * 0.5), 2)

    return {
        "should_hedge": True,
        "hedge_stake": hedge_stake,
        "rationale": f"{city_name} has ${total_yes_stake:.2f} all-directional YES exposure "
                     f"with zero downside cover — hedging ${hedge_stake} against the market's "
                     "own favorite outcome to cap worst-case loss."
    }