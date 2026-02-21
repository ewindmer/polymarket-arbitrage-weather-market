import requests
import json
import datetime

def probe_api():
    lat = 40.7128
    lon = -74.0060
    today = "2026-01-14" # Simulation date
    
    # Check recent dates (Last week)
    today_dt = datetime.date.today()
    start = (today_dt - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    end = (today_dt - datetime.timedelta(days=2)).strftime("%Y-%m-%d")
    
    url1 = "https://historical-forecast-api.open-meteo.com/v1/forecast"
    p1 = {
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "daily": "temperature_2m_max"
        # Removed forecast_days to see default behavior
    }
    
    try:
        print(f"Probing Historical Forecast API for {start} to {end}...")
        r1 = requests.get(url1, params=p1)
        print(f"Status: {r1.status_code}")
        if r1.status_code == 200:
            data = r1.json()
            print("Keys:", data.keys())
            if "daily" in data:
                print("Daily Keys:", data["daily"].keys())
                print("First 3 Data:", data["daily"]["temperature_2m_max"][:3])
            else:
                print("NO 'daily' KEY FOUND. Response:", data)
        else:
            print("Error:", r1.text)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    probe_api()
