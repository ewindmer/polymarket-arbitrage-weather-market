import requests
from datetime import datetime
import logging
from typing import Tuple, Optional

import config

logger = logging.getLogger(__name__)

def get_coordinates(city_name: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Fetches coordinates for a given city name.
    
    Args:
        city_name: Name of the city
        
    Returns:
        Tuple of (latitude, longitude) or (None, None) if not found
    """
    params = {
        "name": city_name,
        "count": 1,
        "language": "en",
        "format": "json"
    }
    
    try:
        response = requests.get(config.GEOCODING_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            return result["latitude"], result["longitude"]
        else:
            logger.warning(f"No coordinates found for city: {city_name}")
            return None, None
    except requests.RequestException as e:
        logger.error(f"Error fetching coordinates for {city_name}: {e}")
        return None, None
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected response format for {city_name}: {e}")
        return None, None

def get_daily_forecast(
    lat: float, 
    lon: float, 
    date_str: str
) -> Tuple[Optional[float], Optional[float]]:
    """
    Fetches daily max/min temperature for a specific date.
    
    Args:
        lat: Latitude
        lon: Longitude
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        Tuple of (max_temp, min_temp) in Celsius, or (None, None) if unavailable
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["temperature_2m_max", "temperature_2m_min"],
        "timezone": "auto",
        "start_date": date_str,
        "end_date": date_str
    }
    
    try:
        response = requests.get(config.FORECAST_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "daily" in data:
            max_temp = data["daily"]["temperature_2m_max"][0]
            min_temp = data["daily"]["temperature_2m_min"][0]
            return max_temp, min_temp
        logger.warning(f"No daily data in forecast response for {date_str}")
        return None, None
        
    except requests.RequestException as e:
        logger.error(f"Error fetching forecast for {date_str}: {e}")
        return None, None
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected forecast response format for {date_str}: {e}")
        return None, None
