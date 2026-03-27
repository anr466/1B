#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML Module - نظام التعلم الآلي للتداول
"""

from backend.ml.signal_classifier import MLSignalClassifier, get_ml_classifier
from backend.ml.training_manager import MLTrainingManager, get_training_manager
from backend.ml.hybrid_learning_system import (
    HybridMLSystem,
    DynamicConfidenceSystem,
    get_hybrid_system,
    get_confidence_system,
    get_all_patterns_status,
)
from backend.ml.pattern_similarity_matcher import (
    PatternSimilarityMatcher,
    get_similarity_matcher,
)
from backend.ml.trading_brain import TradingBrain, get_trading_brain

__all__ = [
    "MLSignalClassifier",
    "get_ml_classifier",
    "MLTrainingManager",
    "get_training_manager",
    "HybridMLSystem",
    "DynamicConfidenceSystem",
    "get_hybrid_system",
    "get_confidence_system",
    "get_all_patterns_status",
    "PatternSimilarityMatcher",
    "get_similarity_matcher",
    "TradingBrain",
    "get_trading_brain",
]
