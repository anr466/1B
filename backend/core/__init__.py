"""
Core Trading System Module
النظام الأساسي الموحد - v3.0
"""


def __getattr__(name):
    """Lazy import — avoids triggering DB connection on `import backend.core`."""
    if name == "GroupBSystem":
        from .group_b_system import GroupBSystem

        return GroupBSystem
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "GroupBSystem",
]
