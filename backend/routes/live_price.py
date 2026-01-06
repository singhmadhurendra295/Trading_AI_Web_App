from flask import Blueprint, jsonify
from services.nse_service import NSEService
from utils.logger import logger

live_price_bp = Blueprint('live_price', __name__)

@live_price_bp.route('/live-price/<symbol>')
def live_price(symbol):
    symbol = symbol.upper()
    logger.info(f"Fetching live price for: {symbol}")

    if not NSEService.is_market_open():
        return jsonify({"error": "Market is closed. No live prices available."}), 503

    price = NSEService.get_live_price(symbol)
    if price is None:
        return jsonify({"error": "Unable to fetch live price"}), 500

    return jsonify({"symbol": symbol, "currentPrice": round(price, 2)})