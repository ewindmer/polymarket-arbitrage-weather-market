from utils.polymarket_api import get_weather_markets
import json

if __name__ == "__main__":
    print("Fetching weather markets...")
    markets = get_weather_markets()
    print(f"Found {len(markets)} potentially relevant markets.")
    
    # Print questions of all found markets
    print(f"Found {len(markets)} markets.")
    for i, m in enumerate(markets):
        print(f"Market {i}: {m.get('question')}")
        
    # Check if we found any common weather cities
    cities = ["New York", "London", "Tokyo", "California", "Texas", "Chicago", "Miami"]
    found_cities = set()
    for m in markets:
        desc = m.get("description", "") + " " + m.get("question", "")
        for city in cities:
            if city.lower() in desc.lower():
                found_cities.add(city)
    
    print(f"Found mentions of: {found_cities}")
