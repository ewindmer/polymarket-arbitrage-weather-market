# Polymarket Arbitrage Bot Weather Market

A specialized bot designed to identify profitable betting opportunities in Polymarket's weather markets. It leverages real-time weather forecasts and compares them with market probabilities to calculate Expected Value (EV) and recommend Long/Short positions or blanket strategies.

## About

This project is an algorithmic trading bot that specializes in identifying arbitrage opportunities in Polymarket's prediction markets, specifically focusing on weather-related events. The bot combines financial modeling, statistical analysis, and real-time data integration to find mispriced markets where the market's implied probability differs from the true probability based on weather forecasts.

The core innovation lies in using accurate weather forecasting data to calculate the true probability of temperature outcomes, then comparing these probabilities against market prices to find positive expected value bets. The system supports both individual position recommendations and portfolio-level strategies using the Kelly Criterion for optimal bet sizing.

Built with Python, the bot integrates with Polymarket's Gamma API for market data and Open-Meteo API for weather forecasts, providing a complete automated solution for weather market arbitrage.

## Features

- **Real-time Market Scanning**: Fetches active weather events from Polymarket (Gamma API).
- **Accurate Forecasting**: Integrates with Open-Meteo API to get precise daily high/low temperature forecasts for specific locations and dates.
- **EV Calculation**: Mathematical modeling to determine the "True Probability" of outcomes versus Market Implied Probability.
- **Strategy Recommendations**:
  - **Individual Bets**: Specific Yes/No bets with positive EV.
  - **Blanket Strategies**: Buying multiple buckets to cover a sure-win range at a discount (Arbitrage).
  - **Portfolio Analysis**: Portfolio sizing and risk analysis (Kelly Criterion) for combined short positions.
- **Safety Checks**: Automatically filters out past or same-day events to avoid execution risk on resolving markets.
- **Demo Mode**: Includes a mock data mode for testing logic without API calls.

## Directory Structure

```
polymarket/
├── main.py                 # Main entry point
├── analysis/               # Core logic for EV and Portfolio math
│   ├── arbitrage.py        # EV calculation
│   └── portfolio.py        # Portfolio simulation and Kelly bet sizing
├── utils/                  # API integrations
│   ├── polymarket_api.py   # Polymarket (Gamma) API wrapper
│   └── weather_api.py      # Open-Meteo Weather API wrapper
├── requirements.txt        # Project dependencies
└── docs/                   # Detailed documentation
```

## Prerequisites

- Python 3.8 or higher.
- Internet connection for fetching API data.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/polymarket-weather-bot.git
    cd polymarket-weather-bot
    ```

2.  **Install dependencies:**
    It is recommended to use a virtual environment.
    ```bash
    # Create virtual environment (optional)
    python -m venv venv
    
    # Activate virtual environment
    # Windows:
    .\venv\Scripts\activate
    # Linux/Mac:
    source venv/bin/activate

    # Install requirements
    pip install -r requirements.txt
    ```

## Usage

### Run the Bot (Live Mode)
To fetch live data from Polymarket and Open-Meteo:
```bash
python main.py
```

### Run in Demo Mode
To see how the bot analyzes data using hardcoded mock examples:
```bash
python main.py --demo
```

## How It Works

1.  **Fetch**: The bot queries Polymarket for "Weather" tagged events (e.g., "Highest temperature in New York on Jan 15").
2.  **Parse**: It extracts the city and date from the event title.
3.  **Forecast**: It queries Open-Meteo for the specific date and location to get the Max/Min temperature forecast.
4.  **Analyze**:
    - Calculates the probability of each temperature bucket (e.g., "< 40F", "40-50F") using a Normal Distribution centered on the forecast.
    - Compares "True Prob" vs. "Market Price".
5.  **Recommend**: Outputs bets where `EV > 0`.

## Topics

- **Arbitrage Trading**: Identifying and exploiting price discrepancies in prediction markets
- **Weather Forecasting**: Integration with meteorological APIs for accurate temperature predictions
- **Expected Value (EV) Calculation**: Mathematical modeling to determine profitable betting opportunities
- **Portfolio Optimization**: Kelly Criterion and risk management for bet sizing
- **Prediction Markets**: Polymarket integration and market analysis
- **Statistical Modeling**: Normal distribution and probability calculations
- **API Integration**: Real-time data fetching from multiple sources
- **Python Automation**: Automated trading bot development
- **Financial Analysis**: Market probability vs. true probability comparison
- **Risk Management**: Portfolio-level analysis and position sizing

## Disclaimer

This software is for educational and research purposes only. Betting involves financial risk. The authors are not responsible for any financial losses incurred from using this software.
