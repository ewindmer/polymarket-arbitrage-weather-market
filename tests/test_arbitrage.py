"""
Unit tests for arbitrage analysis functions.
"""
import unittest
import math
from analysis.arbitrage import (
    parse_event_title,
    parse_bucket_question,
    to_celsius,
    calculate_probability_range,
    get_market_prices,
    calculate_ev_for_event
)


class TestParseEventTitle(unittest.TestCase):
    def test_valid_title(self):
        result = parse_event_title("Highest temperature in New York on January 15?")
        self.assertIsNotNone(result)
        self.assertEqual(result["city"], "New York")
        # Date should be in YYYY-MM-DD format
        self.assertRegex(result["date"], r"\d{4}-01-15")
        
    def test_nyc_abbreviation(self):
        result = parse_event_title("Highest temperature in NYC on January 15?")
        self.assertIsNotNone(result)
        self.assertEqual(result["city"], "New York")
        
    def test_invalid_title(self):
        result = parse_event_title("Invalid title")
        self.assertIsNone(result)
        
    def test_case_insensitive(self):
        result = parse_event_title("HIGHEST TEMPERATURE IN LONDON ON FEBRUARY 20?")
        self.assertIsNotNone(result)
        self.assertEqual(result["city"], "London")


class TestParseBucketQuestion(unittest.TestCase):
    def test_below_fahrenheit(self):
        result = parse_bucket_question("Will it be 41°F or below?")
        self.assertIsNotNone(result)
        self.assertEqual(result["min"], -999)
        self.assertEqual(result["max"], 41)
        self.assertEqual(result["unit"], "F")
        
    def test_above_fahrenheit(self):
        result = parse_bucket_question("Will it be 52°F or higher?")
        self.assertIsNotNone(result)
        self.assertEqual(result["min"], 52)
        self.assertEqual(result["max"], 999)
        self.assertEqual(result["unit"], "F")
        
    def test_between_range(self):
        result = parse_bucket_question("Will it be between 42-43°F?")
        self.assertIsNotNone(result)
        self.assertEqual(result["min"], 42)
        self.assertEqual(result["max"], 43)
        self.assertEqual(result["unit"], "F")
        
    def test_celsius(self):
        result = parse_bucket_question("Will it be 5°C or below?")
        self.assertIsNotNone(result)
        self.assertEqual(result["unit"], "C")
        
    def test_invalid_question(self):
        result = parse_bucket_question("Invalid question")
        self.assertIsNone(result)


class TestToCelsius(unittest.TestCase):
    def test_fahrenheit_to_celsius(self):
        # 32F = 0C
        self.assertAlmostEqual(to_celsius(32, "F"), 0.0, places=1)
        # 212F = 100C
        self.assertAlmostEqual(to_celsius(212, "F"), 100.0, places=1)
        
    def test_celsius_unchanged(self):
        self.assertEqual(to_celsius(25, "C"), 25.0)
        
    def test_freezing_point(self):
        self.assertAlmostEqual(to_celsius(0, "F"), -17.78, places=1)


class TestCalculateProbabilityRange(unittest.TestCase):
    def test_symmetric_range(self):
        # For a normal distribution centered at 0 with std=1
        # Probability of -1 to 1 should be ~68%
        prob = calculate_probability_range(0, -1, 1, std_dev=1.0)
        self.assertAlmostEqual(prob, 0.6827, places=3)
        
    def test_full_range(self):
        # Probability of -inf to +inf should be 1.0
        prob = calculate_probability_range(10, -999, 999, std_dev=1.0)
        self.assertAlmostEqual(prob, 1.0, places=2)
        
    def test_single_point(self):
        # Probability of exact point should be very small
        prob = calculate_probability_range(10, 10, 10.1, std_dev=1.0)
        self.assertGreater(prob, 0)
        self.assertLess(prob, 0.1)


class TestGetMarketPrices(unittest.TestCase):
    def test_best_ask_bid(self):
        market = {
            "bestAsk": "0.65",
            "bestBid": "0.60"
        }
        price_yes, price_no = get_market_prices(market)
        self.assertEqual(price_yes, 0.65)
        self.assertEqual(price_no, 0.40)  # 1.0 - 0.60
        
    def test_outcome_prices_fallback(self):
        market = {
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["0.70", "0.30"]'
        }
        price_yes, price_no = get_market_prices(market)
        self.assertEqual(price_yes, 0.70)
        self.assertEqual(price_no, 0.30)
        
    def test_no_data(self):
        market = {}
        price_yes, price_no = get_market_prices(market)
        self.assertIsNone(price_yes)
        self.assertIsNone(price_no)
        
    def test_invalid_json(self):
        market = {
            "outcomes": "invalid json",
            "outcomePrices": '["0.70"]'
        }
        price_yes, price_no = get_market_prices(market)
        self.assertIsNone(price_yes)
        self.assertIsNone(price_no)


class TestCalculateEVForEvent(unittest.TestCase):
    def test_positive_ev_long(self):
        event = {
            "title": "Highest temperature in New York on January 15?",
            "markets": [
                {
                    "id": "1",
                    "question": "Will it be 41°F or below?",
                    "bestAsk": "0.20",
                    "bestBid": "0.18"
                }
            ]
        }
        # Forecast is 5.9C (42.6F), so probability of <= 41F should be low
        # But if market price is 0.20 and true prob is higher, we get +EV
        result = calculate_ev_for_event(event, 5.9, 0.0)
        self.assertIsNotNone(result)
        self.assertIn("bets", result)
        
    def test_no_positive_ev(self):
        event = {
            "title": "Highest temperature in New York on January 15?",
            "markets": [
                {
                    "id": "1",
                    "question": "Will it be 100°F or higher?",
                    "bestAsk": "0.99",
                    "bestBid": "0.98"
                }
            ]
        }
        # Very unlikely outcome with high price = no +EV
        result = calculate_ev_for_event(event, 5.9, 0.0)
        self.assertIsNotNone(result)
        # Should have no bets if EV threshold not met
        self.assertIsInstance(result["bets"], list)


if __name__ == "__main__":
    unittest.main()
