import requests
from datetime import datetime

# constants
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

def get_coordinates(city_name):
    """
    Fetches coordinates for a given city name.
    """
    params = {
        "name": city_name,
        "count": 1,
        "language": "en",
        "format": "json"
    }
    
    try:
        response = requests.get(GEOCODING_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            return result["latitude"], result["longitude"]
        else:
            return None, None
    except Exception as e:
        print(f"Error fetching coordinates for {city_name}: {e}")
        return None, None

def get_daily_forecast(lat, lon, date_str):
    """
    Fetches daily max/min temperature for a specific date.
    date_str format: YYYY-MM-DD
    Returns: (max_temp, min_temp) in Celsius
    """
    # OpenMeteo allows fetching forecast for specific days.
    # We can ask for 7 days and filter, or just look at the specific date if within range.
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["temperature_2m_max", "temperature_2m_min"],
        "timezone": "auto",
        "start_date": date_str,
        "end_date": date_str
    }
    
    try:
        response = requests.get(FORECAST_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if "daily" in data:
            max_temp = data["daily"]["temperature_2m_max"][0]
            min_temp = data["daily"]["temperature_2m_min"][0]
            return max_temp, min_temp
        return None, None
        
    except Exception as e:
        print(f"Error fetching forecast: {e}")
        return None, None
