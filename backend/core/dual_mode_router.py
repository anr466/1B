#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dual-Mode Trading Engine — Spot LONG + Margin SHORT
=====================================================
Routes signals to the correct execution mode based on:
1. Market regime (BULL → Spot LONG, BEAR → Margin SHORT)
2. User configuration (spot_enabled, margin_enabled)
3. Signal direction (LONG → Spot, SHORT → Margin)

Architecture:
  Signal → Router → Spot Executor (LONG) or Margin Executor (SHORT)
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DualModeRouter:
    """Routes trading signals to Spot or Margin based on regime and signal direction"""

    def __init__(self, spot_enabled=True, margin_enabled=False):
        self.spot_enabled = spot_enabled
        self.margin_enabled = margin_enabled

    def route_signal(
        self, signal: Dict[str, Any], regime: str
    ) -> Optional[Dict[str, Any]]:
        side = signal.get("side", "LONG").upper()

        if side == "LONG":
            if not self.spot_enabled:
                return None
            return {
                "mode": "spot",
                "side": "LONG",
                "signal": signal,
                "regime": regime,
            }

        elif side == "SHORT":
            if not self.margin_enabled:
                return None
            return {
                "mode": "margin",
                "side": "SHORT",
                "signal": signal,
                "regime": regime,
            }

        return None

    def get_allowed_sides(self, regime: str) -> List[str]:
        if regime in ("BULL_STRONG", "BULL_WEAK"):
            return ["LONG"] if self.spot_enabled else []
        elif regime in ("BEAR_STRONG", "BEAR_WEAK"):
            return ["SHORT"] if self.margin_enabled else []
        else:
            sides = []
            if self.spot_enabled:
                sides.append("LONG")
            if self.margin_enabled:
                sides.append("SHORT")
            return sides
