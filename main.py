from utils.polymarket_api import get_weather_markets
from utils.weather_api import get_coordinates, get_daily_forecast
from analysis.arbitrage import calculate_ev_for_event, parse_event_title
import json
from datetime import datetime

def run_bot(mock_data=False):
    print("--- Polymarket Weather Arbitrage Bot ---")
    
    if mock_data:
        print("[DEMO MODE] Using mock market data for demonstration.")
        # Mock Event Structure
        events = [{
            "title": "Highest temperature in New York on January 15?",
            "markets": [
                {
                    "id": "1",
                    "question": "Will ... be 41°F or below?",
                    "outcomes": "[\"Yes\", \"No\"]",
                    "outcomePrices": "[\"0.20\", \"0.80\"]"
                },
                {
                    "id": "2",
                    "question": "Will ... be 44°F or higher?", # Forecast is 42F (5.9C)
                    "outcomes": "[\"Yes\", \"No\"]",
                    "outcomePrices": "[\"0.30\", \"0.70\"]"
                }
            ]
        }]
    else:
        print("Fetching active weather events from Polymarket (Tag: Weather)...")
        # get_weather_markets now returns EVENTS
        events = get_weather_markets()
    
    if not events:
        print("No active weather events found.")
        return

    print(f"Found {len(events)} events to analyze.\n")
    
    for event in events:
        title = event.get("title", "")
        parsed = parse_event_title(title)
        
        if not parsed:
            print(f"[SKIP] could not parse event title: {title}")
            continue
            
        city = parsed['city']
        date = parsed['date']
        
        # New Safety Check: Only analyze FUTURE events
        # "Highest temperature in Seattle on January 14?"
        # If today is Jan 14, we should SKIP because the event is live/resolving
        # and our "forecast" might be stale or not account for observed.
        
        try:
            event_dt = datetime.strptime(date, "%Y-%m-%d").date()
            today = datetime.now().date()
            
            if event_dt <= today:
                print(f"[SKIP] Event date {date} is Today or Past. Too risky/resolving.")
                continue
        except:
            print(f"[SKIP] Could not parse date safety check: {date}")
            continue

        print(f"Analyzing Event: {title}")
        print(f"  -> Location: {city}, Date: {date}")
        
        # Get Coordinates
        lat, lon = get_coordinates(city)
        if not lat:
            print(f"  -> Could not find coordinates for {city}")
            continue
            
        # Get Forecast
        max_temp, min_temp = get_daily_forecast(lat, lon, date)
        
        if max_temp is None:
            if mock_data:
                print("  -> [MOCK] Using mock forecast 5.9C (42.6F).")
                max_temp = 5.9
                min_temp = 0.0
            else:
                print("  -> Could not get forecast.")
                continue
                
        print(f"  -> Forecast Max: {max_temp}C ({max_temp * 9/5 + 32:.1f}F)")
        
        # Calculate EV
        recommendations = calculate_ev_for_event(event, max_temp, min_temp)
        
        if recommendations:
            recs = recommendations # It's a dict now
            
            # 1. Individual Longs
            longs = recs.get("bets", [])
            if longs:
                print(f"  -> Found {len(longs)} +EV 'Bet YES' opportunities:")
                for rec in longs:
                     print(f"     * [{rec['bucket']}] Price: {rec['price']} | Model Prob: {rec['prob']:.2f} | EV: {rec['ev']:.4f}")
            
            # 2. Blanket Strategy
            strategy = recs.get("strategy")
            if strategy:
                print(f"  -> RECOMMENDED STRATEGY: {strategy['type']}")
                print(f"     Covering buckets: {', '.join(strategy['buckets'])}")
                print(f"     Total Cost: {strategy['total_cost']:.3f} | Total Prob: {strategy['total_prob']:.2f}")
                print(f"     Total EV: {strategy['total_ev']:.4f} (ROI: {strategy.get('roi_str', 'N/A')})")
            
            # 3. Shorts
            shorts = recs.get("shorts", [])
            if shorts:
                print(f"  -> Found {len(shorts)} 'Bet NO' (Short) opportunities:")
                for rec in shorts:
                    print(f"     * [{rec['bucket']}] Sell YES at: {rec['implied_yes_price']} (Cost to NO: {rec['price']})")
                    print(f"       Model says YES prob is {rec['true_yes_prob']:.3f} -> EV: {rec['ev']:.4f}")
                
                # NEW: Advanced Portfolio Analysis
                if len(shorts) > 1:
                    from analysis.portfolio import PortfolioAnalyzer
                    analyzer = PortfolioAnalyzer(max_temp) # Using Forecast Mean
                    
                    portfolio_analysis = analyzer.recommend_short_portfolio(shorts)
                    
                    if portfolio_analysis:
                        print(f"  -> PORTFOLIO ANALYSIS (Combined Shorts):")
                        print(f"     Combined Prob of Profit: {portfolio_analysis['combined_prob_profit']*100:.1f}%")
                        print(f"     Expected Total Return: {portfolio_analysis['expected_total_return']:.3f}")
                        print(f"     Recommended Sizing (Quarter Kelly):")
                        for alloc in portfolio_analysis['allocations']:
                            print(f"       - {alloc['bucket']}: {alloc['kelly_pct']:.1f}% bankroll ({alloc['amt']}/$100)")

            if not longs and not strategy and not shorts:
                print("  -> No significant +EV plays found.")
        else:
             print("  -> No recommendations returned.")
            
        print("-" * 30)

if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        run_bot(mock_data=True)
    else:
        run_bot(mock_data=False)
