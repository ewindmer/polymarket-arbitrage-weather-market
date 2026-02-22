import re
from datetime import datetime
import statistics
import math
import json
import logging
from typing import Dict, Optional, Tuple, List, Any

import config

logger = logging.getLogger(__name__)

def parse_event_title(title: str) -> Optional[Dict[str, str]]:
    """
    Parses "Highest temperature in {City} on {Date}?"
    
    Args:
        title: Event title string
        
    Returns:
        Dictionary with 'city' and 'date' keys, or None if parsing fails
    """
    # Title: "Highest temperature in NYC on January 14?"
    # Regex to find City and Date
    match = re.search(r"Highest temperature in (.+) on (.+)\?", title, re.IGNORECASE)
    if not match:
        return None
        
    city_str = match.group(1).strip()
    date_str = match.group(2).strip()
    
    # Clean city name if needed
    city = config.CITY_MAP.get(city_str, city_str)
    
    # Parse Date
    # "January 14" -> Need to add year. Assume current or next.
    now = datetime.now()
    try:
        dt = datetime.strptime(f"{date_str} {now.year}", "%B %d %Y")
        # If date is in past more than a day, maybe it's next year? 
        # But usually these are daily markets. simpler to assume current year.
    except ValueError as e:
        logger.debug(f"Failed to parse date '{date_str}': {e}")
        return None
        
    return {
        "city": city,
        "date": dt.strftime("%Y-%m-%d")
    }

def parse_bucket_question(question: str) -> Optional[Dict[str, Any]]:
    """
    Parses specific market question to get range.
    Examples:
    - "... be 41°F or below ..." -> (-inf, 41)
    - "... be between 42-43°F ..." -> [42, 43]
    - "... be 52°F or higher ..." -> (52, inf)
    
    Args:
        question: Market question string
        
    Returns:
        Dictionary with 'min', 'max', and 'unit' keys, or None if parsing fails
    """
    # Unit check
    unit = "F" if "°F" in question or "F" in question else "C"
    
    # Case 1: "X or below"
    match_below = re.search(r"be (-?\d+)[°]?[CF]? or below", question)
    if match_below:
        val = float(match_below.group(1))
        return {"min": -999, "max": val, "unit": unit}
        
    # Case 2: "X or higher"
    match_above = re.search(r"be (-?\d+)[°]?[CF]? or higher", question)
    if match_above:
        val = float(match_above.group(1))
        return {"min": val, "max": 999, "unit": unit}
        
    # Case 3: "between X-Y"
    match_between = re.search(r"between (-?\d+)-(-?\d+)[°]?[CF]?", question)
    if match_between:
        val_min = float(match_between.group(1))
        val_max = float(match_between.group(2))
        return {"min": val_min, "max": val_max, "unit": unit}
        
    return None

def to_celsius(val: float, unit: str) -> float:
    """Convert temperature to Celsius."""
    if unit == "C":
        return val
    return (val - 32) * 5/9

def calculate_probability_range(
    forecast_val: float, 
    min_c: float, 
    max_c: float, 
    std_dev: float = config.FORECAST_STD_DEV_C
) -> float:
    """
    Calculate probability that temperature falls within range using normal distribution.
    P(min < X < max) = CDF(max) - CDF(min)
    
    Args:
        forecast_val: Forecasted temperature (mean) in Celsius
        min_c: Minimum temperature in Celsius
        max_c: Maximum temperature in Celsius
        std_dev: Standard deviation in Celsius
        
    Returns:
        Probability (0.0 to 1.0)
    """
    def cdf(x: float) -> float:
        return 0.5 * (1 + math.erf((x - forecast_val) / (std_dev * math.sqrt(2))))
    
    p_max = cdf(max_c)
    p_min = cdf(min_c)
    
    return p_max - p_min

def get_market_prices(market: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract buy prices for YES and NO outcomes from market data.
    
    Prefers bestAsk/bestBid for accurate pricing, falls back to outcomePrices.
    
    Args:
        market: Market dictionary from Polymarket API
        
    Returns:
        Tuple of (price_buy_yes, price_buy_no) or (None, None) if unavailable
    """
    price_buy_yes = None
    price_buy_no = None
    
    # Try to get bestAsk/bestBid first (most accurate)
    if "bestAsk" in market and "bestBid" in market:
        try:
            price_buy_yes = float(market["bestAsk"])
            best_bid_yes = float(market["bestBid"])
            # Cost to Buy No = 1.0 - bestBid (since Yes + No = 1.0)
            price_buy_no = 1.0 - best_bid_yes
            return price_buy_yes, price_buy_no
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse bestAsk/bestBid: {e}")
    
    # Fallback to outcomePrices (less accurate, mid prices)
    try:
        outcomes = json.loads(market.get("outcomes", "[]"))
        outcome_prices = json.loads(market.get("outcomePrices", "[]"))
        yes_idx = outcomes.index("Yes")
        price_buy_yes = float(outcome_prices[yes_idx])
        price_buy_no = 1.0 - price_buy_yes
        return price_buy_yes, price_buy_no
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
        logger.debug(f"Failed to parse outcomePrices: {e}")
        return None, None

def calculate_ev_for_event(
    event: Dict[str, Any], 
    forecast_max: float, 
    forecast_min: float
) -> Dict[str, Any]:
    """
    Analyzes all markets in the event and calculates EV for long, short, and blanket strategies.
    
    Args:
        event: Event dictionary with 'title' and 'markets' keys
        forecast_max: Forecasted maximum temperature in Celsius
        forecast_min: Forecasted minimum temperature in Celsius
        
    Returns:
        Dictionary with 'bets' (longs), 'shorts', and 'strategy' (blanket) keys
    """
    event_title = event.get("title", "")
    markets = event.get("markets", [])
    
    recommendations = []
    
    for market in markets:
        question = market.get("question", "")
        # Parse bucket
        bucket = parse_bucket_question(question)
        if not bucket:
            continue
            
        # Convert range to C
        min_c = to_celsius(bucket["min"], bucket["unit"])
        max_c = to_celsius(bucket["max"], bucket["unit"])
        
        # Calculate prob
        # "Highest temperature" implies we check against forecast_max
        true_prob = calculate_probability_range(forecast_max, min_c, max_c)
        
        # Get prices using helper function
        price_buy_yes, price_buy_no = get_market_prices(market)
        
        if price_buy_yes is None:
            continue

        # --- VALIDATION FOR LONG (BET YES) ---
        # We pay `price_buy_yes`
        if price_buy_yes > 0:
            ev_long = true_prob - price_buy_yes
            if ev_long > config.EV_THRESHOLD_LONG:
                recommendations.append({
                    "market_question": question,
                    "bucket": f"{bucket['min']} to {bucket['max']} {bucket['unit']}",
                    "price": price_buy_yes,
                    "prob": true_prob,
                    "ev": ev_long,
                    "id": market.get("id"),
                    "type": "LONG"
                })

    # Sort by best EV
    recommendations.sort(key=lambda x: x['ev'], reverse=True)
    
    # ----------------------------------------------------
    # NEW: Calculate Coverage Strategy (Blanket)
    # ----------------------------------------------------
    
    coverage_candidates = []
    for market in markets:
        question = market.get("question", "")
        bucket = parse_bucket_question(question)
        if not bucket: continue
        
        min_c = to_celsius(bucket["min"], bucket["unit"])
        max_c = to_celsius(bucket["max"], bucket["unit"])
        
        lower_bound = forecast_max - (1.5 * config.FORECAST_STD_DEV_C)
        upper_bound = forecast_max + (1.5 * config.FORECAST_STD_DEV_C)
        
        if (min_c < upper_bound) and (max_c > lower_bound):
            prob = calculate_probability_range(forecast_max, min_c, max_c)
            
            # Get price using helper function
            price, _ = get_market_prices(market)
            
            if price is None or price <= 0:
                continue
                
            coverage_candidates.append({
                "bucket": f"{bucket['min']} to {bucket['max']} {bucket['unit']}",
                "min_c": min_c,
                "max_c": max_c,
                "price": price,
                "prob": prob,
                "ev": prob - price,
                "market_question": question
            })
            
    coverage_candidates.sort(key=lambda x: x['min_c'])
    
    strategy = None
    if coverage_candidates:
        total_cost = sum(c['price'] for c in coverage_candidates)
        total_prob = sum(c['prob'] for c in coverage_candidates)
        total_ev = sum(c['ev'] for c in coverage_candidates)
        
        if total_ev > config.EV_THRESHOLD_STRATEGY:
            if total_cost > 0:
                roi = (total_ev / total_cost) * 100
                roi_str = f"{roi:.1f}%"
            else:
                roi_str = "Inf%"
                
            strategy = {
                "type": "Blanket Coverage",
                "buckets": [c['bucket'] for c in coverage_candidates],
                "total_cost": total_cost,
                "total_prob": total_prob,
                "expected_profit_if_win": 1.0 - total_cost, 
                "total_ev": total_prob - total_cost,
                "roi_str": roi_str
            }

    # ----------------------------------------------------
    # NEW: Identify Short Opportunities (Betting NO)
    # ----------------------------------------------------
    short_recommendations = []
    for market in markets:
         question = market.get("question", "")
         bucket = parse_bucket_question(question)
         if not bucket: continue
         
         min_c = to_celsius(bucket["min"], bucket["unit"])
         max_c = to_celsius(bucket["max"], bucket["unit"])
         
         true_prob_yes = calculate_probability_range(forecast_max, min_c, max_c)
         true_prob_no = 1.0 - true_prob_yes
         
         # Get prices using helper function
         price_buy_yes, price_buy_no = get_market_prices(market)
         
         # For shorts, we need bestBid to calculate accurate price_buy_no
         # If we only have fallback data (outcomePrices), skip shorts for safety
         if price_buy_no is None:
             # Skip if we don't have real bid liquidity
             if "bestBid" not in market:
                 continue
             # If we got here, get_market_prices failed - skip
             continue
         
         # Calculate implied_yes_price from bestBid if available
         implied_yes_price = None
         if "bestBid" in market:
             try:
                 implied_yes_price = float(market["bestBid"])
             except (ValueError, TypeError):
                 pass
         
         # Safety: If price to Buy No is > 0.995 (i.e. Yes Bid is < 0.005)
         if price_buy_no > 0.995:
             continue
             
         ev_no = true_prob_no - price_buy_no
         
         if ev_no > config.EV_THRESHOLD_SHORT:
             short_recommendations.append({
                 "market_question": question,
                 "bucket": f"{bucket['min']} to {bucket['max']} {bucket['unit']}",
                 "type": "BET NO (Short)",
                 "price": price_buy_no, # Cost to bet NO
                 "prob_win": true_prob_no,
                 "ev": ev_no,
                 "implied_yes_price": implied_yes_price,
                 "true_yes_prob": true_prob_yes,
                 "min_c": min_c,
                 "max_c": max_c
             })
             
    short_recommendations.sort(key=lambda x: x['ev'], reverse=True)

    return {
        "bets": recommendations,
        "strategy": strategy,
        "shorts": short_recommendations
    }
