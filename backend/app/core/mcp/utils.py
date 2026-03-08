"""Utility functions for MCP tools."""

import asyncio
import time
from typing import Any, Dict, List

from langchain.tools import BaseTool
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.common.logging import TerraLogUtil


def get_tools_info(tools: List[BaseTool]) -> List[Dict[str, Any]]:
    """Convert tool objects to a list of info dictionaries.

    Args:
        tools: List of tool objects.

    Returns:
        List of tool info dictionaries containing name, description, and args_schema.
    """
    tools_info = []
    for tool in tools:
        tool_info = {
            "name": tool.name if hasattr(tool, "name") else str(tool),
            "description": (
                tool.description if hasattr(
                    tool, "description") else "No description"
            ),
        }
        if hasattr(tool, "args_schema"):
            tool_info["args_schema"] = (
                tool.args_schema
                if isinstance(tool.args_schema, dict)
                else str(tool.args_schema)
            )
        tools_info.append(tool_info)

    return tools_info


async def invoke_tool_with_timeout(
    tool: BaseTool,
    args: Dict[str, Any],
    timeout: int = 10,
    retries: int = 2,
) -> Dict[str, Any]:
    """Invoke a tool with timeout and retry mechanism.

    Args:
        tool: The tool instance to invoke.
        args: Tool arguments.
        timeout: Timeout per invocation attempt in seconds, default 10.
        retries: Number of retry attempts, default 2.

    Returns:
        A dict with the following keys:
            - ok: bool, whether the call succeeded.
            - payload: The result on success.
            - error: Error message on failure.
            - elapsed_ms: Execution time in milliseconds.
    """
    tool_name = tool.name if hasattr(tool, "name") else str(tool)

    @retry(
        stop=stop_after_attempt(retries + 1),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    async def _attempt() -> Any:
        return await asyncio.wait_for(tool.ainvoke(args), timeout=timeout)

    start = time.monotonic()
    try:
        result = await _attempt()
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        TerraLogUtil.info(
            "tool_invoke_success",
            tool_name=tool_name,
            elapsed_ms=elapsed_ms,
        )
        return {
            "ok": True,
            "payload": result,
            "error": None,
            "elapsed_ms": elapsed_ms,
        }
    except asyncio.TimeoutError:
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        TerraLogUtil.exception(
            "tool_invoke_timeout",
            tool_name=tool_name,
            timeout=timeout,
            retries=retries,
            elapsed_ms=elapsed_ms,
        )
        return {
            "ok": False,
            "payload": None,
            "error": f"Tool '{tool_name}' timed out after {timeout}s (retries={retries})",
            "elapsed_ms": elapsed_ms,
        }
    except Exception as exc:
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        TerraLogUtil.exception(
            "tool_invoke_failed",
            tool_name=tool_name,
            error=str(exc),
            elapsed_ms=elapsed_ms,
        )
        return {
            "ok": False,
            "payload": None,
            "error": str(exc),
            "elapsed_ms": elapsed_ms,
        }
