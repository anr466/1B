#!/usr/bin/env python3
"""
Strategy Module Interface — Updated for Continuous Signal Stream
================================================================
Defines the contract that all trading strategy modules must follow.
Modules now return SignalCandidate (never None) for full visibility.
"""

from abc import ABC, abstractmethod
from typing import Dict, List
import pandas as pd
from backend.core.signal_candidate import SignalCandidate


class StrategyModule(ABC):
    """Base class for all trading strategy modules."""

    @abstractmethod
    def name(self) -> str:
        """Return the name of the strategy module."""
        pass

    @abstractmethod
    def supported_regimes(self) -> List[str]:
        """Return list of market regimes this module supports."""
        pass

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, context: Dict) -> SignalCandidate:
        """
        Evaluate market conditions and return a SignalCandidate.
        Always returns a candidate — never None.
        Low confidence candidates indicate weak setups.

        Args:
            df: DataFrame with OHLCV and indicators
            context: Dict with market context (regime, volatility, etc.)

        Returns:
            SignalCandidate with confidence 0-100
        """
        pass

    def get_entry_price(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        """Calculate precise entry price based on signal."""
        return df["close"].iloc[-1]

    def get_stop_loss(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        """Calculate stop loss price based on signal."""
        raise NotImplementedError

    def get_take_profit(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        """Calculate take profit price based on signal."""
        raise NotImplementedError
