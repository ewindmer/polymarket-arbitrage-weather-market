# Quick Start Guide

## Yes, the bot is ready to run! 🚀

### Prerequisites Check
- ✅ Python 3.8+ installed
- ✅ Dependencies: `requests` and `numpy`
- ✅ Internet connection for API calls

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Test in Demo Mode (Recommended first step):**
   ```bash
   python main.py --demo
   ```
   This runs with mock data and doesn't require API access.

3. **Run Live Mode:**
   ```bash
   python main.py
   ```
   This fetches real data from Polymarket and Open-Meteo APIs.

### What the Bot Does

1. **Fetches** weather markets from Polymarket
2. **Gets** weather forecasts from Open-Meteo
3. **Calculates** Expected Value (EV) for each market
4. **Recommends** profitable betting opportunities:
   - Long bets (Bet YES on undervalued outcomes)
   - Short bets (Bet NO on overvalued outcomes)
   - Blanket strategies (Cover multiple buckets)
   - Portfolio analysis with Kelly Criterion sizing

### Expected Output

The bot will:
- Log all activities with timestamps
- Show found events and their analysis
- Display +EV opportunities with probabilities and expected returns
- Provide portfolio recommendations for multiple shorts

### Troubleshooting

- **No events found**: Check if there are active weather markets on Polymarket
- **API errors**: Verify internet connection and API availability
- **Import errors**: Ensure all dependencies are installed (`pip install -r requirements.txt`)

### Configuration

All settings are in `config.py`:
- `FORECAST_STD_DEV_C`: Forecast uncertainty (default: 1.5°C)
- `EV_THRESHOLD_LONG`: Minimum EV for long bets (default: 0.05)
- `EV_THRESHOLD_SHORT`: Minimum EV for short bets (default: 0.10)
- `KELLY_FRACTION`: Fractional Kelly (default: 0.25 = quarter Kelly)

### Running Tests

```bash
python -m unittest discover tests
```

### Important Notes

⚠️ **This bot does NOT execute trades automatically** - it only identifies opportunities. You must manually place bets on Polymarket.

⚠️ **Educational/Research Use Only** - Betting involves financial risk.
