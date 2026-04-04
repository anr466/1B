#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Smart Coin Selector — اختيار العملات الذكي
============================================
يختار العملات ديناميكياً بناءً على:
1. حجم التداول (Top Volume) من Binance
2. التغير السعري (Top Movers) — أعلى ارتفاع/انخفاض
3. التناوب الذكي — إذا لم توجد إشارات، يفحص عملات مختلفة
4. الوعي بالشموع — لا يعيد فحص نفس العملة إلا عند شمعة جديدة
"""

import time
import logging
from typing import Dict, List, Optional, Set, Tuple
from binance.client import Client

logger = logging.getLogger(__name__)


class SmartCoinSelector:
    """اختيار العملات الذكي مع تناوب ووعي بالشموع"""

    # قائمة أساسية — عملات مستقرة ومعروفة
    BASE_COINS = [
        "BTCUSDT",
        "ETHUSDT",
        "BNBUSDT",
        "SOLUSDT",
        "XRPUSDT",
        "ADAUSDT",
        "DOGEUSDT",
        "AVAXUSDT",
        "DOTUSDT",
        "LINKUSDT",
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
        "FETUSDT",
        "RENDERUSDT",
        "TIAUSDT",
        "SEIUSDT",
        "JUPUSDT",
        "ENAUSDT",
        "WUSDT",
    ]

    def __init__(self, binance_client: Optional[Client] = None):
        self.client = binance_client
        # تتبع آخر فحص لكل عملة: {symbol: candle_open_time}
        self._last_scan: Dict[str, int] = {}
        # العملات التي تم فحصها في الدورة الحالية
        self._scanned_this_cycle: Set[str] = set()
        # العملات التي لم تُفحص بعد (للتناوب)
        self._unscanned_pool: List[str] = list(self.BASE_COINS)
        # آخر تحديث للقائمة الديناميكية
        self._last_dynamic_update: float = 0
        self._dynamic_coins: List[str] = list(self.BASE_COINS[:14])
        self._cycle_count: int = 0

    def get_coins_to_scan(
        self,
        max_coins: int = 20,
        timeframe: str = "1h",
        force_refresh: bool = False,
    ) -> List[str]:
        """
        الحصول على العملات التي يجب فحصها في هذه الدورة

        Args:
            max_coins: الحد الأقصى للعملات
            timeframe: الإطار الزمني للشموع
            force_refresh: فرض تحديث القائمة الديناميكية

        Returns:
            قائمة العملات المراد فحصها
        """
        self._cycle_count += 1

        # تحديث القائمة الديناميكية كل 10 دورات
        if force_refresh or (self._cycle_count % 10 == 0):
            self._update_dynamic_coins(max_coins * 2)

        # بناء قائمة العملات المرشحة
        candidates = self._build_scan_candidates(max_coins, timeframe)

        # تصفية العملات التي تم فحصها بالفعل في نفس الشمعة
        filtered = self._filter_by_candle(candidates, timeframe)

        # إذا لم يتبق شيء، أعد القائمة الديناميكية (شمعة جديدة)
        if not filtered:
            self._last_scan.clear()  # شمعة جديدة — ابدأ من جديد
            filtered = self._build_scan_candidates(max_coins, timeframe)

        # حدد العدد الأقصى
        result = filtered[:max_coins]

        # سجل ما تم فحصه
        self._scanned_this_cycle = set(result)

        logger.info(
            f"🪙 Smart Coin Selector: cycle={self._cycle_count}, "
            f"candidates={len(candidates)}, after_candle_filter={len(filtered)}, "
            f"selected={len(result)}"
        )

        return result

    def _build_scan_candidates(self, max_coins: int, timeframe: str) -> List[str]:
        """بناء قائمة المرشحين — مزيج من الديناميكية + التناوب"""
        # ابدأ بالعملات الديناميكية (الأعلى حجم/حركة)
        candidates = list(self._dynamic_coins)

        # أضف عملات من قائمة التناوب (التي لم تُفحص كثيراً)
        rotation_coins = self._get_rotation_candidates(max_coins - len(candidates))
        candidates.extend([c for c in rotation_coins if c not in candidates])

        return candidates[: max_coins * 2]  # نعطيه ضعف العدد للتصفية بالشموع

    def _filter_by_candle(self, symbols: List[str], timeframe: str) -> List[str]:
        """تصفية العملات التي تم فحصها في نفس الشمعة"""
        now_ms = int(time.time() * 1000)
        candle_ms = self._timeframe_to_ms(timeframe)

        if candle_ms <= 0:
            return symbols  # لا يمكن التحديد — افحص الكل

        result = []
        for symbol in symbols:
            last_scan = self._last_scan.get(symbol, 0)
            # إذا مر وقت أكثر من شمعة واحدة، أو لم يُفحص أبداً
            if (now_ms - last_scan) >= candle_ms:
                result.append(symbol)

        return result

    def _update_dynamic_coins(self, max_coins: int) -> None:
        """تحديث القائمة الديناميكية من Binance (حجم + حركة)"""
        if not self.client:
            # بدون عميل Binance — استخدم القائمة الأساسية
            self._dynamic_coins = list(self.BASE_COINS[:max_coins])
            self._last_dynamic_update = time.time()
            return

        try:
            # جلب إحصائيات 24 ساعة
            tickers = self.client.get_ticker_24hr()

            # فلترة USDT فقط
            usdt_tickers = [t for t in tickers if t["symbol"].endswith("USDT")]

            # أعلى حجم تداول
            by_volume = sorted(
                usdt_tickers,
                key=lambda t: float(t.get("quoteVolume", 0)),
                reverse=True,
            )

            # أعلى حركة سعرية (بالقيمة المطلقة)
            by_change = sorted(
                usdt_tickers,
                key=lambda t: abs(float(t.get("priceChangePercent", 0))),
                reverse=True,
            )

            # مزيج: 60% حجم + 40% حركة
            top_volume = {t["symbol"] for t in by_volume[:max_coins]}
            top_movers = {t["symbol"] for t in by_change[:max_coins]}

            # ابدأ بالعملات المشتركة (حجم + حركة)
            combined = list(top_volume & top_movers)

            # ثم العملات عالية الحجم فقط
            combined.extend([s for s in top_volume if s not in combined])

            # ثم العملات عالية الحركة فقط
            combined.extend([s for s in top_movers if s not in combined])

            # تأكد من وجود العملات الأساسية
            for coin in self.BASE_COINS[:8]:
                if coin not in combined:
                    combined.append(coin)

            self._dynamic_coins = combined[:max_coins]
            self._last_dynamic_update = time.time()

            logger.info(
                f"🪙 Dynamic coins updated: {len(self._dynamic_coins)} coins "
                f"(volume={len(top_volume)}, movers={len(top_movers)})"
            )

        except Exception as e:
            logger.warning(f"⚠️ Failed to update dynamic coins: {e}")
            # fallback للقائمة الأساسية
            self._dynamic_coins = list(self.BASE_COINS[:max_coins])

    def _get_rotation_candidates(self, count: int) -> List[str]:
        """الحصول على عملات تناوبية — التي لم تُفحص كثيراً"""
        # العملات التي لم تُفحص في آخر 3 دورات
        rarely_scanned = [
            c
            for c in self.BASE_COINS
            if c not in self._scanned_this_cycle and self._last_scan.get(c, 0) == 0
        ]

        # إذا لم يكن هناك ما يكفي، أضف من القائمة الأساسية
        if len(rarely_scanned) < count:
            rarely_scanned.extend(
                [c for c in self.BASE_COINS if c not in rarely_scanned]
            )

        return rarely_scanned[:count]

    def record_scan(self, symbol: str) -> None:
        """تسجيل أن عملة تم فحصها الآن"""
        self._last_scan[symbol] = int(time.time() * 1000)

    def _timeframe_to_ms(self, timeframe: str) -> int:
        """تحويل الإطار الزمني إلى ميلي ثانية"""
        tf_map = {
            "1m": 60 * 1000,
            "3m": 3 * 60 * 1000,
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "30m": 30 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "2h": 2 * 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
            "6h": 6 * 60 * 60 * 1000,
            "12h": 12 * 60 * 60 * 1000,
            "1d": 24 * 60 * 60 * 1000,
        }
        return tf_map.get(timeframe, 60 * 60 * 1000)  # default 1h

    def get_scan_stats(self) -> Dict:
        """إحصائيات الفحص"""
        return {
            "cycle_count": self._cycle_count,
            "dynamic_coins": len(self._dynamic_coins),
            "scanned_this_cycle": len(self._scanned_this_cycle),
            "total_tracked": len(self._last_scan),
            "last_dynamic_update": self._last_dynamic_update,
        }
