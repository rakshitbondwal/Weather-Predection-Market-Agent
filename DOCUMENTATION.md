# Technical Documentation: Weather Prediction Market AI Agent

This document explains the architecture, mathematical models, risk management, and operational workflows of the Weather Prediction Market AI Agent.

---

## System Architecture

The agent is built as a modular system in Python. It utilizes public meteorology feeds, prediction market APIs, and LLM reasoning models to execute automated paper trades.

```text
+-----------------------+      +-------------------------+
| Polymarket Gamma API  | ---> |   Market Discovery      |
+-----------------------+      +-------------------------+
                                            |
                                            v
+-----------------------+      +-------------------------+
| OpenRouter LLM Parser | ---> | Question Structuring   |
+-----------------------+      +-------------------------+
                                            |
                                            v
+-----------------------+      +-------------------------+
| Global (Open-Meteo)   | ---> | Consensus Weather Model |
| Local APIs / Apify    |      +-------------------------+
+-----------------------+                   |
                                            v
+-----------------------+      +-------------------------+
| normal.cdf() Edge     | ---> |   Kelly Sizing Engine   |
+-----------------------+      +-------------------------+
                                            |
                                            v
+-----------------------+      +-------------------------+
| OpenRouter Critic     | ---> | LLM Trade Reviewer      |
+-----------------------+      +-------------------------+
                                            |
                                            v
                               +-------------------------+
                               | Execution & Hedges      |
                               +-------------------------+
                                            |
                                            v
                               +-------------------------+
                               | SQLite / Streamlit / TG |
                               +-------------------------+
```

---

## Core Components

### 1. Market Discovery (`src/markets/polymarket_gamma.py`)
Queries the Polymarket Gamma API to locate active temperature contracts for the configured target cities. It filters for temperature-related keywords, formats brackets, and extracts current YES/NO contract prices (representing the market's implied probability).

### 2. LLM Parser (`src/agent/llm_agent.py`)
Uses the OpenRouter API to structure Polymarket questions into metadata:
* Target City (e.g., "Hong Kong")
* Target Date (YYYY-MM-DD format)
* Temperature threshold (converts Fahrenheit to Celsius if the market is denominated in Fahrenheit)
* Operator condition ("above" or "below")

*Robustness*: Implements exponential backoff retry logic (3s, 6s, 12s, 24s) to handle `429 Too Many Requests` rate limits on free-tier endpoints. Falls back to regex-based extraction if the API is completely unresponsive.

### 3. Consensus Weather Model (`src/weather/`)
Constructs a unified projection by blending global forecasts and local sources:
* **Global**: Open-Meteo ensemble forecast (combines multiple runs to estimate mean and standard deviation).
* **Local**: Country-specific APIs:
  * Hong Kong Observatory (HKO) Open Data API
  * Japan Meteorological Agency (JMA) forecast API
  * wttr.in weather API (Seoul)
  * China Meteorological Administration via sojson API (Beijing, Shanghai, Guangzhou)
* **Apify Scraper**: If an `APIFY_TOKEN` is set, the client invokes the `oneary/weather-database-scraper` Actor to scrape Weather.com/AccuWeather.
* **Consensus Calculation**: Aggregates the global ensemble mean and the local forecast, outputting a weighted forecast high ($T_{consensus}$).

### 4. Probability & Pricing Engine (`src/strategy/`)
Calculates the probability ($P_{model}$) of the weather outcome using a normal cumulative distribution function (CDF):
* **Probability Model**:
  $$P_{model} = 1 - \Phi\left(\frac{T_{threshold} - T_{consensus}}{\sigma}\right)$$ (for "above" conditions)
  where $\Phi$ is the standard normal CDF, and $\sigma$ is the forecast standard deviation (derived from the Open-Meteo ensemble spread or historic calibration).
* **Kelly Sizing**:
  Compares $P_{model}$ against the market implied probability ($P_{market}$ or contract price) to identify the edge:
  $$\text{Edge} = P_{model} - P_{market}$$
  If the edge exceeds the minimum threshold (6%), it sizes the trade using the fractional Kelly Criterion:
  $$f^* = \text{fraction} \times \left(\frac{P_{model} \times (1 - P_{market}) - (1 - P_{model}) \times P_{market}}{1 - P_{market}}\right)$$
  The maximum allocation is capped at 10% of the bankroll per city to manage systemic risk.

### 5. Risk Critique & Hedging (`src/strategy/hedging.py` & `src/agent/llm_agent.py`)
* **LLM Risk Critique**: Before execution, the trade details are submitted to the LLM. The LLM reviews the calculations, checking for margin thinness, high weather volatility, or calendar mismatches.
* **Directional Hedging**: Runs at the end of each city check. If the net YES exposure in a city exceeds 8% of the total bankroll, the hedging engine automatically identifies the market's favorite outcome and buys YES contracts on it to cap the portfolio's worst-case downside.

### 6. Execution, Storage, and UI (`src/trading/paper_broker.py` & `dashboard/app.py`)
* **Broker**: Logs trade executions, rationales, sides, and LLM critiques in a local SQLite database (`data/paper_trades.db`). Automatically handles database migrations and includes fallback copy mechanisms if the filesystem is read-only.
* **Dashboard**: A Streamlit application displaying key performance indicators, active contracts, resolved predictions ledger, PnL charts, and the LLM analyst critiques.
* **Telegram**: Sends alerts on trade entries, hedging transactions, and performance reports.

---

## Statistical Evaluation (`evaluate_results.py`)

To resolve contracts and compute performance metrics without human intervention:
1. Queries the database for unresolved positions where the target date is in the past.
2. Queries the **Open-Meteo Historical Weather Archive API** to retrieve the actual observed maximum temperature for the target city on that date.
3. Determines the contract outcome (YES/NO) and calculates the PnL ($1.00 payout per winning share).
4. Computes the **Brier Score** for both the model and the market to evaluate calibration accuracy:
   $$BS = \frac{1}{N} \sum_{i=1}^N (P_i - O_i)^2$$
   where $P_i$ is the predicted probability and $O_i$ is the actual outcome (1 or 0). A lower score represents a more accurate model.
