import math
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import logging

import config

logger = logging.getLogger(__name__)

def calculate_kelly_bet(probability: float, price: float, bankroll_fraction: float = 0.25) -> float:
    """
    Calculate Kelly Criterion fraction for binary bets.
    
    For binary options where payout is 1.0 and cost is price:
    - If you win: profit = 1.0 - price
    - If you lose: loss = price
    
    Kelly fraction: f = (p - price) / (1 - price)
    where p = true probability of winning, price = cost to bet
    
    Args:
        probability: True probability of winning (0.0 to 1.0)
        price: Cost to place the bet (0.0 to 1.0)
        bankroll_fraction: Fractional Kelly multiplier (default 0.25 for quarter Kelly)
    
    Returns:
        Recommended fraction of bankroll to bet (0.0 to 1.0)
    """
    if price <= 0 or price >= 1:
        return 0.0
    
    if probability <= 0 or probability >= 1:
        return 0.0
    
    # Kelly fraction: f = (p - price) / (1 - price)
    # This maximizes log growth rate
    kelly_full = (probability - price) / (1 - price)
    
    # Apply fractional Kelly for safety (default quarter Kelly)
    kelly_fractional = max(0.0, kelly_full * bankroll_fraction)
    
    # Cap at 100% of bankroll
    return min(1.0, kelly_fractional)

class PortfolioAnalyzer:
    def __init__(self, forecast_mean: float, forecast_std: float = config.FORECAST_STD_DEV_C):
        """
        Initialize portfolio analyzer with forecast parameters.
        
        Args:
            forecast_mean: Forecasted temperature mean in Celsius
            forecast_std: Standard deviation in Celsius
        """
        self.mean = forecast_mean
        self.std = forecast_std
        
    def simulate_portfolio(
        self, 
        bets: List[Dict[str, Any]], 
        samples: int = config.PORTFOLIO_SAMPLES
    ) -> Dict[str, float]:
        """
        Simulate Profit/Loss across a range of temperatures using Monte Carlo.
        
        Args:
            bets: List of bet dictionaries with keys:
                - 'min_c': Minimum temperature in Celsius
                - 'max_c': Maximum temperature in Celsius
                - 'type': 'LONG' or 'SHORT'
                - 'price': Cost of the bet
            samples: Number of temperature samples for simulation
            
        Returns:
            Dictionary with 'expected_pnl', 'prob_profit', 'min_pnl', 'max_pnl'
        """
        # Define simulation range (Mean +/- N*STD)
        std_mult = config.PORTFOLIO_STD_MULTIPLIER
        temps = np.linspace(
            self.mean - std_mult * self.std, 
            self.mean + std_mult * self.std, 
            samples
        )
        
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

    def recommend_short_portfolio(
        self, 
        short_candidates: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a portfolio of short (Bet NO) candidates.
        
        Args:
            short_candidates: List of short bet dictionaries with keys:
                - 'bucket': String description
                - 'min_c': Minimum temperature in Celsius
                - 'max_c': Maximum temperature in Celsius
                - 'price': Cost to buy NO
                - 'prob_win': True probability of winning
                - 'ev': Expected value
                
        Returns:
            Dictionary with portfolio analysis including allocations, or None if empty
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
            
            # Use Kelly Criterion helper function
            kelly_full = calculate_kelly_bet(p, price, bankroll_fraction=1.0)
            kelly_safe = calculate_kelly_bet(p, price, bankroll_fraction=config.KELLY_FRACTION) 
            
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
