from utils.polymarket_api import get_weather_markets
from utils.weather_api import get_coordinates, get_daily_forecast
from analysis.arbitrage import calculate_ev_for_event, parse_event_title
import json
from datetime import datetime
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def run_bot(mock_data: bool = False) -> None:
    """
    Main bot function that scans markets and calculates EV opportunities.
    
    Args:
        mock_data: If True, use mock data instead of API calls
    """
    logger.info("--- Polymarket Weather Arbitrage Bot ---")
    
    if mock_data:
        logger.info("[DEMO MODE] Using mock market data for demonstration.")
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
        logger.info("Fetching active weather events from Polymarket (Tag: Weather)...")
        # get_weather_markets now returns EVENTS
        events = get_weather_markets()
    
    if not events:
        logger.info("No active weather events found.")
        return

    logger.info(f"Found {len(events)} events to analyze.\n")
    
    for event in events:
        title = event.get("title", "")
        parsed = parse_event_title(title)
        
        if not parsed:
            logger.warning(f"[SKIP] could not parse event title: {title}")
            continue
            
        city = parsed['city']
        date = parsed['date']
        
        # Safety Check: Only analyze FUTURE events
        # If today is the event date, we should SKIP because the event is live/resolving
        # and our "forecast" might be stale or not account for observed.
        
        try:
            event_dt = datetime.strptime(date, "%Y-%m-%d").date()
            today = datetime.now().date()
            
            if event_dt <= today:
                logger.info(f"[SKIP] Event date {date} is Today or Past. Too risky/resolving.")
                continue
        except ValueError as e:
            logger.warning(f"[SKIP] Could not parse date safety check: {date} - {e}")
            continue

        logger.info(f"Analyzing Event: {title}")
        logger.info(f"  -> Location: {city}, Date: {date}")
        
        # Get Coordinates
        lat, lon = get_coordinates(city)
        if not lat:
            logger.warning(f"  -> Could not find coordinates for {city}")
            continue
            
        # Get Forecast
        max_temp, min_temp = get_daily_forecast(lat, lon, date)
        
        if max_temp is None:
            if mock_data:
                logger.info("  -> [MOCK] Using mock forecast 5.9C (42.6F).")
                max_temp = 5.9
                min_temp = 0.0
            else:
                logger.warning("  -> Could not get forecast.")
                continue
                
        logger.info(f"  -> Forecast Max: {max_temp}C ({max_temp * 9/5 + 32:.1f}F)")
        
        # Calculate EV
        try:
            recommendations = calculate_ev_for_event(event, max_temp, min_temp)
        except Exception as e:
            logger.error(f"Error calculating EV for event {title}: {e}", exc_info=True)
            continue
        
        if recommendations:
            recs = recommendations # It's a dict now
            
            # 1. Individual Longs
            longs = recs.get("bets", [])
            if longs:
                logger.info(f"  -> Found {len(longs)} +EV 'Bet YES' opportunities:")
                for rec in longs:
                     logger.info(f"     * [{rec['bucket']}] Price: {rec['price']} | Model Prob: {rec['prob']:.2f} | EV: {rec['ev']:.4f}")
            
            # 2. Blanket Strategy
            strategy = recs.get("strategy")
            if strategy:
                logger.info(f"  -> RECOMMENDED STRATEGY: {strategy['type']}")
                logger.info(f"     Covering buckets: {', '.join(strategy['buckets'])}")
                logger.info(f"     Total Cost: {strategy['total_cost']:.3f} | Total Prob: {strategy['total_prob']:.2f}")
                logger.info(f"     Total EV: {strategy['total_ev']:.4f} (ROI: {strategy.get('roi_str', 'N/A')})")
            
            # 3. Shorts
            shorts = recs.get("shorts", [])
            if shorts:
                logger.info(f"  -> Found {len(shorts)} 'Bet NO' (Short) opportunities:")
                for rec in shorts:
                    logger.info(f"     * [{rec['bucket']}] Sell YES at: {rec['implied_yes_price']} (Cost to NO: {rec['price']})")
                    logger.info(f"       Model says YES prob is {rec['true_yes_prob']:.3f} -> EV: {rec['ev']:.4f}")
                
                # Advanced Portfolio Analysis
                if len(shorts) > 1:
                    from analysis.portfolio import PortfolioAnalyzer
                    analyzer = PortfolioAnalyzer(max_temp) # Using Forecast Mean
                    
                    try:
                        portfolio_analysis = analyzer.recommend_short_portfolio(shorts)
                        
                        if portfolio_analysis:
                            logger.info(f"  -> PORTFOLIO ANALYSIS (Combined Shorts):")
                            logger.info(f"     Combined Prob of Profit: {portfolio_analysis['combined_prob_profit']*100:.1f}%")
                            logger.info(f"     Expected Total Return: {portfolio_analysis['expected_total_return']:.3f}")
                            logger.info(f"     Recommended Sizing (Quarter Kelly):")
                            for alloc in portfolio_analysis['allocations']:
                                logger.info(f"       - {alloc['bucket']}: {alloc['kelly_pct']:.1f}% bankroll ({alloc['amt']}/$100)")
                    except Exception as e:
                        logger.error(f"Error in portfolio analysis: {e}", exc_info=True)

            if not longs and not strategy and not shorts:
                logger.info("  -> No significant +EV plays found.")
        else:
             logger.info("  -> No recommendations returned.")
            
        logger.info("-" * 30)

if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        run_bot(mock_data=True)
    else:
        run_bot(mock_data=False)
