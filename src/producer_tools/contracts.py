"""Typed contracts shared between agent core and tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol, TypeAlias

ToolPayload: TypeAlias = Mapping[str, object]
ToolResult: TypeAlias = Mapping[str, object]
ToolCallable: TypeAlias = Callable[[ToolPayload], ToolResult]


class ToolContract(Protocol):
    """Module-level tool contract."""

    TOOL_NAME: str
    run: ToolCallable
