import pandas as pd
import pandas_ta_classic as ta
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

class IndicatorService:
    @staticmethod
    def compute_indicators(df):
        # #region agent log
        _debug_log("indicator_service.py:7", "compute_indicators - entry", {
            "df_empty": df.empty if hasattr(df, 'empty') else None,
            "df_len": len(df) if hasattr(df, '__len__') else None
        }, "A")
        # #endregion
        try:
            if df.empty or len(df) < 20:
                # #region agent log
                _debug_log("indicator_service.py:9", "insufficient data", {"df_empty": df.empty, "df_len": len(df)}, "A")
                # #endregion
                logger.warning("Insufficient data for indicators")
                return df

            df = df.copy()
            # #region agent log
            _debug_log("indicator_service.py:14", "computing RSI - before", {}, "A")
            # #endregion
            df['RSI'] = ta.rsi(df['Close'], length=14)
            # #region agent log
            _debug_log("indicator_service.py:15", "computing SMA20 - before", {}, "A")
            # #endregion
            df['SMA20'] = ta.sma(df['Close'], length=20)
            # #region agent log
            _debug_log("indicator_service.py:16", "computing SMA50 - before", {}, "A")
            # #endregion
            df['SMA50'] = ta.sma(df['Close'], length=50)
            # #region agent log
            _debug_log("indicator_service.py:17", "computing MACD - before", {}, "A")
            # #endregion
            macd = ta.macd(df['Close'])
            df = df.join(macd)
            # #region agent log
            _debug_log("indicator_service.py:19", "computing BB - before", {}, "A")
            # #endregion
            # pandas-ta-classic bbands returns a DataFrame with columns: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
            bb_result = ta.bbands(df['Close'], length=20)
            if isinstance(bb_result, pd.DataFrame):
                # Extract the columns (BBL=lower, BBM=mid, BBU=upper)
                if 'BBU_20_2.0' in bb_result.columns:
                    df['BB_upper'] = bb_result['BBU_20_2.0']
                    df['BB_mid'] = bb_result['BBM_20_2.0']
                    df['BB_lower'] = bb_result['BBL_20_2.0']
                elif 'BBU' in bb_result.columns:
                    df['BB_upper'] = bb_result['BBU']
                    df['BB_mid'] = bb_result['BBM']
                    df['BB_lower'] = bb_result['BBL']
                else:
                    # Fallback: use first 3 columns (should be lower, mid, upper)
                    cols = list(bb_result.columns[:3])
                    df['BB_lower'] = bb_result[cols[0]]
                    df['BB_mid'] = bb_result[cols[1]] if len(cols) > 1 else bb_result[cols[0]]
                    df['BB_upper'] = bb_result[cols[2]] if len(cols) > 2 else bb_result[cols[0]]
            else:
                # Fallback: try tuple unpacking (for other pandas-ta versions)
                try:
                    df['BB_upper'], df['BB_mid'], df['BB_lower'] = bb_result
                except (ValueError, TypeError):
                    # If all else fails, create dummy BB columns based on SMA
                    df['BB_mid'] = df['SMA20']
                    df['BB_upper'] = df['BB_mid'] * 1.02
                    df['BB_lower'] = df['BB_mid'] * 0.98

            # Improved NaN handling
            df = df.ffill().fillna(50)  # RSI neutral value
            # #region agent log
            _debug_log("indicator_service.py:23", "compute_indicators - success", {
                "has_rsi": 'RSI' in df.columns,
                "has_sma20": 'SMA20' in df.columns,
                "has_macd": 'MACD_12_26_9' in df.columns,
                "has_bb": 'BB_mid' in df.columns
            }, "A")
            # #endregion
            return df
        except Exception as e:
            # #region agent log
            _debug_log("indicator_service.py:25", "compute_indicators - exception", {
                "error": str(e),
                "error_type": type(e).__name__
            }, "A")
            # #endregion
            logger.error(f"Error computing indicators: {str(e)}")
            return df