from flask import Blueprint, jsonify
from services.nse_service import NSEService
from models.predictor import PricePredictor
from utils.logger import logger
import json
import os
from datetime import datetime

# #region agent log
def _debug_log(location, message, data, hypothesis_id=None):
    log_path = r"d:\AI_STUFF\trading-app-full\.cursor\debug.log"
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": hypothesis_id or "A",
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(datetime.now().timestamp() * 1000)
            }) + "\n")
    except: pass
# #endregion

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/analyze/<symbol>')
def analyze(symbol):
    symbol = symbol.upper()
    logger.info(f"Analyzing symbol: {symbol}")
    # #region agent log
    _debug_log("analysis.py:10", "analyze endpoint called", {"symbol": symbol}, "A")
    # #endregion

    # #region agent log
    market_open = NSEService.is_market_open()
    _debug_log("analysis.py:13", "market hours check", {"is_open": market_open, "symbol": symbol}, "E")
    # #endregion
    # Note: Market hours check bypassed to allow testing with yfinance fallback
    # Historical data is always available regardless of market hours
    # if not market_open:
    #     # #region agent log
    #     _debug_log("analysis.py:14", "market closed - early return", {"symbol": symbol}, "E")
    #     # #endregion
    #     return jsonify({"error": "Market is closed. Trading hours: Mon-Fri 9:15 AM - 3:30 PM IST"}), 503

    try:
        # #region agent log
        _debug_log("analysis.py:17", "fetching historical data - before", {"symbol": symbol}, "B")
        # #endregion
        df = NSEService.get_historical_data(symbol)
        # #region agent log
        _debug_log("analysis.py:18", "fetching historical data - after", {
            "symbol": symbol, 
            "df_is_none": df is None,
            "df_empty": getattr(df, 'empty', True) if df is not None else None,
            "df_shape": list(df.shape) if df is not None and hasattr(df, 'shape') else None
        }, "B")
        # #endregion
    except RuntimeError as re:
        # Missing dependency or other runtime problem in service
        msg = str(re).lower()
        # #region agent log
        _debug_log("analysis.py:19", "RuntimeError caught", {"symbol": symbol, "error": str(re), "msg": msg}, "B")
        # #endregion
        if 'pandas' in msg:
            return jsonify({"error": "Server missing dependency: pandas. Run pip install -r requirements.txt"}), 500
        logger.error(f"Runtime error fetching historical data for {symbol}: {str(re)}")
        return jsonify({"error": "Internal server error"}), 500
    except Exception as e:
        # #region agent log
        _debug_log("analysis.py:25", "Exception caught in data fetch", {"symbol": symbol, "error": str(e), "type": type(e).__name__}, "B")
        # #endregion
        logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

    if df is None or getattr(df, 'empty', True):
        # #region agent log
        _debug_log("analysis.py:29", "data validation failed", {"symbol": symbol, "df_is_none": df is None, "df_empty": getattr(df, 'empty', True) if df is not None else None}, "B")
        # #endregion
        return jsonify({"error": "Symbol not found or invalid symbol"}), 404

    # #region agent log
    current_price = df['Close'].iloc[-1]
    _debug_log("analysis.py:32", "current price extracted", {"symbol": symbol, "current_price": float(current_price)}, "C")
    # #endregion

    # #region agent log
    _debug_log("analysis.py:34", "creating predictor - before", {"symbol": symbol}, "C")
    # #endregion
    predictor = PricePredictor()
    # #region agent log
    _debug_log("analysis.py:35", "getting predictions - before", {"symbol": symbol}, "C")
    # #endregion
    ml_results = predictor.get_predictions(df)
    # #region agent log
    _debug_log("analysis.py:35", "getting predictions - after", {"symbol": symbol, "ml_results_keys": list(ml_results.keys()) if ml_results else None}, "C")
    # #endregion

    # Get options for different timeframes
    # #region agent log
    _debug_log("analysis.py:37", "fetching options - before", {"symbol": symbol}, "D")
    # #endregion
    options = {}
    for timeframe in ['daily', 'weekly', 'monthly']:
        # #region agent log
        _debug_log("analysis.py:40", "fetching options for timeframe", {"symbol": symbol, "timeframe": timeframe}, "D")
        # #endregion
        cc, cs, cp, ps, ltp = NSEService.get_cheapest_options(symbol, timeframe)
        # #region agent log
        _debug_log("analysis.py:40", "options fetched", {"symbol": symbol, "timeframe": timeframe, "cc": cc, "cs": cs, "cp": cp, "ps": ps, "ltp": ltp}, "D")
        # #endregion
        options[timeframe] = {
            "callPrice": round(cc, 2) if cc else "N/A",
            "callStrike": cs or "N/A",
            "putPrice": round(cp, 2) if cp else "N/A",
            "putStrike": ps or "N/A",
            "underlyingPrice": round(ltp, 2) if ltp else "N/A"
        }

    # #region agent log
    _debug_log("analysis.py:49", "returning response - before", {"symbol": symbol}, "A")
    # #endregion
    return jsonify({
        "symbol": symbol,
        "currentPrice": round(current_price, 2),
        "signal": ml_results["signal"],
        "mlPredictions": ml_results["predictions"],
        "averagePrediction": ml_results["average"],
        "direction": ml_results["direction"],
        "bestModel": ml_results["best_model"],
        "cheapestOptions": options
    })

@analysis_bp.route('/options/<symbol>/<timeframe>')
def get_options(symbol, timeframe):
    symbol = symbol.upper()
    if timeframe not in ['daily', 'weekly', 'monthly']:
        return jsonify({"error": "Invalid timeframe"}), 400

    cc, cs, cp, ps, ltp = NSEService.get_cheapest_options(symbol, timeframe)

    return jsonify({
        "symbol": symbol,
        "timeframe": timeframe,
        "cheapestCall": {
            "price": round(cc, 2) if cc else "N/A",
            "strike": cs or "N/A"
        },
        "cheapestPut": {
            "price": round(cp, 2) if cp else "N/A",
            "strike": ps or "N/A"
        },
        "underlyingPrice": round(ltp, 2) if ltp else "N/A"
    })