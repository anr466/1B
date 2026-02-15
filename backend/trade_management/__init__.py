"""
Trade Management Module - إدارة متقدمة للصفقات
==============================================

النظام الموحد V4 - يجمع أفضل المزايا:
✅ تصنيف العملات الذكي
✅ Multi-Level TP ديناميكي
✅ Trailing Stop مع حماية الاتجاه
✅ ATR-Based SL
✅ Time-Based Exit
✅ Reversal Detection
✅ Emergency Exit

تاريخ التوحيد: 24 يناير 2026
"""

from .unified_exit_system import (
    UnifiedExitSystem,
    get_unified_exit_system,
    get_asset_profile,
    AssetCategory,
    ExitReason,
    PositionState,
)

__all__ = [
    'UnifiedExitSystem',
    'get_unified_exit_system',
    'get_asset_profile',
    'AssetCategory',
    'ExitReason',
    'PositionState',
]
