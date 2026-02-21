import requests
import datetime
import statistics
import math

# Constants
# We want to check the last 30 days
HISTORY_DAYS = 30
CITIES = {
    "New York": {"lat": 40.7128, "lon": -74.0060},
    "London": {"lat": 51.5074, "lon": -0.1278},
    "Toronto": {"lat": 43.65107, "lon": -79.347015},
    "Seattle": {"lat": 47.6062, "lon": -122.3321},
    "Seoul": {"lat": 37.5665, "lon": 126.9780}
}
DEFAULT_STD_DEV = 2.0

def get_historical_data(lat, lon, start_date, end_date):
    """
    Fetches ACTUAL observed max temp.
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max",
        "timezone": "auto"
    }
    response = requests.get(url, params=params)
    return response.json()

def get_past_forecast(lat, lon, start_date, end_date):
    """
    Fetches the FORECAST that was made, ideally 1 day in advance.
    The historical-forecast-api allows seeing what the forecast WAS.
    We assume the forecast made 'today' for 'tomorrow' (1 day out).
    """
    # Note: Open-Meteo Historical Forecast API might require paid key for commercial, 
    # but free tier usually allows some access or we use the 'previous_runs' if available?
    # Actually, simpler proxy: Use the 'reanalysis' from archive as Truth,
    # and use the 'forecast' API with 'past_days' ... wait, normal forecast API doesn't give historical forecasts easily.
    
    # Correct endpoint: https://historical-forecast-api.open-meteo.com/v1/forecast
    url = "https://historical-forecast-api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max",
        "timezone": "auto",
        # Removed forecast_days based on probe test
    }
    # To get "1 day ahead forecast", it's tricky with the basic API.
    # Let's try to just fetch the data and see.
    # Assuming the API returns the "mixed" series which is generally close to the 0-day or 1-day forecast.
    
    response = requests.get(url, params=params)
    return response.json()

def run_benchmark():
    print("--- Running Model Benchmark (Last 30 Days) ---")
    print(f"Assumed Model StdDev: {DEFAULT_STD_DEV} deg C")
    
    # Shift back by 5 days to ensure Reanalysis (Actuals) are available
    # OpenMeteo ERA5T has ~5 day lag for final, 2 day for preliminary.
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=HISTORY_DAYS + 5)).strftime("%Y-%m-%d")
    end_date = (today - datetime.timedelta(days=5)).strftime("%Y-%m-%d")
    
    all_errors = []
    
    for city, coords in CITIES.items():
        print(f"\nBenchmarking {city}...")
        
        # 1. Get Actuals
        actuals_data = get_historical_data(coords['lat'], coords['lon'], start_date, end_date)
        if 'daily' not in actuals_data:
            print("  Failed to get actuals (Archive data likely not available yet).")
            continue
            
        actual_temps = actuals_data['daily']['temperature_2m_max']
        dates = actuals_data['daily']['time']
        
        # 2. Get Forecasts (Approximation)
        # We will use the 'historical forecast' endpoint which stitches together past forecasts.
        # It's a good proxy for "what did the model think".
        forecast_data = get_past_forecast(coords['lat'], coords['lon'], start_date, end_date)
        if 'daily' not in forecast_data:
            print("  Failed to get forecasts.")
            continue
            
        forecast_temps = forecast_data['daily']['temperature_2m_max']
        
        # 3. Compare
        # OpenMeteo historical forecast is usually 00:00 UTC initialization.
        # So for Day X, it's roughly the Day X-1 prediction. 
        
        city_errors = []
        for i, date in enumerate(dates):
            act = actual_temps[i]
            fcst = forecast_temps[i]
            
            if act is None or fcst is None:
                continue
                
            error = act - fcst
            city_errors.append(error)
            all_errors.append(error)
            
            # print(f"  {date}: Fcst {fcst} | Act {act} | Diff {error:.2f}")

        # City Stats
        if city_errors:
            avg_err = statistics.mean(city_errors)
            std_err = statistics.stdev(city_errors)
            print(f"  -> Mean Bias: {avg_err:.2f}C")
            print(f"  -> Observed StdDev: {std_err:.2f}C")
            
            # Validation check
            if std_err > DEFAULT_STD_DEV:
                print(f"  [WARN] Observed Volatility ({std_err:.2f}) > Model ({DEFAULT_STD_DEV}). Model is UNDER-estimating risk.")
            else:
                print(f"  [OK] Model is conservative (Obs {std_err:.2f} < {DEFAULT_STD_DEV}).")

    # Overall Stats
    print("\n--- Overall Benchmark Results ---")
    if all_errors:
        total_bias = statistics.mean(all_errors)
        total_std = statistics.stdev(all_errors)
        
        print(f"Total Days: {len(all_errors)}")
        print(f"Overall Forecast Bias: {total_bias:.2f} deg C (Positive means Actual > Forecast)")
        print(f"Overall Standard Deviation of Error: {total_std:.2f} deg C")
        print(f"Current Model Assumption: {DEFAULT_STD_DEV} deg C")
        
        recommended_std = total_std * 1.1 # 10% safety buffer
        print(f"\nRECOMMENDATION: Set FORECAST_STD_DEV_C to {recommended_std:.1f}")
        
if __name__ == "__main__":
    run_benchmark()
