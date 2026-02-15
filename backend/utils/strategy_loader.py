#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محمل الاستراتيجيات التلقائي
يفحص مجلد strategies ويحمل جميع الاستراتيجيات المتاحة تلقائياً
"""

import os
import sys
import importlib
import inspect
from pathlib import Path
from typing import Dict, Any, List, Type
from abc import ABC
from config.logging_config import get_logger

logger = get_logger(__name__)

class StrategyLoader:
    """محمل الاستراتيجيات التلقائي"""
    
    def __init__(self, strategies_dir: str = "strategies"):
        """
        تهيئة محمل الاستراتيجيات
        
        Args:
            strategies_dir: مسار مجلد الاستراتيجيات
        """
        self.strategies_dir = Path(strategies_dir)
        self.loaded_strategies = {}
        self.strategy_classes = {}
        
        # التأكد من وجود المجلد
        if not self.strategies_dir.exists():
            logger.error(f"مجلد الاستراتيجيات غير موجود: {self.strategies_dir}")
            raise FileNotFoundError(f"مجلد الاستراتيجيات غير موجود: {self.strategies_dir}")
    
    def _is_strategy_class(self, obj) -> bool:
        """
        فحص ما إذا كان الكائن فئة استراتيجية صالحة
        
        Args:
            obj: الكائن المراد فحصه
            
        Returns:
            True إذا كان فئة استراتيجية صالحة
        """
        return (
            inspect.isclass(obj) and
            hasattr(obj, 'generate_signals') and
            obj.__name__ != 'StrategyBase' and  # استبعاد الفئة الأساسية
            not obj.__name__.startswith('_') and  # استبعاد الفئات الخاصة
            obj.__name__.endswith('Strategy')  # يجب أن ينتهي بـ Strategy
        )
    
    def _load_strategy_from_file(self, file_path: Path) -> List[Type]:
        """
        تحميل الاستراتيجيات من ملف واحد
        
        Args:
            file_path: مسار الملف
            
        Returns:
            قائمة بفئات الاستراتيجيات المحملة
        """
        strategies = []
        
        try:
            # تحويل مسار الملف إلى اسم وحدة
            module_name = file_path.stem
            
            # إضافة مسار المشروع إلى sys.path إذا لم يكن موجوداً
            project_root = file_path.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            # تحميل الوحدة
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                logger.warning(f"لا يمكن تحميل المواصفات للملف: {file_path}")
                return strategies
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # البحث عن فئات الاستراتيجيات في الوحدة
            for name, obj in inspect.getmembers(module):
                if self._is_strategy_class(obj):
                    strategies.append(obj)
                    logger.info(f"تم العثور على استراتيجية: {obj.__name__} في {file_path.name}")
            
        except Exception as e:
            logger.error(f"خطأ في تحميل الاستراتيجيات من {file_path}: {e}")
        
        return strategies
    
    def load_all_strategies(self) -> Dict[str, Any]:
        """
        تحميل جميع الاستراتيجيات من المجلد
        
        Returns:
            قاموس بجميع الاستراتيجيات المحملة
        """
        logger.info(f"بدء تحميل الاستراتيجيات من: {self.strategies_dir}")
        
        self.loaded_strategies.clear()
        self.strategy_classes.clear()
        
        # البحث عن جميع ملفات Python في المجلد
        python_files = list(self.strategies_dir.glob("*.py"))
        
        # استبعاد ملفات معينة
        excluded_files = {'__init__.py', 'strategy_base.py'}
        python_files = [f for f in python_files if f.name not in excluded_files]
        
        logger.info(f"تم العثور على {len(python_files)} ملف استراتيجية")
        
        total_strategies = 0
        
        for file_path in python_files:
            logger.info(f"فحص الملف: {file_path.name}")
            
            # تحميل الاستراتيجيات من الملف
            file_strategies = self._load_strategy_from_file(file_path)
            
            # حفظ فئات الاستراتيجيات
            for strategy_class in file_strategies:
                try:
                    # استخدام اسم الفئة كمفتاح
                    strategy_name = strategy_class.__name__
                    
                    # حفظ الفئة مباشرة (وليس المثيل)
                    self.loaded_strategies[strategy_name] = strategy_class
                    self.strategy_classes[strategy_name] = strategy_class
                    
                    total_strategies += 1
                    
                    logger.info(
                        f"تم تحميل الاستراتيجية: {strategy_name} "
                    )
                    
                except Exception as e:
                    logger.error(f"خطأ في إنشاء كائن الاستراتيجية {strategy_class.__name__}: {e}")
        
        logger.info(f"تم تحميل {total_strategies} استراتيجية بنجاح")
        
        if not self.loaded_strategies:
            logger.warning("لم يتم تحميل أي استراتيجيات!")
            
        return self.loaded_strategies
    
    def get_strategy_info(self) -> Dict[str, Dict[str, Any]]:
        """
        الحصول على معلومات الاستراتيجيات المحملة
        
        Returns:
            قاموس بمعلومات كل استراتيجية
        """
        info = {}
        
        for name, strategy in self.loaded_strategies.items():
            try:
                info[name] = {
                    'class_name': strategy.__class__.__name__,
                    'display_name': getattr(strategy, 'name', name),
                    'description': getattr(strategy, 'description', 'لا يوجد وصف'),
                    'timeframes': getattr(strategy, 'timeframes', ['1h']),
                    'indicators': getattr(strategy, 'required_indicators', []),
                    'file_path': inspect.getfile(strategy.__class__)
                }
            except Exception as e:
                logger.error(f"خطأ في جلب معلومات الاستراتيجية {name}: {e}")
                info[name] = {
                    'class_name': name,
                    'display_name': name,
                    'description': 'خطأ في جلب المعلومات',
                    'error': str(e)
                }
        
        return info
    
    def load_strategy(self, name: str) -> Any:
        """
        تحميل استراتيجية بالاسم
        
        Args:
            name: اسم الاستراتيجية
            
        Returns:
            كائن الاستراتيجية أو None
        """
        # محاولة تحميل الاستراتيجيات إذا لم تكن محملة
        if not self.loaded_strategies:
            self.load_all_strategies()
        
        # البحث بأسماء مختلفة
        strategy_mappings = {
            'momentum_breakout': 'MomentumBreakoutStrategy',
            'mean_reversion': 'MeanReversionStrategy', 
            'scalping_ema': 'ScalpingEMAStrategy',
            'rsi_divergence': 'RSIDivergenceStrategy',
            'volume_price_trend': 'VolumePriceTrendStrategy',
            'trend_following': 'TrendFollowingStrategy',
            'peak_valley_scalping': 'PeakValleyScalpingStrategy'
        }
        
        # البحث المباشر
        if name in self.loaded_strategies:
            return self.loaded_strategies[name]
        
        # البحث بالتطابق
        mapped_name = strategy_mappings.get(name.lower())
        if mapped_name and mapped_name in self.loaded_strategies:
            return self.loaded_strategies[mapped_name]
        
        # البحث الجزئي
        for key, strategy in self.loaded_strategies.items():
            if name.lower() in key.lower() or key.lower() in name.lower():
                return strategy
        
        return None
    
    def get_strategy_by_name(self, name: str) -> Any:
        """
        الحصول على استراتيجية بالاسم
        
        Args:
            name: اسم الاستراتيجية
            
        Returns:
            كائن الاستراتيجية أو None
        """
        return self.load_strategy(name)
    
    def get_available_strategy_names(self) -> List[str]:
        """
        الحصول على أسماء الاستراتيجيات المتاحة
        
        Returns:
            قائمة بأسماء الاستراتيجيات
        """
        return list(self.loaded_strategies.keys())
    
    def reload_strategies(self) -> Dict[str, Any]:
        """
        إعادة تحميل جميع الاستراتيجيات
        
        Returns:
            قاموس بالاستراتيجيات المحملة
        """
        logger.info("إعادة تحميل جميع الاستراتيجيات...")
        
        # مسح الاستراتيجيات الحالية
        self.loaded_strategies.clear()
        self.strategy_classes.clear()
        
        # إعادة التحميل
        return self.load_all_strategies()
    
    def validate_strategy(self, strategy) -> bool:
        """
        التحقق من صحة الاستراتيجية
        
        Args:
            strategy: كائن الاستراتيجية
            
        Returns:
            True إذا كانت الاستراتيجية صالحة
        """
        required_methods = ['generate_signals']
        required_attributes = ['name']
        
        try:
            # فحص الدوال المطلوبة
            for method in required_methods:
                if not hasattr(strategy, method) or not callable(getattr(strategy, method)):
                    logger.error(f"الاستراتيجية تفتقر للدالة المطلوبة: {method}")
                    return False
            
            # فحص الخصائص المطلوبة
            for attr in required_attributes:
                if not hasattr(strategy, attr):
                    logger.error(f"الاستراتيجية تفتقر للخاصية المطلوبة: {attr}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في التحقق من صحة الاستراتيجية: {e}")
            return False

def main():
    """اختبار محمل الاستراتيجيات"""
    
    
    try:
        loader = StrategyLoader()
        strategies = loader.load_all_strategies()
        
        print(f"\n=== تم تحميل {len(strategies)} استراتيجية ===")
        
        info = loader.get_strategy_info()
        for name, details in info.items():
            print(f"\n📊 {name}:")
            print(f"   الاسم: {details.get('display_name', 'غير محدد')}")
            print(f"   الوصف: {details.get('description', 'لا يوجد وصف')}")
            print(f"   الأطر الزمنية: {details.get('timeframes', [])}")
            
    except Exception as e:
        print(f"خطأ في اختبار محمل الاستراتيجيات: {e}")

if __name__ == "__main__":
    main()
