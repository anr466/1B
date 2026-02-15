"""
Arbitrage Strategy for CryptoWave Hopper
Exploits price differences between exchanges for risk-free profits.
"""

import requests
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import time

@dataclass
class ArbitrageOpportunity:
    """Detected arbitrage opportunity"""
    symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_pct: float
    estimated_profit_pct: float
    timestamp: datetime

class ArbitrageStrategy:
    """
    Cross-Exchange Arbitrage Strategy
    
    Monitors price differences between exchanges and executes
    simultaneous buy/sell when spread exceeds threshold.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'min_spread_pct': 0.5,  # Minimum 0.5% spread to trade
            'fee_per_trade_pct': 0.1,  # 0.1% fee per trade
            'min_profit_pct': 0.2,  # Minimum 0.2% profit after fees
            'max_position_pct': 0.10,  # 10% of capital per arb
            'exchanges': ['binance', 'coinbase'],
        }
        self.price_cache: Dict[str, Dict[str, float]] = {}
        self.last_update: Dict[str, datetime] = {}
    
    def fetch_binance_price(self, symbol: str) -> Optional[float]:
        """Fetch current price from Binance"""
        try:
            url = f"https://api.binance.com/api/v3/ticker/price"
            params = {'symbol': symbol}
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            return float(data['price'])
        except Exception as e:
            print(f"[ARB] Binance fetch error: {e}")
            return None
    
    def fetch_coinbase_price(self, symbol: str) -> Optional[float]:
        """Fetch current price from Coinbase"""
        try:
            # Convert symbol format: BTCUSDT -> BTC-USD
            base = symbol.replace('USDT', '').replace('USDC', '')
            quote = 'USD'
            pair = f"{base}-{quote}"
            
            url = f"https://api.coinbase.com/v2/prices/{pair}/spot"
            response = requests.get(url, timeout=5)
            data = response.json()
            return float(data['data']['amount'])
        except Exception as e:
            print(f"[ARB] Coinbase fetch error: {e}")
            return None
    
    def fetch_all_prices(self, symbol: str) -> Dict[str, float]:
        """Fetch prices from all configured exchanges"""
        prices = {}
        
        binance_price = self.fetch_binance_price(symbol)
        if binance_price:
            prices['binance'] = binance_price
        
        coinbase_price = self.fetch_coinbase_price(symbol)
        if coinbase_price:
            prices['coinbase'] = coinbase_price
        
        self.price_cache[symbol] = prices
        self.last_update[symbol] = datetime.now()
        
        return prices
    
    def find_opportunity(self, symbol: str) -> Optional[ArbitrageOpportunity]:
        """
        Find arbitrage opportunity for a symbol
        
        Returns ArbitrageOpportunity if profitable spread found
        """
        prices = self.fetch_all_prices(symbol)
        
        if len(prices) < 2:
            return None
        
        cfg = self.config
        
        # Find best buy and sell exchanges
        exchanges = list(prices.keys())
        best_buy = min(exchanges, key=lambda x: prices[x])
        best_sell = max(exchanges, key=lambda x: prices[x])
        
        buy_price = prices[best_buy]
        sell_price = prices[best_sell]
        
        # Calculate spread
        spread_pct = (sell_price - buy_price) / buy_price * 100
        
        # Check minimum spread
        if spread_pct < cfg['min_spread_pct']:
            return None
        
        # Calculate profit after fees
        total_fees = cfg['fee_per_trade_pct'] * 2  # Buy + Sell
        transfer_cost = 0.1  # Estimated transfer cost
        
        estimated_profit = spread_pct - total_fees - transfer_cost
        
        if estimated_profit < cfg['min_profit_pct']:
            return None
        
        return ArbitrageOpportunity(
            symbol=symbol,
            buy_exchange=best_buy,
            sell_exchange=best_sell,
            buy_price=buy_price,
            sell_price=sell_price,
            spread_pct=spread_pct,
            estimated_profit_pct=estimated_profit,
            timestamp=datetime.now()
        )
    
    def scan_markets(self, symbols: List[str]) -> List[ArbitrageOpportunity]:
        """Scan multiple symbols for arbitrage opportunities"""
        opportunities = []
        
        for symbol in symbols:
            opp = self.find_opportunity(symbol)
            if opp:
                opportunities.append(opp)
            time.sleep(0.2)  # Rate limiting
        
        # Sort by profit
        opportunities.sort(key=lambda x: x.estimated_profit_pct, reverse=True)
        
        return opportunities
    
    def execute_arbitrage(self, opportunity: ArbitrageOpportunity, capital: float) -> Dict:
        """
        Execute arbitrage trade (simulation)
        
        In production, this would place simultaneous orders on both exchanges
        """
        cfg = self.config
        
        position_value = capital * cfg['max_position_pct']
        quantity = position_value / opportunity.buy_price
        
        # Simulate execution
        buy_cost = quantity * opportunity.buy_price * (1 + cfg['fee_per_trade_pct'] / 100)
        sell_revenue = quantity * opportunity.sell_price * (1 - cfg['fee_per_trade_pct'] / 100)
        
        profit = sell_revenue - buy_cost
        profit_pct = profit / buy_cost * 100
        
        return {
            'symbol': opportunity.symbol,
            'quantity': quantity,
            'buy_exchange': opportunity.buy_exchange,
            'sell_exchange': opportunity.sell_exchange,
            'profit_usd': profit,
            'profit_pct': profit_pct,
            'executed': True
        }
    
    def get_market_suitability(self) -> float:
        """
        Arbitrage suitability depends on market inefficiency.
        Always returns moderate score as opportunities are rare.
        """
        return 0.4  # Base score - opportunities are rare


class TrendFollowingStrategy:
    """
    AI-Enhanced Trend Following Strategy
    
    Follows strong trends with pullback entries.
    Uses AI prediction for confirmation.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'adx_min': 25,
            'pullback_min_pct': 0.5,
            'pullback_max_pct': 3.0,
            'rsi_max': 70,
            'sl_atr_mult': 1.5,
            'tp_rr': 3.0,
        }
    
    def find_entry(self, df, ai_prediction=None) -> Optional[Dict]:
        """Find trend following entry"""
        if len(df) < 50:
            return None
        
        c = df['c']
        h = df['h']
        l = df['l']
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        cfg = self.config
        
        # Calculate indicators
        ema21 = c.ewm(span=21).mean()
        ema50 = c.ewm(span=50).mean()
        
        # ATR
        tr = pd.concat([h - l, abs(h - c.shift(1)), abs(l - c.shift(1))], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        # RSI
        delta = c.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1)
        rsi = 100 - (100 / (1 + rs))
        
        # ADX
        plus_dm = h.diff()
        minus_dm = l.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / atr)
        minus_di = 100 * (abs(minus_dm).ewm(alpha=1/14).mean() / atr)
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.rolling(14).mean()
        
        # Check trend
        uptrend = latest['c'] > ema21.iloc[-1] > ema50.iloc[-1]
        strong_trend = adx.iloc[-1] > cfg['adx_min']
        
        if not (uptrend and strong_trend):
            return None
        
        # Check pullback
        recent_high = c.rolling(20).max().iloc[-1]
        pullback_pct = (recent_high - latest['c']) / recent_high * 100
        
        in_pullback = cfg['pullback_min_pct'] <= pullback_pct <= cfg['pullback_max_pct']
        
        if not in_pullback:
            return None
        
        # Check bounce
        bounce = latest['c'] > latest['o'] and prev['c'] < prev['o']
        rsi_ok = rsi.iloc[-1] < cfg['rsi_max']
        
        if bounce and rsi_ok:
            # AI confirmation if available
            confidence = 0.70
            if ai_prediction and ai_prediction.get('direction') == 'up':
                confidence = max(confidence, ai_prediction.get('confidence', 0.70))
            
            entry = latest['c']
            sl = entry - (atr.iloc[-1] * cfg['sl_atr_mult'])
            risk = entry - sl
            tp = entry + (risk * cfg['tp_rr'])
            
            return {
                'action': 'buy',
                'confidence': confidence,
                'entry_price': entry,
                'stop_loss': sl,
                'take_profit': tp,
                'reason': f'Trend pullback bounce (ADX={adx.iloc[-1]:.1f})',
                'strategy': 'trend_following'
            }
        
        return None
    
    def get_market_suitability(self, df) -> float:
        """Calculate suitability for trend following"""
        if len(df) < 50:
            return 0.5
        
        c = df['c']
        h = df['h']
        l = df['l']
        
        # Calculate ADX
        tr = pd.concat([h - l, abs(h - c.shift(1)), abs(l - c.shift(1))], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        plus_dm = h.diff()
        minus_dm = l.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / atr)
        minus_di = 100 * (abs(minus_dm).ewm(alpha=1/14).mean() / atr)
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.rolling(14).mean().iloc[-1]
        
        score = 0.5
        
        # Strong ADX = good for trend following
        if adx > 25:
            score += 0.2
        if adx > 35:
            score += 0.15
        
        # Clear trend
        ema21 = c.ewm(span=21).mean().iloc[-1]
        ema50 = c.ewm(span=50).mean().iloc[-1]
        if c.iloc[-1] > ema21 > ema50 or c.iloc[-1] < ema21 < ema50:
            score += 0.15
        
        return min(score, 1.0)


# === Quick Test ===
if __name__ == '__main__':
    print("Testing Arbitrage & Trend Following Strategies...")
    
    # Test Arbitrage
    arb_strategy = ArbitrageStrategy()
    print("\n📊 Arbitrage Scan (BTC):")
    opp = arb_strategy.find_opportunity('BTCUSDT')
    if opp:
        print(f"   Opportunity: Buy on {opp.buy_exchange} @ ${opp.buy_price:.2f}")
        print(f"   Sell on {opp.sell_exchange} @ ${opp.sell_price:.2f}")
        print(f"   Profit: {opp.estimated_profit_pct:.2f}%")
    else:
        print("   No arbitrage opportunity (spread too small)")
    
    # Test Trend Following
    import pandas as pd
    
    url = "https://api.binance.com/api/v3/klines"
    params = {'symbol': 'BTCUSDT', 'interval': '15m', 'limit': 100}
    response = requests.get(url, params=params)
    data = response.json()
    
    df = pd.DataFrame(data, columns=[
        'ts', 'o', 'h', 'l', 'c', 'v', 'close_time',
        'quote_vol', 'trades', 'taker_base', 'taker_quote', 'ignore'
    ])
    for col in ['o', 'h', 'l', 'c', 'v']:
        df[col] = df[col].astype(float)
    
    trend_strategy = TrendFollowingStrategy()
    trend_signal = trend_strategy.find_entry(df)
    trend_suit = trend_strategy.get_market_suitability(df)
    
    print(f"\n📈 Trend Following:")
    print(f"   Suitability: {trend_suit:.0%}")
    if trend_signal:
        print(f"   Signal: {trend_signal['reason']}")
    else:
        print("   No trend entry detected")
    
    print("\n✅ Arbitrage & Trend test complete!")
