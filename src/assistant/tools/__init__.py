from assistant.tools.base import Tool, ToolArguments, ToolResult
from assistant.tools.faq import faq_tool
from assistant.tools.property_search import property_search_tool

AVAILABLE_TOOLS: dict[str, Tool] = {tool.name: tool for tool in (property_search_tool, faq_tool)}

__all__ = ["AVAILABLE_TOOLS", "Tool", "ToolArguments", "ToolResult"]
