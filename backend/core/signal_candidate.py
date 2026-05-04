#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Signal Candidate — نموذج الإشارة المستمر
==========================================
بدلاً من إرجاع Signal أو None، ترجع الوحدات دائماً SignalCandidate
مع درجة ثقة. حتى الفرص الضعيفة تُسجل وتُرفض لاحقاً بذكاء.

هذا يسمح لـ CognitiveDecisionMatrix برؤية الصورة الكاملة واتخاذ قرارات
مستنيرة بناءً على совокупية البيانات.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SignalCandidate:
    """
    Represents a potential trading signal with confidence scoring.
    Always returned by strategy modules — never None.
    """

    # Core signal data
    symbol: str = ""
    signal_type: str = "NONE"  # LONG, SHORT, NONE
    strategy: str = "Unknown"
    confidence: float = 0.0  # 0-100

    # Price levels
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0

    # Context
    regime: str = "UNKNOWN"
    reason: str = ""
    metadata: Dict = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Check if this signal is actionable (not a 'no signal' candidate)"""
        return (
            self.signal_type in ("LONG", "SHORT")
            and self.confidence > 0
            and self.entry_price > 0
            and self.stop_loss > 0
            and self.take_profit > 0
        )

    @property
    def risk_reward_ratio(self) -> float:
        """Calculate risk:reward ratio"""
        if self.entry_price == 0 or self.stop_loss == 0 or self.take_profit == 0:
            return 0.0
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        return reward / risk if risk > 0 else 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "symbol": self.symbol,
            "type": self.signal_type,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "regime": self.regime,
            "reason": self.reason,
            "risk_reward_ratio": round(self.risk_reward_ratio, 2),
            "is_valid": self.is_valid,
            **self.metadata,
        }

    @classmethod
    def no_signal(
        cls, reason: str = "No setup detected", regime: str = "UNKNOWN"
    ) -> "SignalCandidate":
        """Factory method for creating a 'no signal' candidate"""
        return cls(
            signal_type="NONE",
            strategy="NoSetup",
            confidence=0.0,
            reason=reason,
            regime=regime,
        )
