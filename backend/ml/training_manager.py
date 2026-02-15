#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Training Manager - إدارة تدريب ML
يجمع نتائج التداول ويدرب النموذج تلقائياً
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from backend.ml.signal_classifier import get_ml_classifier, MLSignalClassifier

logger = logging.getLogger(__name__)


class MLTrainingManager:
    """
    مدير تدريب ML
    
    يعمل مع Group B لجمع نتائج التداول وتدريب النموذج
    """
    
    def __init__(self):
        """تهيئة المدير"""
        self.classifier = get_ml_classifier()
        self.current_cycle_data = []
        self.cycle_count = 0
        
        logger.info("✅ تم تهيئة ML Training Manager")
    
    def start_cycle(self):
        """بدء دورة تدريب جديدة"""
        self.current_cycle_data = []
        self.cycle_count += 1
        logger.info(f"🔄 بدء دورة التدريب #{self.cycle_count}")
    
    def add_real_trade(self, 
                      symbol: str,
                      strategy: str,
                      timeframe: str,
                      entry_price: float,
                      exit_price: float,
                      profit_loss: float,
                      profit_pct: float,
                      indicators: Dict = None,
                      source: str = 'real_trading') -> bool:
        """
        إضافة صفقة حقيقية للتدريب (من التداول الفعلي فقط)
        
        Args:
            symbol: رمز العملة
            strategy: اسم الاستراتيجية
            timeframe: الإطار الزمني
            entry_price: سعر الدخول
            exit_price: سعر الخروج
            profit_loss: الربح/الخسارة
            profit_pct: نسبة الربح/الخسارة
            indicators: المؤشرات الفنية
            source: مصدر البيانات (demo_trading أو real_trading)
            
        Returns:
            True إذا تمت الإضافة بنجاح
        """
        try:
            # استيراد النظام الهجين
            from backend.ml.hybrid_learning_system import get_hybrid_system, get_confidence_system
            
            # ✅ التحقق من مصدر البيانات - رفض Backtesting
            if source == 'backtesting' or 'backtest' in str(source).lower():
                logger.warning(f"❌ رفض صفقة من Backtesting: {symbol}")
                return False
            
            # ✅ التحقق من جودة البيانات
            if not all([symbol, strategy, timeframe]):
                logger.warning("❌ بيانات ناقصة في الصفقة")
                return False
            
            if entry_price <= 0 or exit_price <= 0:
                logger.warning("❌ أسعار غير صحيحة")
                return False
            
            result = {
                'symbol': symbol,
                'strategy': strategy,
                'timeframe': timeframe,
                'entry_price': float(entry_price),
                'exit_price': float(exit_price),
                'profit_loss': float(profit_loss),
                'profit_pct': float(profit_pct),
                'is_winning': profit_loss > 0,
                'indicators': indicators or {},
                'source': source,
                'timestamp': datetime.now().isoformat()
            }
            
            self.current_cycle_data.append(result)
            
            # تحديث النظام الهجين
            hybrid_system = get_hybrid_system()
            hybrid_system.real_trades_count += 1
            
            # تحديث نظام الثقة للنمط
            pattern_id = f"{symbol}_{strategy}_{timeframe}"
            confidence_system = get_confidence_system(pattern_id)
            confidence_system.update_after_trade(profit_loss, profit_pct)
            
            logger.debug(f"✅ تمت إضافة صفقة حقيقية: {symbol} ({source})")
            return True
            
        except Exception as e:
            logger.warning(f"❌ خطأ في إضافة صفقة حقيقية: {e}")
            return False
    
    def add_backtest_result(self, 
                           symbol: str,
                           strategy: str,
                           timeframe: str,
                           stats: Dict,
                           indicators: Dict = None) -> bool:
        """
        إضافة نتيجة Backtesting مع النظام الهجين
        يستخدم فقط في المراحل الأولى (< 200 صفقة حقيقية)
        """
        try:
            # استيراد النظام الهجين
            from backend.ml.hybrid_learning_system import get_hybrid_system
            
            hybrid_system = get_hybrid_system()
            
            # فحص إذا كان يجب استخدام Backtesting
            if not hybrid_system.should_use_backtest_data(symbol, strategy, timeframe):
                logger.debug(f"⏭️ تجاوز Backtesting - النظام في مرحلة النضج")
                return False
            
            # تعديل النتائج للواقعية
            adjusted = hybrid_system.adjust_backtest_for_reality({
                'symbol': symbol,
                'strategy': strategy,
                'timeframe': timeframe,
                'profit_pct': stats.get('return_pct', 0),
                'win_rate': stats.get('win_rate', 0)
            })
            
            # إضافة البيانات المعدلة
            result = {
                'symbol': symbol,
                'strategy': strategy,
                'timeframe': timeframe,
                'profit_pct': adjusted['adjusted_profit_pct'],
                'win_rate': adjusted['adjusted_win_rate'],
                'is_winning': adjusted['adjusted_profit_pct'] > 0,
                'indicators': indicators or {},
                'source': 'adjusted_backtest',
                'weight': adjusted['weight'],
                'timestamp': datetime.now().isoformat()
            }
            
            self.current_cycle_data.append(result)
            hybrid_system.backtest_count += 1
            
            logger.debug(f"✅ تمت إضافة Backtest معدل: {symbol} (وزن: {adjusted['weight']:.2f})")
            return True
            
        except Exception as e:
            logger.warning(f"❌ خطأ في إضافة Backtest: {e}")
            return False
    
    def add_batch_results(self, results: List[Dict]) -> int:
        """
        إضافة مجموعة من نتائج Backtesting
        
        Args:
            results: قائمة النتائج
            
        Returns:
            عدد النتائج المضافة
        """
        if not results:
            return 0
            
        added = 0
        for result in results:
            # تجاهل النتائج الفارغة أو None
            if result is None or not isinstance(result, dict):
                continue
                
            # تجاهل النتائج بدون stats
            stats = result.get('stats')
            if stats is None or not isinstance(stats, dict):
                continue
            
            if self.add_backtest_result(
                symbol=result.get('coin', result.get('symbol', '')),
                strategy=result.get('strategy', ''),
                timeframe=result.get('timeframe', result.get('selected_timeframe', '1h')),
                stats=stats,
                indicators=result.get('indicators', {})
            ):
                added += 1
        
        logger.info(f"✅ تم إضافة {added}/{len(results)} نتيجة")
        return added
    
    def end_cycle_and_train(self, force_train: bool = False) -> Dict[str, Any]:
        """
        إنهاء الدورة وتدريب النموذج
        
        Args:
            force_train: فرض التدريب حتى لو البيانات قليلة
            
        Returns:
            نتائج التدريب
        """
        logger.info(f"📊 إنهاء دورة التدريب #{self.cycle_count}")
        logger.info(f"   📈 نتائج هذه الدورة: {len(self.current_cycle_data)}")
        
        # إضافة البيانات للمصنف
        if self.current_cycle_data:
            added = self.classifier.add_backtest_results(self.current_cycle_data)
            logger.info(f"   ✅ تم إضافة {added} صفقة للتدريب")
        
        # تدريب النموذج
        status = self.classifier.get_status()
        total_samples = status['total_samples']
        
        logger.info(f"   📊 إجمالي البيانات المتراكمة: {total_samples}")
        
        # التدريب إذا كانت البيانات كافية
        if total_samples >= MLSignalClassifier.MIN_SAMPLES_FOR_TRAINING or force_train:
            logger.info("🧠 بدء التدريب...")
            train_result = self.classifier.train(force=force_train)
            
            if train_result['success']:
                logger.info(f"✅ تم التدريب بنجاح!")
                logger.info(f"   📊 الدقة: {train_result['accuracy']:.2%}")
                logger.info(f"   🎯 الجاهزية: {'✅ جاهز' if train_result['is_ready'] else '❌ غير جاهز'}")
            else:
                logger.warning(f"⚠️ فشل التدريب: {train_result.get('error', 'غير معروف')}")
            
            return train_result
        else:
            remaining = MLSignalClassifier.MIN_SAMPLES_FOR_TRAINING - total_samples
            logger.info(f"⏳ بيانات غير كافية للتدريب")
            logger.info(f"   📊 الموجود: {total_samples}")
            logger.info(f"   📊 المطلوب: {MLSignalClassifier.MIN_SAMPLES_FOR_TRAINING}")
            logger.info(f"   📊 المتبقي: {remaining}")
            
            return {
                'success': False,
                'reason': 'بيانات غير كافية',
                'total_samples': total_samples,
                'required': MLSignalClassifier.MIN_SAMPLES_FOR_TRAINING,
                'remaining': remaining
            }
    
    def get_status(self) -> Dict[str, Any]:
        """الحصول على حالة المدير"""
        classifier_status = self.classifier.get_status()
        
        return {
            'cycle_count': self.cycle_count,
            'current_cycle_data': len(self.current_cycle_data),
            'classifier': classifier_status
        }
    
    def is_ml_ready(self) -> bool:
        """فحص جاهزية ML"""
        return self.classifier.is_ready()
    
    def predict_signal(self, features: Dict) -> Dict[str, Any]:
        """
        التنبؤ بجودة إشارة
        
        Args:
            features: ميزات الإشارة
            
        Returns:
            نتيجة التنبؤ
        """
        return self.classifier.predict(features)


# Singleton instance
_training_manager = None

def get_training_manager() -> MLTrainingManager:
    """الحصول على مثيل واحد من المدير"""
    global _training_manager
    if _training_manager is None:
        _training_manager = MLTrainingManager()
    return _training_manager
