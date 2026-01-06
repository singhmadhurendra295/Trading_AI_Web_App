#!/usr/bin/env python3
"""
Quick test script to verify symbol fetching works
"""
import sys
from services.nse_service import NSEService
from utils.logger import logger

def test_symbol(symbol):
    print(f"\n{'='*60}")
    print(f"Testing symbol: {symbol}")
    print(f"{'='*60}")
    
    # Test historical data
    print("\n1. Fetching historical data...")
    df = NSEService.get_historical_data(symbol, days=30)
    
    if df.empty:
        print(f"❌ FAILED: No historical data found for {symbol}")
        return False
    else:
        print(f"✓ SUCCESS: Got {len(df)} records")
        print(f"   Columns: {list(df.columns)}")
        print(f"   Date range: {df['Date'].min()} to {df['Date'].max()}")
        print(f"   Latest Close: {df['Close'].iloc[-1]}")
    
    # Test live price
    print("\n2. Fetching live price...")
    price = NSEService.get_live_price(symbol)
    
    if price:
        print(f"✓ SUCCESS: Live price = {price}")
    else:
        print(f"⚠ WARNING: Could not fetch live price (might be outside market hours)")
    
    return True

if __name__ == "__main__":
    # Test common symbols
    test_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "NIFTY"]
    
    if len(sys.argv) > 1:
        # Test symbol provided as argument
        test_symbols = [sys.argv[1].upper()]
    
    print("\n" + "="*60)
    print("NSE Service Symbol Test")
    print("="*60)
    
    results = {}
    for symbol in test_symbols:
        results[symbol] = test_symbol(symbol)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for symbol, passed in results.items():
        status = "✓ PASSED" if passed else "❌ FAILED"
        print(f"{symbol}: {status}")
    
    print("\nNote: Market must be open for live prices to work.")
    print("Historical data should work regardless of market hours.\n")
