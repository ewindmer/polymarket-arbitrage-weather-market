"""
Configuration file for Polymarket Weather Trading Bot
"""
from typing import Dict

# Forecast model parameters
FORECAST_STD_DEV_C: float = 1.5  # Standard deviation of forecast error in Celsius

# EV thresholds
EV_THRESHOLD_LONG: float = 0.05  # Minimum EV for long bets
EV_THRESHOLD_SHORT: float = 0.10  # Minimum EV for short bets
EV_THRESHOLD_STRATEGY: float = 0.05  # Minimum EV for blanket strategies

# Kelly Criterion
KELLY_FRACTION: float = 0.25  # Fractional Kelly (quarter Kelly for safety)

# City name mappings
CITY_MAP: Dict[str, str] = {
    "NYC": "New York",
    "LA": "Los Angeles",
    "SF": "San Francisco",
    "DC": "Washington",
    "CHI": "Chicago"
}

# API endpoints
GAMMA_API_URL: str = "https://gamma-api.polymarket.com"
GEOCODING_URL: str = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL: str = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_FORECAST_URL: str = "https://historical-forecast-api.open-meteo.com/v1/forecast"
ARCHIVE_URL: str = "https://archive-api.open-meteo.com/v1/archive"

# Polymarket tag IDs
WEATHER_TAG_ID: str = "84"

# Portfolio simulation
PORTFOLIO_SAMPLES: int = 1000  # Number of samples for Monte Carlo simulation
PORTFOLIO_STD_MULTIPLIER: float = 4.0  # Mean +/- N*STD for simulation range

# Benchmark settings
BENCHMARK_HISTORY_DAYS: int = 30
BENCHMARK_SAFETY_DAYS: int = 5  # Days to shift back for data availability
