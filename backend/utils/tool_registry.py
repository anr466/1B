"""Tool registration and filtering for the trading system"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    handler: Optional[Callable] = None
    permission_required: str = ""
    category: str = "general"


class ToolRegistry:
    _tools: dict[str, ToolDefinition] = {}
    _categories: dict[str, list[str]] = {}

    @classmethod
    def register(cls, tool: ToolDefinition):
        cls._tools[tool.name] = tool
        if tool.category not in cls._categories:
            cls._categories[tool.category] = []
        cls._categories[tool.category].append(tool.name)

    @classmethod
    def get(cls, name: str) -> Optional[ToolDefinition]:
        return cls._tools.get(name)

    @classmethod
    def get_by_category(cls, category: str) -> list[ToolDefinition]:
        names = cls._categories.get(category, [])
        return [cls._tools[n] for n in names if n in cls._tools]

    @classmethod
    def list_all(cls) -> list[ToolDefinition]:
        return list(cls._tools.values())

    @classmethod
    def filter_by_permission(cls, permission_level: str) -> list[ToolDefinition]:
        return [
            t
            for t in cls._tools.values()
            if not t.permission_required or t.permission_required == permission_level
        ]

    @classmethod
    def execute(cls, name: str, **kwargs):
        tool = cls.get(name)
        if not tool or not tool.handler:
            raise ValueError(f"Tool '{name}' not found or has no handler")
        return tool.handler(**kwargs)
