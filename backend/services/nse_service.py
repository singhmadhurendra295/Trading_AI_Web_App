try:
    import pandas as pd
except Exception:
    pd = None
import datetime
# Delay importing heavy/natively-compiled packages (nsepython/scipy) until used
# to avoid blocking app import. We'll import them inside the functions below.
from utils.cache import cache
from utils.logger import logger
import traceback
import json
from datetime import datetime as dt

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
                "timestamp": int(dt.now().timestamp() * 1000)
            }) + "\n")
    except: pass
# #endregion

# Try to import yfinance as fallback
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not available - fallback disabled")

class NSEService:
    @staticmethod
    def _symbol_variants(symbol: str):
        s = symbol.upper()
        variants = [s]
        if s not in ["NIFTY", "BANKNIFTY"] and not s.endswith('.NS'):
            variants.append(f"{s}.NS")
        return variants
    @staticmethod
    def is_market_open():
        now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)  # IST
        day = now.weekday()  # 0=Monday, 6=Sunday
        if day >= 5:  # Saturday or Sunday
            return False
        market_open = datetime.time(9, 15)
        market_close = datetime.time(15, 30)
        current_time = now.time()
        return market_open <= current_time <= market_close
    @staticmethod
    def get_historical_data(symbol, days=365):
        # #region agent log
        _debug_log("nse_service.py:39", "get_historical_data - entry", {"symbol": symbol, "days": days}, "B")
        # #endregion
        cache_key = f"historical_{symbol}_{days}"
        cached_data = cache.get(cache_key)
        if cached_data:
            # #region agent log
            _debug_log("nse_service.py:43", "using cached data", {"symbol": symbol}, "B")
            # #endregion
            logger.info(f"Using cached historical data for {symbol}")
            return cached_data

        try:
            if pd is None:
                # #region agent log
                _debug_log("nse_service.py:47", "pandas not available", {"symbol": symbol}, "B")
                # #endregion
                logger.error("pandas is not installed. Historical data fetch requires pandas. Please run: pip install -r requirements.txt")
                raise RuntimeError("Missing dependency: pandas")
            end_date = datetime.datetime.today().strftime('%d-%m-%Y')
            start_date = (datetime.datetime.today() - datetime.timedelta(days=days)).strftime('%d-%m-%Y')

            # Import nsepython here to avoid heavy imports at module load time
            try:
                # #region agent log
                _debug_log("nse_service.py:54", "importing nsepython - before", {"symbol": symbol}, "B")
                # #endregion
                from nsepython import index_history, equity_history
                # #region agent log
                _debug_log("nse_service.py:55", "nsepython imported successfully", {"symbol": symbol}, "B")
                # #endregion
            except Exception as exc:
                # #region agent log
                _debug_log("nse_service.py:57", "nsepython import failed", {"symbol": symbol, "error": str(exc), "yfinance_available": YFINANCE_AVAILABLE}, "B")
                # #endregion
                logger.error(f"Failed to import nsepython for historical data: {str(exc)}")
                # Try yfinance fallback if available
                if YFINANCE_AVAILABLE:
                    logger.info("Using yfinance fallback due to nsepython import error")
                    return NSEService._fetch_yfinance_data(symbol, days)
                return pd.DataFrame()

            # Use symbol variants (e.g., add .NS) and try each until we get data
            df = None
            nse_failed = False
            if symbol in ["NIFTY", "BANKNIFTY"]:
                try:
                    # #region agent log
                    _debug_log("nse_service.py:66", "calling index_history", {"symbol": symbol, "start_date": start_date, "end_date": end_date}, "B")
                    # #endregion
                    df = index_history(symbol if symbol != "NIFTY" else "NIFTY 50", start_date, end_date)
                    # #region agent log
                    _debug_log("nse_service.py:68", "index_history returned", {"symbol": symbol, "df_type": type(df).__name__, "df_is_none": df is None, "df_empty": getattr(df, 'empty', None) if df is not None else None}, "B")
                    # #endregion
                except Exception as exc:
                    # #region agent log
                    _debug_log("nse_service.py:70", "index_history exception", {"symbol": symbol, "error": str(exc), "error_type": type(exc).__name__}, "B")
                    # #endregion
                    logger.debug(f"index_history failed for {symbol}: {str(exc)}")
                    nse_failed = True
            else:
                for variant in NSEService._symbol_variants(symbol):
                    try:
                        # #region agent log
                        _debug_log("nse_service.py:74", "calling equity_history", {"variant": variant, "start_date": start_date, "end_date": end_date}, "B")
                        # #endregion
                        logger.debug(f"Trying historical fetch for {variant}")
                        df = equity_history(variant, "EQ", start_date, end_date)
                        # #region agent log
                        _debug_log("nse_service.py:76", "equity_history returned", {"variant": variant, "df_type": type(df).__name__, "df_is_none": df is None, "df_empty": getattr(df, 'empty', None) if df is not None else None}, "B")
                        # #endregion
                        if df is None:
                            logger.debug(f"equity_history returned None for {variant}")
                            continue
                        # If we got something non-empty, break and use it
                        # Coerce non-DataFrame to DataFrame below
                        nse_failed = False
                        break
                    except Exception as exc:
                        # #region agent log
                        _debug_log("nse_service.py:83", "equity_history exception", {"variant": variant, "error": str(exc), "error_type": type(exc).__name__}, "B")
                        # #endregion
                        logger.debug(f"equity_history failed for {variant}: {str(exc)}")
                        nse_failed = True
                
                # If all variants failed, try yfinance fallback
                if nse_failed and df is None and YFINANCE_AVAILABLE:
                    # #region agent log
                    _debug_log("nse_service.py:120", "all nsepython variants failed, trying yfinance", {"symbol": symbol}, "B")
                    # #endregion
                    try:
                        return NSEService._fetch_yfinance_data(symbol, days)
                    except Exception as yf_exc:
                        # #region agent log
                        _debug_log("nse_service.py:125", "yfinance fallback failed after nse failures", {"symbol": symbol, "error": str(yf_exc)}, "B")
                        # #endregion
                        logger.error(f"yfinance fallback failed: {str(yf_exc)}")

            # Defensive handling: equity_history / index_history may return
            # a DataFrame, dict, list or None depending on the underlying
            # library and remote response. Normalize to a DataFrame and
            # log helpful diagnostics if the result is unexpected.
            if df is None:
                # #region agent log
                _debug_log("nse_service.py:126", "df is None, trying yfinance fallback", {"symbol": symbol, "yfinance_available": YFINANCE_AVAILABLE}, "B")
                # #endregion
                logger.warning(f"No data returned (None) from equity/index API for {symbol}")
                # Try yfinance fallback if available
                if YFINANCE_AVAILABLE:
                    try:
                        return NSEService._fetch_yfinance_data(symbol, days)
                    except Exception as yf_exc:
                        logger.error(f"yfinance fallback failed: {str(yf_exc)}")
                return pd.DataFrame()

            # If the library returned a non-DataFrame, try to coerce
            if not isinstance(df, pd.DataFrame):
                try:
                    logger.debug(f"Coercing {type(df)} to DataFrame for {symbol}")
                    df = pd.DataFrame(df)
                except Exception as exc:
                    logger.error(f"Failed to coerce historical data to DataFrame for {symbol}: {str(exc)}")
                    logger.debug(traceback.format_exc())
                    return pd.DataFrame()

            # At this point we should have a DataFrame. If it's empty, log sample info.
            if df.empty:
                # #region agent log
                _debug_log("nse_service.py:104", "DataFrame empty after normalization, trying yfinance fallback", {"symbol": symbol, "df_shape": list(df.shape) if hasattr(df, 'shape') else None, "df_columns": list(df.columns) if hasattr(df, 'columns') else None, "yfinance_available": YFINANCE_AVAILABLE}, "B")
                # #endregion
                logger.warning(f"No data found for {symbol} after normalization. DataFrame shape: {getattr(df, 'shape', None)} Columns: {list(df.columns)}")
                # Try yfinance fallback if available
                if YFINANCE_AVAILABLE:
                    try:
                        # #region agent log
                        _debug_log("nse_service.py:147", "trying yfinance fallback for empty df", {"symbol": symbol}, "B")
                        # #endregion
                        yf_result = NSEService._fetch_yfinance_data(symbol, days)
                        # #region agent log
                        _debug_log("nse_service.py:150", "yfinance fallback result", {"symbol": symbol, "df_empty": getattr(yf_result, 'empty', None) if yf_result is not None else None, "df_shape": list(yf_result.shape) if yf_result is not None and hasattr(yf_result, 'shape') else None}, "B")
                        # #endregion
                        if not yf_result.empty:
                            return yf_result
                    except Exception as yf_exc:
                        # #region agent log
                        _debug_log("nse_service.py:155", "yfinance fallback failed for empty df", {"symbol": symbol, "error": str(yf_exc)}, "B")
                        # #endregion
                        logger.error(f"yfinance fallback failed: {str(yf_exc)}")
                return pd.DataFrame()

            # Log the columns we received for debugging
            logger.debug(f"DataFrame columns for {symbol}: {list(df.columns)}")

            # Handle Date column with multiple possible column names
            date_col = None
            for col_name in ['CH_TIMESTAMP', 'TIMESTAMP', 'HistoricalDate', 'Date', 'date']:
                if col_name in df.columns:
                    date_col = col_name
                    break
            
            if date_col:
                df['Date'] = pd.to_datetime(df[date_col])
            elif df.index.name and 'date' in df.index.name.lower():
                df['Date'] = pd.to_datetime(df.index)
            else:
                df['Date'] = pd.to_datetime(df.index)

            # Flexible column mapping - handle different API response formats
            column_mapping = {
                'CH_CLOSING_PRICE': 'Close', 'CH_OPENING_PRICE': 'Open',
                'CH_HIGH_PRICE': 'High', 'CH_LOW_PRICE': 'Low',
                'CLOSE': 'Close', 'OPEN': 'Open', 'HIGH': 'High', 'LOW': 'Low',
                'close': 'Close', 'open': 'Open', 'high': 'High', 'low': 'Low',
                'Close': 'Close', 'Open': 'Open', 'High': 'High', 'Low': 'Low'
            }
            
            # Apply column mapping only for columns that exist
            rename_dict = {k: v for k, v in column_mapping.items() if k in df.columns}
            if rename_dict:
                df = df.rename(columns=rename_dict)

            # Handle Volume column
            volume_col = None
            for col_name in ['CH_TRADE_QUANTITY', 'TOTTRDQTY', 'Volume', 'volume', 'VOLUME']:
                if col_name in df.columns:
                    volume_col = col_name
                    break
            
            if volume_col and volume_col != 'Volume':
                df['Volume'] = df[volume_col]
            elif 'Volume' not in df.columns:
                df['Volume'] = 1000000  # Default volume if not available

            # Verify we have the required columns
            required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.error(f"Missing required columns for {symbol}: {missing_columns}. Available columns: {list(df.columns)}")
                return pd.DataFrame()

            # Select and sort the data
            df = df[required_columns].sort_values('Date').reset_index(drop=True)
            
            # Remove any rows with NaN values in critical columns
            df = df.dropna(subset=['Close', 'Open', 'High', 'Low'])
            
            if df.empty:
                logger.warning(f"DataFrame empty after cleaning for {symbol}")
                return pd.DataFrame()

            cache.set(cache_key, df)
            # #region agent log
            _debug_log("nse_service.py:169", "historical data fetched successfully", {"symbol": symbol, "records": len(df)}, "B")
            # #endregion
            logger.info(f"Fetched historical data for {symbol}, {len(df)} records")
            return df
        except Exception as e:
            # #region agent log
            _debug_log("nse_service.py:172", "exception in get_historical_data", {"symbol": symbol, "error": str(e), "error_type": type(e).__name__, "yfinance_available": YFINANCE_AVAILABLE}, "B")
            # #endregion
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            logger.debug(traceback.format_exc())
            
            # Try yfinance as fallback
            if YFINANCE_AVAILABLE:
                # #region agent log
                _debug_log("nse_service.py:178", "trying yfinance fallback", {"symbol": symbol}, "B")
                # #endregion
                logger.info(f"Trying yfinance fallback for {symbol}")
                try:
                    yf_result = NSEService._fetch_yfinance_data(symbol, days)
                    # #region agent log
                    _debug_log("nse_service.py:182", "yfinance fallback success", {"symbol": symbol, "df_empty": getattr(yf_result, 'empty', None) if yf_result is not None else None, "df_shape": list(yf_result.shape) if yf_result is not None and hasattr(yf_result, 'shape') else None}, "B")
                    # #endregion
                    return yf_result
                except Exception as yf_exc:
                    # #region agent log
                    _debug_log("nse_service.py:185", "yfinance fallback failed", {"symbol": symbol, "error": str(yf_exc), "error_type": type(yf_exc).__name__}, "B")
                    # #endregion
                    logger.error(f"yfinance fallback also failed for {symbol}: {str(yf_exc)}")
            
            return pd.DataFrame()
    
    @staticmethod
    def _fetch_yfinance_data(symbol, days=365):
        """Fallback method to fetch data using yfinance"""
        try:
            # yfinance uses .NS suffix for NSE stocks
            ticker_symbol = symbol if symbol.endswith('.NS') else f"{symbol}.NS"
            
            # Special handling for indices
            if symbol == "NIFTY":
                ticker_symbol = "^NSEI"
            elif symbol == "BANKNIFTY":
                ticker_symbol = "^NSEBANK"
            
            logger.debug(f"Fetching from yfinance: {ticker_symbol}")
            
            # Calculate date range
            end_date = datetime.datetime.today()
            start_date = end_date - datetime.timedelta(days=days)
            
            # Download data
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                logger.warning(f"yfinance returned empty DataFrame for {ticker_symbol}")
                return pd.DataFrame()
            
            # yfinance returns data with index as date
            df = df.reset_index()
            
            # Rename columns to match our format
            df = df.rename(columns={'Date': 'Date'})
            
            # Ensure we have required columns
            required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_columns):
                logger.error(f"yfinance data missing required columns for {ticker_symbol}")
                return pd.DataFrame()
            
            df = df[required_columns].dropna()
            logger.info(f"Successfully fetched {len(df)} records from yfinance for {symbol}")
            
            return df
        except Exception as e:
            logger.error(f"Error in yfinance fallback for {symbol}: {str(e)}")
            logger.debug(traceback.format_exc())
            return pd.DataFrame()

    @staticmethod
    def get_live_price(symbol):
        cache_key = f"live_{symbol}"
        cached_price = cache.get(cache_key)
        if cached_price:
            return cached_price

        try:
            if pd is None:
                # live price doesn't strictly require pandas, but our code paths
                # and caching expect pandas to be available for consistent types.
                logger.error("pandas is not installed. Live price fetch may fail. Please run: pip install -r requirements.txt")
                raise RuntimeError("Missing dependency: pandas")
            # Try variants for equity symbols (some APIs require .NS)
            try:
                from nsepython import nse_fno, nse_eq
            except Exception as exc:
                logger.error(f"Failed to import nsepython for live price: {str(exc)}")
                return None
            if symbol in ["NIFTY", "BANKNIFTY"]:
                quote = nse_fno(symbol)
                price = quote['underlyingValue']
            else:
                price = None
                for variant in NSEService._symbol_variants(symbol):
                    try:
                        quote = nse_eq(variant)
                        # quote may be dict-like; attempt to read lastPrice
                        price = quote.get('priceInfo', {}).get('lastPrice') if isinstance(quote, dict) else None
                        if price is None:
                            # Some nse_eq implementations return simple dicts with price
                            price = quote.get('lastPrice') if isinstance(quote, dict) else None
                        if price is not None:
                            logger.debug(f"Live price found for {variant}: {price}")
                            break
                    except Exception as exc:
                        logger.debug(f"nse_eq failed for {variant}: {str(exc)}")

                if price is None:
                    raise ValueError(f"No live price found for {symbol}")

            cache.set(cache_key, price)
            return price
        except Exception as e:
            logger.error(f"Error fetching live price for {symbol}: {str(e)}")
            return None

    @staticmethod
    def get_cheapest_options(symbol, timeframe='weekly'):
        cache_key = f"options_{symbol}_{timeframe}"
        cached_options = cache.get(cache_key)
        if cached_options:
            return cached_options

        try:
            # Determine expiry based on timeframe
            if timeframe == 'daily':
                expiry = "latest"  # Assuming daily options if available
            elif timeframe == 'weekly':
                expiry = "next"  # Next weekly expiry
            elif timeframe == 'monthly':
                expiry = "monthly"  # Monthly expiry
            else:
                expiry = "latest"

            # Import oi_chain_builder lazily to avoid heavy imports at startup
            try:
                from nsepython import oi_chain_builder
            except Exception as exc:
                logger.error(f"Failed to import nsepython for OI chain: {str(exc)}")
                return None, None, None, None, None

            # Try symbol variants for options chain as some APIs expect .NS
            oi_data = None
            ltp = None
            for variant in NSEService._symbol_variants(symbol):
                try:
                    logger.debug(f"Trying OI chain for {variant} expiry={expiry}")
                    maybe_oi, maybe_ltp, _ = oi_chain_builder(variant, expiry=expiry, oi_mode="full")
                    if maybe_oi is None:
                        logger.debug(f"oi_chain_builder returned None for {variant}")
                        continue
                    # Coerce DataFrame if needed
                    if not isinstance(maybe_oi, pd.DataFrame):
                        try:
                            maybe_oi = pd.DataFrame(maybe_oi)
                        except Exception:
                            logger.debug(f"Failed to coerce oi data for {variant}")
                            continue

                    if maybe_oi.empty:
                        logger.debug(f"OI data empty for {variant}")
                        continue

                    oi_data = maybe_oi
                    ltp = maybe_ltp
                    break
                except Exception as exc:
                    logger.debug(f"oi_chain_builder failed for {variant}: {str(exc)}")

            if oi_data is None or (hasattr(oi_data, 'empty') and oi_data.empty):
                logger.warning(f"No OI data for {symbol} {timeframe}")
                return None, None, None, None, None

            calls = oi_data[oi_data['optionType'] == 'CE'] if 'optionType' in oi_data.columns else oi_data.filter(like='CE')
            puts = oi_data[oi_data['optionType'] == 'PE'] if 'optionType' in oi_data.columns else oi_data.filter(like='PE')

            cheapest_call = calls[calls['askPrice'] > 0]['askPrice'].min() if not calls.empty else None
            call_strike = calls[calls['askPrice'] == cheapest_call]['strikePrice'].iloc[0] if cheapest_call else None

            cheapest_put = puts[puts['askPrice'] > 0]['askPrice'].min() if not puts.empty else None
            put_strike = puts[puts['askPrice'] == cheapest_put]['strikePrice'].iloc[0] if cheapest_put else None

            options_data = (cheapest_call, call_strike, cheapest_put, put_strike, ltp)
            cache.set(cache_key, options_data)
            return options_data
        except Exception as e:
            logger.error(f"Error fetching options for {symbol} {timeframe}: {str(e)}")
            return None, None, None, None, None
