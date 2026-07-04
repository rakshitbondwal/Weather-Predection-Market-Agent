# Weather Prediction Market AI Agent

An automated quantitative trading agent that predictions and trades on Polymarket weather contracts using consensus weather forecasts, LLM-based risk assessments, and fractional-Kelly capital allocation.

---

## Features

1. **Consensus Weather Forecast Model**: Merges global Open-Meteo ensemble projections with regional per-country weather data.
2. **Apify Scraper & Local Fallbacks**: Scrapes weather databases using Apify if credentials are provided, falling back seamlessly to public official APIs for Tokyo (JMA), Hong Kong (HKO), Seoul (wttr.in), and Chinese cities (sojson) for instant, free, and exact forecasts.
3. **LLM Risk Analyst Layer**: Uses OpenRouter to parse Polymarket questions into structured metadata (handles Celsius/Fahrenheit conversions) and generates critical evaluations of proposed trades before execution. Includes retry logic to handle rate-limiting.
4. **Kelly Criteria Allocation & Hedging**: Sizes trades based on mathematical edges and city exposure limits, triggering portfolio hedges to cap downside risks.
5. **Interactive Streamlit Dashboard**: Displays active positions, past resolved logs, city PnL charts, and a detailed list of LLM critiques.
6. **Telegram Notifier**: Pushes execution logs, hedges, and resolution reports to your chat group.

---

## Project Structure

```text
├── config.py              # Main configuration and agent boundaries
├── main.py                # Main orchestration loop (discovers, sizes, and trades)
├── evaluate_results.py    # Resolves past trades against historical records and logs Brier scores
├── dashboard/
│   └── app.py             # Streamlit dashboard interface code
├── skills/
│   └── weather_trader/
│       └── SKILL.md       # Hermes Agent skill definition
└── src/
    ├── agent/             # LLM OpenRouter interfaces and Telegram notifier
    ├── markets/           # Polymarket Gamma API client
    ├── strategy/          # Kelly sizing models and directional hedging
    ├── trading/           # Database broker logging systems
    └── weather/           # Apify client and regional weather API clients
```

---

## Setup and Installation

### 1. Clone the Repository
```bash
git clone https://github.com/rakshitbondwal/Weather-Predection-Market-Agent.git
cd Weather-Predection-Market-Agent
```

### 2. Set Up a Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate   # On Windows
source venv/bin/activate # On Unix/macOS
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
# If requirements.txt is not yet generated, install core packages:
pip install streamlit pandas numpy scipy httpx python-dotenv apify-client
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```env
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=openrouter/free

# Optional integrations:
APIFY_TOKEN=your_apify_api_token
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

---

## How to Run

### 1. Run the Trading Cycle
To discover weather contracts, build consensus forecasts, apply Kelly criteria, review with the LLM layer, and execute paper trades:
```bash
python main.py
```

### 2. Resolve Past Trades & View Statistics
To pull historical temperatures and calculate PnL and Model vs. Market Brier scores for expired target dates:
```bash
python evaluate_results.py
```

### 3. Launch the Dashboard
To start the Streamlit dashboard on your local server:
```bash
streamlit run dashboard/app.py
```
Open `http://localhost:8501` in your browser.
