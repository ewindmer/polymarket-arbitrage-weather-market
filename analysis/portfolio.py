import math
import numpy as np

def calculate_kelly_bet(ev, odds, bankroll_fraction=0.1):
    """
    Simple Kelly Criterion.
    f* = (bp - q) / b
    where b = net odds received (b to 1), p = probability of winning, q = probability of losing.
    
    For binary options:
    Payout is 1. Price is C.
    Profit if win = 1 - C.
    Cost if lose = C.
    b = (1 - C) / C
    p = true_prob
    q = 1 - p
    
    f* = ( ((1-C)/C * p) - q ) / ((1-C)/C)
       = p - q / ((1-C)/C)
       = p - (1-p) * C / (1-C)
       ... simplified Kelly for binary: f = p/C - q/(1-C)? No.
       
    Actually standard formula: f = Edge / Odds.
    Edge = p - C.
    """
    # Safe impl
    # f = (p(b+1) - 1) / b
    # where b is 'odds' 
    # payout = 1/price
    # b = 1/price - 1
    
    # Example: Price 0.53, Prob 0.39.
    # Cost = 0.53. Net Win = 0.47.
    # b = 0.47 / 0.53 = 0.886
    # p = 0.39.
    # f = (0.39 * (0.886 + 1) - 1) / 0.886 ... wait, EV is negative here.
    
    # Our EV in arbitrage.py is per share.
    # f = EV / (1 - Price) ? No.
    
    # Kelly for binary bets:
    # f = (p - price) / (1 - price) ... NO.
    
    # Correct Formula: f = p/price - (1-p)/(1-price) ... wait this is for maximizing log growth?
    # Let's use Edge / Variance proxy or just (Prob * (Payout/Cost)) - 1...
    
    # Standard: f = (p * (b + 1) - 1) / b
    # b is net odds. b = (1 - Price)/Price.
    # b+1 = 1/Price.
    # f = (p/Price - 1) / ((1-Price)/Price) = (p - Price) / (1 - Price)
    
    # Let's stick to partial Kelly (fraction) to be safe.
    pass

class PortfolioAnalyzer:
    def __init__(self, forecast_mean, forecast_std=2.0):
        self.mean = forecast_mean
        self.std = forecast_std
        
    def simulate_portfolio(self, bets, samples=1000):
        """
        Simulate Profit/Loss across a range of temperatures.
        bets: list of dicts with {'min_c', 'max_c', 'type'='LONG'|'SHORT', 'price', 'quantity'}
        """
        # Define simulation range (Mean +/- 4 STD)
        temps = np.linspace(self.mean - 4*self.std, self.mean + 4*self.std, samples)
        
        # Calculate P(T) for each temp step
        # PDF of normal dist
        pdf = (1 / (self.std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((temps - self.mean) / self.std) ** 2)
        # Normalize just in case step size isn't perfectly 1, though we weight by PDF * dX implies sum is 1 approx.
        # Actually we just want Prob(Profit>0).
        
        total_ev = 0
        prob_profit = 0
        sum_pdf = np.sum(pdf)
        
        pnl_dist = []
        
        for i, t in enumerate(temps):
            round_pnl = 0
            for bet in bets:
                # Did bet win?
                bet_min = bet.get('min_c', -999)
                bet_max = bet.get('max_c', 999)
                is_in_range = bet_min < t < bet_max
                
                # Check outcome based on Type
                won = False
                if bet['type'] == 'LONG':
                    won = is_in_range
                else: # SHORT (Betting NO)
                    won = not is_in_range # Win if temp is OUTSIDE range
                    
                # Payout
                cost = bet['price']
                if won:
                    round_pnl += (1.0 - cost) # Net profit
                else:
                    round_pnl -= cost # Net loss
            
            pnl_dist.append(round_pnl)
            
            # Weighted sums for expected stats
            weight = pdf[i]
            total_ev += round_pnl * weight
            
            if round_pnl > 0:
                prob_profit += weight
                
        # Normalize
        total_ev /= sum_pdf
        prob_profit /= sum_pdf
        
        return {
            "expected_pnl": total_ev,
            "prob_profit": prob_profit,
            "min_pnl": min(pnl_dist),
            "max_pnl": max(pnl_dist)
        }

    def recommend_short_portfolio(self, short_candidates):
        """
        Takes a list of 'Bet No' candidates.
        Optimizes weights?
        """
        # User goal: "Sure win".
        # We need to find the combination of shorts where the "Safe Zone" (where all win)
        # has the highest integral.
        
        # Actually, "Combined Prob" is just Prob( Temp NOT in Union(Short Ranges) )
        # Short Ranges are usually disjoint outliers.
        # Temp needs to land in the "Middle".
        
        if not short_candidates:
            return None
            
        # Simplified: Recommend 1 share of each +EV short
        # And simulate the result.
        
        bets = []
        for s in short_candidates:
            bets.append({
                "min_c": s['min_c'] if 'min_c' in s else -999, # need to ensure `arbitrage.py` passes this
                "max_c": s['max_c'] if 'max_c' in s else 999,
                "type": "SHORT",
                "price": s['price'],
                "desc": s['bucket'],
                "ev": s['ev']
            })
            
        sim = self.simulate_portfolio(bets)
        
        # Weighting?
        # Simple Kelly: Allocate proportional to Edge/Odds.
        # Weight = (ProbWin - Price) / (1 - Price) * Bankroll
        # Let's verify each bet's Kelly.
        
        allocations = []
        for s in short_candidates:
            p = s['prob_win']
            price = s['price'] # This is Cost to Buy NO
            
            # Kelly Fraction
            if (1-price) == 0: kelly = 0
            else: kelly = (p - price) / (1 - price)
            
            # Scale down for safety (quarter Kelly)
            kelly_safe = max(0, kelly * 0.25) 
            
            allocations.append({
                "bucket": s['bucket'],
                "kelly_pct": kelly_safe * 100,
                "amt": f"${kelly_safe * 100:.1f}" # Assuming $100 bankroll unit for display
            })
            
        return {
            "combined_prob_profit": sim['prob_profit'],
            "expected_total_return": sim['expected_pnl'],
            "allocations": allocations
        }
