import requests
import datetime
import statistics
import math
import logging
from typing import Dict, Any, List, Tuple

import config

logger = logging.getLogger(__name__)

# Benchmark cities
CITIES: Dict[str, Dict[str, float]] = {
    "New York": {"lat": 40.7128, "lon": -74.0060},
    "London": {"lat": 51.5074, "lon": -0.1278},
    "Toronto": {"lat": 43.65107, "lon": -79.347015},
    "Seattle": {"lat": 47.6062, "lon": -122.3321},
    "Seoul": {"lat": 37.5665, "lon": 126.9780}
}

def get_historical_data(
    lat: float, 
    lon: float, 
    start_date: str, 
    end_date: str
) -> Dict[str, Any]:
    """
    Fetches ACTUAL observed max temp from archive API.
    
    Args:
        lat: Latitude
        lon: Longitude
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        JSON response from archive API
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max",
        "timezone": "auto"
    }
    try:
        response = requests.get(config.ARCHIVE_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching historical data: {e}")
        return {}

def get_past_forecast(
    lat: float, 
    lon: float, 
    start_date: str, 
    end_date: str
) -> Dict[str, Any]:
    """
    Fetches the FORECAST that was made, ideally 1 day in advance.
    The historical-forecast-api allows seeing what the forecast WAS.
    
    Args:
        lat: Latitude
        lon: Longitude
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        JSON response from historical forecast API
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max",
        "timezone": "auto",
    }
    try:
        response = requests.get(
            config.HISTORICAL_FORECAST_URL, 
            params=params, 
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching past forecast: {e}")
        return {}

def run_benchmark() -> None:
    """
    Run benchmark analysis comparing forecast accuracy to model assumptions.
    """
    logger.info("--- Running Model Benchmark (Last 30 Days) ---")
    logger.info(f"Assumed Model StdDev: {config.FORECAST_STD_DEV_C} deg C")
    
    # Shift back by safety days to ensure Reanalysis (Actuals) are available
    # OpenMeteo ERA5T has ~5 day lag for final, 2 day for preliminary.
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(
        days=config.BENCHMARK_HISTORY_DAYS + config.BENCHMARK_SAFETY_DAYS
    )).strftime("%Y-%m-%d")
    end_date = (today - datetime.timedelta(
        days=config.BENCHMARK_SAFETY_DAYS
    )).strftime("%Y-%m-%d")
    
    all_errors: List[float] = []
    
    for city, coords in CITIES.items():
        logger.info(f"\nBenchmarking {city}...")
        
        # 1. Get Actuals
        actuals_data = get_historical_data(coords['lat'], coords['lon'], start_date, end_date)
        if 'daily' not in actuals_data:
            logger.warning("  Failed to get actuals (Archive data likely not available yet).")
            continue
            
        actual_temps = actuals_data['daily']['temperature_2m_max']
        dates = actuals_data['daily']['time']
        
        # 2. Get Forecasts (Approximation)
        # We will use the 'historical forecast' endpoint which stitches together past forecasts.
        # It's a good proxy for "what did the model think".
        forecast_data = get_past_forecast(coords['lat'], coords['lon'], start_date, end_date)
        if 'daily' not in forecast_data:
            logger.warning("  Failed to get forecasts.")
            continue
            
        forecast_temps = forecast_data['daily']['temperature_2m_max']
        
        # 3. Compare
        # OpenMeteo historical forecast is usually 00:00 UTC initialization.
        # So for Day X, it's roughly the Day X-1 prediction. 
        
        city_errors: List[float] = []
        for i, date in enumerate(dates):
            if i >= len(forecast_temps):
                break
            act = actual_temps[i]
            fcst = forecast_temps[i]
            
            if act is None or fcst is None:
                continue
                
            error = act - fcst
            city_errors.append(error)
            all_errors.append(error)

        # City Stats
        if city_errors:
            avg_err = statistics.mean(city_errors)
            std_err = statistics.stdev(city_errors)
            logger.info(f"  -> Mean Bias: {avg_err:.2f}C")
            logger.info(f"  -> Observed StdDev: {std_err:.2f}C")
            
            # Validation check
            if std_err > config.FORECAST_STD_DEV_C:
                logger.warning(
                    f"  [WARN] Observed Volatility ({std_err:.2f}) > Model ({config.FORECAST_STD_DEV_C}). "
                    "Model is UNDER-estimating risk."
                )
            else:
                logger.info(
                    f"  [OK] Model is conservative (Obs {std_err:.2f} < {config.FORECAST_STD_DEV_C})."
                )

    # Overall Stats
    logger.info("\n--- Overall Benchmark Results ---")
    if all_errors:
        total_bias = statistics.mean(all_errors)
        total_std = statistics.stdev(all_errors)
        
        logger.info(f"Total Days: {len(all_errors)}")
        logger.info(
            f"Overall Forecast Bias: {total_bias:.2f} deg C "
            "(Positive means Actual > Forecast)"
        )
        logger.info(f"Overall Standard Deviation of Error: {total_std:.2f} deg C")
        logger.info(f"Current Model Assumption: {config.FORECAST_STD_DEV_C} deg C")
        
        recommended_std = total_std * 1.1  # 10% safety buffer
        logger.info(f"\nRECOMMENDATION: Set FORECAST_STD_DEV_C to {recommended_std:.1f}")
        
if __name__ == "__main__":
    run_benchmark()
