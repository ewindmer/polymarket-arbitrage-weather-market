import requests
import json

def inspect_market():
    # Fetch specific event by slug found in browser
    slug = "highest-temperature-in-nyc-on-january-14"
    url = "https://gamma-api.polymarket.com/events"
    params = {
        "slug": slug
    }
    
    print(f"Fetching event slug: {slug}...")
    response = requests.get(url, params=params) 
    events = response.json()
    
    if events:
        e = events[0]
        print("Found Event!")
        print(f"Title: {e.get('title')}")
        print(f"ID: {e.get('id')}")
        print(f"Tags: {json.dumps(e.get('tags'), indent=2)}")
        
        print("Markets:")
        if "markets" in e:
            for m in e["markets"]:
                print(f"  - {m.get('question')} (ID: {m.get('id')})")
                print(f"    Outcomes: {m.get('outcomes')}")
    else:
        print("Event not found by slug.")

if __name__ == "__main__":
    inspect_market()
