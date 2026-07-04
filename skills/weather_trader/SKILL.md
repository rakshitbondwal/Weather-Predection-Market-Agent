---
name: weather-trader
description: Automated Polymarket weather prediction market trading, risk analysis, portfolio hedging, and statistical performance tracking.
version: 1.0.0
platforms: [windows, linux, macos]
requires_toolsets: [terminal]
metadata:
  hermes:
    category: quantitative-finance
---

## Overview
This skill implements an autonomous predictive trading agent that reads global weather forecasts and local country-specific weather APIs, builds consensus forecasts, analyzes Polymarket weather contract pricing, executes fractional-Kelly size paper trades, executes directional portfolio hedging, and resolves past trades to calculate net PnL and Brier scores.

## Prerequisites
Before running, ensure that your virtual environment is active and variables in `.env` are configured:
* `OPENROUTER_API_KEY`: OpenRouter credentials for the LLM reasoning layer.
* `OPENROUTER_MODEL`: E.g., `openrouter/free`.
* `APIFY_TOKEN`: (Optional) Apify credentials for weather database scraping.
* `TELEGRAM_BOT_TOKEN`: (Optional) Telegram bot token for instant execution pushes.
* `TELEGRAM_CHAT_ID`: (Optional) Telegram target chat ID.

## Commands

### 1. Run Trading Cycle
Trigger the market discovery, consensus weather modeling, Kelly trade sizing, LLM critique, hedging check, and trade executions:
```bash
venv\Scripts\python.exe main.py
```

### 2. Run Results Evaluator
Resolve previous days' trades using historical weather records from Open-Meteo, write results, and update net metrics (Brier score & PnL):
```bash
venv\Scripts\python.exe evaluate_results.py
```

### 3. Launch Dashboard
Run the Streamlit app to visually inspect active positions, resolved metrics, and LLM critical risk review sheets:
```bash
venv\Scripts\streamlit.exe run dashboard/app.py
```

## Agent Action Checklist
When tasked to execute trading or report performance:
1. **Configure Environment**: Confirm `.env` values are present and loaded.
2. **Execute Cycle**: Run `venv\Scripts\python.exe main.py`. Parse output for executed YES/NO contracts or hedges.
3. **Resolve Trades**: Run `venv\Scripts\python.exe evaluate_results.py` to process dates that are now in the past.
4. **Inspect Performance**: Monitor the metrics: Net Portfolio PnL (USD) and Model vs Market Brier Score difference.
5. **Review Risk Sheet**: Inspect the "LLM Critique" column in the dashboard to review risk warnings.
