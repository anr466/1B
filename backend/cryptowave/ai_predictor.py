"""
AI Predictor for CryptoWave Hopper
Uses machine learning to predict price direction and confidence.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

@dataclass
class Prediction:
    """AI Prediction Result"""
    direction: str  # 'up', 'down', 'neutral'
    confidence: float  # 0.0 to 1.0
    predicted_move_pct: float
    timeframe_minutes: int
    features_used: int

class AIPredictor:
    """
    AI-Powered Price Direction Predictor
    
    Uses ensemble of technical features and ML models to predict:
    - Direction (up/down/neutral)
    - Confidence (0-100%)
    - Expected move magnitude
    """
    
    def __init__(self, model_type: str = 'ensemble'):
        self.model_type = model_type
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.is_trained = False
        self.min_confidence = 0.70
        
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare ML features from OHLCV data
        Returns DataFrame with normalized features
        """
        features = pd.DataFrame(index=df.index)
        
        c = df['c']
        o = df['o']
        h = df['h']
        l = df['l']
        v = df['v']
        
        # === Price Action Features ===
        features['returns_1'] = c.pct_change(1) * 100
        features['returns_5'] = c.pct_change(5) * 100
        features['returns_10'] = c.pct_change(10) * 100
        features['returns_20'] = c.pct_change(20) * 100
        
        # === Candle Features ===
        features['body_pct'] = (c - o) / o * 100
        features['upper_wick_pct'] = (h - c.clip(lower=o)) / c * 100
        features['lower_wick_pct'] = (c.clip(upper=o) - l) / c * 100
        features['range_pct'] = (h - l) / c * 100
        
        # === Momentum Features ===
        # RSI
        delta = c.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1)
        features['rsi'] = 100 - (100 / (1 + rs))
        features['rsi_slope'] = features['rsi'].diff(5)
        
        # MACD
        ema12 = c.ewm(span=12).mean()
        ema26 = c.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        features['macd_hist'] = macd - signal
        features['macd_hist_slope'] = features['macd_hist'].diff(3)
        
        # === Trend Features ===
        ema21 = c.ewm(span=21).mean()
        ema50 = c.ewm(span=50).mean()
        ema200 = c.ewm(span=200).mean()
        
        features['ema21_dist'] = (c - ema21) / ema21 * 100
        features['ema50_dist'] = (c - ema50) / ema50 * 100
        features['ema200_dist'] = (c - ema200) / ema200 * 100
        features['ema_alignment'] = ((ema21 > ema50).astype(int) + (ema50 > ema200).astype(int)) - 1
        
        # === Volatility Features ===
        tr1 = h - l
        tr2 = abs(h - c.shift(1))
        tr3 = abs(l - c.shift(1))
        atr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()
        features['atr_pct'] = atr / c * 100
        features['volatility_5'] = c.rolling(5).std() / c * 100
        features['volatility_20'] = c.rolling(20).std() / c * 100
        
        # === Volume Features ===
        vol_ma = v.rolling(20).mean()
        features['volume_ratio'] = v / vol_ma
        features['volume_trend'] = v.rolling(5).mean() / vol_ma
        
        # === Bollinger Band Features ===
        bb_mid = c.rolling(20).mean()
        bb_std = c.rolling(20).std()
        bb_upper = bb_mid + (bb_std * 2)
        bb_lower = bb_mid - (bb_std * 2)
        features['bb_position'] = (c - bb_lower) / (bb_upper - bb_lower)
        features['bb_width'] = (bb_upper - bb_lower) / bb_mid * 100
        
        # === ADX Feature ===
        features['adx'] = self._calc_adx(h, l, c, 14)
        
        # === Support/Resistance Features ===
        features['near_high_20'] = (c / h.rolling(20).max()) * 100
        features['near_low_20'] = (c / l.rolling(20).min()) * 100
        
        # Drop NaN
        features = features.fillna(0)
        
        self.feature_names = list(features.columns)
        return features
    
    def _calc_adx(self, high, low, close, period=14):
        """Calculate ADX"""
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
        minus_di = 100 * (abs(minus_dm).ewm(alpha=1/period).mean() / atr)
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1)) * 100
        return dx.rolling(period).mean()
    
    def create_labels(self, df: pd.DataFrame, lookahead: int = 5, threshold: float = 0.5) -> pd.Series:
        """
        Create target labels for training
        
        Args:
            lookahead: Number of bars to look ahead
            threshold: Minimum % move to classify as up/down
        
        Returns:
            Series with labels: 1 (up), 0 (neutral), -1 (down)
        """
        future_return = df['c'].shift(-lookahead) / df['c'] - 1
        future_return_pct = future_return * 100
        
        labels = pd.Series(0, index=df.index)
        labels[future_return_pct > threshold] = 1
        labels[future_return_pct < -threshold] = -1
        
        return labels
    
    def train(self, df: pd.DataFrame, lookahead: int = 5):
        """
        Train the AI model on historical data
        
        Uses XGBoost classifier for prediction
        """
        try:
            from sklearn.ensemble import GradientBoostingClassifier
            from sklearn.preprocessing import StandardScaler
            from sklearn.model_selection import train_test_split
            
            # Prepare data
            features = self.prepare_features(df)
            labels = self.create_labels(df, lookahead)
            
            # Remove last 'lookahead' rows (no labels)
            features = features.iloc[:-lookahead]
            labels = labels.iloc[:-lookahead]
            
            # Remove rows with NaN
            valid_idx = features.notna().all(axis=1) & labels.notna()
            X = features.loc[valid_idx]
            y = labels.loc[valid_idx]
            
            if len(X) < 100:
                print("[AI] Not enough data for training")
                return False
            
            # Split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, shuffle=False
            )
            
            # Scale
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate
            train_score = self.model.score(X_train_scaled, y_train)
            test_score = self.model.score(X_test_scaled, y_test)
            
            print(f"[AI] Training complete: Train={train_score:.2%}, Test={test_score:.2%}")
            self.is_trained = True
            return True
            
        except ImportError:
            print("[AI] sklearn not available, using rule-based prediction")
            self.model_type = 'rules'
            return False
        except Exception as e:
            print(f"[AI] Training error: {e}")
            return False
    
    def predict(self, df: pd.DataFrame) -> Prediction:
        """
        Make prediction on latest data
        
        Returns Prediction with direction, confidence, and expected move
        """
        if self.model_type == 'rules' or not self.is_trained:
            return self._rule_based_predict(df)
        
        try:
            features = self.prepare_features(df)
            latest_features = features.iloc[-1:].values
            
            # Scale
            scaled = self.scaler.transform(latest_features)
            
            # Predict
            pred_class = self.model.predict(scaled)[0]
            pred_proba = self.model.predict_proba(scaled)[0]
            
            # Get confidence and direction
            confidence = max(pred_proba)
            
            if pred_class == 1:
                direction = 'up'
            elif pred_class == -1:
                direction = 'down'
            else:
                direction = 'neutral'
            
            # Estimate move based on ATR
            atr_pct = features.iloc[-1]['atr_pct']
            predicted_move = atr_pct * (confidence - 0.5) * 2
            
            return Prediction(
                direction=direction,
                confidence=confidence,
                predicted_move_pct=predicted_move,
                timeframe_minutes=5 * 15,  # 5 bars * 15min
                features_used=len(self.feature_names)
            )
            
        except Exception as e:
            print(f"[AI] Prediction error: {e}")
            return self._rule_based_predict(df)
    
    def _rule_based_predict(self, df: pd.DataFrame) -> Prediction:
        """
        Fallback rule-based prediction when ML model unavailable
        Uses weighted technical indicators
        """
        if len(df) < 50:
            return Prediction('neutral', 0.5, 0.0, 60, 0)
        
        latest = df.iloc[-1]
        
        score = 0
        weights_sum = 0
        
        # RSI Signal (weight: 2)
        if 'rsi' in df.columns:
            rsi = latest['rsi']
            if rsi < 30:
                score += 2
            elif rsi > 70:
                score -= 2
            elif rsi < 40:
                score += 1
            elif rsi > 60:
                score -= 1
            weights_sum += 2
        
        # MACD Signal (weight: 2)
        if 'macd_hist' in df.columns:
            macd = latest['macd_hist']
            if macd > 0:
                score += 2
            else:
                score -= 2
            weights_sum += 2
        
        # EMA Trend (weight: 3)
        if all(col in df.columns for col in ['ema21', 'ema50', 'ema200']):
            c = latest['c']
            if c > latest['ema21'] > latest['ema50']:
                score += 3
            elif c < latest['ema21'] < latest['ema50']:
                score -= 3
            weights_sum += 3
        
        # ADX Strength (weight: 1)
        if 'adx' in df.columns:
            adx = latest['adx']
            if adx > 25:
                # Trend is strong, amplify signal
                if score > 0:
                    score += 1
                elif score < 0:
                    score -= 1
            weights_sum += 1
        
        # Normalize to confidence
        if weights_sum > 0:
            normalized = score / weights_sum
            confidence = 0.5 + (normalized * 0.3)  # Range: 0.2 to 0.8
        else:
            confidence = 0.5
        
        # Direction
        if score > 2:
            direction = 'up'
        elif score < -2:
            direction = 'down'
        else:
            direction = 'neutral'
        
        return Prediction(
            direction=direction,
            confidence=min(max(confidence, 0.3), 0.85),
            predicted_move_pct=score * 0.2,
            timeframe_minutes=60,
            features_used=4
        )


# === Quick Test ===
if __name__ == '__main__':
    print("Testing AI Predictor...")
    
    import requests
    
    # Fetch sample data
    url = "https://api.binance.com/api/v3/klines"
    params = {'symbol': 'BTCUSDT', 'interval': '15m', 'limit': 500}
    response = requests.get(url, params=params)
    data = response.json()
    
    df = pd.DataFrame(data, columns=[
        'ts', 'o', 'h', 'l', 'c', 'v', 'close_time',
        'quote_vol', 'trades', 'taker_base', 'taker_quote', 'ignore'
    ])
    for col in ['o', 'h', 'l', 'c', 'v']:
        df[col] = df[col].astype(float)
    
    # Test predictor
    predictor = AIPredictor()
    
    # Try ML training
    trained = predictor.train(df)
    
    # Make prediction
    pred = predictor.predict(df)
    print(f"\n📊 Prediction Result:")
    print(f"   Direction: {pred.direction}")
    print(f"   Confidence: {pred.confidence:.1%}")
    print(f"   Expected Move: {pred.predicted_move_pct:+.2f}%")
    print(f"   Features Used: {pred.features_used}")
    
    print("\n✅ AI Predictor test complete!")
