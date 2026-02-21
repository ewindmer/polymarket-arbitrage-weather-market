# System Architecture

## Overview

The Polymarket Weather Arbitrage Bot is designed as a data pipeline system that ingests market data and weather forecasts to produce actionable trading signals.

## Data Flow Pipeline

1.  **Ingestion Layer**:
    - **Market Data**: Leverages `utils/polymarket_api.py` to fetch "Weather" tagged events from the **Polymarket Gamma API**. It filters for events related to daily high/low temperatures.
    - **Weather Data**: Leverages `utils/weather_api.py` to fetch hyper-local weather forecasts from **Open-Meteo**. It converts city names to Coordinates (Lat/Lon) and then queries forecast models.

2.  **Normalization Layer**:
    - Events are parsed to extract metadata: `City`, `Date`, and `Market Type`.
    - Market prices are standardized.
    - Weather forecasts are retrieved for the exact target date.

3.  **Analysis Layer (`analysis/`)**:
    - **Probabilistic Modeling**: `arbitrage.py` uses a **Normal Distribution** (Gaussian) model centered around the forecasted temperature (Mean) with a configurable Standard Deviation (Vol) to estimate the true probability of each outcome bucket.
    - **EV Calculation**:
        ```
        EV = (True Probability * Payout) - Cost
        ```
        Where `Payout` is assumed to be $1.00 (normalized) and `Cost` is the current market Ask price.

4.  **Optimization Layer**:
    - **Portfolio Analyzer**: `portfolio.py` simulates thousands of temperature scenarios to check the correlation/combined risk of multiple bets.
    - **Kelly Criterion**: Uses a fractional Kelly formula to recommend optimal bet sizing based on the "Edge" and "Odds".

## Key Components

### `main.py`
The orchestrator. It runs the loop, handles the `--demo` flag, and formats the output for the console. It enforces safety checks, such as ensuring the event date is in the future.

### `utils/polymarket_api.py`
- **Endpoint**: `https://gamma-api.polymarket.com/events`
- **Tag**: `84` (Weather)
- **Logic**: Handles pagination and detailed market fetching (fetching Order Book data like `bestAsk` / `bestBid` if implemented, currently uses summarized prices).

### `utils/weather_api.py`
- **Provider**: Open-Meteo (No API Key required for non-commercial use).
- **Functions**:
    - `get_coordinates(city)`: Geocoding.
    - `get_daily_forecast(lat, lon, date)`: Time-machine/Forecast API.

### `analysis/arbitrage.py`
- parses complex market questions (e.g., "Will it be < 50F?").
- Maps these string questions to numerical ranges (`-inf` to `50`).
- Integrates the PDF (Probability Density Function) over these ranges to get `True Prob`.

### `analysis/portfolio.py`
- **Monte Carlo Simulation**: Used to validate "Short Portfolios" where multiple "No" bets are placed.
- Calculates `Combined Probability of Profit` and `Expected Total Return`.

## Future Improvements

- **Execution**: Integrate `py-clob-client` for automated trade execution.
- **Better Weather Models**: Integrate ensemble models (ECMWF, GFS) for better mean/std estimation.
- **Liquidity filtering**: Filter out markets with wide spreads to avoid slippage.
