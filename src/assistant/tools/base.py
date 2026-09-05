from collections.abc import Callable, Mapping
from dataclasses import dataclass

from assistant.context import ToolContext

ToolArguments = Mapping[str, object]
ToolResult = Mapping[str, object]
ToolHandler = Callable[[ToolContext, ToolArguments], ToolResult]


@dataclass(frozen=True, slots=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, object]
    handler: ToolHandler
