import requests
import datetime
import logging
from typing import List, Dict, Any, Optional

import config

logger = logging.getLogger(__name__)

def get_weather_markets() -> List[Dict[str, Any]]:
    """
    Fetches active markets that are likely related to weather.
    Strategies:
    1. Search for markets with "Weather" tag (if ID known) or "Weather" in title/description.
    2. Filter for daily resolution markets.
    
    Returns:
        List of event dictionaries with detailed market data
    """
    
    # Strategy: Fetch EVENTS by TAG ID (84 = Weather)
    # Endpoint: /events
    
    params = {
        "tag_id": config.WEATHER_TAG_ID,
        "active": "true",
        "closed": "false",
        "limit": 50,
        "order": "startDate", # Get upcoming first
        "ascending": "true"
    }
    
    try:
        response = requests.get(f"{config.GAMMA_API_URL}/events", params=params, timeout=10)
        response.raise_for_status()
        events = response.json()
        
        weather_events = []
        for event in events:
            # Filter for "Highest temperature" to avoid other weather events like "Hurricane"
            title = event.get("title", "")
            if "Highest temperature in" in title:
                 # Fetch detailed markets to get bestBid/bestAsk for accurate pricing
                 # The 'markets' list in /events is simplified.
                 # We need to query /markets?id=... for each market to get liquidity.
                 
                 detailed_markets = []
                 if "markets" in event:
                     market_ids = [m["id"] for m in event["markets"]]
                     
                     # Chunking in case of limits, though max 5-10 per event
                     if market_ids:
                         try:
                             # Query param format for multiple IDs
                             # Requests handles list as multiple params: id=1&id=2
                             m_params = [("id", mid) for mid in market_ids]
                             m_res = requests.get(
                                 f"{config.GAMMA_API_URL}/markets", 
                                 params=m_params,
                                 timeout=10
                             )
                             m_res.raise_for_status()
                             detailed_markets = m_res.json()
                         except (requests.RequestException, ValueError) as e:
                             logger.warning(f"Failed to fetch details for event {title}: {e}")
                             detailed_markets = event["markets"] # Fallback
                             
                 # Replace simplified markets with detailed ones
                 event["markets"] = detailed_markets
                 weather_events.append(event)
                 
        return weather_events

    except requests.RequestException as e:
        logger.error(f"Error fetching events from Polymarket API: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching events: {e}", exc_info=True)
        return []

# Removed duplicate function definition 
