#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 Smart Coin Selector - استراتيجية ذكية لاختيار العملات

استراتيجية متقدمة مبنية على خبرة التحليل الفني:
- كشف الزخم المبكر (Early Momentum Detection)
- تجنب العملات المتأخرة (topgains الذين ارتفعوا بالفعل)
- تحليل تدفق السيولة (Smart Money Flow)
- فلترة Volume Profile المتقدمة
- مؤشرات فنية متعددة الأطر

المبدأ:
نبحث عن عملات في بداية الحركة، ليس بعد الارتفاع القوي!
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from binance.client import Client
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SmartCoinSelector:
    """محدد عملات ذكي - يجد الفرص قبل الارتفاع الكبير"""
    
    def __init__(self, client: Client, requests_per_second: float = 5.0):
        self.client = client
        self.requests_per_second = requests_per_second
        self.min_delay = 1.0 / requests_per_second  # تأخير بين الطلبات
        self.last_request_time = 0
        
        # العملات المستبعدة تماماً
        self.excluded_coins = {
            # العملات المستقرة
            'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'FRAX', 'LUSD',
            'FDUSD', 'PYUSD', 'USDD', 'GUSD', 'SUSD', 'USTC', 'VAI',
            # العملات الاحتياطية
            'WBTC', 'STETH', 'WETH', 'LIDO', 'RETH', 'CBETH', 'SFRXETH'
        }
        
        # العملات الكبيرة (نتجنبها لأن حركتها بطيئة)
        self.major_coins = {
            'BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'DOGE', 'SOL', 'TRX', 'DOT',
            'MATIC', 'LTC', 'SHIB', 'AVAX', 'UNI', 'LINK'
        }
        
        # معايير الكشف المبكر
        self.early_momentum_criteria = {
            'price_change_min': 2.0,      # تغير سعر إيجابي لكن ليس كبير جداً
            'price_change_max': 15.0,     # أقصى تغير (تجنب العملات التي انفجرت)
            'volume_increase_min': 30.0,  # زيادة حجم 30%+ (نشاط متزايد)
            'min_volume_usdt': 500000,    # حجم أدنى 500K
            'max_volume_usdt': 500000000, # حد أقصى 500M (تجنب الكبار جداً)
            'min_trade_count': 1000,      # عدد صفقات أدنى
        }
        
        # معايير Smart Money
        self.smart_money_criteria = {
            'buyer_ratio_min': 0.52,      # 52%+ من الحجم مشتريات
            'volume_spike_threshold': 2.0, # مضاعفة الحجم العادي
        }
    
    def _throttle_request(self):
        """تطبيق تأخير بين الطلبات لتجنب rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def get_smart_coins(self, limit: int = 100, mode: str = 'balanced') -> List[str]:
        """
        اختيار عملات ذكي بناءً على معايير متقدمة
        
        Args:
            limit: عدد العملات المطلوب
            mode: نمط الاختيار (aggressive, balanced, conservative)
        
        Returns:
            قائمة بأفضل العملات مرتبة حسب الجودة
        """
        try:
            logger.info(f"🎯 بدء الاختيار الذكي للعملات (النمط: {mode})")
            
            # جلب بيانات السوق
            tickers_24h = self.client.get_ticker()
            
            # المرحلة 1: الفلترة الأولية
            logger.info("🔍 المرحلة 1: فلترة أولية...")
            initial_candidates = self._initial_filter(tickers_24h, mode)
            logger.info(f"   ✅ {len(initial_candidates)} عملة بعد الفلترة الأولية")
            
            if len(initial_candidates) < limit:
                logger.warning(f"⚠️ عدد العملات أقل من المطلوب، سنخفف المعايير")
            
            # المرحلة 2: تحليل الزخم المبكر
            logger.info("📈 المرحلة 2: كشف الزخم المبكر...")
            momentum_coins = self._detect_early_momentum(initial_candidates)
            logger.info(f"   ✅ {len(momentum_coins)} عملة بزخم مبكر")
            
            # المرحلة 3: تحليل Smart Money
            logger.info("💰 المرحلة 3: تحليل تدفق السيولة...")
            smart_money_scores = self._analyze_smart_money_flow(momentum_coins)
            logger.info(f"   ✅ تم تحليل {len(smart_money_scores)} عملة")
            
            # المرحلة 4: حساب النقاط النهائية
            logger.info("🎯 المرحلة 4: حساب النقاط النهائية...")
            final_scores = self._calculate_final_scores(smart_money_scores)
            
            # ترتيب وتحديد أفضل العملات
            final_scores.sort(key=lambda x: x['total_score'], reverse=True)
            
            # عرض النتائج
            selected = final_scores[:limit]
            logger.info(f"\n✨ أفضل {len(selected)} عملة:")
            for i, coin in enumerate(selected[:10], 1):  # عرض أول 10
                logger.info(
                    f"  {i}. {coin['symbol']}: "
                    f"النقاط={coin['total_score']:.1f}, "
                    f"السعر↑{coin['price_change']:.2f}%, "
                    f"الحجم↑{coin['volume_increase']:.1f}%, "
                    f"مشتريات={coin['buyer_ratio']*100:.1f}%"
                )
            
            return [coin['symbol'] for coin in selected]
            
        except Exception as e:
            logger.error(f"❌ خطأ في الاختيار الذكي: {e}")
            # فشل النظام الذكي، استخدم خطة احتياطية
            return self._get_fallback_coins(limit)
    
    def _initial_filter(self, tickers: List[Dict], mode: str) -> List[Dict]:
        """الفلترة الأولية - إزالة غير المناسبين"""
        candidates = []
        
        # تعديل المعايير حسب النمط
        if mode == 'aggressive':
            price_min, price_max = 1.0, 20.0
            volume_min = 300000
        elif mode == 'conservative':
            price_min, price_max = 3.0, 12.0
            volume_min = 1000000
        else:  # balanced
            price_min = self.early_momentum_criteria['price_change_min']
            price_max = self.early_momentum_criteria['price_change_max']
            volume_min = self.early_momentum_criteria['min_volume_usdt']
        
        for ticker in tickers:
            symbol = ticker['symbol']
            
            # فقط أزواج USDT
            if not symbol.endswith('USDT'):
                continue
            
            base = symbol.replace('USDT', '')
            
            # تخطي المستبعدين
            if base in self.excluded_coins or base in self.major_coins:
                continue
            
            try:
                price_change = float(ticker['priceChangePercent'])
                volume_usdt = float(ticker['quoteVolume'])
                trade_count = int(ticker['count'])
                
                # معايير الزخم المبكر
                if (price_min <= price_change <= price_max and
                    volume_usdt >= volume_min and
                    volume_usdt <= self.early_momentum_criteria['max_volume_usdt'] and
                    trade_count >= self.early_momentum_criteria['min_trade_count']):
                    
                    candidates.append({
                        'symbol': symbol,
                        'price_change': price_change,
                        'volume_usdt': volume_usdt,
                        'trade_count': trade_count,
                        'ticker': ticker
                    })
                    
            except (ValueError, KeyError):
                continue
        
        return candidates
    
    def _detect_early_momentum(self, candidates: List[Dict]) -> List[Dict]:
        """كشف الزخم المبكر - العملات في بداية الحركة"""
        momentum_coins = []
        
        for coin in candidates:
            symbol = coin['symbol']
            
            try:
                # تطبيق rate limiting
                self._throttle_request()
                
                # جلب كاندلات قصيرة المدى (1 ساعة)
                klines_1h = self.client.get_klines(
                    symbol=symbol,
                    interval='1h',
                    limit=24  # آخر 24 ساعة
                )
                
                if len(klines_1h) < 10:
                    continue
                
                # تحويل لـ DataFrame
                df = pd.DataFrame(klines_1h, columns=[
                    'time', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                df['close'] = df['close'].astype(float)
                df['volume'] = df['volume'].astype(float)
                df['quote_volume'] = df['quote_volume'].astype(float)
                df['taker_buy_quote'] = df['taker_buy_quote'].astype(float)
                
                # حساب مؤشرات الزخم
                momentum_score = self._calculate_momentum_score(df)
                
                if momentum_score > 50:  # حد أدنى للنقاط
                    coin['momentum_score'] = momentum_score
                    coin['df_1h'] = df
                    momentum_coins.append(coin)
                    
            except Exception as e:
                logger.debug(f"خطأ في تحليل زخم {symbol}: {e}")
                continue
        
        return momentum_coins
    
    def _calculate_momentum_score(self, df: pd.DataFrame) -> float:
        """حساب نقاط الزخم بناءً على عدة مؤشرات"""
        try:
            score = 0.0
            
            # 1. اتجاه السعر (Price Trend)
            recent_prices = df['close'].tail(6)
            older_prices = df['close'].tail(12).head(6)
            
            recent_avg = recent_prices.mean()
            older_avg = older_prices.mean()
            
            if recent_avg > older_avg:
                price_increase = ((recent_avg - older_avg) / older_avg) * 100
                score += min(price_increase * 5, 30)  # حد أقصى 30 نقطة
            
            # 2. زيادة الحجم (Volume Increase)
            recent_volume = df['quote_volume'].tail(6).mean()
            older_volume = df['quote_volume'].tail(12).head(6).mean()
            
            if older_volume > 0:
                volume_increase = ((recent_volume - older_volume) / older_volume) * 100
                if volume_increase > 0:
                    score += min(volume_increase * 0.5, 25)  # حد أقصى 25 نقطة
            
            # 3. قوة المشترين (Buyer Strength)
            recent_buyer_volume = df['taker_buy_quote'].tail(6).sum()
            recent_total_volume = df['quote_volume'].tail(6).sum()
            
            if recent_total_volume > 0:
                buyer_ratio = recent_buyer_volume / recent_total_volume
                if buyer_ratio > 0.5:  # أكثر من 50% مشتريات
                    score += (buyer_ratio - 0.5) * 100  # حد أقصى 25 نقطة
            
            # 4. استقرار الاتجاه (Trend Stability)
            price_changes = df['close'].pct_change().tail(6)
            positive_changes = (price_changes > 0).sum()
            
            if positive_changes >= 4:  # 4 من 6 إيجابية
                score += 20
            
            return score
            
        except Exception as e:
            logger.debug(f"خطأ في حساب نقاط الزخم: {e}")
            return 0.0
    
    def _analyze_smart_money_flow(self, coins: List[Dict]) -> List[Dict]:
        """تحليل تدفق السيولة الذكية"""
        analyzed_coins = []
        
        for coin in coins:
            try:
                df = coin.get('df_1h')
                if df is None or len(df) < 6:
                    continue
                
                # حساب نسبة المشترين في آخر 6 ساعات
                recent_buyer_volume = df['taker_buy_quote'].tail(6).sum()
                recent_total_volume = df['quote_volume'].tail(6).sum()
                
                if recent_total_volume > 0:
                    buyer_ratio = recent_buyer_volume / recent_total_volume
                    coin['buyer_ratio'] = buyer_ratio
                    
                    # حساب تغير الحجم
                    recent_volume = df['quote_volume'].tail(6).mean()
                    older_volume = df['quote_volume'].tail(12).head(6).mean()
                    
                    if older_volume > 0:
                        volume_increase = ((recent_volume - older_volume) / older_volume) * 100
                        coin['volume_increase'] = volume_increase
                    else:
                        coin['volume_increase'] = 0.0
                    
                    analyzed_coins.append(coin)
                    
            except Exception as e:
                logger.debug(f"خطأ في تحليل {coin['symbol']}: {e}")
                continue
        
        return analyzed_coins
    
    def _calculate_final_scores(self, coins: List[Dict]) -> List[Dict]:
        """حساب النقاط النهائية المركبة"""
        scored_coins = []
        
        for coin in coins:
            try:
                total_score = 0.0
                
                # 1. نقاط الزخم (40%)
                momentum = coin.get('momentum_score', 0)
                total_score += momentum * 0.4
                
                # 2. نقاط نسبة المشترين (30%)
                buyer_ratio = coin.get('buyer_ratio', 0.5)
                if buyer_ratio > 0.5:
                    total_score += (buyer_ratio - 0.5) * 200 * 0.3
                
                # 3. نقاط زيادة الحجم (20%)
                volume_increase = coin.get('volume_increase', 0)
                if volume_increase > 0:
                    total_score += min(volume_increase * 0.5, 50) * 0.2
                
                # 4. نقاط تغير السعر (10%)
                price_change = coin.get('price_change', 0)
                if 2 <= price_change <= 15:  # النطاق المثالي
                    total_score += price_change * 2 * 0.1
                
                coin['total_score'] = total_score
                scored_coins.append(coin)
                
            except Exception as e:
                logger.debug(f"خطأ في حساب النقاط لـ {coin['symbol']}: {e}")
                continue
        
        return scored_coins
    
    def _get_fallback_coins(self, limit: int) -> List[str]:
        """قائمة احتياطية عند فشل النظام الذكي"""
        logger.warning("⚠️ استخدام القائمة الاحتياطية")
        
        fallback = [
            'ARBUSDT', 'OPUSDT', 'APTUSDT', 'SUIUSDT', 'INJUSDT',
            'TIAUSDT', 'SEIUSDT', 'JUPUSDT', 'WLDUSDT', 'PYTHUSDT',
            'PENDLEUSDT', 'WIFUSDT', 'AIUSDT', 'ALTUSDT', 'NEARUSDT',
            'RNDRUSDT', 'FETUSDT', 'GMXUSDT', 'ARUSDT', 'MANTAUSDT'
        ]
        
        return fallback[:limit]
    
    def get_coin_detailed_analysis(self, symbol: str) -> Dict[str, Any]:
        """تحليل تفصيلي لعملة واحدة"""
        try:
            ticker = self.client.get_ticker(symbol=symbol)
            
            # جلب كاندلات
            klines_1h = self.client.get_klines(symbol=symbol, interval='1h', limit=24)
            klines_4h = self.client.get_klines(symbol=symbol, interval='4h', limit=24)
            
            df_1h = pd.DataFrame(klines_1h, columns=[
                'time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df_1h['close'] = df_1h['close'].astype(float)
            df_1h['volume'] = df_1h['volume'].astype(float)
            df_1h['quote_volume'] = df_1h['quote_volume'].astype(float)
            df_1h['taker_buy_quote'] = df_1h['taker_buy_quote'].astype(float)
            
            momentum_score = self._calculate_momentum_score(df_1h)
            
            # حساب نسبة المشترين
            buyer_volume = df_1h['taker_buy_quote'].tail(6).sum()
            total_volume = df_1h['quote_volume'].tail(6).sum()
            buyer_ratio = buyer_volume / total_volume if total_volume > 0 else 0
            
            return {
                'symbol': symbol,
                'price': float(ticker['lastPrice']),
                'price_change_24h': float(ticker['priceChangePercent']),
                'volume_24h_usdt': float(ticker['quoteVolume']),
                'momentum_score': momentum_score,
                'buyer_ratio': buyer_ratio,
                'trade_count_24h': int(ticker['count']),
                'recommendation': 'قوي' if momentum_score > 70 else 'متوسط' if momentum_score > 50 else 'ضعيف'
            }
            
        except Exception as e:
            logger.error(f"خطأ في التحليل التفصيلي لـ {symbol}: {e}")
            return {}
