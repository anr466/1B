#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dynamic Coin Selector — Smart coin pool for trading
=====================================================
Selects coins dynamically from Binance based on:
1. Volume (minimum liquidity)
2. Volatility (opportunity for profit)
3. Momentum (coins about to move)
4. Excludes stablecoins
5. Includes meme coins with high volatility
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Stablecoins to EXCLUDE
STABLECOINS = {
    "USDT",
    "USDC",
    "BUSD",
    "DAI",
    "TUSD",
    "USDP",
    "FRAX",
    "USDN",
    "USDD",
    "LUSD",
    "GUSD",
    "USDK",
    "EURS",
    "EURS",
    "EURT",
    "XAUT",
    "PAXG",
    "SUSD",
    "HUSD",
    "OUSD",
    "RSR",
    "USTC",
    "VAI",
    "DUSD",
    "CUSD",
    "USDX",
    "MAI",
    "MIM",
    "FEI",
    "TRIBE",
    "ALUSD",
    "DOLA",
    "USDP",
    "USDD",
    # Pairs with stablecoins as base
    "BUSD",
    "USDC",
    "DAI",
    "TUSD",
}

# Meme coins (high volatility — good for scalping)
MEME_COINS = {
    "DOGE",
    "SHIB",
    "PEPE",
    "FLOKI",
    "BONK",
    "WIF",
    "MEME",
    "POPCAT",
    "MOG",
    "TURBO",
    "MYRO",
    "NEIRO",
    "GOAT",
    "PNUT",
    "ACT",
    "MOVE",
    "MEW",
    "SLERF",
    "BOME",
    "WEN",
}

# Minimum 24h volume in USDT
MIN_VOLUME_USDT = 1_000_000  # $1M minimum

# Maximum coins to trade
MAX_COINS = 30


class DynamicCoinSelector:
    """Smart coin selection based on market conditions"""

    def __init__(self, binance_client=None):
        self.client = binance_client
        self._cache = {}
        self._cache_time = 0
        self._last_scan = {}

    def record_scan(self, symbol):
        self._last_scan[symbol] = datetime.utcnow()

    def get_all_tradeable_coins(self) -> List[Dict[str, Any]]:
        """
        Get ALL tradeable USDT pairs from Binance, excluding stablecoins.
        Returns sorted by volume (highest first).
        """
        if not self.client:
            return self._default_coins()

        try:
            tickers = self.client.get_ticker()
            coins = []

            for ticker in tickers:
                symbol = ticker.get("symbol", "")

                # Only USDT pairs
                if not symbol.endswith("USDT"):
                    continue

                base = symbol.replace("USDT", "")

                # Exclude stablecoins
                if base in STABLECOINS:
                    continue

                # Exclude leveraged tokens
                if any(x in base for x in ["UP", "DOWN", "BULL", "BEAR"]):
                    continue

                volume_usd = float(ticker.get("quoteVolume", 0))
                if volume_usd < MIN_VOLUME_USDT:
                    continue

                price = float(ticker.get("lastPrice", 0))
                if price <= 0:
                    continue

                price_change = float(ticker.get("priceChangePercent", 0))
                high_24h = float(ticker.get("highPrice", 0))
                low_24h = float(ticker.get("lowPrice", 0))
                volatility = (
                    ((high_24h - low_24h) / low_24h * 100) if low_24h > 0 else 0
                )

                coins.append(
                    {
                        "symbol": symbol,
                        "base": base,
                        "price": price,
                        "volume_usd": volume_usd,
                        "price_change_24h": price_change,
                        "volatility_24h": volatility,
                        "is_meme": base in MEME_COINS,
                        "high_price_24h": high_24h,
                        "low_price_24h": low_24h,
                    }
                )

            # Sort by volume
            coins.sort(key=lambda x: x["volume_usd"], reverse=True)
            return coins[:200]  # Top 200 by volume

        except Exception as e:
            logger.error(f"Error fetching coins from Binance: {e}")
            return self._default_coins()

    def select_coins(
        self,
        regime: str = "NEUTRAL",
        max_coins: int = MAX_COINS,
        include_memes: bool = True,
        min_volatility: float = 2.0,
    ) -> List[str]:
        """
        Select coins for trading based on market regime.

        Args:
            regime: Current market regime
            max_coins: Maximum number of coins to return
            include_memes: Whether to include meme coins
            min_volatility: Minimum 24h volatility %

        Returns:
            List of symbol strings
        """
        all_coins = self.get_all_tradeable_coins()

        # Filter by volatility
        coins = [c for c in all_coins if c["volatility_24h"] >= min_volatility]

        # Score coins based on regime
        scored = []
        for coin in coins:
            score = self._score_coin(coin, regime, include_memes)
            scored.append((coin, score))

        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)

        # Return top coins
        symbols = [c["symbol"] for c, s in scored[:max_coins]]

        # Ensure at least some major coins for stability
        majors = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"}
        for major in majors:
            if major not in symbols and len(symbols) < max_coins:
                symbols.append(major)

        logger.info(
            f"DynamicCoinSelector: selected {len(symbols)} coins "
            f"(regime={regime}, min_vol={min_volatility}%)"
        )

        return symbols

    def _score_coin(
        self,
        coin: Dict[str, Any],
        regime: str,
        include_memes: bool,
    ) -> float:
        """Score a coin for trading opportunity"""
        score = 0.0

        # Volume score (0-30 points)
        vol_usd = coin["volume_usd"]
        if vol_usd > 100_000_000:
            score += 30
        elif vol_usd > 50_000_000:
            score += 25
        elif vol_usd > 10_000_000:
            score += 20
        elif vol_usd > 5_000_000:
            score += 15
        else:
            score += 10

        # Volatility score (0-40 points) — higher is better for scalping
        vol = coin["volatility_24h"]
        if vol > 15:
            score += 40  # Very volatile — great for scalping
        elif vol > 10:
            score += 35
        elif vol > 7:
            score += 30
        elif vol > 5:
            score += 25
        elif vol > 3:
            score += 20
        else:
            score += 10

        # Momentum score (0-20 points)
        change = abs(coin["price_change_24h"])
        if change > 20:
            score += 20  # Huge move — potential continuation
        elif change > 10:
            score += 18
        elif change > 5:
            score += 15
        elif change > 3:
            score += 10
        else:
            score += 5

        # Meme coin bonus (0-10 points)
        if coin["is_meme"] and include_memes:
            score += 10  # Meme coins have high volatility = opportunity

        return score

    def _default_coins(self) -> List[Dict[str, Any]]:
        """Fallback when Binance is unavailable"""
        symbols = [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "SOLUSDT",
            "XRPUSDT",
            "DOGEUSDT",
            "AVAXUSDT",
            "LINKUSDT",
            "ADAUSDT",
            "DOTUSDT",
            "MATICUSDT",
            "LTCUSDT",
            "BCHUSDT",
            "ETCUSDT",
            "FILUSDT",
            "APTUSDT",
            "ARBUSDT",
            "OPUSDT",
            "SUIUSDT",
            "INJUSDT",
            "NEARUSDT",
            "PEPEUSDT",
            "WIFUSDT",
            "FLOKIUSDT",
            "BONKUSDT",
            "SHIBUSDT",
            "MEMEUSDT",
            "TURBOUSDT",
        ]
        return [
            {
                "symbol": s,
                "base": s.replace("USDT", ""),
                "price": 0,
                "volume_usd": 10_000_000,
                "price_change_24h": 5.0,
                "volatility_24h": 5.0,
                "is_meme": s.replace("USDT", "") in MEME_COINS,
                "high_price_24h": 0,
                "low_price_24h": 0,
            }
            for s in symbols
        ]
