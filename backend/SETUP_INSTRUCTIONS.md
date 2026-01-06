# Trading App Backend - Setup Instructions

## Problem Fixed
The "Symbol not found or invalid symbol" error has been resolved with the following improvements:

1. **Flexible column mapping** - Handles different NSE API response formats
2. **yfinance fallback** - Automatically uses yfinance if nsepython fails
3. **Better error handling** - Detailed logging for troubleshooting
4. **Robust data validation** - Ensures data integrity before processing

## Installation Steps

### 1. Install Dependencies

#### Option A: Using pip (Recommended)
```bash
# Navigate to backend folder
cd trading-app-full\backend

# Install requirements
pip install flask flask-cors nsepython yfinance pandas numpy tensorflow pandas-ta-classic scikit-learn
```

#### Option B: From requirements.txt
```bash
cd trading-app-full\backend
pip install -r requirements.txt
```

### 2. Verify Installation
```bash
python -c "import pandas, flask, nsepython, yfinance; print('All dependencies installed successfully!')"
```

### 3. Run the Application
```bash
# Start the Flask server
python app.py
```

The server will start at `http://localhost:5000`

## Testing the API

### Test with curl
```bash
# Test RELIANCE
curl http://localhost:5000/analyze/RELIANCE

# Test TCS
curl http://localhost:5000/analyze/TCS

# Test NIFTY
curl http://localhost:5000/analyze/NIFTY
```

### Test with Python script
```bash
python test_symbol.py RELIANCE
```

## Common Symbols to Test
- **Large Cap Stocks**: RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, WIPRO, LT
- **Indices**: NIFTY, BANKNIFTY

## Troubleshooting

### 1. "Market is closed" error
- This is expected outside trading hours (Mon-Fri 9:15 AM - 3:30 PM IST)
- The API will still work but with cached or historical data

### 2. nsepython fails but yfinance works
- This is normal - nsepython can be unreliable
- The app automatically falls back to yfinance
- Check logs to see which data source was used

### 3. Both APIs fail
- NSE website might be blocking requests
- Try a different symbol
- Check your internet connection
- Wait a few minutes and retry (rate limiting)

### 4. Missing dependencies
```bash
pip install --upgrade pip
pip install flask flask-cors nsepython yfinance pandas numpy
```

## Logging

Enable detailed logging by checking the console output when running `python app.py`. You'll see:
- Which API is being used (nsepython or yfinance)
- Column names received from APIs
- Any errors encountered
- Data fetching success/failure

## API Endpoints

### 1. Analyze Symbol
```
GET /analyze/<symbol>
```
Returns trading recommendations with ML predictions

**Example Response:**
```json
{
  "symbol": "RELIANCE",
  "currentPrice": 2456.75,
  "signal": "BUY",
  "mlPredictions": {...},
  "averagePrediction": 2478.30,
  "direction": "UP",
  "bestModel": "LSTM",
  "cheapestOptions": {...}
}
```

### 2. Live Price
```
GET /live/<symbol>
```
Returns current price for the symbol

### 3. Options Data
```
GET /options/<symbol>/<timeframe>
```
Timeframes: daily, weekly, monthly

## Notes

- **Data Source Priority**: nsepython → yfinance fallback
- **Caching**: Data is cached for 5 minutes to reduce API calls
- **Market Hours**: Some features only work during market hours
- **Historical Data**: Always available regardless of market hours
