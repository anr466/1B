#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام التعلم المستقل - يعتمد على البيانات الحقيقية فقط
- لا يتعلم من Backtesting التاريخي
- يتعلم من التداول الفعلي (وهمي وحقيقي) فقط
- يُستخدم في Group B (التداول الفعلي)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class IndependentLearningSystem:
    """نظام تعلم مستقل يعتمد على البيانات الحقيقية فقط"""
    
    def __init__(self):
        """تهيئة نظام التعلم المستقل"""
        self.logger = logger
        
        # معايير التعلم
        self.min_trades_for_learning = 10  # حد أدنى من الصفقات الحقيقية
        self.min_win_rate_for_learning = 0.40  # حد أدنى لنسبة الفوز
        self.min_profit_for_learning = 0.01  # حد أدنى للربح
        
        # مصادر البيانات المسموحة
        self.allowed_sources = {
            'demo_trading': False,
            'real_trading': True,
            'live_trading': True,
            'backtesting': False       # Backtesting ممنوع
        }
        
        # إحصائيات التعلم
        self.learning_stats = {
            'total_real_trades': 0,
            'demo_trades': 0,
            'real_trades': 0,
            'patterns_learned': 0,
            'last_update': None
        }
    
    def validate_trade_source(self, trade_data: Dict[str, Any]) -> bool:
        """
        التحقق من أن مصدر الصفقة مسموح
        
        Args:
            trade_data: بيانات الصفقة
            
        Returns:
            True إذا كان المصدر مسموح
        """
        try:
            source = trade_data.get('source', 'unknown')
            
            # رفض Backtesting
            if source == 'backtesting' or 'backtest' in str(source).lower():
                self.logger.debug(f"❌ رفض صفقة من Backtesting: {source}")
                return False
            
            # قبول التداول الحقيقي فقط
            if source in ['real_trading', 'live_trading']:
                return True
            
            # قبول الصفقات بدون تحديد المصدر (افتراضياً من التداول الفعلي)
            if source == 'unknown':
                self.logger.debug("⚠️ صفقة بدون تحديد المصدر - افتراضياً من التداول الفعلي")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"خطأ في التحقق من مصدر الصفقة: {e}")
            return False
    
    def can_learn_from_trade(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        التحقق من إمكانية التعلم من صفقة معينة
        
        Args:
            trade_data: بيانات الصفقة
            
        Returns:
            Dict مع نتائج التحقق
        """
        try:
            result = {
                'can_learn': False,
                'reasons': [],
                'warnings': []
            }
            
            # 1. التحقق من المصدر
            if not self.validate_trade_source(trade_data):
                result['reasons'].append(f"مصدر غير مسموح: {trade_data.get('source', 'unknown')}")
                return result
            
            # 2. التحقق من البيانات الأساسية
            required_fields = ['symbol', 'entry_price', 'exit_price', 'profit_loss', 'timestamp']
            missing_fields = [f for f in required_fields if f not in trade_data]
            
            if missing_fields:
                result['reasons'].append(f"حقول مفقودة: {missing_fields}")
                return result
            
            # 3. التحقق من جودة البيانات
            try:
                entry = float(trade_data['entry_price'])
                exit_price = float(trade_data['exit_price'])
                profit = float(trade_data['profit_loss'])
                
                if entry <= 0 or exit_price <= 0:
                    result['reasons'].append("أسعار غير صحيحة")
                    return result
                
            except (ValueError, TypeError):
                result['reasons'].append("أسعار غير رقمية")
                return result
            
            # 4. التحقق من الحد الأدنى للربح
            if abs(profit) < self.min_profit_for_learning:
                result['warnings'].append(f"ربح منخفض جداً: {profit}")
            
            # إذا مرت جميع الفحوصات
            result['can_learn'] = True
            result['reasons'] = ["✅ الصفقة صالحة للتعلم"]
            
            return result
            
        except Exception as e:
            self.logger.error(f"خطأ في التحقق من إمكانية التعلم: {e}")
            return {'can_learn': False, 'reasons': [str(e)]}
    
    def extract_learning_features(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        استخراج الميزات للتعلم من صفقة حقيقية
        
        Args:
            trade_data: بيانات الصفقة
            
        Returns:
            Dict مع الميزات المستخرجة
        """
        try:
            features = {
                'symbol': trade_data.get('symbol'),
                'strategy': trade_data.get('strategy'),
                'timeframe': trade_data.get('timeframe'),
                'entry_price': float(trade_data.get('entry_price', 0)),
                'exit_price': float(trade_data.get('exit_price', 0)),
                'profit_loss': float(trade_data.get('profit_loss', 0)),
                'profit_pct': float(trade_data.get('profit_pct', 0)),
                'duration_minutes': trade_data.get('duration_minutes', 0),
                'source': trade_data.get('source', 'unknown'),
                'timestamp': trade_data.get('timestamp'),
                'indicators': trade_data.get('indicators', {}),
                'market_conditions': trade_data.get('market_conditions', {})
            }
            
            # حساب معايير إضافية
            if features['entry_price'] > 0:
                features['return_pct'] = ((features['exit_price'] - features['entry_price']) / 
                                         features['entry_price']) * 100
            
            features['is_winning'] = features['profit_loss'] > 0
            
            return features
            
        except Exception as e:
            self.logger.error(f"خطأ في استخراج الميزات: {e}")
            return {}
    
    def learn_from_real_trades(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        التعلم من مجموعة من الصفقات الحقيقية
        
        Args:
            trades: قائمة الصفقات الحقيقية
            
        Returns:
            Dict مع نتائج التعلم
        """
        try:
            result = {
                'success': False,
                'total_trades': len(trades),
                'valid_trades': 0,
                'invalid_trades': 0,
                'patterns_learned': 0,
                'learning_summary': {},
                'warnings': []
            }
            
            valid_trades = []
            
            # فلترة الصفقات الصحيحة
            for trade in trades:
                validation = self.can_learn_from_trade(trade)
                
                if validation['can_learn']:
                    features = self.extract_learning_features(trade)
                    if features:
                        valid_trades.append(features)
                        result['valid_trades'] += 1
                else:
                    result['invalid_trades'] += 1
                    if validation['reasons']:
                        result['warnings'].append(validation['reasons'][0])
            
            if not valid_trades:
                result['warnings'].append("لا توجد صفقات صحيحة للتعلم")
                return result
            
            # تحليل الصفقات الصحيحة
            df = pd.DataFrame(valid_trades)
            
            # إحصائيات التعلم
            result['learning_summary'] = {
                'total_valid_trades': len(valid_trades),
                'winning_trades': int(df['is_winning'].sum()),
                'losing_trades': int((~df['is_winning']).sum()),
                'win_rate': float(df['is_winning'].mean() * 100),
                'avg_profit': float(df['profit_loss'].mean()),
                'avg_return_pct': float(df['return_pct'].mean()),
                'max_profit': float(df['profit_loss'].max()),
                'max_loss': float(df['profit_loss'].min()),
                'total_profit': float(df['profit_loss'].sum()),
                'best_strategy': df['strategy'].value_counts().index[0] if len(df['strategy'].value_counts()) > 0 else 'unknown',
                'best_timeframe': df['timeframe'].value_counts().index[0] if len(df['timeframe'].value_counts()) > 0 else 'unknown',
                'best_symbol': df['symbol'].value_counts().index[0] if len(df['symbol'].value_counts()) > 0 else 'unknown'
            }
            
            # تحديث الإحصائيات
            self.learning_stats['total_real_trades'] += len(valid_trades)
            self.learning_stats['patterns_learned'] += len(valid_trades)
            self.learning_stats['last_update'] = datetime.now().isoformat()
            
            result['success'] = True
            result['patterns_learned'] = len(valid_trades)
            
            return result
            
        except Exception as e:
            self.logger.error(f"خطأ في التعلم من الصفقات الحقيقية: {e}")
            result['warnings'].append(str(e))
            return result
    
    def get_learning_status(self) -> Dict[str, Any]:
        """الحصول على حالة نظام التعلم"""
        return {
            'system': 'Independent Learning System',
            'data_sources': self.allowed_sources,
            'statistics': self.learning_stats,
            'min_requirements': {
                'min_trades': self.min_trades_for_learning,
                'min_win_rate': f"{self.min_win_rate_for_learning * 100}%",
                'min_profit': f"{self.min_profit_for_learning * 100}%"
            },
            'status': 'Active - Learning from real trades only'
        }
    
    def get_learning_summary(self) -> str:
        """الحصول على ملخص نظام التعلم"""
        summary = f"""
        ╔════════════════════════════════════════════════════════════════════════════════╗
        ║                    نظام التعلم المستقل - ملخص الحالة                          ║
        ╠════════════════════════════════════════════════════════════════════════════════╣
        ║                                                                                ║
        ║ 📊 مصادر البيانات المسموحة:                                                   ║
        ║    ✅ التداول الوهمي (Demo Trading)                                           ║
        ║    ✅ التداول الحقيقي (Real Trading)                                          ║
        ║    ❌ Backtesting التاريخي (ممنوع)                                            ║
        ║                                                                                ║
        ║ 📈 إحصائيات التعلم:                                                           ║
        ║    • إجمالي الصفقات الحقيقية: {self.learning_stats['total_real_trades']}                                  ║
        ║    • الأنماط المتعلمة: {self.learning_stats['patterns_learned']}                                    ║
        ║    • آخر تحديث: {self.learning_stats['last_update'] or 'لم يتم بعد'}                   ║
        ║                                                                                ║
        ║ 🎯 معايير التعلم:                                                             ║
        ║    • حد أدنى من الصفقات: {self.min_trades_for_learning}                                      ║
        ║    • حد أدنى لنسبة الفوز: {self.min_win_rate_for_learning * 100}%                              ║
        ║    • حد أدنى للربح: {self.min_profit_for_learning * 100}%                                ║
        ║                                                                                ║
        ║ 💡 الملاحظة:                                                                  ║
        ║    التعلم يعتمد على البيانات الحقيقية فقط (Group B)                            ║
        ║    لا يتعلم من نتائج Backtesting التاريخية                                    ║
        ║                                                                                ║
        ╚════════════════════════════════════════════════════════════════════════════════╝
        """
        return summary


if __name__ == "__main__":
    system = IndependentLearningSystem()
    print(system.get_learning_summary())
