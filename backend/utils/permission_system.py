"""Tool permission context for trading operations"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolPermissionContext:
    deny_names: frozenset[str] = field(default_factory=frozenset)
    deny_prefixes: tuple[str, ...] = ()

    @classmethod
    def from_iterables(cls, deny_names=None, deny_prefixes=None):
        return cls(
            deny_names=frozenset(n.lower() for n in (deny_names or [])),
            deny_prefixes=tuple(p.lower() for p in (deny_prefixes or [])),
        )

    def blocks(self, tool_name: str) -> bool:
        lowered = tool_name.lower()
        return lowered in self.deny_names or any(
            lowered.startswith(p) for p in self.deny_prefixes
        )


TRADING_PERMISSIONS = {
    "real": ToolPermissionContext.from_iterables(
        deny_names=["demo_trade", "paper_trade"],
    ),
    "demo": ToolPermissionContext.from_iterables(
        deny_names=["real_trade"],
        deny_prefixes=["real_"],
    ),
}


def get_permission_context(trading_mode: str) -> ToolPermissionContext:
    return TRADING_PERMISSIONS.get(trading_mode, ToolPermissionContext())
