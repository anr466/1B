#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cognitive Trading Module - الطبقة المعرفية لنظام التداول
========================================================

المكونات النشطة (مُنظّفة — فبراير 2026):
1. MarketStateDetector - تصنيف حالة السوق
2. MTFReversalConfirmation - تأكيد الانعكاس متعدد الأطر
3. MarketSurveillanceEngine - المراقبة الذكية المستمرة
4. MultiExitEngine - أنظمة خروج متعددة مستقلة (5 أنظمة)
5. CognitiveOrchestrator - المُنسّق المعرفي الرئيسي
"""

from .market_state_detector import (
    MarketStateDetector,
    MarketState,
    MarketStateResult,
    get_market_state_detector,
)

from .mtf_reversal_confirmation import (
    MTFReversalConfirmation,
    ReversalType,
    ReversalStrength,
    ReversalSignal,
    get_mtf_reversal_confirmation,
)

from .market_surveillance_engine import (
    MarketSurveillanceEngine,
    MarketQuality,
    MarketPhase,
    BehaviorSignal,
    SurveillanceReport,
    get_surveillance_engine,
)

from .multi_exit_engine import (
    MultiExitEngine,
    ExitReason,
    ExitUrgency,
    MultiExitDecision,
    get_multi_exit_engine,
)

from .cognitive_orchestrator import (
    CognitiveOrchestrator,
    CognitiveAction,
    EntryStrategy,
    CognitiveDecision,
    get_cognitive_orchestrator,
)

__all__ = [
    # Market State
    "MarketStateDetector",
    "MarketState",
    "MarketStateResult",
    "get_market_state_detector",
    # MTF Reversal
    "MTFReversalConfirmation",
    "ReversalType",
    "ReversalStrength",
    "ReversalSignal",
    "get_mtf_reversal_confirmation",
    # Surveillance
    "MarketSurveillanceEngine",
    "MarketQuality",
    "MarketPhase",
    "BehaviorSignal",
    "SurveillanceReport",
    "get_surveillance_engine",
    # Multi-Exit
    "MultiExitEngine",
    "ExitReason",
    "ExitUrgency",
    "MultiExitDecision",
    "get_multi_exit_engine",
    # Orchestrator
    "CognitiveOrchestrator",
    "CognitiveAction",
    "EntryStrategy",
    "CognitiveDecision",
    "get_cognitive_orchestrator",
]
