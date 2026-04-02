"""Token usage and cost tracking for trading operations"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    def add_turn(self, prompt: str, output: str) -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + len(prompt.split()),
            output_tokens=self.output_tokens + len(output.split()),
        )

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class CostTracker:
    model_costs: dict[str, float] = field(default_factory=dict)
    total_cost: float = 0.0
    session_costs: dict[str, float] = field(default_factory=dict)
    daily_usage: dict[str, TokenUsage] = field(default_factory=dict)

    def record_cost(self, session_id: str, model: str, tokens: int):
        cost_per_token = self.model_costs.get(model, 0.0)
        cost = tokens * cost_per_token
        self.total_cost += cost
        self.session_costs[session_id] = self.session_costs.get(session_id, 0.0) + cost

    def record_daily_usage(
        self, date_str: str | None = None, usage: TokenUsage | None = None
    ):
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        if usage:
            self.daily_usage[date_str] = usage

    def get_session_cost(self, session_id: str) -> float:
        return self.session_costs.get(session_id, 0.0)

    def get_daily_usage(self, date_str: str | None = None) -> TokenUsage:
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        return self.daily_usage.get(date_str, TokenUsage())

    def reset_session(self, session_id: str):
        self.session_costs.pop(session_id, None)

    def reset_daily(self, date_str: str | None = None):
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        self.daily_usage.pop(date_str, None)
