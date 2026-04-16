#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cognitive Trading Module - الطبقة المعرفية لنظام التداول
========================================================

المكونات النشطة:
1. MultiExitEngine - أنظمة خروج متعددة مستقلة
2. CognitiveOrchestrator - المُنسّق المعرفي الرئيسي
"""

from .multi_exit_engine import (
    MultiExitEngine,
    ExitReason,
    ExitUrgency,
    MultiExitDecision,
    get_multi_exit_engine,
)

try:
    from .cognitive_orchestrator import (
        CognitiveOrchestrator,
        CognitiveAction,
        EntryStrategy,
        CognitiveDecision,
        get_cognitive_orchestrator,
    )

    COGNITIVE_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    COGNITIVE_ORCHESTRATOR_AVAILABLE = False

__all__ = [
    "MultiExitEngine",
    "ExitReason",
    "ExitUrgency",
    "MultiExitDecision",
    "get_multi_exit_engine",
]

if COGNITIVE_ORCHESTRATOR_AVAILABLE:
    __all__.extend(
        [
            "CognitiveOrchestrator",
            "CognitiveAction",
            "EntryStrategy",
            "CognitiveDecision",
            "get_cognitive_orchestrator",
        ]
    )
