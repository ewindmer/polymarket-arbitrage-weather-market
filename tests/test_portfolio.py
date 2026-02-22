"""
Unit tests for portfolio analysis functions.
"""
import unittest
from analysis.portfolio import calculate_kelly_bet, PortfolioAnalyzer


class TestCalculateKellyBet(unittest.TestCase):
    def test_positive_ev_bet(self):
        # Probability 0.6, price 0.5 -> positive EV
        kelly = calculate_kelly_bet(0.6, 0.5, bankroll_fraction=1.0)
        self.assertGreater(kelly, 0)
        # Full Kelly: (0.6 - 0.5) / (1 - 0.5) = 0.2
        self.assertAlmostEqual(kelly, 0.2, places=3)
        
    def test_negative_ev_bet(self):
        # Probability 0.4, price 0.5 -> negative EV
        kelly = calculate_kelly_bet(0.4, 0.5, bankroll_fraction=1.0)
        self.assertEqual(kelly, 0.0)  # Should be 0 or negative, capped at 0
        
    def test_fractional_kelly(self):
        # Quarter Kelly
        kelly_full = calculate_kelly_bet(0.6, 0.5, bankroll_fraction=1.0)
        kelly_quarter = calculate_kelly_bet(0.6, 0.5, bankroll_fraction=0.25)
        self.assertAlmostEqual(kelly_quarter, kelly_full * 0.25, places=3)
        
    def test_edge_cases(self):
        # Price = 0 or 1 should return 0
        self.assertEqual(calculate_kelly_bet(0.5, 0.0, bankroll_fraction=1.0), 0.0)
        self.assertEqual(calculate_kelly_bet(0.5, 1.0, bankroll_fraction=1.0), 0.0)
        
    def test_capped_at_one(self):
        # Very high probability, very low price
        kelly = calculate_kelly_bet(0.99, 0.01, bankroll_fraction=1.0)
        self.assertLessEqual(kelly, 1.0)


class TestPortfolioAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = PortfolioAnalyzer(forecast_mean=10.0, forecast_std=2.0)
        
    def test_simulate_portfolio_single_long(self):
        bets = [{
            "min_c": 8.0,
            "max_c": 12.0,
            "type": "LONG",
            "price": 0.5
        }]
        result = self.analyzer.simulate_portfolio(bets, samples=100)
        self.assertIn("expected_pnl", result)
        self.assertIn("prob_profit", result)
        self.assertIn("min_pnl", result)
        self.assertIn("max_pnl", result)
        
    def test_simulate_portfolio_single_short(self):
        bets = [{
            "min_c": 8.0,
            "max_c": 12.0,
            "type": "SHORT",
            "price": 0.3
        }]
        result = self.analyzer.simulate_portfolio(bets, samples=100)
        self.assertIn("expected_pnl", result)
        # Short wins when temp is outside range
        # With mean=10, std=2, temp outside 8-12 has reasonable probability
        self.assertGreaterEqual(result["prob_profit"], 0)
        
    def test_simulate_portfolio_multiple_bets(self):
        bets = [
            {
                "min_c": 8.0,
                "max_c": 10.0,
                "type": "LONG",
                "price": 0.4
            },
            {
                "min_c": 10.0,
                "max_c": 12.0,
                "type": "LONG",
                "price": 0.4
            }
        ]
        result = self.analyzer.simulate_portfolio(bets, samples=100)
        self.assertIn("expected_pnl", result)
        # Combined probability should be higher than individual
        self.assertGreaterEqual(result["prob_profit"], 0)
        
    def test_recommend_short_portfolio(self):
        short_candidates = [
            {
                "bucket": "0 to 5 F",
                "min_c": -17.8,  # 0F
                "max_c": -15.0,  # 5F
                "price": 0.2,
                "prob_win": 0.85,
                "ev": 0.65
            },
            {
                "bucket": "50 to 55 F",
                "min_c": 10.0,  # 50F
                "max_c": 12.8,  # 55F
                "price": 0.3,
                "prob_win": 0.75,
                "ev": 0.45
            }
        ]
        result = self.analyzer.recommend_short_portfolio(short_candidates)
        self.assertIsNotNone(result)
        self.assertIn("combined_prob_profit", result)
        self.assertIn("expected_total_return", result)
        self.assertIn("allocations", result)
        self.assertEqual(len(result["allocations"]), 2)


if __name__ == "__main__":
    unittest.main()
