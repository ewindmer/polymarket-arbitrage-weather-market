import requests
import datetime

# constants
GAMMA_API_URL = "https://gamma-api.polymarket.com"

def get_weather_markets():
    """
    Fetches active markets that are likely related to weather.
    Strategies:
    1. Search for markets with "Weather" tag (if ID known) or "Weather" in title/description.
    2. Filter for daily resolution markets.
    """
    
    # Strategy: Fetch EVENTS by TAG ID (84 = Weather)
    # Endpoint: /events
    
    params = {
        "tag_id": "84", # Weather
        "active": "true",
        "closed": "false",
        "limit": 50,
        "order": "startDate", # Get upcoming first
        "ascending": "true"
    }
    
    try:
        response = requests.get(f"{GAMMA_API_URL}/events", params=params)
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
                 
                 # Optimization: Collect all market IDs and do a batch query if possible,
                 # or just iterate. Batch /markets?id=1&id=2 is often supported by Gamma?
                 # Gamma API supports multiple IDs via `id` param array or comma sep?
                 # Docs say: `GET /markets` accepts `id` as string.
                 
                 # Let's clean up the 'markets' in the event object with fresh data
                 detailed_markets = []
                 if "markets" in event:
                     market_ids = [m["id"] for m in event["markets"]]
                     
                     # Chunking in case of limits, though max 5-10 per event
                     if market_ids:
                         try:
                             # Query param format for multiple IDs might need check.
                             # Trying comma separated or repeated. Gamma assumes `id` list.
                             # Requests handles list as multiple params: id=1&id=2
                             m_params = [("id", mid) for mid in market_ids]
                             m_res = requests.get(f"{GAMMA_API_URL}/markets", params=m_params)
                             m_res.raise_for_status()
                             detailed_markets = m_res.json()
                         except Exception as e:
                             print(f"  [WARN] Failed to fetch details for event {title}: {e}")
                             detailed_markets = event["markets"] # Fallback
                             
                 # Replace simplified markets with detailed ones
                 event["markets"] = detailed_markets
                 weather_events.append(event)
                 
        return weather_events

    except Exception as e:
        print(f"Error fetching events: {e}")
        return []

def group_markets_by_location_date(markets):
    # Deprecated, we now get grouped events directly
    pass

def group_markets_by_location_date(markets):
    """
    Groups markets by location and date to form a 'bucket' strategy.
    E.g. Group all "NY Jan 15 High Temp" markets.
    """
    # This requires parsing the question string which is unstructured.
    # Example: "Will the High Temperature in New York be > 50F on Jan 15?"
    # Implementation detail: Regex or simple string split.
    pass 
