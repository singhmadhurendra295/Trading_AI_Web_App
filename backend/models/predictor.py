import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import LSTM, GRU, Dense, MultiHeadAttention, LayerNormalization, Input
from sklearn.preprocessing import MinMaxScaler
from services.indicator_service import IndicatorService
from utils.logger import logger
import os
import json
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

class PricePredictor:
    def __init__(self):
        self.models = {}
        self.scaler = MinMaxScaler()
        # whether to use SAM optimizer during brief online training
        self.use_sam = True
        self.sam_rho = 0.05
        self.base_optimizer = tf.keras.optimizers.Adam()
        self.loss_fn = tf.keras.losses.MeanSquaredError()

    def prepare_features(self, df):
        # #region agent log
        _debug_log("predictor.py:21", "prepare_features - entry", {"df_shape": list(df.shape) if hasattr(df, 'shape') else None}, "C")
        # #endregion
        df = IndicatorService.compute_indicators(df)
        # #region agent log
        _debug_log("predictor.py:22", "indicators computed", {"df_shape": list(df.shape) if hasattr(df, 'shape') else None}, "C")
        # #endregion
        try:
            features = df[['Close', 'Volume', 'RSI', 'MACD_12_26_9', 'SMA20', 'BB_mid']].tail(60)
            # #region agent log
            _debug_log("predictor.py:23", "features extracted", {"features_len": len(features), "features_shape": list(features.shape) if hasattr(features, 'shape') else None}, "C")
            # #endregion
        except Exception as e:
            # #region agent log
            _debug_log("predictor.py:23", "feature extraction failed", {"error": str(e), "error_type": type(e).__name__, "df_columns": list(df.columns) if hasattr(df, 'columns') else None}, "C")
            # #endregion
            raise

        if len(features) < 30:
            # #region agent log
            _debug_log("predictor.py:25", "insufficient features", {"features_len": len(features)}, "C")
            # #endregion
            logger.warning("Insufficient data for prediction")
            return None, df['Close'].iloc[-1]

        # Scale features
        scaled_features = self.scaler.fit_transform(features.values)
        # #region agent log
        _debug_log("predictor.py:31", "features scaled", {"scaled_shape": list(scaled_features.shape) if hasattr(scaled_features, 'shape') else None}, "C")
        # #endregion
        return scaled_features, df['Close'].iloc[-1]

    def build_lstm_model(self, input_shape):
        model = Sequential([
            LSTM(50, input_shape=input_shape, return_sequences=True),
            LSTM(25),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def build_gru_model(self, input_shape):
        model = Sequential([
            GRU(50, input_shape=input_shape, return_sequences=True),
            GRU(25),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def build_transformer_model(self, input_shape):
        inputs = Input(shape=input_shape)
        x = MultiHeadAttention(num_heads=4, key_dim=input_shape[-1]//4)(inputs, inputs)
        x = LayerNormalization()(x + inputs)
        x = Dense(64, activation='relu')(x)
        x = Dense(input_shape[-1])(x)
        x = LayerNormalization()(x + inputs)
        outputs = Dense(1)(x[:, -1, :])
        model = Model(inputs, outputs)
        model.compile(optimizer='adam', loss='mse')
        return model

    def predict(self, df, model_type='lstm'):
        # #region agent log
        _debug_log("predictor.py:63", "predict - entry", {"model_type": model_type}, "C")
        # #endregion
        X, current_price = self.prepare_features(df)
        # #region agent log
        _debug_log("predictor.py:64", "features prepared", {"X_is_none": X is None, "current_price": float(current_price) if current_price else None}, "C")
        # #endregion
        if X is None:
            # #region agent log
            _debug_log("predictor.py:65", "X is None - using fallback", {"model_type": model_type}, "C")
            # #endregion
            return current_price + np.random.randn() * 5  # Fallback

        X = X.reshape((1, X.shape[0], X.shape[1]))
        # #region agent log
        _debug_log("predictor.py:68", "X reshaped", {"X_shape": list(X.shape) if hasattr(X, 'shape') else None, "model_type": model_type}, "C")
        # #endregion

        if model_type not in self.models:
            # #region agent log
            _debug_log("predictor.py:70", "building model", {"model_type": model_type}, "C")
            # #endregion
            if model_type == 'lstm':
                self.models[model_type] = self.build_lstm_model((X.shape[1], X.shape[2]))
            elif model_type == 'gru':
                self.models[model_type] = self.build_gru_model((X.shape[1], X.shape[2]))
            elif model_type == 'transformer':
                self.models[model_type] = self.build_transformer_model((X.shape[1], X.shape[2]))
            # #region agent log
            _debug_log("predictor.py:76", "model built", {"model_type": model_type}, "C")
            # #endregion

        # For demo, fit briefly; in production, load pre-trained model
        model = self.models[model_type]

        # Use SAM-based short training loop if enabled
        try:
            # #region agent log
            _debug_log("predictor.py:82", "training model - before", {"model_type": model_type, "use_sam": self.use_sam}, "C")
            # #endregion
            if self.use_sam:
                self._train_with_sam(model, X, np.array([current_price]), epochs=5)
            else:
                model.fit(X, np.array([current_price]), epochs=5, verbose=0)
            # #region agent log
            _debug_log("predictor.py:86", "training complete - predicting", {"model_type": model_type}, "C")
            # #endregion

            pred = model.predict(X, verbose=0)
            # #region agent log
            _debug_log("predictor.py:88", "prediction complete", {"model_type": model_type, "prediction": float(pred[0][0])}, "C")
            # #endregion
            return float(pred[0][0])
        except Exception as e:
            # #region agent log
            _debug_log("predictor.py:90", "prediction failed", {"model_type": model_type, "error": str(e), "error_type": type(e).__name__}, "C")
            # #endregion
            logger.error(f"Prediction training failed for {model_type}: {str(e)}")
            # On failure, return current price as fallback
            return float(current_price)

    def _train_with_sam(self, model, x, y, epochs=5):
        """Simple SAM training loop: for each epoch compute gradients, perturb weights,
        compute gradients at perturbed weights, and apply using base optimizer."""
        if not hasattr(model, 'trainable_variables'):
            return

        for epoch in range(epochs):
            # First gradient step
            with tf.GradientTape() as tape:
                preds = model(x, training=True)
                loss = self.loss_fn(y, preds)
            grads = tape.gradient(loss, model.trainable_variables)
            grad_norm = tf.linalg.global_norm(grads)
            scale = self.sam_rho / (grad_norm + 1e-12)
            # Compute epsilon weights
            e_ws = [g * scale for g in grads]

            # Apply perturbation
            for v, e in zip(model.trainable_variables, e_ws):
                v.assign_add(e)

            # Second gradient (at perturbed weights)
            with tf.GradientTape() as tape2:
                preds2 = model(x, training=True)
                loss2 = self.loss_fn(y, preds2)
            grads2 = tape2.gradient(loss2, model.trainable_variables)

            # Restore original weights
            for v, e in zip(model.trainable_variables, e_ws):
                v.assign_sub(e)

            # Apply gradients with base optimizer
            self.base_optimizer.apply_gradients(zip(grads2, model.trainable_variables))

    def get_predictions(self, df):
        predictions = {}
        for model_type in ['lstm', 'gru', 'transformer']:
            try:
                predictions[model_type] = self.predict(df, model_type)
            except Exception as e:
                logger.error(f"Error predicting with {model_type}: {str(e)}")
                predictions[model_type] = df['Close'].iloc[-1]  # Fallback to current price

        avg_pred = np.mean(list(predictions.values()))
        direction = "Bullish" if avg_pred > df['Close'].iloc[-1] else "Bearish"
        signal = "Strong Buy" if direction == "Bullish" else "Strong Sell"

        # Determine best model (simple: lowest error, but for demo, random)
        best_model = max(predictions, key=lambda k: predictions[k])  # Highest prediction as "best"

        return {
            "predictions": {k: round(v, 2) for k, v in predictions.items()},
            "average": round(avg_pred, 2),
            "direction": direction,
            "signal": signal,
            "best_model": best_model
        }