#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار نظام تأكيد الانعكاس متعدد الأطر (MTF Reversal Confirmation)
يختبر على بيانات حقيقية من Binance
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
import logging

from cognitive import (
    get_market_state_detector,
    get_asset_classifier,
    get_pattern_objective_analyzer,
    get_mtf_reversal_confirmation
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def fetch_binance_data(symbol: str, timeframe: str, limit: int = 100):
    """جلب البيانات من Binance"""
    try:
        exchange = ccxt.binance()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # حساب المؤشرات
        df = add_indicators(df)
        
        return df
    except Exception as e:
        logger.error(f"خطأ في جلب {symbol}: {e}")
        return None


def add_indicators(df):
    """إضافة المؤشرات الفنية"""
    try:
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # Support/Resistance (بسيط)
        df['support'] = df['low'].rolling(window=20).min()
        df['resistance'] = df['high'].rolling(window=20).max()
        
        return df
    except Exception as e:
        logger.error(f"خطأ في حساب المؤشرات: {e}")
        return df


def test_mtf_reversal_confirmation():
    """اختبار نظام MTF على عملات حقيقية"""
    
    logger.info("="*100)
    logger.info("🧪 اختبار نظام تأكيد الانعكاس متعدد الأطر (MTF)")
    logger.info("="*100)
    
    # العملات للاختبار
    symbols = [
        'BTC/USDT',
        'ETH/USDT',
        'BNB/USDT',
        'SOL/USDT',
        'XRP/USDT',
        'ADA/USDT',
        'DOT/USDT',
        'MATIC/USDT',
        'LINK/USDT',
        'AVAX/USDT'
    ]
    
    # الأنظمة
    market_detector = get_market_state_detector()
    asset_classifier = get_asset_classifier()
    pattern_analyzer = get_pattern_objective_analyzer()
    mtf_reversal = get_mtf_reversal_confirmation()
    
    results = {
        'total': 0,
        'bullish_confirmed': 0,
        'bullish_weak': 0,
        'bearish_confirmed': 0,
        'bearish_weak': 0,
        'no_reversal': 0,
        'high_quality_entries': 0,
        'details': []
    }
    
    for symbol in symbols:
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"📊 تحليل {symbol}")
            logger.info(f"{'='*80}")
            
            # جلب البيانات
            logger.info("جلب بيانات 1H...")
            df_1h = fetch_binance_data(symbol, '1h', limit=100)
            
            logger.info("جلب بيانات 15m...")
            df_15m = fetch_binance_data(symbol, '15m', limit=100)
            
            if df_1h is None or df_15m is None:
                logger.error(f"فشل جلب البيانات لـ {symbol}")
                continue
            
            results['total'] += 1
            
            # التحليل الأساسي
            market_state = market_detector.detect_state(df_1h, symbol)
            asset_class = asset_classifier.classify_asset(symbol, df_1h)
            
            logger.info(f"حالة السوق: {market_state.state.value} ({market_state.confidence:.0f}%)")
            logger.info(f"نوع الأصل: {asset_class.asset_type.value}")
            
            current_price = df_1h['close'].iloc[-1]
            
            # اختبار تأكيد الانعكاس الصعودي
            logger.info("\n🔍 اختبار الانعكاس الصعودي...")
            bullish_signal = mtf_reversal.confirm_bullish_reversal(
                df_1h=df_1h,
                df_15m=df_15m,
                current_price=current_price
            )
            
            logger.info(f"  النوع: {bullish_signal.type.value}")
            logger.info(f"  القوة: {bullish_signal.strength.value}")
            logger.info(f"  الثقة: {bullish_signal.confidence:.0f}%")
            logger.info(f"  الأطر المؤكدة: {bullish_signal.timeframes_confirmed}")
            logger.info(f"  الأنماط: {bullish_signal.patterns_detected}")
            logger.info(f"  المؤشرات الموافقة: {bullish_signal.indicators_aligned}")
            logger.info(f"  الشموع منذ الانعكاس: {bullish_signal.candles_since_reversal}")
            logger.info(f"  جودة الدخول: {bullish_signal.entry_quality:.0f}%")
            logger.info(f"  التفسير: {bullish_signal.reasoning}")
            
            # تصنيف النتيجة
            if bullish_signal.type.value == 'bullish':
                if bullish_signal.confidence >= 60:
                    results['bullish_confirmed'] += 1
                    logger.info("  ✅ انعكاس صعودي مؤكد!")
                    
                    if bullish_signal.entry_quality >= 70:
                        results['high_quality_entries'] += 1
                        logger.info("  ⭐ جودة دخول عالية!")
                else:
                    results['bullish_weak'] += 1
                    logger.info("  ⚠️ انعكاس صعودي ضعيف")
            
            # اختبار تأكيد الانعكاس الهبوطي (للخروج)
            logger.info("\n🔍 اختبار الانعكاس الهبوطي...")
            bearish_signal = mtf_reversal.confirm_bearish_reversal(
                df_1h=df_1h,
                df_15m=df_15m,
                current_price=current_price,
                entry_price=current_price * 0.98  # افتراضي
            )
            
            logger.info(f"  النوع: {bearish_signal.type.value}")
            logger.info(f"  القوة: {bearish_signal.strength.value}")
            logger.info(f"  الثقة: {bearish_signal.confidence:.0f}%")
            logger.info(f"  الأطر المؤكدة: {bearish_signal.timeframes_confirmed}")
            logger.info(f"  التفسير: {bearish_signal.reasoning}")
            
            if bearish_signal.type.value == 'bearish':
                if bearish_signal.confidence >= 60:
                    results['bearish_confirmed'] += 1
                    logger.info("  ⚠️ انعكاس هبوطي مؤكد - إشارة خروج!")
                else:
                    results['bearish_weak'] += 1
                    logger.info("  ℹ️ انعكاس هبوطي ضعيف")
            
            if bullish_signal.type.value == 'none' and bearish_signal.type.value == 'none':
                results['no_reversal'] += 1
            
            # حفظ التفاصيل
            results['details'].append({
                'symbol': symbol,
                'market_state': market_state.state.value,
                'bullish_confidence': bullish_signal.confidence,
                'bullish_quality': bullish_signal.entry_quality,
                'bearish_confidence': bearish_signal.confidence,
                'price': current_price
            })
            
        except Exception as e:
            logger.error(f"خطأ في تحليل {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    # التقرير النهائي
    print_final_report(results)


def print_final_report(results):
    """طباعة التقرير النهائي"""
    logger.info("\n" + "="*100)
    logger.info("📊 التقرير النهائي - MTF Reversal Confirmation System")
    logger.info("="*100)
    
    total = results['total']
    if total == 0:
        logger.warning("لا توجد بيانات للتحليل!")
        return
    
    logger.info(f"\n📈 الإحصائيات العامة:")
    logger.info(f"  إجمالي العملات: {total}")
    logger.info(f"  انعكاسات صعودية مؤكدة: {results['bullish_confirmed']} ({results['bullish_confirmed']/total*100:.1f}%)")
    logger.info(f"  انعكاسات صعودية ضعيفة: {results['bullish_weak']} ({results['bullish_weak']/total*100:.1f}%)")
    logger.info(f"  انعكاسات هبوطية مؤكدة: {results['bearish_confirmed']} ({results['bearish_confirmed']/total*100:.1f}%)")
    logger.info(f"  انعكاسات هبوطية ضعيفة: {results['bearish_weak']} ({results['bearish_weak']/total*100:.1f}%)")
    logger.info(f"  بدون انعكاس: {results['no_reversal']} ({results['no_reversal']/total*100:.1f}%)")
    
    logger.info(f"\n⭐ جودة الإشارات:")
    logger.info(f"  إشارات دخول عالية الجودة: {results['high_quality_entries']} ({results['high_quality_entries']/total*100:.1f}%)")
    
    # أفضل الفرص
    logger.info(f"\n🎯 أفضل فرص الدخول (جودة عالية):")
    high_quality = [d for d in results['details'] if d['bullish_quality'] >= 70]
    high_quality = sorted(high_quality, key=lambda x: x['bullish_quality'], reverse=True)
    
    for i, detail in enumerate(high_quality[:5], 1):
        logger.info(
            f"  {i}. {detail['symbol']}: "
            f"جودة {detail['bullish_quality']:.0f}% | "
            f"ثقة {detail['bullish_confidence']:.0f}% | "
            f"{detail['market_state']}"
        )
    
    # إشارات الخروج
    logger.info(f"\n🚨 إشارات الخروج (انعكاس هبوطي قوي):")
    exit_signals = [d for d in results['details'] if d['bearish_confidence'] >= 60]
    exit_signals = sorted(exit_signals, key=lambda x: x['bearish_confidence'], reverse=True)
    
    for i, detail in enumerate(exit_signals[:5], 1):
        logger.info(
            f"  {i}. {detail['symbol']}: "
            f"ثقة {detail['bearish_confidence']:.0f}% | "
            f"{detail['market_state']}"
        )
    
    logger.info("\n" + "="*100)
    logger.info("✅ اكتمل الاختبار!")
    logger.info("="*100)


def test_integration_with_cognitive():
    """اختبار التكامل مع النظام المعرفي الكامل"""
    logger.info("\n" + "="*100)
    logger.info("🧠 اختبار التكامل مع النظام المعرفي")
    logger.info("="*100)
    
    symbol = 'BTC/USDT'
    
    # جلب البيانات
    df_1h = fetch_binance_data(symbol, '1h', limit=100)
    df_15m = fetch_binance_data(symbol, '15m', limit=100)
    
    if df_1h is None or df_15m is None:
        logger.error("فشل جلب البيانات!")
        return
    
    # الأنظمة
    market_detector = get_market_state_detector()
    asset_classifier = get_asset_classifier()
    pattern_analyzer = get_pattern_objective_analyzer()
    
    # التحليل
    market_state = market_detector.detect_state(df_1h, symbol)
    asset_class = asset_classifier.classify_asset(symbol, df_1h)
    
    # تحليل الهدف مع MTF
    objective = pattern_analyzer.determine_objective(
        market_state=market_state,
        asset_class=asset_class,
        df=df_1h,
        df_15m=df_15m,  # إضافة 15m للتأكيد
        symbol=symbol
    )
    
    logger.info(f"\n📊 نتيجة التحليل المتكامل:")
    logger.info(f"  الهدف: {objective.objective.value}")
    logger.info(f"  الثقة: {objective.confidence:.0f}%")
    logger.info(f"  R:R: {objective.risk_reward_ratio:.2f}")
    
    if hasattr(objective, 'reversal_confirmed'):
        logger.info(f"\n  🔍 تأكيد MTF:")
        logger.info(f"    الانعكاس مؤكد: {'✅ نعم' if objective.reversal_confirmed else '❌ لا'}")
        logger.info(f"    ثقة الانعكاس: {objective.reversal_confidence:.0f}%")
        logger.info(f"    الأطر المؤكدة: {objective.reversal_timeframes}")
        logger.info(f"    جودة الدخول: {objective.entry_quality:.0f}%")
    
    logger.info(f"\n  التفسير: {objective.reasoning}")


if __name__ == "__main__":
    # اختبار نظام MTF
    test_mtf_reversal_confirmation()
    
    # اختبار التكامل
    test_integration_with_cognitive()
