"""Command registration and routing for the trading system"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class CommandDefinition:
    name: str
    description: str
    handler: Callable
    requires_auth: bool = True
    category: str = "general"


class CommandRegistry:
    _commands: dict[str, CommandDefinition] = {}
    _categories: dict[str, list[str]] = {}

    @classmethod
    def register(cls, cmd: CommandDefinition):
        cls._commands[cmd.name] = cmd
        if cmd.category not in cls._categories:
            cls._categories[cmd.category] = []
        cls._categories[cmd.category].append(cmd.name)

    @classmethod
    def get(cls, name: str) -> Optional[CommandDefinition]:
        return cls._commands.get(name)

    @classmethod
    def execute(cls, name: str, **kwargs):
        cmd = cls.get(name)
        if not cmd:
            raise ValueError(f"Command '{name}' not found")
        return cmd.handler(**kwargs)

    @classmethod
    def list_by_category(cls, category: str) -> list[CommandDefinition]:
        names = cls._categories.get(category, [])
        return [cls._commands[n] for n in names if n in cls._commands]

    @classmethod
    def list_all(cls) -> list[CommandDefinition]:
        return list(cls._commands.values())

    @classmethod
    def find(cls, query: str, limit: int = 10) -> list[CommandDefinition]:
        needle = query.lower()
        matches = [
            c
            for c in cls._commands.values()
            if needle in c.name.lower() or needle in c.description.lower()
        ]
        return matches[:limit]
