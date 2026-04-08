#!/usr/bin/env python3
"""
Strategy Module Interface
Defines the contract that all trading strategy modules must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd


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
    def evaluate(self, df: pd.DataFrame, context: Dict) -> Optional[Dict]:
        """
        Evaluate market conditions and return a signal if valid.

        Args:
            df: DataFrame with OHLCV and indicators
            context: Dict with market context (regime, volatility, etc.)

        Returns:
            Dict with signal details or None if no signal
        """
        pass

    @abstractmethod
    def get_entry_price(self, df: pd.DataFrame, signal: Dict) -> float:
        """Calculate precise entry price based on signal."""
        pass

    @abstractmethod
    def get_stop_loss(self, df: pd.DataFrame, signal: Dict) -> float:
        """Calculate stop loss price based on signal."""
        pass

    @abstractmethod
    def get_take_profit(self, df: pd.DataFrame, signal: Dict) -> float:
        """Calculate take profit price based on signal."""
        pass
