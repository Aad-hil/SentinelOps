from typing import Callable

from graph.state import InvestigationState


ToolRunner = Callable[[InvestigationState], dict]


def run_tool_safely(tool_name: str, tool: ToolRunner, state: InvestigationState) -> dict:
    """Execute an agent tool and turn unexpected tool failures into a finding-safe message."""
    try:
        return tool(state)
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "messages": [f"{tool_name} tool failed: {type(exc).__name__}: {exc}"],
        }
