import re
from datetime import datetime
import statistics
import math
import json

# Standard deviation of forecast error in degrees Celsius
# Benchmark (Jan 2026) showed observed StdDev of ~1.1C.
# We use 1.5C to be safe but more accurate than the default 2.0C.
FORECAST_STD_DEV_C = 1.5

def parse_event_title(title):
    """
    Parses "Highest temperature in {City} on {Date}?"
    """
    # Title: "Highest temperature in NYC on January 14?"
    # Regex to find City and Date
    match = re.search(r"Highest temperature in (.+) on (.+)\?", title, re.IGNORECASE)
    if not match:
        return None
        
    city_str = match.group(1).strip()
    date_str = match.group(2).strip()
    
    # Clean city name if needed
    # Map common abbr
    city_map = {
        "NYC": "New York",
        "LA": "Los Angeles"
    }
    city = city_map.get(city_str, city_str)
    
    # Parse Date
    # "January 14" -> Need to add year. Assume current or next.
    now = datetime.now()
    try:
        dt = datetime.strptime(f"{date_str} {now.year}", "%B %d %Y")
        # If date is in past more than a day, maybe it's next year? 
        # But usually these are daily markets. simpler to assume current year.
    except:
        return None
        
    return {
        "city": city,
        "date": dt.strftime("%Y-%m-%d")
    }

def parse_bucket_question(question):
    """
    Parses specific market question to get range.
    Examples:
    - "... be 41°F or below ..." -> (-inf, 41)
    - "... be between 42-43°F ..." -> [42, 43]
    - "... be 52°F or higher ..." -> (52, inf)
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

def to_celsius(val, unit):
    if unit == "C":
        return val
    return (val - 32) * 5/9

def calculate_probability_range(forecast_val, min_c, max_c, std_dev=FORECAST_STD_DEV_C):
    """
    P(min < X < max) = CDF(max) - CDF(min)
    """
    def cdf(x):
        return 0.5 * (1 + math.erf((x - forecast_val) / (std_dev * math.sqrt(2))))
    
    p_max = cdf(max_c)
    p_min = cdf(min_c)
    
    return p_max - p_min

def calculate_ev_for_event(event, forecast_max, forecast_min):
    """
    Analyzes all markets in the event.
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
        
        # Get Price
        # Use bestAsk for BUYING YES
        # Use bestBid for SELLING YES (which is effectively Buying NO, wait...)
        # Polymarket "Buy Yes" price is the `bestAsk` for Yes outcome.
        # Polymarket "Buy No" price is ... implied by `bestBid` of Yes?
        # Actually Gamma returns `bestAsk` and `bestBid`.
        
        # Structure of Gamma Market:
        # bestAsk: price to BUY YES immediately.
        # bestBid: price to SELL YES immediately.
        
        # If we want to "Bet YES", we buy at `bestAsk`.
        # If we want to "Bet NO" (Short), we effectively "Buy No". 
        # In Polymarket UI, "Buy No" takes liquidity from the YES SIDES?
        # "Buy No" @ 0.73 means you pay 0.73.
        # This is equivalent to Selling Yes @ 0.27?
        # If I Sell Yes @ 0.27, I put up 0.27 collateral? No.
        # If I Sell Yes @ 0.27, I get 0.27?
        # Let's stick to the UI perspective.
        # Gamma also provides `bestAsk` and `bestBid` for the "No" outcome? 
        # No, typically usually only one token (YES).
        
        # Actually, Gamma `bestAsk` is the cheapest price to BUY 1 outcome token.
        # `outcomePrices` was the mid.
        
        # We need to rely on `bestAsk` field if available.
        
        price_buy_yes = None
        price_buy_no = None
        
        # Check if we have bestAsk/Bid
        if "bestAsk" in market and "bestBid" in market:
              try:
                  price_buy_yes = float(market["bestAsk"])
                  # To Buy NO, we are effectively hitting the BID of YES?
                  # Buying NO at $0.74 means Selling YES at $0.26? 
                  # Yes + No = 1.
                  # Buy No Price = 1 - Sell Yes Price (bestBid).
                  # Example: bestBid (Sell Yes) is 0.40. You can sell your Yes for 0.40.
                  # Or someone else sells Yes for 0.40.
                  # If I want to Buy No, I match against someone buying Yes?
                  # Yes. BestBid is the highest price someone acts to BUY Yes.
                  # If I "Buy No", I am satisfying their Buy Yes order.
                  # So Cost to Buy No = 1.0 - bestBid.
                  
                  best_bid_yes = float(market["bestBid"])
                  price_buy_no = 1.0 - best_bid_yes
              except:
                  pass
                  
        # Fallback to unreliable outcomePrices if detailed data failed
        if price_buy_yes is None:
             outcomes = json.loads(market.get("outcomes", "[]"))
             outcome_prices = json.loads(market.get("outcomePrices", "[]"))
             try:
                 yes_idx = outcomes.index("Yes")
                 # Fallback, highly inaccurate for illiquid markets
                 price_buy_yes = float(outcome_prices[yes_idx])
                 price_buy_no = 1.0 - price_buy_yes 
             except:
                 continue

        # --- VALIDATION FOR LONG (BET YES) ---
        # We pay `price_buy_yes`
        if price_buy_yes > 0:
            ev_long = true_prob - price_buy_yes
            if ev_long > 0.05:
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
        
        lower_bound = forecast_max - (1.5 * FORECAST_STD_DEV_C)
        upper_bound = forecast_max + (1.5 * FORECAST_STD_DEV_C)
        
        if (min_c < upper_bound) and (max_c > lower_bound):
            prob = calculate_probability_range(forecast_max, min_c, max_c)
            
            # Re-fetch price logic for blanket (Buying Yes)
            price = None
            if "bestAsk" in market:
                try: price = float(market["bestAsk"])
                except: pass
                
            if price is None:
                # Fallback
                outcomes = json.loads(market.get("outcomes", "[]"))
                outcome_prices = json.loads(market.get("outcomePrices", "[]"))
                try:
                    yes_idx = outcomes.index("Yes")
                    price = float(outcome_prices[yes_idx])
                except: continue

            if price <= 0: continue
                
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
        
        if total_ev > 0.05:
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
         
         # Price to Buy No = 1 - bestBid (Sell Yes)
         price_buy_no = None
         implied_yes_price = None
         
         if "bestBid" in market:
             try:
                 bid = float(market["bestBid"])
                 if bid > 0: 
                    price_buy_no = 1.0 - bid
                    implied_yes_price = bid
             except: pass
         
         # Fallback
         if price_buy_no is None:
             outcomes = json.loads(market.get("outcomes", "[]"))
             outcome_prices = json.loads(market.get("outcomePrices", "[]"))
             try:
                 yes_price_mid = float(outcome_prices[outcomes.index("Yes")])
                 # Mid price is a terrible proxy for Bid if spread is wide.
                 # Conservatively assume spread is big for fallback? 
                 # Or just skip if no real bid?
                 # If we rely on fallback, we prompt the user with bad data.
                 # BETTER: Skip shorts if we don't have real bid liquidity.
                 if not "bestBid" in market:
                     # print(f"Skipping short since no bestBid for {bucket}")
                     # Wait, if `bestBid` is None/0, it means NO ONE wants to buy Yes.
                     # So you CANNOT Sell Yes (Buy No).
                     # So cost to Buy No is effectively infinity or market doesn't exist.
                     continue
             except:
                 continue
         
         # Safety: If price to Buy No is > 0.995 (i.e. Yes Bid is < 0.005)
         if price_buy_no > 0.995:
             continue
             
         ev_no = true_prob_no - price_buy_no
         
         if ev_no > 0.10: 
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
