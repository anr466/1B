#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
مزود البيانات لنظام التداول
يستخدم عميل البروكسي لـ Binance لتجنب حظر IP وتحقيق تحليل دقيق للعملات
"""

import os
import time
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import pickle
import hashlib
from pathlib import Path

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

# استيراد نظام Retry Logic
try:
    from backend.utils.retry_utils import (
        retry_on_network_error,
        retry_on_api_error,
        retry_aggressive,
        DEFAULT_RETRY_CONFIG
    )
    RETRY_AVAILABLE = True
except ImportError:
    RETRY_AVAILABLE = False

# استيراد نظام Circuit Breaker
try:
    from backend.utils.circuit_breaker import (
        circuit_breaker,
        circuit_breaker_manager,
        DATA_PROVIDER_BREAKER_CONFIG
    )
    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False

# إعداد التسجيل
logger = logging.getLogger(__name__)

class DataProvider:
    """
    مزود البيانات لجلب وتخزين بيانات التداول من Binance مع دعم التخزين المؤقت وتجنب حظر IP
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None, 
                use_testnet: bool = False, cache_dir: str = None,
                cache_ttl: int = 3600, rate_limit_per_minute: int = 60):
        """
        تهيئة مزود البيانات
        
        Args:
            api_key: مفتاح API لـ Binance (اختياري)
            api_secret: كلمة سر API لـ Binance (اختياري)
            use_testnet: استخدام بيئة الاختبار Testnet (اختياري، افتراضي False)
            cache_dir: مسار دليل التخزين المؤقت (اختياري)
            cache_ttl: فترة صلاحية التخزين المؤقت بالثواني (افتراضي: ساعة واحدة)

            rate_limit_per_minute: حد الطلبات لكل دقيقة (افتراضي: 60)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.use_testnet = use_testnet
        
        # إنشاء عميل Binance مباشرة
        try:
            self.client = Client(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=self.use_testnet,
                requests_params={'timeout': 30}  # زيادة timeout لتجنب الأخطاء
            )
        except Exception as e:
            logger.debug(f"تأخير في إنشاء عميل Binance: {e}")
            self.client = None
        
        # إعدادات الاتصال البديل
        self._connection_errors = []
        self._last_successful_connection = None
        self._fallback_mode = False
        
        # إعدادات إعادة الاتصال التلقائي
        self._auto_reconnect_enabled = True
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 5  # ثواني
        self._last_reconnect_check = None
        
        # إدارة معدل الطلبات
        self.rate_limit_per_minute = rate_limit_per_minute
        self.request_count = 0
        self.minute_start_time = time.time()
        
        # إعداد التخزين المؤقت
        if cache_dir is None:
            _project_root = Path(__file__).parent.parent.parent
            cache_dir = _project_root / ".cache"
        self.cache_dir = Path(cache_dir)
        self.cache_ttl = cache_ttl
        self.price_cache_ttl = 2
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            import tempfile
            self.cache_dir = Path(tempfile.gettempdir()) / "trading_ai_cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # قائمة مؤقتة لأزواج التداول الشائعة للتقليل من استدعاءات API
        self.common_pairs = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT",
            "DOGEUSDT", "DOTUSDT", "UNIUSDT", "BCHUSDT", "LTCUSDT",
            "LINKUSDT", "MATICUSDT", "XLMUSDT", "ETCUSDT", "THETAUSDT",
            "VETUSDT", "TRXUSDT", "FILUSDT", "XMRUSDT", "EOSUSDT"
        ]
    
    def _get_cache_key(self, prefix: str, **kwargs) -> str:
        """
        إنشاء مفتاح للتخزين المؤقت بناءً على البارامترات
        
        Args:
            prefix: بادئة المفتاح
            **kwargs: البارامترات المستخدمة لإنشاء المفتاح
            
        Returns:
            str: مفتاح التخزين المؤقت
        """
        # تحويل البارامترات إلى سلسلة نصية مرتبة
        params_str = '&'.join([f"{k}={v}" for k, v in sorted(kwargs.items())])
        key = f"{prefix}_{params_str}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """
        الحصول على مسار ملف التخزين المؤقت
        
        Args:
            cache_key: مفتاح التخزين المؤقت
            
        Returns:
            Path: مسار ملف التخزين المؤقت
        """
        return self.cache_dir / f"{cache_key}.pkl"
    
    def _save_to_cache(self, data: any, cache_key: str) -> None:
        """
        حفظ البيانات في التخزين المؤقت
        
        Args:
            data: البيانات المراد حفظها
            cache_key: مفتاح التخزين المؤقت
        """
        try:
            cache_path = self._get_cache_path(cache_key)
            cache_data = {
                'timestamp': time.time(),
                'data': data
            }
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
                
            logger.debug(f"تم حفظ البيانات في التخزين المؤقت: {cache_key}")
        except Exception as e:
            logger.warning(f"فشل في حفظ البيانات في التخزين المؤقت: {str(e)}")
    
    def _load_from_cache(self, cache_key: str) -> Tuple[bool, any]:
        """
        تحميل البيانات من التخزين المؤقت
        
        Args:
            cache_key: مفتاح التخزين المؤقت
            
        Returns:
            Tuple[bool, any]: (نجاح/فشل، البيانات أو None)
        """
        cache_path = self._get_cache_path(cache_key)
        
        try:
            if not cache_path.exists():
                return False, None
            
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            # التحقق من صلاحية التخزين المؤقت
            if time.time() - cache_data['timestamp'] > self.cache_ttl:
                logger.debug(f"التخزين المؤقت منتهي الصلاحية: {cache_key}")
                return False, None
            
            logger.debug(f"تم تحميل البيانات من التخزين المؤقت: {cache_key}")
            return True, cache_data['data']
            
        except Exception as e:
            logger.warning(f"فشل في تحميل البيانات من التخزين المؤقت: {str(e)}")
            return False, None
    
    def _manage_rate_limit(self) -> None:
        """
        إدارة معدل الطلبات لتجنب تجاوز حدود API (محسنة للمعالجة المتوازية)
        """
        current_time = time.time()
        elapsed = current_time - self.minute_start_time
        
        # إعادة تعيين العداد بعد دقيقة
        if elapsed > 60:
            self.minute_start_time = current_time
            self.request_count = 0
            return
        
        # التحقق من تجاوز الحد
        if self.request_count >= self.rate_limit_per_minute:
            wait_time = 60 - elapsed + 1
            logger.warning(f"تجاوز حد الطلبات. انتظار {wait_time:.2f} ثانية...")
            
            # استخدام انتظار تدريجي بدلاً من توقف كامل
            # هذا يسمح للخيوط الأخرى بالاستمرار
            sleep_intervals = min(int(wait_time), 10)  # أقصى 10 فترات
            sleep_duration = wait_time / sleep_intervals
            
            for i in range(sleep_intervals):
                time.sleep(sleep_duration)
                # فحص إذا كان هناك خيوط أخرى تحتاج للمتابعة
                if i % 3 == 0:  # كل 3 فترات
                    logger.debug(f"انتظار API: {(i+1)*sleep_duration:.1f}/{wait_time:.1f} ثانية")
            
            self.minute_start_time = time.time()
            self.request_count = 0
        
        # زيادة عداد الطلبات
        self.request_count += 1
    
    @retry_on_network_error
    @circuit_breaker(name="data_provider_klines", failure_threshold=3, recovery_timeout=30)
    def _fetch_klines_from_api(self, symbol: str, interval: str, limit: int):
        """جلب بيانات الشموع من API مع Retry Logic و Circuit Breaker"""
        return self.client.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit
        )
    
    def get_klines(self, symbol: str, interval: str = '1h', 
                  limit: int = 500, calculate_indicators: bool = False) -> pd.DataFrame:
        """
        الحصول على بيانات الشموع (Klines) لزوج تداول معين
        
        Args:
            symbol: رمز زوج التداول (مثل 'BTCUSDT')
            interval: الفاصل الزمني ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: عدد الشموع للجلب (أقصى حد 1000)
            calculate_indicators: حساب المؤشرات الفنية
            
        Returns:
            pd.DataFrame: إطار بيانات يحتوي على بيانات الشموع
        """
        # التحقق من معدل الطلبات
        self._manage_rate_limit()
        
        # فحص الاتصال وإعادة الاتصال التلقائي إذا لزم الأمر
        if not self.check_and_reconnect():
            logger.warning("⚠️ Connection issue, trying with cached data...")
        
        # إنشاء مفتاح التخزين المؤقت
        cache_key = self._get_cache_key(
            'klines', symbol=symbol, interval=interval, limit=limit
        )
        
        # محاولة تحميل البيانات من التخزين المؤقت
        success, cached_data = self._load_from_cache(cache_key)
        if success:
            df = cached_data
            if calculate_indicators and not self._has_indicators(df):
                df = self._calculate_technical_indicators(df)
            return df
        
        # جلب البيانات من API مع Retry Logic
        try:
            # جلب البيانات من Binance API مع إعادة المحاولة
            if RETRY_AVAILABLE:
                klines = self._fetch_klines_from_api(symbol, interval, limit)
            else:
                klines = self.client.get_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=limit
                )
            
            # تحويل البيانات إلى إطار بيانات
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # تحويل أنواع البيانات
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                              'quote_asset_volume', 'taker_buy_base_asset_volume', 
                              'taker_buy_quote_asset_volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
            
            # تحويل الطوابع الزمنية
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            # تعيين الطابع الزمني كفهرس
            df.set_index('timestamp', inplace=True)
            
            # حساب المؤشرات الفنية إذا كان مطلوبًا
            if calculate_indicators:
                df = self._calculate_technical_indicators(df)
            
            # حفظ البيانات في التخزين المؤقت
            self._save_to_cache(df, cache_key)
            
            return df
            
        except Exception as e:
            logger.error(f"فشل في جلب بيانات الشموع لـ {symbol}: {str(e)}")
            
            # إرجاع بيانات فارغة في حالة الفشل
            return pd.DataFrame()
    
    def _has_indicators(self, df: pd.DataFrame) -> bool:
        """
        التحقق مما إذا كان إطار البيانات يحتوي على المؤشرات الفنية
        
        Args:
            df: إطار البيانات
            
        Returns:
            bool: True إذا كان يحتوي على المؤشرات، False خلاف ذلك
        """
        indicator_columns = ['sma_20', 'ema_50', 'rsi_14', 'volume_change']
        return all(col in df.columns for col in indicator_columns)
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        حساب المؤشرات الفنية لإطار البيانات
        
        Args:
            df: إطار البيانات
            
        Returns:
            pd.DataFrame: إطار البيانات مع المؤشرات الفنية المضافة
        """
        if df.empty:
            return df
        
        try:
            # نسخة من إطار البيانات
            df_copy = df.copy()
            
            # المتوسط المتحرك البسيط (SMA)
            df_copy['sma_20'] = df_copy['close'].rolling(window=20).mean()
            
            # المتوسط المتحرك الأسي (EMA)
            df_copy['ema_50'] = df_copy['close'].ewm(span=50, adjust=False).mean()
            
            # مؤشر القوة النسبية (RSI)
            delta = df_copy['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=14).mean()
            avg_loss = loss.rolling(window=14).mean()
            rs = avg_gain / avg_loss
            df_copy['rsi_14'] = 100 - (100 / (1 + rs))
            
            # مؤشر تقلب بولينجر (Bollinger Bands)
            df_copy['bb_middle'] = df_copy['close'].rolling(window=20).mean()
            df_copy['bb_stddev'] = df_copy['close'].rolling(window=20).std()
            df_copy['bb_upper'] = df_copy['bb_middle'] + 2 * df_copy['bb_stddev']
            df_copy['bb_lower'] = df_copy['bb_middle'] - 2 * df_copy['bb_stddev']
            
            # تغير الحجم
            df_copy['volume_change'] = df_copy['volume'].pct_change() * 100
            
            # تغير السعر
            df_copy['price_change'] = df_copy['close'].pct_change() * 100
            
            # متوسط المدى الحقيقي (ATR)
            high_low = df_copy['high'] - df_copy['low']
            high_close = (df_copy['high'] - df_copy['close'].shift()).abs()
            low_close = (df_copy['low'] - df_copy['close'].shift()).abs()
            ranges = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df_copy['atr_14'] = ranges.rolling(window=14).mean()
            
            # مؤشر تدفق المال (MFI)
            typical_price = (df_copy['high'] + df_copy['low'] + df_copy['close']) / 3
            money_flow = typical_price * df_copy['volume']
            
            positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
            negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
            
            positive_mf = positive_flow.rolling(window=14).sum()
            negative_mf = negative_flow.rolling(window=14).sum()
            
            money_ratio = positive_mf / negative_mf
            df_copy['mfi_14'] = 100 - (100 / (1 + money_ratio))
            
            # مؤشر الانحراف والتقارب المتوسط المتحرك (MACD)
            df_copy['ema_12'] = df_copy['close'].ewm(span=12, adjust=False).mean()
            df_copy['ema_26'] = df_copy['close'].ewm(span=26, adjust=False).mean()
            df_copy['macd'] = df_copy['ema_12'] - df_copy['ema_26']
            df_copy['macd_signal'] = df_copy['macd'].ewm(span=9, adjust=False).mean()
            df_copy['macd_hist'] = df_copy['macd'] - df_copy['macd_signal']
            
            return df_copy
            
        except Exception as e:
            logger.error(f"فشل في حساب المؤشرات الفنية: {str(e)}")
            return df
    
    @retry_on_network_error
    @circuit_breaker(name="data_provider_tickers", failure_threshold=3, recovery_timeout=30)
    def _fetch_tickers_from_api(self):
        """جلب بيانات Tickers من API مع Retry Logic و Circuit Breaker"""
        return self.client.get_ticker()
    
    def get_top_volume_coins(self, limit: int = 20, min_volume: float = 1000000) -> List[str]:
        """
        الحصول على العملات الأعلى من حيث حجم التداول
        
        Args:
            limit: عدد العملات للإرجاع
            min_volume: الحد الأدنى للحجم اليومي
            
        Returns:
            List[str]: قائمة برموز العملات
        """
        try:
            # جلب جميع البيانات من get_ticker مع Retry Logic
            if RETRY_AVAILABLE:
                tickers = self._fetch_tickers_from_api()
            else:
                tickers = self.client.get_ticker()
            
            # فلترة أزواج USDT فقط
            usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
            
            # فلترة حسب الحد الأدنى للحجم
            filtered_pairs = []
            for ticker in usdt_pairs:
                try:
                    volume_24h = float(ticker['quoteVolume'])
                    if volume_24h >= min_volume:
                        filtered_pairs.append(ticker)
                except (KeyError, ValueError, TypeError):
                    continue
            
            # ترتيب حسب الحجم من الأعلى إلى الأدنى
            sorted_pairs = sorted(filtered_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)
            
            # استخراج أسماء العملات
            top_coins = [ticker['symbol'] for ticker in sorted_pairs[:limit]]
            
            return top_coins
            
        except Exception as e:
            logger.error(f"خطأ في جلب العملات الأعلى حجماً: {str(e)}")
            return self.common_pairs[:limit]
    
    def get_top_volume_pairs(self, quote_asset: str = 'USDT', limit: int = 20) -> List[str]:
        """
        الحصول على أزواج التداول الأعلى من حيث حجم التداول
        
        Args:
            quote_asset: الأصل المقتبس (مثل 'USDT', 'BTC')
            limit: عدد الأزواج للإرجاع
            
        Returns:
            List[str]: قائمة برموز أزواج التداول
        """
        # التحقق من معدل الطلبات
        self._manage_rate_limit()
        
        # إنشاء مفتاح التخزين المؤقت
        cache_key = self._get_cache_key(
            'top_volume', quote_asset=quote_asset, limit=limit
        )
        
        # محاولة تحميل البيانات من التخزين المؤقت
        success, cached_data = self._load_from_cache(cache_key)
        if success:
            return cached_data
        
        try:
            # جلب المعلومات من Binance API مع Retry Logic
            if RETRY_AVAILABLE:
                tickers = self._fetch_tickers_from_api()
            else:
                tickers = self.client.get_ticker()
            
            # تصفية الأزواج بناءً على الأصل المقتبس
            filtered_tickers = [t for t in tickers if t['symbol'].endswith(quote_asset)]
            
            # ترتيب حسب حجم التداول (من الأعلى إلى الأدنى)
            sorted_tickers = sorted(
                filtered_tickers, 
                key=lambda x: float(x['quoteVolume']), 
                reverse=True
            )
            
            # الحصول على رموز الأزواج
            top_pairs = [t['symbol'] for t in sorted_tickers[:limit]]
            
            # حفظ البيانات في التخزين المؤقت
            self._save_to_cache(top_pairs, cache_key)
            
            return top_pairs
            
        except Exception as e:
            logger.error(f"فشل في جلب أزواج التداول الأعلى من حيث الحجم: {str(e)}")
            
            # في حالة الفشل، إرجاع قائمة أزواج التداول الشائعة
            return self.common_pairs[:limit]
    
    @retry_on_network_error
    @circuit_breaker(name="data_provider_exchange_info", failure_threshold=3, recovery_timeout=60)
    def _fetch_exchange_info_from_api(self):
        """جلب معلومات البورصة من API مع Retry Logic و Circuit Breaker"""
        return self.client.get_exchange_info()
    
    def get_exchange_info(self) -> Dict:
        """
        الحصول على معلومات البورصة
        
        Returns:
            Dict: معلومات البورصة
        """
        # التحقق من معدل الطلبات
        self._manage_rate_limit()
        
        # إنشاء مفتاح التخزين المؤقت
        cache_key = self._get_cache_key('exchange_info')
        
        # محاولة تحميل البيانات من التخزين المؤقت
        success, cached_data = self._load_from_cache(cache_key)
        if success:
            return cached_data
        
        try:
            # جلب المعلومات من Binance API مع Retry Logic
            if RETRY_AVAILABLE:
                info = self._fetch_exchange_info_from_api()
            else:
                info = self.client.get_exchange_info()
            
            # حفظ البيانات في التخزين المؤقت (مدة صلاحية أطول - 24 ساعة)
            self._save_to_cache(info, cache_key)
            
            return info
            
        except Exception as e:
            logger.error(f"فشل في جلب معلومات البورصة: {str(e)}")
            return {}
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        الحصول على معلومات زوج تداول محدد
        
        Args:
            symbol: رمز زوج التداول (مثل 'BTCUSDT')
            
        Returns:
            Dict: معلومات زوج التداول
        """
        exchange_info = self.get_exchange_info()
        
        if not exchange_info or 'symbols' not in exchange_info:
            return {}
        
        # البحث عن معلومات الزوج المحدد
        for sym_info in exchange_info['symbols']:
            if sym_info['symbol'] == symbol:
                return sym_info
        
        return {}
    
    def get_historical_data(self, symbol: str, timeframe: str, start_date=None, end_date=None, limit: int = 500) -> pd.DataFrame:
        """
        جلب البيانات التاريخية للعملة
        
        Args:
            symbol: رمز العملة
            timeframe: الإطار الزمني
            start_date: تاريخ البداية (اختياري)
            end_date: تاريخ النهاية (اختياري)
            limit: عدد الشموع
            
        Returns:
            pd.DataFrame: البيانات التاريخية
        """
        return self.get_klines(symbol=symbol, interval=timeframe, limit=limit)
    
    @retry_on_network_error
    @circuit_breaker(name="data_provider_ticker", failure_threshold=3, recovery_timeout=30)
    def _fetch_symbol_ticker_from_api(self, symbol: str = None):
        """جلب أسعار الرموز من API مع Retry Logic و Circuit Breaker"""
        if symbol:
            return self.client.get_symbol_ticker(symbol=symbol)
        else:
            return self.client.get_symbol_ticker()
    
    def get_current_price(self, symbol: str = None) -> Union[Dict, float]:
        """
        الحصول على السعر الحالي
        
        Args:
            symbol: رمز زوج التداول (اختياري). إذا لم يتم تحديده، يتم إرجاع أسعار جميع الرموز.
            
        Returns:
            Union[Dict, float]: قاموس الأسعار الحالية أو سعر الرمز المحدد
        """
        # التحقق من معدل الطلبات
        self._manage_rate_limit()
        
        # فحص الاتصال وإعادة الاتصال التلقائي إذا لزم الأمر
        if not self.check_and_reconnect():
            logger.warning("⚠️ Connection issue, returning cached/default prices...")
        
        try:
            if symbol:
                cache_key = self._get_cache_key('current_price', symbol=symbol)
                success, cached_price = self._load_from_cache(cache_key)
                if success:
                    return float(cached_price)

            # جلب الأسعار من Binance API مع Retry Logic
            if RETRY_AVAILABLE:
                ticker_data = self._fetch_symbol_ticker_from_api(symbol)
            else:
                ticker_data = self.client.get_symbol_ticker(symbol=symbol) if symbol else self.client.get_symbol_ticker()
            
            if symbol:
                price = float(ticker_data['price'])
                original_ttl = self.cache_ttl
                try:
                    self.cache_ttl = self.price_cache_ttl
                    self._save_to_cache(price, cache_key)
                finally:
                    self.cache_ttl = original_ttl
                return price
            else:
                return {t['symbol']: float(t['price']) for t in ticker_data}
                
        except Exception as e:
            logger.error(f"فشل في جلب السعر الحالي: {str(e)}")
            return {} if symbol is None else 0.0

    def check_connection(self) -> Dict:
        """
        فحص حالة الاتصال بـ Binance مع تشخيص كامل
        
        Returns:
            Dict: حالة الاتصال مع تفاصيل المشكلة
        """
        result = {
            'connected': False,
            'latency_ms': None,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            start = time.time()
            # جرب الاتصال البسيط
            self.client.ping()
            latency = (time.time() - start) * 1000
            
            result['connected'] = True
            result['latency_ms'] = round(latency, 2)
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if 'resolve' in error_msg or 'nodename' in error_msg:
                result['error'] = 'DNS_ERROR'
                result['error_detail'] = 'فشل في حل اسم النطاق api.binance.com - تحقق من الاتصال بالإنترنت أو إعدادات DNS'
            elif 'connection' in error_msg:
                result['error'] = 'CONNECTION_ERROR'
                result['error_detail'] = 'فشل في الاتصال بـ Binance - تحقق من الاتصال بالإنترنت'
            elif 'timeout' in error_msg:
                result['error'] = 'TIMEOUT'
                result['error_detail'] = 'انتهت مهلة الاتصال - الشبكة بطيئة أو معطلة'
            elif '429' in error_msg:
                result['error'] = 'RATE_LIMIT'
                result['error_detail'] = 'تم تجاوز حد الطلبات - انتظر قليلاً'
            elif '401' in error_msg or '403' in error_msg:
                result['error'] = 'AUTH_ERROR'
                result['error_detail'] = 'خطأ في المصادقة - تحقق من مفاتيح API'
            else:
                result['error'] = 'UNKNOWN'
                result['error_detail'] = str(e)
        
        return result
    
    def get_connection_status(self) -> Dict:
        """
        الحصول على حالة الاتصال الشاملة مع جميع Circuit Breakers
        
        Returns:
            Dict: حالة شاملة للاتصال
        """
        status = self.check_connection()
        
        # إضافة حالة Circuit Breakers
        if CIRCUIT_BREAKER_AVAILABLE:
            try:
                breakers = circuit_breaker_manager.get_all_states()
                status['circuit_breakers'] = breakers
                
                # تحديد إذا كان أي circuit مفتوح
                open_breakers = [name for name, state in breakers.items() 
                               if state.get('state') == 'open']
                if open_breakers:
                    status['circuit_breakers_open'] = open_breakers
                    status['connected'] = False
                    status['error'] = 'CIRCUIT_OPEN'
                    status['error_detail'] = f'الدوائر التالية مفتوحة: {", ".join(open_breakers)}'
            except Exception as e:
                logger.warning(f"فشل في جلب حالة Circuit Breakers: {e}")
        
        return status
    
    def _record_connection_error(self, error: str):
        """تسجيل خطأ الاتصال ومحاولة إعادة الاتصال"""
        self._connection_errors.append({
            'timestamp': datetime.now(),
            'error': error
        })
        
        # الاحتفاظ بآخر 10 أخطاء
        if len(self._connection_errors) > 10:
            self._connection_errors = self._connection_errors[-10:]
        
        # إذا فشلنا عدة مرات متتالية، نعلم أننا في وضع الفشل
        recent_errors = len(self._connection_errors)
        if recent_errors >= 5:
            self._fallback_mode = True
            logger.warning(f"⚠️ وضع الفشل مفعل بعد {recent_errors} أخطاء متتالية")
        
        logger.error(f"❌ خطأ في الاتصال بـ Binance: {error}")
    
    def _on_successful_connection(self):
        """تسجيل اتصال ناجح"""
        self._last_successful_connection = datetime.now()
        self._connection_errors = []
        self._fallback_mode = False
        logger.info("✅ استعادة الاتصال بـ Binance")
    
    def retry_connection(self) -> Dict:
        """
        محاولة إعادة الاتصال مع Binance
        
        Returns:
            Dict: نتيجة محاولة إعادة الاتصال
        """
        result = {
            'success': False,
            'message': '',
            'latency_ms': None
        }
        
        try:
            start = time.time()
            self.client.ping()
            latency = (time.time() - start) * 1000
            
            result['success'] = True
            result['latency_ms'] = round(latency, 2)
            result['message'] = 'تم استعادة الاتصال بنجاح'
            
            self._on_successful_connection()
            
            # إعادة تعيين Circuit Breakers
            if CIRCUIT_BREAKER_AVAILABLE:
                circuit_breaker_manager.reset_all()
                result['message'] = 'تم استعادة الاتصال وإعادة تعيين الدوائر'
                
        except Exception as e:
            result['message'] = f'فشل إعادة الاتصال: {str(e)}'
        
        return result
    
    def _attempt_auto_reconnect(self) -> bool:
        """
        محاولة إعادة الاتصال التلقائي مع Exponential Backoff
        
        Returns:
            bool: True إذا نجح الاتصال
        """
        if not self._auto_reconnect_enabled:
            return False
        
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.warning(f"⚠️ reached max reconnect attempts ({self._max_reconnect_attempts})")
            return False
        
        # حساب التأخير مع Exponential Backoff
        delay = min(self._reconnect_delay * (2 ** self._reconnect_attempts), 60)
        self._reconnect_attempts += 1
        
        logger.info(f"🔄 Attempting auto-reconnect {self._reconnect_attempts}/{self._max_reconnect_attempts} in {delay}s...")
        time.sleep(delay)
        
        try:
            if self.client:
                self.client.ping()
                self._on_successful_connection()
                self._reconnect_attempts = 0
                logger.info("✅ Auto-reconnect successful!")
                return True
        except Exception as e:
            logger.warning(f"❌ Auto-reconnect failed: {e}")
        
        return False
    
    def handle_rate_limit(self, retry_after: int = None) -> None:
        """
        معالجة تجاوز حد الطلبات مع انتظار ذكي
        
        Args:
            retry_after: عدد الثواني للانتظار (اختياري)
        """
        wait_time = retry_after if retry_after else 60
        
        # استخدام انتظار تدريجي لتجنب تجميد النظام
        logger.warning(f"⚠️ Rate limit exceeded. Waiting {wait_time}s...")
        
        # تقسيم الانتظار إلى فترات أصغر مع فحص الحالة
        chunks = min(wait_time, 10)
        chunk_time = wait_time / chunks
        
        for i in range(int(chunks)):
            time.sleep(chunk_time)
            # فحص إذا كان يمكن الاستمرار
            if self.request_count < self.rate_limit_per_minute / 2:
                logger.info("✅ Rate limit recovered early")
                break
        
        # إعادة تعيين عداد الوقت
        self.minute_start_time = time.time()
        self.request_count = 0
    
    def check_and_reconnect(self) -> bool:
        """
        فحص الاتصال والمحاولة إذا كان هناك مشكلة
        
        Returns:
            bool: True إذا كان الاتصال نشط
        """
        if not self.client:
            return self._attempt_auto_reconnect()
        
        try:
            self.client.ping()
            if self._reconnect_attempts > 0:
                self._reconnect_attempts = 0
                self._on_successful_connection()
            return True
        except Exception as e:
            error_msg = str(e).lower()
            
            # فحص نوع الخطأ
            if '429' in error_msg:
                self.handle_rate_limit()
            elif 'timeout' in error_msg or 'connection' in error_msg or 'resolve' in error_msg:
                return self._attempt_auto_reconnect()
            
            return False
    
    def clear_cache(self, older_than: int = None) -> int:
        """
        مسح التخزين المؤقت
        
        Args:
            older_than: مسح العناصر الأقدم من عدد الثواني المحدد. إذا كانت None، مسح الكل.
            
        Returns:
            int: عدد الملفات التي تم مسحها
        """
        try:
            count = 0
            current_time = time.time()
            
            for cache_file in self.cache_dir.glob('*.pkl'):
                # مسح الكل أو التحقق من عمر الملف
                if older_than is None or (current_time - cache_file.stat().st_mtime > older_than):
                    cache_file.unlink()
                    count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"فشل في مسح التخزين المؤقت: {str(e)}")
            return 0

# دالة مساعدة لإنشاء مزود بيانات
def create_data_provider(api_key: str = None, api_secret: str = None,
                        use_testnet: bool = False, cache_dir: str = None,
                        cache_ttl: int = 3600, rate_limit_per_minute: int = 60) -> DataProvider:
    """
    إنشاء مزود بيانات جديد
    
    Args:
        api_key: مفتاح API لـ Binance (اختياري)
        api_secret: كلمة سر API لـ Binance (اختياري)
        use_testnet: استخدام بيئة الاختبار Testnet (اختياري، افتراضي False)
        cache_dir: مسار دليل التخزين المؤقت (اختياري)
        cache_ttl: فترة صلاحية التخزين المؤقت بالثواني (افتراضي: ساعة واحدة)

        rate_limit_per_minute: حد الطلبات لكل دقيقة (افتراضي: 60)
        
    Returns:
        DataProvider: مزود البيانات
    """
    return DataProvider(
        api_key=api_key,
        api_secret=api_secret,
        use_testnet=use_testnet,
        cache_dir=cache_dir,
        cache_ttl=cache_ttl,
        rate_limit_per_minute=rate_limit_per_minute
    )
