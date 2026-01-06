from flask import Blueprint, jsonify, request
from utils.logger import logger
import traceback

search_bp = Blueprint('search', __name__)

@search_bp.route('/search-symbols')
def search_symbols():
    """Search for NSE stock symbols and indices dynamically"""
    query = request.args.get('q', '').upper().strip()
    limit = int(request.args.get('limit', 20))
    
    if not query or len(query) < 1:
        return jsonify({"symbols": []})
    
    try:
        symbols = []
        
        # Get indices from nsepython
        try:
            from nsepython import nse_get_index_list, fnolist
            
            # Get NSE indices
            indices = nse_get_index_list()
            if indices:
                if isinstance(indices, list):
                    for idx in indices:
                        if isinstance(idx, dict):
                            idx_name = idx.get('indexSymbol', idx.get('symbol', ''))
                        elif isinstance(idx, str):
                            idx_name = idx
                        else:
                            continue
                        
                        if query in idx_name.upper():
                            symbols.append({
                                "symbol": idx_name,
                                "name": idx_name,
                                "type": "index"
                            })
                elif isinstance(indices, dict):
                    for idx_name in indices.keys():
                        if query in idx_name.upper():
                            symbols.append({
                                "symbol": idx_name,
                                "name": idx_name,
                                "type": "index"
                            })
            
            # Get FNO (Futures & Options) list - these are actively traded stocks
            fno_list = fnolist()
            if fno_list:
                if isinstance(fno_list, list):
                    for stock in fno_list:
                        if isinstance(stock, dict):
                            stock_symbol = stock.get('symbol', stock.get('SYMBOL', ''))
                            stock_name = stock.get('name', stock.get('NAME', stock_symbol))
                        elif isinstance(stock, str):
                            stock_symbol = stock
                            stock_name = stock
                        else:
                            continue
                        
                        if query in stock_symbol.upper() or (isinstance(stock_name, str) and query in stock_name.upper()):
                            symbols.append({
                                "symbol": stock_symbol,
                                "name": stock_name if isinstance(stock_name, str) else stock_symbol,
                                "type": "equity"
                            })
                elif isinstance(fno_list, dict):
                    for stock_symbol in fno_list.keys():
                        if query in stock_symbol.upper():
                            symbols.append({
                                "symbol": stock_symbol,
                                "name": stock_symbol,
                                "type": "equity"
                            })
        
        except Exception as e:
            logger.error(f"Error fetching symbols from nsepython: {str(e)}")
            logger.debug(traceback.format_exc())
        
        # Add common indices if not found
        common_indices = ["NIFTY", "BANKNIFTY", "NIFTYIT", "NIFTYPHARMA", "NIFTYFMCG", "NIFTYAUTO"]
        for idx in common_indices:
            if query in idx and not any(s['symbol'] == idx for s in symbols):
                symbols.append({
                    "symbol": idx,
                    "name": idx,
                    "type": "index"
                })
        
        # Add popular stocks if query matches
        popular_stocks = [
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
            "BHARTIARTL", "SBIN", "BAJFINANCE", "KOTAKBANK", "LT", "HCLTECH",
            "AXISBANK", "ASIANPAINT", "MARUTI", "TITAN", "ULTRACEMCO", "NESTLEIND",
            "WIPRO", "ONGC", "POWERGRID", "NTPC", "TECHM", "SUNPHARMA", "TATAMOTORS"
        ]
        
        for stock in popular_stocks:
            if query in stock and not any(s['symbol'] == stock for s in symbols):
                symbols.append({
                    "symbol": stock,
                    "name": stock,
                    "type": "equity"
                })
        
        # Sort: exact matches first, then by type (indices first), then alphabetically
        def sort_key(s):
            symbol = s['symbol']
            exact_match = 0 if symbol.startswith(query) else 1
            type_order = 0 if s['type'] == 'index' else 1
            return (exact_match, type_order, symbol)
        
        symbols.sort(key=sort_key)
        
        # Limit results
        symbols = symbols[:limit]
        
        return jsonify({
            "symbols": symbols,
            "count": len(symbols)
        })
    
    except Exception as e:
        logger.error(f"Error in search_symbols: {str(e)}")
        logger.debug(traceback.format_exc())
        return jsonify({"error": "Internal server error", "symbols": []}), 500
