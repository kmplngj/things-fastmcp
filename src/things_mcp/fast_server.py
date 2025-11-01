#!/usr/bin/env python3
"""
Things MCP Server implementation using the FastMCP pattern.
This provides a more modern and maintainable approach to the Things integration.
"""
import os
from functools import lru_cache
from typing import Dict, Any, Optional, List, Union
import inspect
import things
from dotenv import load_dotenv

from fastmcp import FastMCP, Context
import mcp.types as types

# Import FastMCP middleware for performance monitoring and error handling
from fastmcp.server.middleware.timing import DetailedTimingMiddleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware

# Import supporting modules
from .formatters import format_todo, format_project, format_area, format_tag
from .utils import app_state
from .url_scheme import (
    add_todo, add_project, update_todo, update_project, show,
    search, launch_things, execute_url
)

# Import and configure enhanced logging
from .logging_config import setup_logging, get_logger, log_operation_start, log_operation_end
# Import caching
from .cache import cached, invalidate_caches_for, get_cache_stats, CACHE_TTL
from .tag_handler import ensure_tags_exist

# Load environment variables from .env file
load_dotenv()

READ_ONLY_ANNOTATIONS = types.ToolAnnotations(
    readOnlyHint=True,
    idempotentHint=True,
    openWorldHint=False,
)

ADD_ANNOTATIONS = types.ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)

UPDATE_ANNOTATIONS = types.ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

MODIFY_ANNOTATIONS = types.ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,  # Has confirmation step
    idempotentHint=False,  # Affects multiple items
    openWorldHint=False,
)

TOOL_ANNOTATIONS: Dict[str, types.ToolAnnotations] = {
    "get-inbox": READ_ONLY_ANNOTATIONS,
    "get-today": READ_ONLY_ANNOTATIONS,
    "get-upcoming": READ_ONLY_ANNOTATIONS,
    "get-anytime": READ_ONLY_ANNOTATIONS,
    "get-someday": READ_ONLY_ANNOTATIONS,
    "get-logbook": READ_ONLY_ANNOTATIONS,
    "get-trash": READ_ONLY_ANNOTATIONS,
    "get-todos": READ_ONLY_ANNOTATIONS,
    "get-projects": READ_ONLY_ANNOTATIONS,
    "get-areas": READ_ONLY_ANNOTATIONS,
    "get-tags": READ_ONLY_ANNOTATIONS,
    "get-tagged-items": READ_ONLY_ANNOTATIONS,
    "count-items": READ_ONLY_ANNOTATIONS,
    "count-search": READ_ONLY_ANNOTATIONS,
    "count-tagged-items": READ_ONLY_ANNOTATIONS,
    "count-project-items": READ_ONLY_ANNOTATIONS,
    "count-advanced": READ_ONLY_ANNOTATIONS,
    "get-overdue-items": READ_ONLY_ANNOTATIONS,
    "get-items-due-soon": READ_ONLY_ANNOTATIONS,
    "set-deadline": UPDATE_ANNOTATIONS,
    "get-checklist-items": READ_ONLY_ANNOTATIONS,
    "add-checklist-item": ADD_ANNOTATIONS,
    "update-checklist-item": UPDATE_ANNOTATIONS,
    "get-todos-with-checklists": READ_ONLY_ANNOTATIONS,
    "add-heading": ADD_ANNOTATIONS,
    "get-project-structure": READ_ONLY_ANNOTATIONS,
    "move-todo-under-heading": UPDATE_ANNOTATIONS,
    "move-item-to-project": UPDATE_ANNOTATIONS,
    "search-todos": READ_ONLY_ANNOTATIONS,
    "search-advanced": READ_ONLY_ANNOTATIONS,
    "add-todo": ADD_ANNOTATIONS,
    "add-todo-interactive": ADD_ANNOTATIONS,
    "bulk-complete-todos": MODIFY_ANNOTATIONS,
    "bulk-schedule-todos": MODIFY_ANNOTATIONS,
    "bulk-tag-todos": MODIFY_ANNOTATIONS,
    "bulk-move-todos": MODIFY_ANNOTATIONS,
    "add-project": ADD_ANNOTATIONS,
    "update-todo": UPDATE_ANNOTATIONS,
    "update-project": UPDATE_ANNOTATIONS,
    "show-item": READ_ONLY_ANNOTATIONS,
    "search-items": READ_ONLY_ANNOTATIONS,
    "get-recent": READ_ONLY_ANNOTATIONS,
    "get-cache-stats": READ_ONLY_ANNOTATIONS,
}

# Configure enhanced logging
setup_logging(console_level="INFO", file_level="DEBUG", structured_logs=True)
logger = get_logger(__name__)


INSTRUCTIONS_TEXT = (
    "### Things MCP server guidance\n\n"
    "Use these tools to review and maintain your Things 3 workspace on macOS."
    "\n\n"
    "**Capabilities**\n"
    "- List inbox, Today, Upcoming, Someday, Anytime, and Logbook items\n"
    "- Inspect and update projects, areas, tags, and todos via the Things URL scheme\n"
    "- Launch advanced Things automations with pre-built URL actions\n\n"
    "**Limitations**\n"
    "- Requires Things 3 for macOS with scripting permissions enabled\n"
    "- Only accesses data stored locally in Things; attachments remain unavailable\n"
    "- Some operations depend on the Things URL scheme and may take a few seconds\n\n"
    "**Support & Contact**\n"
    "- Review outputs before sharing because personal data may be present\n"
    "- Report issues or request features at https://github.com/CaseyRo/things-fastmcp/issues\n"
)

WEBSITE_URL = "https://github.com/CaseyRo/things-fastmcp"

# Type alias supporting both newer FastMCP installs (with mcp.types.Icon)
# and older releases that still expect simple dictionaries for icon metadata.
IconLike = Union[Any, Dict[str, Any]]


def _build_icon(src: str, *, sizes: Optional[List[str]] = None, mime_type: Optional[str] = None) -> IconLike:
    """Create an icon instance compatible with the available MCP types module."""
    icon_cls = getattr(types, "Icon", None)
    if icon_cls is not None:
        return icon_cls(src=src, sizes=sizes, mimeType=mime_type)

    # Fall back to a plain dictionary for environments running an older MCP build
    # that predates the Icon model.
    icon_data: Dict[str, Any] = {"src": src}
    if sizes:
        icon_data["sizes"] = sizes
    if mime_type:
        icon_data["mimeType"] = mime_type
    return icon_data


ICONS: List[IconLike] = [
    _build_icon(
        src="https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/72x72/1F4DD.png",
        sizes=["64x64"],
    ),
]


def _error_result(message: str) -> types.CallToolResult:
    """Return a standardized error result for MCP tools."""

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        isError=True,
    )


def _apply_sort_and_limit(items: List[Any], sort_by: Optional[str] = None, limit: Optional[int] = None) -> List[Any]:
    """
    Apply sorting and limiting to a list of items.
    
    Args:
        items: List of items to process
        sort_by: Field to sort by ('title', 'created', 'modified', 'deadline', 'start_date')
        limit: Maximum number of items to return
        
    Returns:
        Processed list of items
    """
    if not items:
        return items
    
    # Sort if requested using a mapping dictionary for cleaner code
    if sort_by:
        def get_field_value(item, field: str) -> Any:
            """Helper to get field value from either object attribute or dict key."""
            if hasattr(item, field):
                return getattr(item, field, None) or ''
            elif isinstance(item, dict):
                return item.get(field, '') or ''
            return ''
        
        sort_configs = {
            'title': (lambda x: get_field_value(x, 'title').lower(), False),
            'created': (lambda x: get_field_value(x, 'created'), True),
            'modified': (lambda x: get_field_value(x, 'modified'), True),
            'deadline': (lambda x: get_field_value(x, 'deadline'), True),
            'start_date': (lambda x: get_field_value(x, 'start_date'), True),
        }
        
        if sort_by in sort_configs:
            key_func, reverse = sort_configs[sort_by]
            items = sorted(items, key=key_func, reverse=reverse)
    
    # Limit results if requested
    if limit and limit > 0:
        items = items[:limit]
    
    return items


def _format_metadata(total: int, limit: Optional[int] = None, sort_by: Optional[str] = None, extra: str = "") -> str:
    """
    Format metadata string for result output.
    
    Args:
        total: Total number of items
        limit: Limit applied (if any)
        sort_by: Sort field applied (if any)
        extra: Additional metadata text
        
    Returns:
        Formatted metadata string
    """
    metadata = f"Found {total} item(s)"
    if extra:
        metadata += f" {extra}"
    if limit and total >= limit:
        metadata += f" (limited to {limit})"
    if sort_by:
        metadata += f" sorted by {sort_by}"
    return metadata


def _apply_type_filter(items: List[Dict], type_filter: Optional[str]) -> List[Dict]:
    """
    Filter items by type.
    
    Args:
        items: List of Things items (todos, projects, headings, etc.)
        type_filter: Type to filter by ('to-do', 'project', 'heading', 'area')
                    If None, no filtering is applied.
    
    Returns:
        Filtered list of items
    """
    if not type_filter:
        return items
    
    return [item for item in items if item.get('type') == type_filter]


def _apply_status_filter(items: List[Dict], status_filter: Optional[str]) -> List[Dict]:
    """
    Filter items by status.
    
    Args:
        items: List of Things items
        status_filter: Status to filter by ('incomplete', 'completed', 'canceled')
                      If None, no filtering is applied.
    
    Returns:
        Filtered list of items
    """
    if not status_filter:
        return items
    
    return [item for item in items if item.get('status') == status_filter]


def _apply_deadline_filter(items: List[Dict], deadline_filter: Optional[str]) -> List[Dict]:
    """
    Filter items by deadline status.
    
    Args:
        items: List of Things items
        deadline_filter: Deadline status to filter by:
                        - 'overdue': Items with deadlines in the past
                        - 'today': Items with deadlines today
                        - 'upcoming': Items with future deadlines
                        - 'none': Items without deadlines
                        If None, no filtering is applied.
    
    Returns:
        Filtered list of items
    """
    if not deadline_filter:
        return items
    
    from datetime import datetime, date
    today = date.today()
    
    filtered = []
    for item in items:
        deadline_str = item.get('deadline')
        
        if deadline_filter == 'none':
            if not deadline_str:
                filtered.append(item)
        elif deadline_filter == 'overdue':
            if deadline_str:
                try:
                    deadline_date = datetime.fromisoformat(deadline_str).date()
                    if deadline_date < today:
                        filtered.append(item)
                except (ValueError, AttributeError):
                    pass
        elif deadline_filter == 'today':
            if deadline_str:
                try:
                    deadline_date = datetime.fromisoformat(deadline_str).date()
                    if deadline_date == today:
                        filtered.append(item)
                except (ValueError, AttributeError):
                    pass
        elif deadline_filter == 'upcoming':
            if deadline_str:
                try:
                    deadline_date = datetime.fromisoformat(deadline_str).date()
                    if deadline_date > today:
                        filtered.append(item)
                except (ValueError, AttributeError):
                    pass
    
    return filtered


# Network binding configuration
HOST_ENV_VAR = "THINGS_FASTMCP_HOST"
PORT_ENV_VAR = "THINGS_FASTMCP_PORT"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8009


@lru_cache(maxsize=1)
def get_binding_host() -> str:
    """Return the host for the FastMCP server, honoring the override env var."""
    value = os.getenv(HOST_ENV_VAR)
    if value is None:
        return DEFAULT_HOST

    value = value.strip()
    return value or DEFAULT_HOST


@lru_cache(maxsize=1)
def get_binding_port() -> int:
    """Return the port for the FastMCP server, honoring the override env var."""
    value = os.getenv(PORT_ENV_VAR)
    if value is None or not value.strip():
        return DEFAULT_PORT

    stripped = value.strip()

    try:
        port = int(stripped)
    except ValueError:
        logger.warning(
            "Invalid %s value '%s'; falling back to default port %s",
            PORT_ENV_VAR,
            value,
            DEFAULT_PORT,
        )
        return DEFAULT_PORT

    if not 0 < port < 65536:
        logger.warning(
            "%s value %s out of valid TCP port range; using default %s",
            PORT_ENV_VAR,
            port,
            DEFAULT_PORT,
        )
        return DEFAULT_PORT

    return port

# Determine supported FastMCP constructor arguments at import time so the
# server remains compatible with runtimes that predate newer metadata
# parameters like `website_url` and `icons`.
_fastmcp_init_params = inspect.signature(FastMCP.__init__).parameters

_FASTMCP_SUPPORTS_WEBSITE_URL = "website_url" in _fastmcp_init_params
_FASTMCP_SUPPORTS_ICONS = "icons" in _fastmcp_init_params


def _create_fastmcp_instance() -> FastMCP:
    kwargs: Dict[str, Any] = {
        "instructions": INSTRUCTIONS_TEXT,
    }

    if _FASTMCP_SUPPORTS_WEBSITE_URL:
        kwargs["website_url"] = WEBSITE_URL
    else:
        logger.debug("FastMCP runtime does not support website_url; skipping metadata field")

    if _FASTMCP_SUPPORTS_ICONS:
        kwargs["icons"] = ICONS
    else:
        logger.debug("FastMCP runtime does not support icons; skipping metadata field")

    return FastMCP("Things", **kwargs)


# Create the FastMCP server
mcp = _create_fastmcp_instance()

# Add middleware for performance monitoring and error handling
logger.info("Adding FastMCP middleware: Performance monitoring and error handling")
mcp.add_middleware(DetailedTimingMiddleware())  # Per-operation timing
mcp.add_middleware(ErrorHandlingMiddleware(
    include_traceback=True,  # Include traceback for debugging
    transform_errors=True,   # Transform errors to consistent format
))
logger.info("FastMCP middleware configured successfully")

# LIST VIEWS

@mcp.tool(name="get-inbox", annotations=TOOL_ANNOTATIONS["get-inbox"])
async def get_inbox(
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    type_filter: Optional[str] = None,
    deadline_filter: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Get todos from Inbox with optional filtering
    
    IMPORTANT: Use the 'limit' parameter to avoid overwhelming the context window.
    For targeted queries (e.g., "find 10 items with URLs"), always specify a limit.
    
    Args:
        limit: Maximum number of results to return. Recommended: 10-50 for focused tasks. (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
        type_filter: Filter by item type - 'to-do', 'project', 'heading' (optional)
        deadline_filter: Filter by deadline - 'overdue', 'today', 'upcoming', 'none' (optional)
    """
    import time
    start_time = time.time()
    log_operation_start("get-inbox")

    try:
        todos = things.inbox()

        if not todos:
            log_operation_end("get-inbox", True, time.time() - start_time, count=0)
            return "No items found in Inbox"

        # Apply filters
        if type_filter:
            todos = _apply_type_filter(todos, type_filter)
        if deadline_filter:
            todos = _apply_deadline_filter(todos, deadline_filter)
        
        if not todos:
            filter_desc = []
            if type_filter:
                filter_desc.append(f"type={type_filter}")
            if deadline_filter:
                filter_desc.append(f"deadline={deadline_filter}")
            log_operation_end("get-inbox", True, time.time() - start_time, count=0)
            return f"No inbox items matching filters: {', '.join(filter_desc)}"

        total_count = len(todos)
        
        # Warn if returning large result set without limit
        if ctx and not limit and total_count > 20:
            await ctx.warning(
                f"Returning all {total_count} inbox items without a limit. "
                f"Consider using limit parameter (e.g., limit=10) to reduce context window usage.",
                extra={"total_items": total_count, "limit_used": False}
            )

        # Apply sorting and limiting
        todos = _apply_sort_and_limit(todos, sort_by, limit)
        
        formatted_todos = [format_todo(todo) for todo in todos]
        log_operation_end("get-inbox", True, time.time() - start_time, count=len(todos))
        
        result = "\n\n---\n\n".join(formatted_todos)
        extra_info = f"from {total_count} total" if limit and total_count > len(todos) else ""
        metadata = _format_metadata(len(todos), limit, sort_by, extra=extra_info)
        return f"{metadata}\n\n{result}"
    except Exception as e:
        log_operation_end("get-inbox", False, time.time() - start_time, error=str(e))
        raise

@mcp.tool(name="get-today", annotations=TOOL_ANNOTATIONS["get-today"])
@cached(ttl=CACHE_TTL.get("today", 30))
async def get_today(
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    type_filter: Optional[str] = None,
    deadline_filter: Optional[str] = None
) -> str:
    """
    Get todos due today
    
    IMPORTANT: Use the 'limit' parameter to avoid overwhelming the context window.
    For targeted queries, always specify a limit.
    
    Args:
        limit: Maximum number of results to return. Recommended: 10-50 for focused tasks. (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
        type_filter: Filter by item type - 'to-do', 'project', 'heading' (optional)
        deadline_filter: Filter by deadline - 'overdue', 'today', 'upcoming', 'none' (optional)
    """
    import time
    start_time = time.time()
    log_operation_start("get-today")

    try:
        todos = things.today()

        if not todos:
            log_operation_end("get-today", True, time.time() - start_time, count=0)
            return "No items due today"

        # Apply filters
        todos = _apply_type_filter(todos, type_filter)
        todos = _apply_deadline_filter(todos, deadline_filter)

        total_count = len(todos)

        # Apply sorting and limiting
        todos = _apply_sort_and_limit(todos, sort_by, limit)
        
        formatted_todos = [format_todo(todo) for todo in todos]
        log_operation_end("get-today", True, time.time() - start_time, count=len(todos))
        
        result = "\n\n---\n\n".join(formatted_todos)
        metadata = _format_metadata(total_count, limit, sort_by, extra=f"from {total_count} total")
        return f"{metadata}\n\n{result}"
    except Exception as e:
        log_operation_end("get-today", False, time.time() - start_time, error=str(e))
        raise

@mcp.tool(name="get-upcoming", annotations=TOOL_ANNOTATIONS["get-upcoming"])
async def get_upcoming(
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    type_filter: Optional[str] = None,
    deadline_filter: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Get upcoming todos
    
    IMPORTANT: Use the 'limit' parameter to avoid overwhelming the context window.
    For targeted queries, always specify a limit.
    
    Args:
        limit: Maximum number of results to return. Recommended: 10-50 for focused tasks. (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
        type_filter: Filter by item type - 'to-do', 'project', 'heading' (optional)
        deadline_filter: Filter by deadline - 'overdue', 'today', 'upcoming', 'none' (optional)
    """
    todos = things.upcoming()

    if not todos:
        return "No upcoming items"

    # Apply filters
    todos = _apply_type_filter(todos, type_filter)
    todos = _apply_deadline_filter(todos, deadline_filter)

    total_count = len(todos)
    
    # Warn if returning large result set without limit
    if ctx and not limit and total_count > 20:
        await ctx.warning(
            f"Returning all {total_count} upcoming items without a limit. "
            f"Consider using limit parameter (e.g., limit=10) to reduce context window usage.",
            extra={"total_items": total_count, "limit_used": False}
        )

    # Apply sorting and limiting
    todos = _apply_sort_and_limit(todos, sort_by, limit)
    
    formatted_todos = [format_todo(todo) for todo in todos]
    result = "\n\n---\n\n".join(formatted_todos)
    metadata = _format_metadata(total_count, limit, sort_by, extra=f"from {total_count} total")
    return f"{metadata}\n\n{result}"

@mcp.tool(name="get-anytime", annotations=TOOL_ANNOTATIONS["get-anytime"])
async def get_anytime(
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    type_filter: Optional[str] = None,
    deadline_filter: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Get todos from Anytime list
    
    IMPORTANT: Use the 'limit' parameter to avoid overwhelming the context window.
    For targeted queries, always specify a limit.
    
    Args:
        limit: Maximum number of results to return. Recommended: 10-50 for focused tasks. (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
        type_filter: Filter by item type - 'to-do', 'project', 'heading' (optional)
        deadline_filter: Filter by deadline - 'overdue', 'today', 'upcoming', 'none' (optional)
    """
    todos = things.anytime()

    if not todos:
        return "No items in Anytime list"

    # Apply filters
    todos = _apply_type_filter(todos, type_filter)
    todos = _apply_deadline_filter(todos, deadline_filter)

    total_count = len(todos)
    
    # Warn if returning large result set without limit
    if ctx and not limit and total_count > 20:
        await ctx.warning(
            f"Returning all {total_count} anytime items without a limit. "
            f"Consider using limit parameter (e.g., limit=10) to reduce context window usage.",
            extra={"total_items": total_count, "limit_used": False}
        )

    # Apply sorting and limiting
    todos = _apply_sort_and_limit(todos, sort_by, limit)
    
    formatted_todos = [format_todo(todo) for todo in todos]
    result = "\n\n---\n\n".join(formatted_todos)
    metadata = _format_metadata(total_count, limit, sort_by, extra=f"from {total_count} total")
    return f"{metadata}\n\n{result}"

@mcp.tool(name="get-someday", annotations=TOOL_ANNOTATIONS["get-someday"])
async def get_someday(
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    type_filter: Optional[str] = None,
    deadline_filter: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Get todos from Someday list
    
    IMPORTANT: Use the 'limit' parameter to avoid overwhelming the context window.
    For targeted queries, always specify a limit.
    
    Args:
        limit: Maximum number of results to return. Recommended: 10-50 for focused tasks. (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
        type_filter: Filter by item type - 'to-do', 'project', 'heading' (optional)
        deadline_filter: Filter by deadline - 'overdue', 'today', 'upcoming', 'none' (optional)
    """
    todos = things.someday()

    if not todos:
        return "No items in Someday list"

    # Apply filters
    todos = _apply_type_filter(todos, type_filter)
    todos = _apply_deadline_filter(todos, deadline_filter)

    total_count = len(todos)
    
    # Warn if returning large result set without limit
    if ctx and not limit and total_count > 20:
        await ctx.warning(
            f"Returning all {total_count} someday items without a limit. "
            f"Consider using limit parameter (e.g., limit=10) to reduce context window usage.",
            extra={"total_items": total_count, "limit_used": False}
        )

    # Apply sorting and limiting
    todos = _apply_sort_and_limit(todos, sort_by, limit)
    
    formatted_todos = [format_todo(todo) for todo in todos]
    result = "\n\n---\n\n".join(formatted_todos)
    metadata = _format_metadata(total_count, limit, sort_by, extra=f"from {total_count} total")
    return f"{metadata}\n\n{result}"

@mcp.tool(name="get-logbook", annotations=TOOL_ANNOTATIONS["get-logbook"])
async def get_logbook(
    period: str = "7d",
    limit: int = 50,
    sort_by: Optional[str] = None,
    type_filter: Optional[str] = None,
    deadline_filter: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Get completed todos from Logbook, defaults to last 7 days

    IMPORTANT: Use the 'limit' parameter to avoid overwhelming the context window.
    For targeted queries, always specify a limit.

    Args:
        period: Time period to look back (e.g., '3d', '1w', '2m', '1y'). Defaults to '7d'
        limit: Maximum number of entries to return. Defaults to 50. Recommended: 10-50 for focused tasks.
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
        type_filter: Filter by item type - 'to-do', 'project', 'heading' (optional)
        deadline_filter: Filter by deadline - 'overdue', 'today', 'upcoming', 'none' (optional)
    """
    todos = things.last(period, status='completed')

    if not todos:
        return "No completed items found"

    # Apply filters
    todos = _apply_type_filter(todos, type_filter)
    todos = _apply_deadline_filter(todos, deadline_filter)

    total_count = len(todos)
    
    # Warn if returning large result set without reasonable limit
    if ctx and limit and limit > 50:
        await ctx.warning(
            f"Returning {limit} logbook items. Large limits may overwhelm the context window. "
            f"Consider using smaller limit (e.g., limit=20) for better performance.",
            extra={"total_items": total_count, "limit_used": limit}
        )

    # Apply sorting and limiting
    todos = _apply_sort_and_limit(todos, sort_by, limit)

    formatted_todos = [format_todo(todo) for todo in todos]
    result = "\n\n---\n\n".join(formatted_todos)
    metadata = _format_metadata(total_count, limit, sort_by, f"from last {period}")
    return f"{metadata}\n\n{result}"

@mcp.tool(name="get-trash", annotations=TOOL_ANNOTATIONS["get-trash"])
async def get_trash(
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    type_filter: Optional[str] = None,
    deadline_filter: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Get trashed todos
    
    IMPORTANT: Use the 'limit' parameter to avoid overwhelming the context window.
    For targeted queries, always specify a limit.
    
    Args:
        limit: Maximum number of results to return. Recommended: 10-50 for focused tasks. (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
        type_filter: Filter by item type - 'to-do', 'project', 'heading' (optional)
        deadline_filter: Filter by deadline - 'overdue', 'today', 'upcoming', 'none' (optional)
    """
    todos = things.trash()

    if not todos:
        return "No items in trash"

    # Apply filters
    todos = _apply_type_filter(todos, type_filter)
    todos = _apply_deadline_filter(todos, deadline_filter)

    total_count = len(todos)
    
    # Warn if returning large result set without limit
    if ctx and not limit and total_count > 20:
        await ctx.warning(
            f"Returning all {total_count} trash items without a limit. "
            f"Consider using limit parameter (e.g., limit=10) to reduce context window usage.",
            extra={"total_items": total_count, "limit_used": False}
        )

    # Apply sorting and limiting
    todos = _apply_sort_and_limit(todos, sort_by, limit)

    formatted_todos = [format_todo(todo) for todo in todos]
    result = "\n\n---\n\n".join(formatted_todos)
    metadata = _format_metadata(total_count, limit, sort_by, extra=f"from {total_count} total")
    return f"{metadata}\n\n{result}"

# BASIC TODO OPERATIONS

@mcp.tool(name="get-todos", annotations=TOOL_ANNOTATIONS["get-todos"])
def get_todos(
    project_uuid: Optional[str] = None, include_items: bool = True
) -> str:
    """
    Get todos from Things, optionally filtered by project

    Args:
        project_uuid: Optional UUID of a specific project to get todos from
        include_items: Include checklist items
    """
    if project_uuid:
        project = things.get(project_uuid)
        # things.get() returns a dict or None (type checker may not know this)
        if not project or (isinstance(project, dict) and project.get('type') != 'project'):
            return _error_result(f"Error: Invalid project UUID '{project_uuid}'")

    todos = things.todos(project=project_uuid, start=None)

    if not todos:
        return "No todos found"

    formatted_todos = [format_todo(todo) for todo in todos]
    return "\n\n---\n\n".join(formatted_todos)

@mcp.tool(name="get-projects", annotations=TOOL_ANNOTATIONS["get-projects"])
def get_projects(include_items: bool = False) -> str:
    """
    Get all projects from Things

    Args:
        include_items: Include tasks within projects
    """
    projects = things.projects()

    if not projects:
        return "No projects found"

    formatted_projects = [format_project(project, include_items) for project in projects]
    return "\n\n---\n\n".join(formatted_projects)

@mcp.tool(name="get-areas", annotations=TOOL_ANNOTATIONS["get-areas"])
def get_areas(include_items: bool = False) -> str:
    """
    Get all areas from Things

    Args:
        include_items: Include projects and tasks within areas
    """
    areas = things.areas()

    if not areas:
        return "No areas found"

    formatted_areas = [format_area(area, include_items) for area in areas]
    return "\n\n---\n\n".join(formatted_areas)

# TAG OPERATIONS

@mcp.tool(name="get-tags", annotations=TOOL_ANNOTATIONS["get-tags"])
def get_tags(include_items: bool = False) -> str:
    """
    Get all tags

    Args:
        include_items: Include items tagged with each tag
    """
    tags = things.tags()

    if not tags:
        return "No tags found"

    formatted_tags = [format_tag(tag, include_items) for tag in tags]
    return "\n\n---\n\n".join(formatted_tags)

@mcp.tool(name="get-tagged-items", annotations=TOOL_ANNOTATIONS["get-tagged-items"])
def get_tagged_items(
    tag: str,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: Optional[int] = None,
    sort_by: Optional[str] = None
) -> str:
    """
    Get items with a specific tag, with optional filtering and sorting

    Args:
        tag: Tag title to filter by
        type_filter: Filter by item type - 'to-do', 'project', 'heading', 'area' (optional)
        status_filter: Filter by status - 'incomplete', 'completed', 'canceled' (optional)
        limit: Maximum number of results to return (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
    
    Example:
        >>> get_tagged_items("work", type_filter="to-do", status_filter="incomplete")
        Get incomplete work todos
        
        >>> get_tagged_items("urgent", limit=10, sort_by="deadline")
        Get first 10 urgent items sorted by deadline
    """
    todos = things.todos(tag=tag)

    if not todos:
        return f"No items found with tag '{tag}'"

    # Apply filters
    if type_filter:
        todos = _apply_type_filter(todos, type_filter)
    if status_filter:
        todos = _apply_status_filter(todos, status_filter)
    
    # Check if filters removed all results
    if not todos:
        filter_desc = []
        if type_filter:
            filter_desc.append(f"type={type_filter}")
        if status_filter:
            filter_desc.append(f"status={status_filter}")
        return f"No items found with tag '{tag}' matching filters: {', '.join(filter_desc)}"
    
    # Store total before limiting
    total_count = len(todos)
    
    # Apply sorting and limiting
    todos = _apply_sort_and_limit(todos, sort_by, limit)

    formatted_todos = [format_todo(todo) for todo in todos]
    result = "\n\n---\n\n".join(formatted_todos)
    
    # Add metadata
    extra_info = f"from {total_count} total" if limit and total_count > len(todos) else ""
    metadata = _format_metadata(len(todos), limit, sort_by, extra=extra_info)
    
    return f"{metadata}\n\n{result}"

# SEARCH OPERATIONS

@mcp.tool(name="count-items", annotations=TOOL_ANNOTATIONS["count-items"])
def count_items() -> str:
    """
    Get counts of items in each main Things area (lightweight alternative to fetching full data)
    
    Use this tool to check the size of different areas before deciding whether to use
    limit parameters on other query tools. This helps prevent context window overflow.
    
    Returns counts for:
    - Inbox: Items in the inbox
    - Today: Items scheduled for today
    - Upcoming: Items with future start dates
    - Anytime: Items without specific scheduling
    - Someday: Items in the someday list
    - Logbook: Completed/cancelled items
    - Trash: Deleted items
    
    Note: This is a read-only operation that queries the local Things database directly.
    No URL schemes or authentication tokens are needed.
    """
    try:
        logger.debug("count-items: Starting read-only database queries")
        counts = {
            'inbox': len(things.inbox()),
            'today': len(things.today()),
            'upcoming': len(things.upcoming()),
            'anytime': len(things.anytime()),
            'someday': len(things.someday()),
            'logbook': len(things.logbook()),
            'trash': len(things.trash())
        }
        logger.debug(f"count-items: Successfully retrieved counts: {counts}")
        
        result_lines = [
            "Item counts by area:",
            f"  Inbox: {counts['inbox']} items",
            f"  Today: {counts['today']} items",
            f"  Upcoming: {counts['upcoming']} items",
            f"  Anytime: {counts['anytime']} items",
            f"  Someday: {counts['someday']} items",
            f"  Logbook: {counts['logbook']} items",
            f"  Trash: {counts['trash']} items",
            "",
            f"Total items: {sum(counts.values())}"
        ]
        
        # Add recommendations based on counts
        large_areas = [area for area, count in counts.items() if count > 20]
        if large_areas:
            result_lines.extend([
                "",
                f"Recommendation: Use 'limit' parameter when querying {', '.join(large_areas)} "
                f"to prevent context window overflow."
            ])
        
        return "\n".join(result_lines)
    except Exception as e:
        logger.error(f"count-items error: {str(e)}", exc_info=True)
        return _error_result(f"Error getting item counts: {str(e)}")

@mcp.tool(name="count-search", annotations=TOOL_ANNOTATIONS.get("count-search", READ_ONLY_ANNOTATIONS))
def count_search(query: str) -> str:
    """
    Count how many items match a search query without fetching full data
    
    Use this before search-todos to determine result size and plan pagination strategy.
    
    Args:
        query: Search term to look for in todo titles and notes
    """
    try:
        todos = things.search(query)
        count = len(todos)
        
        result = f"Found {count} item(s) matching '{query}'"
        
        if count > 20:
            result += "\n\nRecommendation: Use offset/limit parameters with search-todos to paginate through results."
            result += "\nExample: offset=0, limit=20 for first page, then offset=20, limit=20 for second page."
        
        return result
    except Exception as e:
        return _error_result(f"Error counting search results: {str(e)}")

@mcp.tool(name="count-tagged-items", annotations=TOOL_ANNOTATIONS.get("count-tagged-items", READ_ONLY_ANNOTATIONS))
def count_tagged_items(tag: str) -> str:
    """
    Count how many items have a specific tag without fetching full data
    
    Use this before get-tagged-items to determine result size and plan pagination strategy.
    
    Args:
        tag: Tag name to count items for
    """
    try:
        todos = things.todos(tag=tag)
        count = len(todos)
        
        result = f"Found {count} item(s) with tag '{tag}'"
        
        if count > 20:
            result += "\n\nRecommendation: Use limit parameter with get-tagged-items to manage result size."
        
        return result
    except Exception as e:
        return _error_result(f"Error counting tagged items: {str(e)}")

@mcp.tool(name="count-project-items", annotations=TOOL_ANNOTATIONS.get("count-project-items", READ_ONLY_ANNOTATIONS))
def count_project_items(project_uuid: str) -> str:
    """
    Count how many items are in a specific project without fetching full data
    
    Use this before get-todos to determine result size and plan pagination strategy.
    
    Args:
        project_uuid: UUID of the project to count items for
    """
    try:
        todos = things.todos(project=project_uuid, start=None)
        count = len(todos)
        
        result = f"Found {count} item(s) in project '{project_uuid}'"
        
        if count > 20:
            result += "\n\nRecommendation: Use limit parameter with get-todos to manage result size."
        
        return result
    except Exception as e:
        return _error_result(f"Error counting project items: {str(e)}")

@mcp.tool(name="count-advanced", annotations=TOOL_ANNOTATIONS.get("count-advanced", READ_ONLY_ANNOTATIONS))
def count_advanced(
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    deadline: Optional[str] = None,
    tag: Optional[str] = None,
    area: Optional[str] = None,
    type: Optional[str] = None
) -> str:
    """
    Count how many items match advanced search criteria without fetching full data
    
    Use this before search-advanced to determine result size and plan pagination strategy.
    
    Args:
        status: Filter by todo status (incomplete/completed/canceled)
        start_date: Filter by start date (YYYY-MM-DD)
        deadline: Filter by deadline (YYYY-MM-DD)
        tag: Filter by tag
        area: Filter by area UUID
        type: Filter by item type (to-do/project/heading)
    """
    try:
        kwargs = {}
        if status:
            kwargs['status'] = status
        if deadline:
            kwargs['deadline'] = deadline
        if start_date:
            kwargs['start'] = start_date
        if tag:
            kwargs['tag'] = tag
        if area:
            kwargs['area'] = area
        if type:
            kwargs['type'] = type
        
        todos = things.todos(**kwargs)
        count = len(todos)
        
        filters_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        result = f"Found {count} item(s) matching criteria: {filters_str}"
        
        if count > 20:
            result += "\n\nRecommendation: Use offset/limit parameters with search-advanced to paginate through results."
        
        return result
    except Exception as e:
        return _error_result(f"Error counting advanced search results: {str(e)}")

# ============================================================================
# Deadline Management (Phase 1: Critical Gaps)
# ============================================================================

@mcp.tool(name="get-overdue-items", annotations=TOOL_ANNOTATIONS["get-overdue-items"])
def get_overdue_items(
    limit: Optional[int] = None,
    sort_by: Optional[str] = 'deadline'
) -> str:
    """
    Get all incomplete items with deadlines in the past (overdue).
    
    Returns todos sorted by deadline (most overdue first) with metadata showing
    how many days overdue each item is.
    
    Args:
        limit: Maximum number of items to return (default: all)
        sort_by: Sort method - 'deadline' (most overdue first), 'title', 'created', 'modified'
    
    Returns:
        Formatted list of overdue items with deadline information and days overdue
    
    Example:
        overdue = get_overdue_items(limit=10)  # Get 10 most overdue items
    """
    try:
        from datetime import datetime, date
        
        # Get all todos
        all_todos = things.todos()
        
        # Filter to incomplete items with deadlines in the past
        today = date.today()
        overdue_items = []
        
        for item in all_todos:
            # Only incomplete items
            if item.get('status') != 'incomplete':
                continue
            
            deadline_str = item.get('deadline')
            if not deadline_str:
                continue
            
            try:
                deadline_date = datetime.fromisoformat(deadline_str).date()
                if deadline_date < today:
                    # Calculate days overdue
                    days_overdue = (today - deadline_date).days
                    item['days_overdue'] = days_overdue
                    overdue_items.append(item)
            except (ValueError, AttributeError):
                pass
        
        total_count = len(overdue_items)
        
        # Sort items (default: most overdue first)
        if sort_by == 'deadline':
            overdue_items.sort(key=lambda x: x.get('deadline', ''), reverse=False)  # Oldest first
        else:
            overdue_items = _apply_sort_and_limit(overdue_items, sort_by, None)
        
        # Apply limit after sorting
        if limit:
            overdue_items = overdue_items[:limit]
        
        if not overdue_items:
            return "No overdue items found."
        
        # Format results
        result_lines = []
        for item in overdue_items:
            title = item.get('title', 'Untitled')
            deadline = item.get('deadline', 'No deadline')
            days_overdue = item.get('days_overdue', 0)
            uuid = item.get('uuid', '')
            
            # Format deadline display
            if deadline and deadline != 'No deadline':
                try:
                    deadline_date = datetime.fromisoformat(deadline).date()
                    deadline_str = deadline_date.strftime('%Y-%m-%d')
                    overdue_badge = f"⚠️  {days_overdue} day{'s' if days_overdue != 1 else ''} overdue"
                except Exception:
                    deadline_str = deadline
                    overdue_badge = "⚠️  Overdue"
            else:
                deadline_str = "No deadline"
                overdue_badge = ""
            
            result_lines.append(f"• {title}")
            result_lines.append(f"  Deadline: {deadline_str} {overdue_badge}")
            result_lines.append(f"  UUID: {uuid}")
            result_lines.append("")
        
        result = "\n".join(result_lines)
        
        # Add metadata
        extra_info = f"from {total_count} total" if limit and total_count > len(overdue_items) else ""
        metadata = _format_metadata(len(overdue_items), limit, sort_by, extra=extra_info)
        
        return f"{metadata}\n\n{result}"
    
    except Exception as e:
        return _error_result(f"Error getting overdue items: {str(e)}")

@mcp.tool(name="get-items-due-soon", annotations=TOOL_ANNOTATIONS["get-items-due-soon"])
def get_items_due_soon(
    days: int = 7,
    limit: Optional[int] = None,
    sort_by: Optional[str] = 'deadline'
) -> str:
    """
    Get incomplete items with deadlines coming up within specified days.
    
    Returns todos sorted by deadline (soonest first) to help prioritize upcoming work.
    
    Args:
        days: Number of days to look ahead (default: 7)
        limit: Maximum number of items to return (default: all)
        sort_by: Sort method - 'deadline' (soonest first), 'title', 'created', 'modified'
    
    Returns:
        Formatted list of items due soon with deadline information
    
    Example:
        due_soon = get_items_due_soon(days=3, limit=10)  # Next 10 items due in 3 days
    """
    try:
        from datetime import datetime, date, timedelta
        
        # Get all todos
        all_todos = things.todos()
        
        # Calculate date range
        today = date.today()
        end_date = today + timedelta(days=days)
        
        # Filter to incomplete items with deadlines in the next N days
        due_soon_items = []
        
        for item in all_todos:
            # Only incomplete items
            if item.get('status') != 'incomplete':
                continue
            
            deadline_str = item.get('deadline')
            if not deadline_str:
                continue
            
            try:
                deadline_date = datetime.fromisoformat(deadline_str).date()
                if today <= deadline_date <= end_date:
                    # Calculate days until due
                    days_until = (deadline_date - today).days
                    item['days_until'] = days_until
                    due_soon_items.append(item)
            except (ValueError, AttributeError):
                pass
        
        total_count = len(due_soon_items)
        
        # Sort items (default: soonest first)
        if sort_by == 'deadline':
            due_soon_items.sort(key=lambda x: x.get('deadline', ''))
        else:
            due_soon_items = _apply_sort_and_limit(due_soon_items, sort_by, None)
        
        # Apply limit after sorting
        if limit:
            due_soon_items = due_soon_items[:limit]
        
        if not due_soon_items:
            return f"No items due in the next {days} day{'s' if days != 1 else ''}."
        
        # Format results
        result_lines = []
        for item in due_soon_items:
            title = item.get('title', 'Untitled')
            deadline = item.get('deadline', 'No deadline')
            days_until = item.get('days_until', 0)
            uuid = item.get('uuid', '')
            
            # Format deadline display
            if deadline and deadline != 'No deadline':
                try:
                    deadline_date = datetime.fromisoformat(deadline).date()
                    deadline_str = deadline_date.strftime('%Y-%m-%d')
                    
                    if days_until == 0:
                        urgency_badge = "🔴 Due today"
                    elif days_until == 1:
                        urgency_badge = "🟠 Due tomorrow"
                    else:
                        urgency_badge = f"🟡 Due in {days_until} days"
                except Exception:
                    deadline_str = deadline
                    urgency_badge = ""
            else:
                deadline_str = "No deadline"
                urgency_badge = ""
            
            result_lines.append(f"• {title}")
            result_lines.append(f"  Deadline: {deadline_str} {urgency_badge}")
            result_lines.append(f"  UUID: {uuid}")
            result_lines.append("")
        
        result = "\n".join(result_lines)
        
        # Add metadata
        extra_info = f"from {total_count} total" if limit and total_count > len(due_soon_items) else ""
        extra_info = f"due in next {days} day{'s' if days != 1 else ''}, {extra_info}" if extra_info else f"due in next {days} day{'s' if days != 1 else ''}"
        metadata = _format_metadata(len(due_soon_items), limit, sort_by, extra=extra_info)
        
        return f"{metadata}\n\n{result}"
    
    except Exception as e:
        return _error_result(f"Error getting items due soon: {str(e)}")

@mcp.tool(name="set-deadline", annotations=TOOL_ANNOTATIONS["set-deadline"])
def set_deadline(
    todo_uuid: str,
    deadline: str
) -> str:
    """
    Set or update the deadline for a todo.
    
    Uses Things URL scheme to set a deadline date. The deadline can be in ISO format
    (YYYY-MM-DD) or a natural language date that can be parsed.
    
    Args:
        todo_uuid: UUID of the todo to update
        deadline: Deadline date in YYYY-MM-DD format (e.g., '2025-12-31')
                 Special values: 'today', 'tomorrow', 'none' (to clear deadline)
    
    Returns:
        Success message with the todo title and new deadline
    
    Example:
        result = set_deadline(todo_uuid="ABC123", deadline="2025-12-31")
        result = set_deadline(todo_uuid="ABC123", deadline="today")
        result = set_deadline(todo_uuid="ABC123", deadline="none")  # Clear deadline
    """
    try:
        from datetime import datetime, date, timedelta
        import urllib.parse
        
        # Validate todo exists
        todo = things.get(todo_uuid)
        if not todo:
            return _error_result(f"Todo not found: {todo_uuid}")
        
        if isinstance(todo, list):
            if not todo:
                return _error_result(f"Todo not found: {todo_uuid}")
            todo = todo[0]
        
        if todo.get('type') != 'to-do':
            return _error_result(f"Item {todo_uuid} is not a todo (type: {todo.get('type')})")
        
        # Parse deadline
        parsed_deadline = None
        today = date.today()
        
        if deadline.lower() == 'none':
            # Clear deadline - pass empty string
            parsed_deadline = ''
            deadline_display = "cleared"
        elif deadline.lower() == 'today':
            parsed_deadline = today.strftime('%Y-%m-%d')
            deadline_display = f"{parsed_deadline} (today)"
        elif deadline.lower() == 'tomorrow':
            tomorrow = today + timedelta(days=1)
            parsed_deadline = tomorrow.strftime('%Y-%m-%d')
            deadline_display = f"{parsed_deadline} (tomorrow)"
        else:
            # Try to parse as ISO date
            try:
                parsed_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                parsed_deadline = parsed_date.strftime('%Y-%m-%d')
                deadline_display = parsed_deadline
            except ValueError:
                return _error_result(f"Invalid deadline format: '{deadline}'. Use YYYY-MM-DD, 'today', 'tomorrow', or 'none'")
        
        # Build Things URL
        if parsed_deadline == '':
            # Clear deadline - don't include deadline parameter
            url = f"things:///update?id={urllib.parse.quote(todo_uuid)}&deadline="
        else:
            url = f"things:///update?id={urllib.parse.quote(todo_uuid)}&deadline={urllib.parse.quote(parsed_deadline)}"
        
        # Execute URL scheme
        success = execute_url(url)
        
        if success:
            # Invalidate cache
            invalidate_caches_for(["get-todos"])
            
            todo_title = todo.get('title', 'Untitled')
            return f"✓ Set deadline for '{todo_title}' to: {deadline_display}"
        else:
            return _error_result(f"Failed to set deadline for todo: {todo_uuid}")
    
    except Exception as e:
        return _error_result(f"Error setting deadline: {str(e)}")

# ============================================================================
# Checklist Operations (Phase 1: Critical Gaps)
# ============================================================================

@mcp.tool(name="get-checklist-items", annotations=TOOL_ANNOTATIONS["get-checklist-items"])
def get_checklist_items(todo_uuid: str) -> str:
    """
    Get all checklist items for a specific todo.
    
    Returns formatted list of checklist items with their completion status.
    Use this to review what needs to be done within a todo's checklist.
    
    Args:
        todo_uuid: UUID of the todo containing the checklist
    """
    try:
        # First verify the todo exists
        todo = things.get(todo_uuid)
        if not todo:
            return _error_result(f"Todo {todo_uuid} not found")
        
        # Handle list response from things.get()
        if isinstance(todo, list):
            if not todo:
                return _error_result(f"Todo {todo_uuid} not found")
            todo = todo[0]
        
        if todo.get('type') != 'to-do':
            return _error_result(f"Item {todo_uuid} is not a todo (type: {todo.get('type')})")
        
        # Get checklist items
        items = things.checklist_items(todo_uuid)
        
        if not items:
            return f"No checklist found for todo: {todo.get('title', todo_uuid)}"
        
        # Format output
        lines = [
            f"Checklist for: {todo.get('title', 'Untitled')}",
            f"Todo UUID: {todo_uuid}",
            f"Total items: {len(items)}",
            ""
        ]
        
        completed_count = 0
        for item in items:
            status = item.get('status', 'incomplete')
            if status == 'completed':
                status_icon = "✓"
                completed_count += 1
            else:
                status_icon = "○"
            
            lines.append(f"  {status_icon} {item.get('title', 'Untitled item')}")
        
        # Add progress summary
        progress_pct = (completed_count / len(items) * 100) if items else 0
        lines.append(f"\nProgress: {completed_count}/{len(items)} ({progress_pct:.0f}%)")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error getting checklist items: {str(e)}")
        return _error_result(f"Error getting checklist items: {str(e)}")

@mcp.tool(name="add-checklist-item", annotations=TOOL_ANNOTATIONS["add-checklist-item"])
def add_checklist_item(
    todo_uuid: str,
    items: str,
    ctx: Optional[Context] = None
) -> str:
    """
    Add checklist items to an existing todo.
    
    Creates or appends to a checklist within a todo. Items can be added one at a time
    or multiple items separated by newlines.
    
    Args:
        todo_uuid: UUID of the todo to add checklist items to
        items: Checklist items to add (newline-separated for multiple items)
        ctx: Context for progress reporting
    
    Example:
        items="Buy milk\\nBuy eggs\\nBuy bread" adds 3 checklist items
    """
    try:
        # Ensure Things app is running
        if not app_state.update_app_state():
            if not launch_things():
                return _error_result("Error: Unable to launch Things app")
        
        # Verify todo exists
        todo = things.get(todo_uuid)
        if not todo:
            return _error_result(f"Todo {todo_uuid} not found")
        
        # Handle list response from things.get()
        if isinstance(todo, list):
            if not todo:
                return _error_result(f"Todo {todo_uuid} not found")
            todo = todo[0]
        
        if todo.get('type') != 'to-do':
            return _error_result(f"Item {todo_uuid} is not a todo (type: {todo.get('type')})")
        
        # Build URL scheme - Things uses checklist-items parameter
        # Format: items separated by newlines, URL encoded
        import urllib.parse
        items_encoded = urllib.parse.quote(items)
        url = f"things:///update?id={todo_uuid}&checklist-items={items_encoded}"
        
        logger.debug(f"Add checklist URL: {url}")
        success = execute_url(url)
        
        if not success:
            return _error_result("Error: Failed to add checklist items")
        
        # Count items added
        item_list = items.split("\n")
        item_count = len([item for item in item_list if item.strip()])
        
        # Invalidate caches
        invalidate_caches_for(["get-todos"])
        
        return f"✓ Added {item_count} checklist item(s) to: {todo.get('title', 'todo')}"
        
    except Exception as e:
        logger.error(f"Error adding checklist items: {str(e)}")
        return _error_result(f"Error adding checklist items: {str(e)}")

@mcp.tool(name="update-checklist-item", annotations=TOOL_ANNOTATIONS["update-checklist-item"])
def update_checklist_item(
    todo_uuid: str,
    updated_items: str,
    ctx: Optional[Context] = None
) -> str:
    """
    Update/replace all checklist items for a todo.
    
    NOTE: This replaces the ENTIRE checklist. To mark individual items complete,
    include them in the updated list without modification (incomplete items),
    or prefix completed items with a checkbox marker.
    
    Things URL scheme limitation: Cannot update individual checklist items.
    Must send complete list. Use get-checklist-items first to see current state.
    
    Args:
        todo_uuid: UUID of the todo with the checklist
        updated_items: Complete new checklist (newline-separated)
        ctx: Context for progress reporting
    
    Example workflow:
        1. Get current items: get-checklist-items(uuid)
        2. Modify the list (add/remove/reorder)
        3. Send complete new list: update-checklist-item(uuid, new_list)
    """
    try:
        # Ensure Things app is running
        if not app_state.update_app_state():
            if not launch_things():
                return _error_result("Error: Unable to launch Things app")
        
        # Verify todo exists
        todo = things.get(todo_uuid)
        if not todo:
            return _error_result(f"Todo {todo_uuid} not found")
        
        # Handle list response from things.get()
        if isinstance(todo, list):
            if not todo:
                return _error_result(f"Todo {todo_uuid} not found")
            todo = todo[0]
        
        if todo.get('type') != 'to-do':
            return _error_result(f"Item {todo_uuid} is not a todo (type: {todo.get('type')})")
        
        # Build URL scheme
        import urllib.parse
        items_encoded = urllib.parse.quote(updated_items)
        url = f"things:///update?id={todo_uuid}&checklist-items={items_encoded}"
        
        logger.debug(f"Update checklist URL: {url}")
        success = execute_url(url)
        
        if not success:
            return _error_result("Error: Failed to update checklist")
        
        # Count items
        item_list = updated_items.split("\n")
        item_count = len([item for item in item_list if item.strip()])
        
        # Invalidate caches
        invalidate_caches_for(["get-todos"])
        
        return f"✓ Updated checklist for: {todo.get('title', 'todo')} ({item_count} items)"
        
    except Exception as e:
        logger.error(f"Error updating checklist: {str(e)}")
        return _error_result(f"Error updating checklist: {str(e)}")

@mcp.tool(name="get-todos-with-checklists", annotations=TOOL_ANNOTATIONS["get-todos-with-checklists"])
def get_todos_with_checklists(
    include_completed: bool = False,
    limit: Optional[int] = None
) -> str:
    """
    Find all todos that have checklists.
    
    Useful for reviewing todos with sub-tasks or finding incomplete checklists
    that need attention.
    
    Args:
        include_completed: Include completed todos (default: False)
        limit: Maximum number of results to return
    """
    try:
        # Get all todos with checklists
        status = None if include_completed else "incomplete"
        todos = things.todos(status=status)
        
        # Filter for todos with checklists
        todos_with_checklists = [t for t in todos if t.get('checklist')]
        
        if not todos_with_checklists:
            return "No todos with checklists found"
        
        # Apply limit
        if limit:
            todos_with_checklists = todos_with_checklists[:limit]
        
        # Format output
        lines = [
            f"Found {len(todos_with_checklists)} todo(s) with checklists:",
            ""
        ]
        
        for todo in todos_with_checklists:
            # Get checklist items to show progress
            checklist = things.checklist_items(todo['uuid'])
            total_items = len(checklist) if checklist else 0
            completed_items = sum(1 for item in checklist if item.get('status') == 'completed') if checklist else 0
            progress = f"{completed_items}/{total_items}"
            
            status_icon = "✓" if todo.get('status') == 'completed' else "○"
            lines.append(f"{status_icon} {todo.get('title', 'Untitled')} [{progress}]")
            lines.append(f"   UUID: {todo['uuid']}")
            
            # Show project/area if present
            if todo.get('project'):
                project = things.get(todo['project'])
                if project:
                    # Handle list response from things.get()
                    if isinstance(project, list):
                        project = project[0] if project else None
                    if project:
                        lines.append(f"   Project: {project.get('title', 'Unknown')}")
            if todo.get('area'):
                area = things.get(todo['area'])
                if area:
                    # Handle list response from things.get()
                    if isinstance(area, list):
                        area = area[0] if area else None
                    if area:
                        lines.append(f"   Area: {area.get('title', 'Unknown')}")
            
            lines.append("")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error getting todos with checklists: {str(e)}")
        return _error_result(f"Error getting todos with checklists: {str(e)}")


# ============================================================================
# HEADING MANAGEMENT TOOLS
# ============================================================================

@mcp.tool()
def add_heading(
    project_uuid: str,
    heading: str,
    after_uuid: Optional[str] = None
) -> str:
    """
    Add a heading to a project to organize todos into sections.
    
    Headings provide visual structure within projects and allow grouping
    related todos together. They appear as bold section titles in Things 3.
    
    Args:
        project_uuid: UUID of the project to add heading to
        heading: Title for the new heading (used for organization)
        after_uuid: Optional UUID of item to insert after (heading or todo).
                   If omitted, heading is added at end of project.
    
    Returns:
        Success confirmation with heading title and project context.
    
    Raises:
        ValueError: If project doesn't exist or after_uuid is invalid.
    
    Example:
        >>> add_heading("ABC123", "Phase 1 Tasks")
        ✓ Added heading "Phase 1 Tasks" to project: "Q1 Planning"
        
        >>> add_heading("ABC123", "Phase 2 Tasks", after_uuid="DEF456")
        ✓ Added heading "Phase 2 Tasks" after existing item in project: "Q1 Planning"
    """
    try:
        # Validate project exists
        project = things.get(project_uuid)
        if not project or (isinstance(project, dict) and project.get('type') != 'project'):
            return _error_result(f"Project {project_uuid} not found or is not a project")
        
        project_title = project.get('title', 'Unknown') if isinstance(project, dict) else 'Unknown'
        
        # Validate after_uuid if provided
        if after_uuid:
            after_item = things.get(after_uuid)
            if not after_item:
                return _error_result(f"After item {after_uuid} not found")
            
            # Verify after_item is in the same project
            if isinstance(after_item, dict):
                item_project_uuid = after_item.get('project')
                if item_project_uuid != project_uuid:
                    return _error_result(
                        f"After item {after_uuid} is not in project {project_uuid}"
                    )
        
        # Build Things URL scheme command
        import urllib.parse
        url_params = [
            'type=heading',
            f'heading={urllib.parse.quote(heading)}',
            f'list-id={project_uuid}'
        ]
        
        if after_uuid:
            url_params.append(f'after={after_uuid}')
        
        url = f"things:///add?{'&'.join(url_params)}"
        
        logger.debug(f"Add heading URL: {url}")
        success = execute_url(url)
        
        if not success:
            return _error_result("Failed to add heading to project")
        
        # Invalidate relevant caches
        invalidate_caches_for(["get-projects"])
        
        logger.info(f"Added heading '{heading}' to project {project_uuid}")
        
        if after_uuid:
            return f"✓ Added heading \"{heading}\" after existing item in project: \"{project_title}\""
        else:
            return f"✓ Added heading \"{heading}\" to project: \"{project_title}\""
    
    except Exception as e:
        logger.error(f"Failed to add heading: {e}")
        return _error_result(f"Failed to add heading: {str(e)}")


@mcp.tool()
def get_project_structure(
    project_uuid: str,
    show_completed: bool = False
) -> str:
    """
    Get the hierarchical structure of a project showing headings and grouped todos.
    
    This provides a visual overview of how a project is organized, with todos
    grouped under their respective headings. Useful for understanding project
    structure before moving items or planning additions.
    
    Args:
        project_uuid: UUID of the project to analyze
        show_completed: If True, include completed todos (default: False)
    
    Returns:
        Formatted hierarchical structure with headings and todos.
        Shows heading titles followed by indented todos under each heading.
        Includes metadata: total items, heading count, completion stats.
    
    Raises:
        ValueError: If project doesn't exist.
    
    Example:
        >>> get_project_structure("ABC123")
        
        Project Structure: "Q1 Planning"
        ========================================
        
        📌 Phase 1 Tasks
           ○ Define requirements
           ○ Create wireframes
        
        📌 Phase 2 Tasks
           ✓ Review mockups
           ○ Implement features
        
        (No heading)
           ○ Final review
        
        ────────────────────────────────────────
        Total: 5 items | 3 headings | 1/5 complete
    """
    try:
        # Get project with include_items=True for structure
        project_data = things.projects(uuid=project_uuid, include_items=True)
        
        if not project_data:
            return _error_result(f"Project {project_uuid} not found")
        
        # Handle both single dict and list of dicts
        project = project_data[0] if isinstance(project_data, list) else project_data
        project_title = project.get('title', 'Untitled Project')
        
        # Get all items in the project
        items = project.get('items', [])
        
        if not items:
            return f"Project \"{project_title}\" is empty (no headings or todos)"
        
        # Organize items by heading
        lines = [
            f"\nProject Structure: \"{project_title}\"",
            "=" * 40,
            ""
        ]
        
        current_heading = None
        heading_count = 0
        total_items = 0
        completed_count = 0
        
        for item in items:
            item_type = item.get('type')
            
            if item_type == 'heading':
                heading_count += 1
                current_heading = item.get('title', 'Untitled Heading')
                lines.append(f"\n📌 {current_heading}")
            
            elif item_type == 'to-do':
                status = item.get('status')
                
                # Skip completed todos if show_completed=False
                if status == 'completed' and not show_completed:
                    continue
                
                total_items += 1
                if status == 'completed':
                    completed_count += 1
                
                # Show heading context for first todo without a heading
                if current_heading is None and total_items == 1:
                    lines.append("\n(No heading)")
                
                # Format todo
                icon = "✓" if status == 'completed' else "○"
                title = item.get('title', 'Untitled')
                lines.append(f"   {icon} {title}")
        
        # Summary footer
        lines.extend([
            "",
            "─" * 40,
            f"Total: {total_items} items | {heading_count} headings | {completed_count}/{total_items} complete"
        ])
        
        logger.info(f"Retrieved structure for project {project_uuid}: {total_items} items, {heading_count} headings")
        return "\n".join(lines)
    
    except Exception as e:
        logger.error(f"Failed to get project structure: {e}")
        return _error_result(f"Failed to get project structure: {str(e)}")


@mcp.tool()
def move_todo_under_heading(
    todo_uuid: str,
    heading_uuid: str
) -> str:
    """
    Move a todo to appear under a specific heading within its project.
    
    This reorganizes project structure by placing todos under the appropriate
    heading sections. Both items must be in the same project.
    
    Args:
        todo_uuid: UUID of the todo to move
        heading_uuid: UUID of the heading to move todo under
    
    Returns:
        Success confirmation with todo and heading titles.
    
    Raises:
        ValueError: If todo or heading not found, not in same project,
                   or types are invalid.
    
    Example:
        >>> move_todo_under_heading("TODO123", "HEAD456")
        ✓ Moved "Implement API" under heading "Phase 2 Tasks"
    
    Notes:
        - Both todo and heading must exist in the same project
        - Todo will appear directly after the heading
        - Other todos under the heading are not affected
        - Use get-project-structure to see current organization
    """
    try:
        # Validate todo exists and is a todo
        todo = things.get(todo_uuid)
        if not todo:
            return _error_result(f"Todo {todo_uuid} not found")
        
        if isinstance(todo, dict) and todo.get('type') != 'to-do':
            return _error_result(f"Item {todo_uuid} is not a todo (type: {todo.get('type')})")
        
        # Validate heading exists and is a heading
        heading = things.get(heading_uuid)
        if not heading:
            return _error_result(f"Heading {heading_uuid} not found")
        
        if isinstance(heading, dict) and heading.get('type') != 'heading':
            return _error_result(f"Item {heading_uuid} is not a heading (type: {heading.get('type')})")
        
        # Verify both items are in the same project
        todo_project = todo.get('project') if isinstance(todo, dict) else None
        heading_project = heading.get('project') if isinstance(heading, dict) else None
        
        if todo_project != heading_project:
            return _error_result(
                f"Todo and heading must be in the same project. "
                f"Todo project: {todo_project}, Heading project: {heading_project}"
            )
        
        # Get titles for response
        todo_title = todo.get('title', 'Untitled') if isinstance(todo, dict) else 'Untitled'
        heading_title = heading.get('title', 'Untitled') if isinstance(heading, dict) else 'Untitled'
        
        # Move todo under heading using Things URL scheme
        # The heading parameter moves the todo directly under that heading
        url = f"things:///update?id={todo_uuid}&heading={heading_uuid}"
        
        logger.debug(f"Move todo under heading URL: {url}")
        success = execute_url(url)
        
        if not success:
            return _error_result("Failed to move todo under heading")
        
        # Invalidate relevant caches
        invalidate_caches_for(["get-projects"])
        
        logger.info(f"Moved todo {todo_uuid} under heading {heading_uuid}")
        return f"✓ Moved \"{todo_title}\" under heading \"{heading_title}\""
    
    except Exception as e:
        logger.error(f"Failed to move todo under heading: {e}")
        return _error_result(f"Failed to move todo under heading: {str(e)}")


@mcp.tool(name="move-item-to-project", annotations=TOOL_ANNOTATIONS["move-item-to-project"])
def move_item_to_project(
    item_uuid: str,
    project_uuid: str,
    heading_uuid: Optional[str] = None
) -> str:
    """
    Move a todo or project to a different project or area.
    
    This tool allows you to reorganize your Things database by moving items
    between projects. You can also move items directly under a specific heading
    within the target project.
    
    Args:
        item_uuid: UUID of the todo or project to move
        project_uuid: UUID of the destination project or area to move item to
        heading_uuid: Optional UUID of heading within destination project to place item under
    
    Returns:
        Success confirmation with item and destination titles.
    
    Raises:
        ValueError: If item or project not found, or invalid types.
    
    Example:
        >>> # Move todo to a project
        >>> move_item_to_project("TODO123", "PROJECT456")
        ✓ Moved "Buy groceries" to project "Personal Tasks"
        
        >>> # Move todo to a project under a specific heading
        >>> move_item_to_project("TODO123", "PROJECT456", "HEADING789")
        ✓ Moved "Buy groceries" to project "Personal Tasks" under heading "Shopping"
        
        >>> # Move a project to an area (projects can be nested in areas)
        >>> move_item_to_project("PROJECT123", "AREA456")
        ✓ Moved project "Q4 Planning" to area "Work"
    
    Notes:
        - Works for both todos and projects
        - Can move to projects or areas
        - Optionally place under a specific heading
        - Use get-todos, get-projects, get-areas to find UUIDs
        - Use get-project-structure to see available headings
    """
    try:
        # Validate item exists
        item = things.get(item_uuid)
        if not item:
            return _error_result(f"Item {item_uuid} not found")
        
        # Handle list response from things.get()
        if isinstance(item, list):
            if not item:
                return _error_result(f"Item {item_uuid} not found")
            item = item[0]
        
        item_type = item.get('type', 'unknown')
        item_title = item.get('title', 'Untitled')
        
        # Validate destination exists
        destination = things.get(project_uuid)
        if not destination:
            return _error_result(f"Destination {project_uuid} not found")
        
        # Handle list response from things.get()
        if isinstance(destination, list):
            if not destination:
                return _error_result(f"Destination {project_uuid} not found")
            destination = destination[0]
        
        destination_type = destination.get('type', 'unknown')
        destination_title = destination.get('title', 'Untitled')
        
        # Validate destination is a project or area
        if destination_type not in ['project', 'area']:
            return _error_result(
                f"Destination must be a project or area, not {destination_type}"
            )
        
        # If heading is specified, validate it
        heading_title = None
        if heading_uuid:
            heading = things.get(heading_uuid)
            if not heading:
                return _error_result(f"Heading {heading_uuid} not found")
            
            # Handle list response
            if isinstance(heading, list):
                if not heading:
                    return _error_result(f"Heading {heading_uuid} not found")
                heading = heading[0]
            
            if heading.get('type') != 'heading':
                return _error_result(
                    f"Item {heading_uuid} is not a heading (type: {heading.get('type')})"
                )
            
            heading_title = heading.get('title', 'Untitled')
            
            # Verify heading is in destination project
            heading_project = heading.get('project')
            if heading_project != project_uuid:
                return _error_result(
                    f"Heading must be in destination project. "
                    f"Heading project: {heading_project}, Destination: {project_uuid}"
                )
        
        # Build URL based on item type using proper URL scheme helpers
        # These helpers automatically add the authentication token
        if item_type == 'to-do':
            url = update_todo(
                id=item_uuid,
                list_id=project_uuid,
                heading=heading_uuid
            )
        elif item_type == 'project':
            if destination_type != 'area':
                return _error_result(
                    "Projects can only be moved to areas, not other projects"
                )
            url = update_project(
                id=item_uuid,
                area_id=project_uuid
            )
        else:
            return _error_result(f"Cannot move items of type {item_type}")
        
        logger.debug(f"Move item to project URL: {url}")
        success = execute_url(url)
        
        if not success:
            return _error_result("Failed to move item")
        
        # Invalidate relevant caches
        invalidate_caches_for(["get-todos", "get-projects", "get-inbox"])
        
        # Build response message
        if heading_title:
            result_msg = (
                f"✓ Moved \"{item_title}\" to {destination_type} \"{destination_title}\" "
                f"under heading \"{heading_title}\""
            )
        else:
            result_msg = (
                f"✓ Moved \"{item_title}\" to {destination_type} \"{destination_title}\""
            )
        
        logger.info(f"Moved {item_type} {item_uuid} to {destination_type} {project_uuid}")
        return result_msg
    
    except Exception as e:
        logger.error(f"Failed to move item to project: {e}")
        return _error_result(f"Failed to move item to project: {str(e)}")


# ============================================================================
# SEARCH TOOLS
# ============================================================================

@mcp.tool(name="search-todos", annotations=TOOL_ANNOTATIONS["search-todos"])
async def search_todos(
    query: str,
    offset: int = 0,
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    deadline_filter: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Search todos by title or notes with pagination and advanced filtering
    
    IMPORTANT: Use the 'limit' parameter to prevent overwhelming the context window when
    searching across large todo collections. Use 'offset' for pagination through results.
    
    For large result sets:
    1. Use count-search to get total count
    2. Fetch pages with offset/limit: offset=0,limit=20 then offset=20,limit=20, etc.

    Args:
        query: Search term to look for in todo titles and notes
        offset: Starting position for results (default 0, for pagination)
        limit: Maximum number of results to return (optional, recommended for large result sets)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
        type_filter: Filter by item type - 'to-do', 'project', 'heading', 'area' (optional)
        status_filter: Filter by status - 'incomplete', 'completed', 'canceled' (optional)
        deadline_filter: Filter by deadline - 'overdue', 'today', 'upcoming', 'none' (optional)
        ctx: Context object for progress reporting (internal use)
    
    Example:
        >>> search_todos("meeting", type_filter="to-do", status_filter="incomplete")
        Searches for incomplete todos containing "meeting"
        
        >>> search_todos("project", deadline_filter="overdue")
        Searches for items with overdue deadlines containing "project"
    """
    todos = things.search(query)

    if not todos:
        return f"No todos found matching '{query}'"

    # Apply filters
    if type_filter:
        todos = _apply_type_filter(todos, type_filter)
    if status_filter:
        todos = _apply_status_filter(todos, status_filter)
    if deadline_filter:
        todos = _apply_deadline_filter(todos, deadline_filter)
    
    # Check if filters removed all results
    if not todos:
        filter_desc = []
        if type_filter:
            filter_desc.append(f"type={type_filter}")
        if status_filter:
            filter_desc.append(f"status={status_filter}")
        if deadline_filter:
            filter_desc.append(f"deadline={deadline_filter}")
        return f"No items found matching '{query}' with filters: {', '.join(filter_desc)}"

    # Store total count before pagination
    total_count = len(todos)
    
    # Warn if returning large result set without limit
    if ctx and not limit and total_count > 20:
        await ctx.warning(
            f"Search returned {total_count} items without a limit. "
            "Consider using the 'limit' parameter to reduce context window usage."
        )

    # Apply sorting first
    if sort_by:
        sort_configs = {
            'title': (lambda x: getattr(x, 'title', '').lower(), False),
            'created': (lambda x: getattr(x, 'created', ''), True),
            'modified': (lambda x: getattr(x, 'modified', ''), True),
            'deadline': (lambda x: getattr(x, 'deadline', '') or '', True),
            'start_date': (lambda x: getattr(x, 'start_date', '') or '', True),
        }
        if sort_by in sort_configs:
            key_fn, reverse = sort_configs[sort_by]
            todos.sort(key=key_fn, reverse=reverse)
    
    # Apply offset and limit for pagination
    start_idx = offset
    end_idx = offset + limit if limit else total_count
    todos = todos[start_idx:end_idx]

    formatted_todos = [format_todo(todo) for todo in todos]
    result = "\n\n---\n\n".join(formatted_todos)
    
    # Add pagination metadata
    showing_from = start_idx + 1
    showing_to = start_idx + len(todos)
    metadata = f"Showing items {showing_from}-{showing_to} of {total_count} total"
    if sort_by:
        metadata += f" (sorted by {sort_by})"
    
    return f"{metadata}\n\n{result}"

@mcp.tool(name="search-advanced", annotations=TOOL_ANNOTATIONS["search-advanced"])
async def search_advanced(
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    deadline: Optional[str] = None,
    tag: Optional[str] = None,
    area: Optional[str] = None,
    type: Optional[str] = None,
    offset: int = 0,
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Advanced todo search with multiple filters and pagination support
    
    IMPORTANT: Use the 'limit' parameter to prevent overwhelming the context window when
    searching across large todo collections. Use 'offset' for pagination through results.
    
    For large result sets:
    1. Use count-advanced with same filters to get total count
    2. Fetch pages with offset/limit: offset=0,limit=20 then offset=20,limit=20, etc.

    Args:
        status: Filter by todo status (incomplete/completed/canceled)
        start_date: Filter by start date (YYYY-MM-DD)
        deadline: Filter by deadline (YYYY-MM-DD)
        tag: Filter by tag
        area: Filter by area UUID
        type: Filter by item type (to-do/project/heading)
        offset: Starting position for results (default 0, for pagination)
        limit: Maximum number of results to return (optional, recommended for large result sets)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
        ctx: Context object for progress reporting (internal use)
    """
    # Build filter parameters
    kwargs = {}

    # Add filters that are provided
    if status:
        kwargs['status'] = status
    if deadline:
        kwargs['deadline'] = deadline
    if start_date:
        kwargs['start'] = start_date
    if tag:
        kwargs['tag'] = tag
    if area:
        kwargs['area'] = area
    if type:
        kwargs['type'] = type

    # Execute search with applicable filters
    try:
        todos = things.todos(**kwargs)

        if not todos:
            return "No items found matching your search criteria"

        # Store total count before pagination
        total_count = len(todos)
        
        # Warn if returning large result set without limit
        if ctx and not limit and total_count > 20:
            await ctx.warning(
                f"Advanced search returned {total_count} items without a limit. "
                "Consider using the 'limit' parameter to reduce context window usage."
            )

        # Apply sorting first
        if sort_by:
            sort_configs = {
                'title': (lambda x: getattr(x, 'title', '').lower(), False),
                'created': (lambda x: getattr(x, 'created', ''), True),
                'modified': (lambda x: getattr(x, 'modified', ''), True),
                'deadline': (lambda x: getattr(x, 'deadline', '') or '', True),
                'start_date': (lambda x: getattr(x, 'start_date', '') or '', True),
            }
            if sort_by in sort_configs:
                key_fn, reverse = sort_configs[sort_by]
                todos.sort(key=key_fn, reverse=reverse)
        
        # Apply offset and limit for pagination
        start_idx = offset
        end_idx = offset + limit if limit else total_count
        todos = todos[start_idx:end_idx]

        formatted_todos = [format_todo(todo) for todo in todos]
        result = "\n\n---\n\n".join(formatted_todos)
        
        # Add pagination metadata
        showing_from = start_idx + 1
        showing_to = start_idx + len(todos)
        metadata = f"Showing items {showing_from}-{showing_to} of {total_count} total"
        if sort_by:
            metadata += f" (sorted by {sort_by})"
        
        return f"{metadata}\n\n{result}"
    except Exception as e:
        return _error_result(f"Error in advanced search: {str(e)}")

# MODIFICATION OPERATIONS

@mcp.tool(name="add-todo", annotations=TOOL_ANNOTATIONS["add-todo"])
def add_task(
    title: str,
    notes: Optional[str] = None,
    when: Optional[str] = None,
    deadline: Optional[str] = None,
    tags: Optional[Union[List[str], str]] = None,
    checklist_items: Optional[Union[List[str], str]] = None,
    list_id: Optional[str] = None,
    list_title: Optional[str] = None,
    heading: Optional[str] = None
) -> str:
    """
    Create a new todo in Things.

    Args:
        title: Title of the todo
        notes: Notes for the todo
        when: When to schedule the todo (today, tomorrow, evening, anytime, someday, or YYYY-MM-DD)
        deadline: Deadline for the todo (YYYY-MM-DD)
        tags: Tags to apply to the todo. Missing tags will be created automatically.
        checklist_items: Checklist items to add
        list_id: ID of project/area to add to
        list_title: Title of project/area to add to
        heading: Heading to add under
    """
    try:
        # Ensure Things app is running
        if not app_state.update_app_state():
            if not launch_things():
                return _error_result("Error: Unable to launch Things app")

        # Handle tags and checklist_items - some MCP clients send them as JSON strings
        if tags and isinstance(tags, str):
            import json
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                # If it's not valid JSON, treat it as a comma-separated string
                tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        if checklist_items and isinstance(checklist_items, str):
            import json
            try:
                checklist_items = json.loads(checklist_items)
            except json.JSONDecodeError:
                # If it's not valid JSON, treat it as newline-separated string
                checklist_items = [item.strip() for item in checklist_items.split("\n") if item.strip()]

        # Ensure tags exist before using them (tags should be List[str] now after conversion)
        if tags and isinstance(tags, list):
            ensure_tags_exist(tags)

        # Build the add_todo URL command and execute it
        url = add_todo(
            title=title,
            notes=notes,
            when=when,
            deadline=deadline,
            tags=tags if isinstance(tags, list) else None,
            checklist_items=checklist_items if isinstance(checklist_items, list) else None,
            list_id=list_id,
            list_title=list_title,
            heading=heading
        )

        # Log the generated URL before executing
        logger.debug(f"Add todo URL: {url}")

        success = execute_url(url)

        if not success:
            return _error_result("Error: Failed to create todo")

        # Invalidate relevant caches after creating a todo
        invalidate_caches_for(["get-inbox", "get-today", "get-upcoming", "get-todos"])

        return f"Successfully created todo: {title}"
    except Exception as e:
        logger.error(f"Error creating todo: {str(e)}")
        return _error_result(f"Error creating todo: {str(e)}")

@mcp.tool(name="add-todo-interactive", annotations=ADD_ANNOTATIONS)
async def add_todo_interactive(ctx: Context) -> str:
    """
    Create a new todo interactively with step-by-step guidance
    
    This tool uses interactive elicitation to guide you through creating a todo,
    asking for each piece of information step by step. This is especially useful
    when you want guidance on what information to provide.
    
    The tool will ask for:
    1. Title (required)
    2. Notes (optional)
    3. When to schedule (optional: today, tomorrow, evening, anytime, someday, or YYYY-MM-DD)
    4. Deadline (optional: YYYY-MM-DD)
    5. Tags (optional: comma-separated list)
    """
    try:
        # Ensure Things app is running
        if not app_state.update_app_state():
            if not launch_things():
                return _error_result("Error: Unable to launch Things app")
        
        await ctx.info("Let's create a new todo. I'll guide you through the process.")
        
        # Step 1: Get title (required)
        title_result = await ctx.elicit(
            "What's the title of your todo?",
            response_type=str
        )
        if title_result.action != "accept" or not title_result.data:
            return "Todo creation cancelled"
        title = title_result.data
        
        # Step 2: Get notes (optional)
        notes_result = await ctx.elicit(
            "Any notes? (Press Enter to skip)",
            response_type=str
        )
        notes = notes_result.data if notes_result.action == "accept" and notes_result.data else None
        
        # Step 3: Get when (optional)
        when_result = await ctx.elicit(
            "When should this be done? (today, tomorrow, evening, anytime, someday, YYYY-MM-DD, or press Enter to skip)",
            response_type=str
        )
        when = when_result.data if when_result.action == "accept" and when_result.data else None
        
        # Step 4: Get deadline (optional)
        deadline_result = await ctx.elicit(
            "Deadline? (YYYY-MM-DD format, or press Enter to skip)",
            response_type=str
        )
        deadline = deadline_result.data if deadline_result.action == "accept" and deadline_result.data else None
        
        # Step 5: Get tags (optional)
        tags_result = await ctx.elicit(
            "Tags? (comma-separated, or press Enter to skip)",
            response_type=str
        )
        tags = None
        if tags_result.action == "accept" and tags_result.data:
            tags = [tag.strip() for tag in tags_result.data.split(",")]
            ensure_tags_exist(tags)
        
        await ctx.info(f"Creating todo: {title}")
        
        # Build the add_todo URL command and execute it
        url = add_todo(
            title=title,
            notes=notes,
            when=when,
            deadline=deadline,
            tags=tags,
            checklist_items=None,
            list_id=None,
            list_title=None,
            heading=None
        )
        
        logger.debug(f"Add todo URL: {url}")
        success = execute_url(url)
        
        if not success:
            return _error_result("Error: Failed to create todo")
        
        # Invalidate relevant caches
        invalidate_caches_for(["get-inbox", "get-today", "get-upcoming", "get-todos"])
        
        summary = f"✓ Successfully created todo: {title}"
        if when:
            summary += f"\n  Scheduled: {when}"
        if deadline:
            summary += f"\n  Deadline: {deadline}"
        if tags:
            summary += f"\n  Tags: {', '.join(tags)}"
        
        return summary
        
    except Exception as e:
        logger.error(f"Error in interactive todo creation: {str(e)}")
        return _error_result(f"Error creating todo: {str(e)}")

@mcp.tool(name="bulk-complete-todos", annotations=TOOL_ANNOTATIONS["bulk-complete-todos"])
async def bulk_complete_todos(ctx: Context) -> str:
    """
    Complete multiple todos at once with interactive preview and confirmation
    
    This tool provides a safe way to batch-complete todos by:
    1. Asking what criteria to filter by (tag, project, area, or all inbox items)
    2. Showing a preview of matching incomplete todos
    3. Confirming before making changes
    4. Providing progress updates during execution
    
    This is useful for:
    - Completing all todos with a specific tag (e.g., "quick-wins")
    - Marking an entire project complete
    - Clearing out inbox items
    - Bulk operations with safety guardrails
    """
    try:
        # Ensure Things app is running
        if not app_state.update_app_state():
            if not launch_things():
                return _error_result("Error: Unable to launch Things app")
        
        await ctx.info("Let's complete some todos. I'll help you select which ones.")
        
        # Step 1: Ask for filter criteria
        filter_result = await ctx.elicit(
            "What should I filter by?\n"
            "Options:\n"
            "- 'tag:NAME' - All todos with specific tag\n"
            "- 'project:UUID' - All todos in specific project\n"
            "- 'area:UUID' - All todos in specific area\n"
            "- 'inbox' - All inbox items\n"
            "- 'today' - All today items\n"
            "- 'upcoming' - All upcoming items",
            response_type=str
        )
        
        if filter_result.action != "accept" or not filter_result.data:
            return "Operation cancelled"
        
        filter_input = filter_result.data.strip().lower()
        
        # Step 2: Fetch matching todos based on filter
        todos = []
        filter_description = ""
        
        if filter_input.startswith("tag:"):
            tag_name = filter_input[4:].strip()
            all_items = things.search(query="", tag=tag_name)
            todos = [item for item in all_items if item.get('type') == 'to-do' and item.get('status') == 'incomplete']
            filter_description = f"tag '{tag_name}'"
        
        elif filter_input.startswith("project:"):
            project_id = filter_input[8:].strip()
            project = things.get(project_id)
            if not project or not isinstance(project, dict):
                return _error_result(f"Project not found: {project_id}")
            todos = [item for item in project.get('items', []) if item.get('type') == 'to-do' and item.get('status') == 'incomplete']
            filter_description = f"project '{project.get('title', project_id)}'"
        
        elif filter_input.startswith("area:"):
            area_id = filter_input[5:].strip()
            area = things.get(area_id)
            if not area or not isinstance(area, dict):
                return _error_result(f"Area not found: {area_id}")
            todos = [item for item in area.get('items', []) if item.get('type') == 'to-do' and item.get('status') == 'incomplete']
            filter_description = f"area '{area.get('title', area_id)}'"
        
        elif filter_input == "inbox":
            all_inbox = things.inbox()
            todos = [item for item in all_inbox if item.get('type') == 'to-do' and item.get('status') == 'incomplete']
            filter_description = "inbox"
        
        elif filter_input == "today":
            all_today = things.today()
            todos = [item for item in all_today if item.get('type') == 'to-do' and item.get('status') == 'incomplete']
            filter_description = "today"
        
        elif filter_input == "upcoming":
            all_upcoming = things.upcoming()
            todos = [item for item in all_upcoming if item.get('type') == 'to-do' and item.get('status') == 'incomplete']
            filter_description = "upcoming"
        
        else:
            return _error_result(f"Invalid filter: {filter_input}. Use format like 'tag:work' or 'inbox'")
        
        # Step 3: Show preview
        if not todos:
            return f"No incomplete todos found in {filter_description}"
        
        # Limit batch size to 100 items
        if len(todos) > 100:
            await ctx.warning(f"Found {len(todos)} todos, but bulk operations are limited to 100 items at a time for safety.")
            todos = todos[:100]
        
        # Show preview of first 10 items
        preview_titles = [f"- {todo.get('title', 'Untitled')}" for todo in todos[:10]]
        preview_text = "\n".join(preview_titles)
        if len(todos) > 10:
            preview_text += f"\n... and {len(todos) - 10} more"
        
        await ctx.info(f"Found {len(todos)} incomplete todos in {filter_description}:\n{preview_text}")
        
        # Step 4: Confirm
        confirm_result = await ctx.elicit(
            f"Complete all {len(todos)} todos? Type 'yes' to confirm",
            response_type=str
        )
        
        if confirm_result.action != "accept" or confirm_result.data.lower() != "yes":
            return "Operation cancelled - no todos were modified"
        
        # Step 5: Execute bulk completion with progress updates
        await ctx.info(f"Completing {len(todos)} todos...")
        
        completed_count = 0
        failed_count = 0
        
        for i, todo in enumerate(todos):
            try:
                # Report progress every 10 items
                if i > 0 and i % 10 == 0:
                    await ctx.report_progress(i, len(todos))
                
                # Build URL to mark as complete
                todo_id = todo.get('uuid')
                if not todo_id:
                    failed_count += 1
                    continue
                
                url = update_todo(id=todo_id, completed=True)
                success = execute_url(url)
                
                if success:
                    completed_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Error completing todo {todo.get('uuid')}: {str(e)}")
                failed_count += 1
        
        # Invalidate relevant caches
        invalidate_caches_for(["get-inbox", "get-today", "get-upcoming", "get-todos", "get-logbook"])
        
        # Final report
        result = "✓ Bulk completion complete!\n"
        result += f"  Successfully completed: {completed_count} todos\n"
        if failed_count > 0:
            result += f"  Failed: {failed_count} todos\n"
        result += f"  Filter: {filter_description}"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in bulk complete: {str(e)}")
        return _error_result(f"Error completing todos: {str(e)}")

@mcp.tool(name="bulk-schedule-todos", annotations=TOOL_ANNOTATIONS["bulk-schedule-todos"])
async def bulk_schedule_todos(ctx: Context) -> str:
    """
    Schedule multiple todos at once using filters (interactive)
    
    This is an interactive bulk operation that:
    1. Asks for filter criteria (tag, project, area, or list)
    2. Fetches matching incomplete todos
    3. Shows preview of items to be scheduled
    4. Asks for schedule destination
    5. Requires explicit confirmation ("yes")
    6. Executes batch scheduling with progress updates
    
    Safety features:
    - Preview before execution (first 10 items shown)
    - Explicit confirmation required
    - 100-item batch limit
    - Progress reporting every 10 items
    - Continues on individual failures
    
    Returns:
        Summary of scheduled todos with success/failure counts
    """
    try:
        # Step 1: Elicit filter criteria
        filter_input = await ctx.elicit(
            "Enter filter criteria for todos to schedule:\n"
            "  - tag:NAME (e.g., tag:work)\n"
            "  - project:UUID (e.g., project:ABC123)\n"
            "  - area:UUID (e.g., area:XYZ789)\n"
            "  - inbox, today, upcoming\n"
            "Filter: ",
            response_type=str
        )
        
        if filter_input.action != "accept" or not filter_input.data:
            return "Operation cancelled"
        
        filter_input = filter_input.data.strip().lower()
        if not filter_input:
            return _error_result("No filter provided. Operation cancelled.")
        
        # Step 2: Fetch matching incomplete todos
        await ctx.info(f"Fetching todos matching filter: {filter_input}...")
        
        todos = []
        filter_description = filter_input
        
        if filter_input.startswith("tag:"):
            tag_name = filter_input[4:].strip()
            all_todos = things.todos()
            todos = [t for t in all_todos if t.get('status') == 'incomplete' 
                    and tag_name in [tag.get('title', '').lower() for tag in t.get('tags', [])]]
            filter_description = f"tag '{tag_name}'"
        elif filter_input.startswith("project:"):
            project_uuid = filter_input[8:].strip()
            project = things.get(project_uuid)
            if not project or not isinstance(project, dict):
                return _error_result(f"Project not found: {project_uuid}")
            todos = things.todos(project=project_uuid)
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = f"project '{project.get('title', project_uuid)}'"
        elif filter_input.startswith("area:"):
            area_uuid = filter_input[5:].strip()
            area = things.get(area_uuid)
            if not area or not isinstance(area, dict):
                return _error_result(f"Area not found: {area_uuid}")
            todos = things.todos(area=area_uuid)
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = f"area '{area.get('title', area_uuid)}'"
        elif filter_input == "inbox":
            todos = things.inbox()
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = "Inbox"
        elif filter_input == "today":
            todos = things.today()
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = "Today"
        elif filter_input == "upcoming":
            todos = things.upcoming()
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = "Upcoming"
        else:
            return _error_result(f"Invalid filter: {filter_input}. Use tag:NAME, project:UUID, area:UUID, inbox, today, or upcoming")
        
        if not todos:
            return f"No incomplete todos found matching filter: {filter_description}"
        
        # Step 3: Show preview
        total_count = len(todos)
        preview_todos = todos[:10]
        
        preview = f"Found {total_count} incomplete todo(s) matching '{filter_description}':\n\n"
        for i, todo in enumerate(preview_todos, 1):
            title = todo.get('title', 'Untitled')
            tags = [tag.get('title', '') for tag in todo.get('tags', [])]
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            preview += f"  {i}. {title}{tag_str}\n"
        
        if total_count > 10:
            preview += f"\n  ... and {total_count - 10} more\n"
        
        # Check batch limit
        if total_count > 100:
            await ctx.warning(f"⚠️ Found {total_count} items, but batch limit is 100. Only first 100 will be scheduled.")
            todos = todos[:100]
            total_count = 100
        
        await ctx.info(preview)
        
        # Step 4: Elicit schedule destination
        schedule_input = await ctx.elicit(
            "\nWhere should these todos be scheduled?\n"
            "  - today (Today list)\n"
            "  - tomorrow (Tomorrow's date)\n"
            "  - evening (This Evening)\n"
            "  - anytime (Anytime list)\n"
            "  - someday (Someday list)\n"
            "  - YYYY-MM-DD (specific date, e.g., 2025-11-15)\n"
            "Schedule to: ",
            response_type=str
        )
        
        if schedule_input.action != "accept" or not schedule_input.data:
            return "Operation cancelled"
        
        schedule_input = schedule_input.data.strip().lower()
        if not schedule_input:
            return _error_result("No schedule destination provided. Operation cancelled.")
        
        # Validate and parse schedule destination
        schedule_param = None
        schedule_description = schedule_input
        
        if schedule_input == "today":
            schedule_param = "today"
            schedule_description = "Today"
        elif schedule_input == "tomorrow":
            schedule_param = "tomorrow"
            schedule_description = "Tomorrow"
        elif schedule_input == "evening":
            schedule_param = "evening"
            schedule_description = "This Evening"
        elif schedule_input == "anytime":
            schedule_param = "anytime"
            schedule_description = "Anytime"
        elif schedule_input == "someday":
            schedule_param = "someday"
            schedule_description = "Someday"
        else:
            # Try to parse as date (YYYY-MM-DD)
            from datetime import datetime
            try:
                parsed_date = datetime.strptime(schedule_input, "%Y-%m-%d").date()
                schedule_param = schedule_input
                schedule_description = parsed_date.strftime("%B %d, %Y")
            except ValueError:
                return _error_result(f"Invalid schedule destination: {schedule_input}. Use today, tomorrow, evening, anytime, someday, or YYYY-MM-DD")
        
        # Step 5: Confirmation
        confirmation = await ctx.elicit(
            f"\n⚠️ About to schedule {total_count} todo(s) to '{schedule_description}'.\n"
            f"   Filter: {filter_description}\n"
            f"   Type 'yes' to confirm: ",
            response_type=str
        )
        
        if confirmation.action != "accept" or confirmation.data.strip().lower() != "yes":
            return "Operation cancelled by user."
        
        # Step 6: Execute batch scheduling
        await ctx.info(f"Scheduling {total_count} todos to '{schedule_description}'...")
        
        scheduled_count = 0
        failed_count = 0
        
        for i, todo in enumerate(todos, 1):
            try:
                todo_uuid = todo.get('uuid')
                if not todo_uuid:
                    failed_count += 1
                    continue
                
                # Build URL scheme command
                url = f"things:///update?id={todo_uuid}&when={schedule_param}"
                execute_url(url)
                scheduled_count += 1
                
                # Progress update every 10 items
                if i % 10 == 0:
                    await ctx.report_progress(i, total_count)
                    
            except Exception as e:
                logger.error(f"Failed to schedule todo {todo.get('uuid')}: {str(e)}")
                failed_count += 1
                continue
        
        # Invalidate caches for affected lists
        cache_keys = ["get-inbox", "get-today", "get-upcoming", "get-anytime", "get-someday", "get-todos"]
        invalidate_caches_for(cache_keys)
        
        # Final report
        result = "✓ Bulk scheduling complete!\n"
        result += f"  Successfully scheduled: {scheduled_count} todos\n"
        if failed_count > 0:
            result += f"  Failed: {failed_count} todos\n"
        result += f"  Destination: {schedule_description}\n"
        result += f"  Filter: {filter_description}"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in bulk schedule: {str(e)}")
        return _error_result(f"Error scheduling todos: {str(e)}")

@mcp.tool(name="bulk-tag-todos", annotations=TOOL_ANNOTATIONS["bulk-tag-todos"])
async def bulk_tag_todos(ctx: Context) -> str:
    """
    Add or remove tags from multiple todos at once (interactive)
    
    This is an interactive bulk operation that:
    1. Asks for filter criteria (tag, project, area, or list)
    2. Fetches matching incomplete todos
    3. Shows preview of items to be tagged
    4. Asks for tag operation (add or remove)
    5. Asks for tag names (comma-separated)
    6. Requires explicit confirmation ("yes")
    7. Executes batch tagging with progress updates
    
    Safety features:
    - Preview before execution (first 10 items shown)
    - Explicit confirmation required
    - 100-item batch limit
    - Progress reporting every 10 items
    - Continues on individual failures
    
    Returns:
        Summary of tagged todos with success/failure counts
    """
    try:
        # Step 1: Elicit filter criteria
        filter_input = await ctx.elicit(
            "Enter filter criteria for todos to tag:\n"
            "  - tag:NAME (e.g., tag:work)\n"
            "  - project:UUID (e.g., project:ABC123)\n"
            "  - area:UUID (e.g., area:XYZ789)\n"
            "  - inbox, today, upcoming\n"
            "Filter: ",
            response_type=str
        )
        
        if filter_input.action != "accept" or not filter_input.data:
            return "Operation cancelled"
        
        filter_input = filter_input.data.strip().lower()
        if not filter_input:
            return _error_result("No filter provided. Operation cancelled.")
        
        # Step 2: Fetch matching incomplete todos
        await ctx.info(f"Fetching todos matching filter: {filter_input}...")
        
        todos = []
        filter_description = filter_input
        
        if filter_input.startswith("tag:"):
            tag_name = filter_input[4:].strip()
            all_todos = things.todos()
            todos = [t for t in all_todos if t.get('status') == 'incomplete' 
                    and tag_name in [tag.get('title', '').lower() for tag in t.get('tags', [])]]
            filter_description = f"tag '{tag_name}'"
        elif filter_input.startswith("project:"):
            project_uuid = filter_input[8:].strip()
            project = things.get(project_uuid)
            if not project or not isinstance(project, dict):
                return _error_result(f"Project not found: {project_uuid}")
            todos = things.todos(project=project_uuid)
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = f"project '{project.get('title', project_uuid)}'"
        elif filter_input.startswith("area:"):
            area_uuid = filter_input[5:].strip()
            area = things.get(area_uuid)
            if not area or not isinstance(area, dict):
                return _error_result(f"Area not found: {area_uuid}")
            todos = things.todos(area=area_uuid)
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = f"area '{area.get('title', area_uuid)}'"
        elif filter_input == "inbox":
            todos = things.inbox()
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = "Inbox"
        elif filter_input == "today":
            todos = things.today()
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = "Today"
        elif filter_input == "upcoming":
            todos = things.upcoming()
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = "Upcoming"
        else:
            return _error_result(f"Invalid filter: {filter_input}. Use tag:NAME, project:UUID, area:UUID, inbox, today, or upcoming")
        
        if not todos:
            return f"No incomplete todos found matching filter: {filter_description}"
        
        # Step 3: Show preview
        total_count = len(todos)
        preview_todos = todos[:10]
        
        preview = f"Found {total_count} incomplete todo(s) matching '{filter_description}':\n\n"
        for i, todo in enumerate(preview_todos, 1):
            title = todo.get('title', 'Untitled')
            current_tags = [tag.get('title', '') for tag in todo.get('tags', [])]
            tag_str = f" [Current tags: {', '.join(current_tags)}]" if current_tags else " [No tags]"
            preview += f"  {i}. {title}{tag_str}\n"
        
        if total_count > 10:
            preview += f"\n  ... and {total_count - 10} more\n"
        
        # Check batch limit
        if total_count > 100:
            await ctx.warning(f"⚠️ Found {total_count} items, but batch limit is 100. Only first 100 will be processed.")
            todos = todos[:100]
            total_count = 100
        
        await ctx.info(preview)
        
        # Step 4: Elicit tag operation
        operation_input = await ctx.elicit(
            "\nWhat tag operation should be performed?\n"
            "  - add (add tags to todos)\n"
            "  - remove (remove tags from todos)\n"
            "Operation: ",
            response_type=str
        )
        
        if operation_input.action != "accept" or not operation_input.data:
            return "Operation cancelled"
        
        operation = operation_input.data.strip().lower()
        if operation not in ["add", "remove"]:
            return _error_result(f"Invalid operation: {operation}. Use 'add' or 'remove'")
        
        # Step 5: Elicit tag names
        tags_input = await ctx.elicit(
            f"\nEnter tag names to {operation} (comma-separated, e.g., 'work, urgent'):\n"
            "Tags: ",
            response_type=str
        )
        
        if tags_input.action != "accept" or not tags_input.data:
            return "Operation cancelled"
        
        tag_names = [tag.strip() for tag in tags_input.data.split(",") if tag.strip()]
        if not tag_names:
            return _error_result("No tags provided. Operation cancelled.")
        
        # Ensure tags exist
        ensure_tags_exist(tag_names)
        
        # Step 6: Confirmation
        tag_list = ", ".join(tag_names)
        confirmation = await ctx.elicit(
            f"\n⚠️ About to {operation} tags '{tag_list}' for {total_count} todo(s).\n"
            f"   Filter: {filter_description}\n"
            f"   Type 'yes' to confirm: ",
            response_type=str
        )
        
        if confirmation.action != "accept" or confirmation.data.strip().lower() != "yes":
            return "Operation cancelled by user."
        
        # Step 7: Execute batch tagging
        await ctx.info(f"Processing {total_count} todos...")
        
        tagged_count = 0
        failed_count = 0
        
        for i, todo in enumerate(todos, 1):
            try:
                todo_uuid = todo.get('uuid')
                if not todo_uuid:
                    failed_count += 1
                    continue
                
                if operation == "add":
                    # Use add-tags parameter to add without removing existing tags
                    tag_param = ",".join(tag_names)
                    url = f"things:///update?id={todo_uuid}&add-tags={tag_param}"
                    execute_url(url)
                else:
                    # For remove: get current tags, remove specified ones, then set
                    current_tags = [tag.get('title', '') for tag in todo.get('tags', [])]
                    remaining_tags = [t for t in current_tags if t not in tag_names]
                    
                    if len(remaining_tags) != len(current_tags):
                        # Only update if tags were actually removed
                        tag_param = ",".join(remaining_tags) if remaining_tags else ""
                        url = f"things:///update?id={todo_uuid}&tags={tag_param}"
                        execute_url(url)
                
                tagged_count += 1
                
                # Progress update every 10 items
                if i % 10 == 0:
                    await ctx.report_progress(i, total_count)
                    
            except Exception as e:
                logger.error(f"Failed to tag todo {todo.get('uuid')}: {str(e)}")
                failed_count += 1
                continue
        
        # Invalidate caches
        cache_keys = ["get-todos", "get-inbox", "get-today", "get-upcoming", "get-tagged-items"]
        invalidate_caches_for(cache_keys)
        
        # Final report
        result = "✓ Bulk tagging complete!\n"
        result += f"  Successfully processed: {tagged_count} todos\n"
        if failed_count > 0:
            result += f"  Failed: {failed_count} todos\n"
        result += f"  Operation: {operation} tags '{tag_list}'\n"
        result += f"  Filter: {filter_description}"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in bulk tag: {str(e)}")
        return _error_result(f"Error tagging todos: {str(e)}")

@mcp.tool(name="bulk-move-todos", annotations=TOOL_ANNOTATIONS["bulk-move-todos"])
async def bulk_move_todos(ctx: Context) -> str:
    """
    Move multiple todos to a different project or area (interactive)
    
    This is an interactive bulk operation that:
    1. Asks for filter criteria (tag, project, area, or list)
    2. Fetches matching incomplete todos
    3. Shows preview of items to be moved
    4. Asks for destination (project, area, or inbox)
    5. Requires explicit confirmation ("yes")
    6. Executes batch move with progress updates
    
    Safety features:
    - Preview before execution (first 10 items shown)
    - Explicit confirmation required
    - 100-item batch limit
    - Progress reporting every 10 items
    - Continues on individual failures
    
    Returns:
        Summary of moved todos with success/failure counts
    """
    try:
        # Step 1: Elicit filter criteria
        filter_input = await ctx.elicit(
            "Enter filter criteria for todos to move:\n"
            "  - tag:NAME (e.g., tag:work)\n"
            "  - project:UUID (e.g., project:ABC123)\n"
            "  - area:UUID (e.g., area:XYZ789)\n"
            "  - inbox, today, upcoming\n"
            "Filter: ",
            response_type=str
        )
        
        if filter_input.action != "accept" or not filter_input.data:
            return "Operation cancelled"
        
        filter_input = filter_input.data.strip().lower()
        if not filter_input:
            return _error_result("No filter provided. Operation cancelled.")
        
        # Step 2: Fetch matching incomplete todos
        await ctx.info(f"Fetching todos matching filter: {filter_input}...")
        
        todos = []
        filter_description = filter_input
        
        if filter_input.startswith("tag:"):
            tag_name = filter_input[4:].strip()
            all_todos = things.todos()
            todos = [t for t in all_todos if t.get('status') == 'incomplete' 
                    and tag_name in [tag.get('title', '').lower() for tag in t.get('tags', [])]]
            filter_description = f"tag '{tag_name}'"
        elif filter_input.startswith("project:"):
            project_uuid = filter_input[8:].strip()
            project = things.get(project_uuid)
            if not project or not isinstance(project, dict):
                return _error_result(f"Project not found: {project_uuid}")
            todos = things.todos(project=project_uuid)
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = f"project '{project.get('title', project_uuid)}'"
        elif filter_input.startswith("area:"):
            area_uuid = filter_input[5:].strip()
            area = things.get(area_uuid)
            if not area or not isinstance(area, dict):
                return _error_result(f"Area not found: {area_uuid}")
            todos = things.todos(area=area_uuid)
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = f"area '{area.get('title', area_uuid)}'"
        elif filter_input == "inbox":
            todos = things.inbox()
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = "Inbox"
        elif filter_input == "today":
            todos = things.today()
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = "Today"
        elif filter_input == "upcoming":
            todos = things.upcoming()
            todos = [t for t in todos if t.get('status') == 'incomplete']
            filter_description = "Upcoming"
        else:
            return _error_result(f"Invalid filter: {filter_input}. Use tag:NAME, project:UUID, area:UUID, inbox, today, or upcoming")
        
        if not todos:
            return f"No incomplete todos found matching filter: {filter_description}"
        
        # Step 3: Show preview
        total_count = len(todos)
        preview_todos = todos[:10]
        
        preview = f"Found {total_count} incomplete todo(s) matching '{filter_description}':\n\n"
        for i, todo in enumerate(preview_todos, 1):
            title = todo.get('title', 'Untitled')
            current_project = todo.get('project', {}).get('title', 'No project')
            current_area = todo.get('area', {}).get('title', 'No area')
            location = f" [Currently in: {current_project}"
            if current_area != 'No area':
                location += f", Area: {current_area}"
            location += "]"
            preview += f"  {i}. {title}{location}\n"
        
        if total_count > 10:
            preview += f"\n  ... and {total_count - 10} more\n"
        
        # Check batch limit
        if total_count > 100:
            await ctx.warning(f"⚠️ Found {total_count} items, but batch limit is 100. Only first 100 will be moved.")
            todos = todos[:100]
            total_count = 100
        
        await ctx.info(preview)
        
        # Step 4: Elicit destination
        destination_input = await ctx.elicit(
            "\nWhere should these todos be moved?\n"
            "  - project:UUID (move to specific project)\n"
            "  - area:UUID (move to specific area)\n"
            "  - inbox (move to inbox)\n"
            "Destination: ",
            response_type=str
        )
        
        if destination_input.action != "accept" or not destination_input.data:
            return "Operation cancelled"
        
        destination = destination_input.data.strip().lower()
        if not destination:
            return _error_result("No destination provided. Operation cancelled.")
        
        # Validate and parse destination
        destination_uuid = None
        destination_description = destination
        
        if destination.startswith("project:"):
            destination_uuid = destination[8:].strip()
            project = things.get(destination_uuid)
            if not project or not isinstance(project, dict):
                return _error_result(f"Project not found: {destination_uuid}")
            destination_description = f"project '{project.get('title', destination_uuid)}'"
        elif destination.startswith("area:"):
            destination_uuid = destination[5:].strip()
            area = things.get(destination_uuid)
            if not area or not isinstance(area, dict):
                return _error_result(f"Area not found: {destination_uuid}")
            destination_description = f"area '{area.get('title', destination_uuid)}'"
        elif destination == "inbox":
            destination_uuid = "inbox"
            destination_description = "Inbox"
        else:
            return _error_result(f"Invalid destination: {destination}. Use project:UUID, area:UUID, or inbox")
        
        # Step 5: Confirmation
        confirmation = await ctx.elicit(
            f"\n⚠️ About to move {total_count} todo(s) to {destination_description}.\n"
            f"   Source: {filter_description}\n"
            f"   Type 'yes' to confirm: ",
            response_type=str
        )
        
        if confirmation.action != "accept" or confirmation.data.strip().lower() != "yes":
            return "Operation cancelled by user."
        
        # Step 6: Execute batch move
        await ctx.info(f"Moving {total_count} todos to {destination_description}...")
        
        moved_count = 0
        failed_count = 0
        
        for i, todo in enumerate(todos, 1):
            try:
                todo_uuid = todo.get('uuid')
                if not todo_uuid:
                    failed_count += 1
                    continue
                
                # Build URL scheme command
                url = f"things:///update?id={todo_uuid}&list-id={destination_uuid}"
                execute_url(url)
                moved_count += 1
                
                # Progress update every 10 items
                if i % 10 == 0:
                    await ctx.report_progress(i, total_count)
                    
            except Exception as e:
                logger.error(f"Failed to move todo {todo.get('uuid')}: {str(e)}")
                failed_count += 1
                continue
        
        # Invalidate caches
        cache_keys = ["get-todos", "get-inbox", "get-today", "get-upcoming", "get-projects"]
        invalidate_caches_for(cache_keys)
        
        # Final report
        result = "✓ Bulk move complete!\n"
        result += f"  Successfully moved: {moved_count} todos\n"
        if failed_count > 0:
            result += f"  Failed: {failed_count} todos\n"
        result += f"  Destination: {destination_description}\n"
        result += f"  Source: {filter_description}"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in bulk move: {str(e)}")
        return _error_result(f"Error moving todos: {str(e)}")

@mcp.tool(name="add-project", annotations=TOOL_ANNOTATIONS["add-project"])
def add_new_project(
    title: str,
    notes: Optional[str] = None,
    when: Optional[str] = None,
    deadline: Optional[str] = None,
    tags: Optional[Union[List[str], str]] = None,
    area_id: Optional[str] = None,
    area_title: Optional[str] = None,
    todos: Optional[Union[List[str], str]] = None
) -> str:
    """
    Create a new project in Things

    Args:
        title: Title of the project
        notes: Notes for the project
        when: When to schedule the project
        deadline: Deadline for the project
        tags: Tags to apply to the project
        area_id: ID of area to add to
        area_title: Title of area to add to
        todos: Initial todos to create in the project
    """
    try:
        # Ensure Things app is running
        if not app_state.update_app_state():
            if not launch_things():
                return _error_result("Error: Unable to launch Things app")

        # Handle tags and todos - some MCP clients send them as JSON strings
        if tags and isinstance(tags, str):
            import json
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        if todos and isinstance(todos, str):
            import json
            try:
                todos = json.loads(todos)
            except json.JSONDecodeError:
                todos = [todo.strip() for todo in todos.split("\n") if todo.strip()]

        # Build the add_project URL command and execute it
        url = add_project(
            title=title,
            notes=notes,
            when=when,
            deadline=deadline,
            tags=tags if isinstance(tags, list) else None,
            area_id=area_id,
            area_title=area_title,
            todos=todos if isinstance(todos, list) else None
        )

        # Log the generated URL before executing
        logger.debug(f"Add project URL: {url}")

        success = execute_url(url)

        if not success:
            return _error_result("Error: Failed to create project")

        return f"Successfully created project: {title}"
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        return _error_result(f"Error creating project: {str(e)}")

@mcp.tool(name="update-todo", annotations=TOOL_ANNOTATIONS["update-todo"])
def update_task(
    id: str,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    when: Optional[str] = None,
    deadline: Optional[str] = None,
    tags: Optional[Union[List[str], str]] = None,
    completed: Optional[bool] = None,
    canceled: Optional[bool] = None
) -> str:
    """
    Update an existing todo in Things.

    Args:
        id: ID of the todo to update
        title: New title
        notes: New notes
        when: New schedule
        deadline: New deadline
        tags: New tags. Missing tags will be created automatically.
        completed: Mark as completed
        canceled: Mark as canceled
    """
    try:
        # Ensure Things app is running
        if not app_state.update_app_state():
            if not launch_things():
                return _error_result("Error: Unable to launch Things app")

        # Handle tags parameter - some MCP clients send it as a JSON string
        if tags and isinstance(tags, str):
            import json
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                # If it's not valid JSON, treat it as a comma-separated string
                tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # Ensure tags exist before using them (tags should be List[str] now)
        if tags and isinstance(tags, list):
            ensure_tags_exist(tags)

        # Build the update_todo URL command and execute it
        url = update_todo(
            id=id,
            title=title,
            notes=notes,
            when=when,
            deadline=deadline,
            tags=tags,
            completed=completed,
            canceled=canceled
        )

        # Log the generated URL before executing
        logger.debug(f"Update todo URL: {url}")

        success = execute_url(url)

        if not success:
            return _error_result("Error: Failed to update todo")

        return f"Successfully updated todo with ID: {id}"
    except Exception as e:
        logger.error(f"Error updating todo: {str(e)}")
        return _error_result(f"Error updating todo: {str(e)}")

@mcp.tool(name="update-project", annotations=TOOL_ANNOTATIONS["update-project"])
def update_existing_project(
    id: str,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    when: Optional[str] = None,
    deadline: Optional[str] = None,
    tags: Optional[Union[List[str], str]] = None,
    completed: Optional[bool] = None,
    canceled: Optional[bool] = None
) -> str:
    """
    Update an existing project in Things

    Args:
        id: ID of the project to update
        title: New title
        notes: New notes
        when: New schedule
        deadline: New deadline
        tags: New tags
        completed: Mark as completed
        canceled: Mark as canceled
    """
    try:
        # Ensure Things app is running
        if not app_state.update_app_state():
            if not launch_things():
                return _error_result("Error: Unable to launch Things app")

        # Handle tags parameter - some MCP clients send it as a JSON string
        if tags and isinstance(tags, str):
            import json
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # Build the update_project URL command and execute it
        url = update_project(
            id=id,
            title=title,
            notes=notes,
            when=when,
            deadline=deadline,
            tags=tags if isinstance(tags, list) else None,
            completed=completed,
            canceled=canceled
        )

        # Log the generated URL before executing
        logger.debug(f"Update project URL: {url}")

        success = execute_url(url)

        if not success:
            return _error_result("Error: Failed to update project")

        return f"Successfully updated project with ID: {id}"
    except Exception as e:
        logger.error(f"Error updating project: {str(e)}")
        return _error_result(f"Error updating project: {str(e)}")

@mcp.tool(name="show-item", annotations=TOOL_ANNOTATIONS["show-item"])
def show_item(
    id: str,
    query: Optional[str] = None,
    filter_tags: Optional[Union[List[str], str]] = None
) -> str:
    """
    Show a specific item or list in Things

    Args:
        id: ID of item to show, or one of: inbox, today, upcoming, anytime, someday, logbook
        query: Optional query to filter by
        filter_tags: Optional tags to filter by
    """
    try:
        # Ensure Things app is running
        if not app_state.update_app_state():
            if not launch_things():
                return _error_result("Error: Unable to launch Things app")

        # Handle filter_tags parameter - some MCP clients send it as a JSON string
        if filter_tags and isinstance(filter_tags, str):
            import json
            try:
                filter_tags = json.loads(filter_tags)
            except json.JSONDecodeError:
                filter_tags = [tag.strip() for tag in filter_tags.split(",") if tag.strip()]

        # Execute the show URL command
        result = show(
            id=id,
            query=query,
            filter_tags=filter_tags if isinstance(filter_tags, list) else None
        )

        if not result:
            return _error_result(f"Error: Failed to show item/list '{id}'")

        return f"Successfully opened '{id}' in Things"
    except Exception as e:
        logger.error(f"Error showing item: {str(e)}")
        return _error_result(f"Error showing item: {str(e)}")

@mcp.tool(name="search-items", annotations=TOOL_ANNOTATIONS["search-items"])
def search_all_items(query: str) -> str:
    """
    Search for items in Things

    Args:
        query: Search query
    """
    try:
        # Ensure Things app is running
        if not app_state.update_app_state():
            if not launch_things():
                return _error_result("Error: Unable to launch Things app")

        # Execute the search URL command
        result = search(query=query)

        if not result:
            return _error_result(f"Error: Failed to search for '{query}'")

        return f"Successfully searched for '{query}' in Things"
    except Exception as e:
        logger.error(f"Error searching: {str(e)}")
        return _error_result(f"Error searching: {str(e)}")

@mcp.tool(name="get-recent", annotations=TOOL_ANNOTATIONS["get-recent"])
def get_recent(
    period: str,
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    deadline_filter: Optional[str] = None
) -> str:
    """
    Get recently created items with optional filtering

    Args:
        period: Time period (e.g., '3d', '1w', '2m', '1y')
        limit: Maximum number of results to return (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
        type_filter: Filter by item type - 'to-do', 'project', 'heading', 'area' (optional)
        status_filter: Filter by status - 'incomplete', 'completed', 'canceled' (optional)
        deadline_filter: Filter by deadline - 'overdue', 'today', 'upcoming', 'none' (optional)
    
    Example:
        >>> get_recent("7d", type_filter="to-do", status_filter="incomplete")
        Get incomplete todos from last 7 days
    """
    try:
        # Check if period format is valid
        if not period or not any(period.endswith(unit) for unit in ['d', 'w', 'm', 'y']):
            return _error_result("Error: Period must be in format '3d', '1w', '2m', '1y'")

        # Get recent items
        items = things.last(period)

        if not items:
            return f"No items found in the last {period}"

        # Apply filters
        if type_filter:
            items = _apply_type_filter(items, type_filter)
        if status_filter:
            items = _apply_status_filter(items, status_filter)
        if deadline_filter:
            items = _apply_deadline_filter(items, deadline_filter)
        
        # Check if filters removed all results
        if not items:
            filter_desc = []
            if type_filter:
                filter_desc.append(f"type={type_filter}")
            if status_filter:
                filter_desc.append(f"status={status_filter}")
            if deadline_filter:
                filter_desc.append(f"deadline={deadline_filter}")
            return f"No items found in last {period} matching filters: {', '.join(filter_desc)}"

        # Store total before limiting
        total_count = len(items)

        # Sort if requested
        if sort_by:
            if sort_by == 'title':
                items.sort(key=lambda x: x.get('title', '').lower())
            elif sort_by == 'created':
                items.sort(key=lambda x: x.get('created', ''), reverse=True)
            elif sort_by == 'modified':
                items.sort(key=lambda x: x.get('modified', ''), reverse=True)
            elif sort_by == 'deadline':
                items.sort(key=lambda x: x.get('deadline', '') or '', reverse=True)
            elif sort_by == 'start_date':
                items.sort(key=lambda x: x.get('start_date', '') or '', reverse=True)

        # Limit results if requested
        if limit and limit > 0:
            items = items[:limit]

        formatted_items = []
        for item in items:
            if item.get('type') == 'to-do':
                formatted_items.append(format_todo(item))
            elif item.get('type') == 'project':
                formatted_items.append(format_project(item, include_items=False))

        result = "\n\n---\n\n".join(formatted_items)
        
        # Add metadata about results
        extra_info = f"from {total_count} total" if limit and total_count > len(items) else ""
        metadata = _format_metadata(len(items), limit, sort_by, extra=extra_info)
        metadata += f" (period: {period})"
        if limit and len(items) >= limit:
            metadata += f" (limited to {limit})"
        if sort_by:
            metadata += f" sorted by {sort_by}"
        
        return f"{metadata}\n\n{result}"
    except Exception as e:
        logger.error(f"Error getting recent items: {str(e)}")
        return _error_result(f"Error getting recent items: {str(e)}")

@mcp.tool(name="get-cache-stats", annotations=TOOL_ANNOTATIONS["get-cache-stats"])
def get_cache_statistics() -> str:
    """Get cache performance statistics"""
    stats = get_cache_stats()

    return f"""Cache Statistics:
- Total entries: {stats['entries']}
- Cache hits: {stats['hits']}
- Cache misses: {stats['misses']}
- Hit rate: {stats['hit_rate']}
- Total requests: {stats['total_requests']}"""

# Main entry point
def run_things_mcp_server():
    """Run the Things MCP server"""
    host = get_binding_host()
    if host == DEFAULT_HOST:
        logger.info(
            "FastMCP will bind to %s (set %s=0.0.0.0 to allow remote connections)",
            DEFAULT_HOST,
            HOST_ENV_VAR,
        )
    else:
        logger.info(
            "FastMCP binding override detected: %s=%s",
            HOST_ENV_VAR,
            host,
        )

    # Check if Things app is available
    if not app_state.update_app_state():
        logger.warning("Things app is not running at startup. MCP will attempt to launch it when needed.")
        try:
            # Try to launch Things
            if launch_things():
                logger.info("Successfully launched Things app")
            else:
                logger.error("Unable to launch Things app. Some operations may fail.")
        except Exception as e:
            logger.error(f"Error launching Things app: {str(e)}")
    else:
        logger.info("Things app is running and ready for operations")

    # Determine transport based on environment
    # Use STDIO for Claude Desktop and other MCP clients (default)
    # Use HTTP only when explicitly requested via THINGS_MCP_TRANSPORT=http
    transport = os.getenv("THINGS_MCP_TRANSPORT", "stdio")
    
    if transport == "http" or transport == "streamable-http":
        logger.info("Starting MCP server with HTTP transport on %s:%d", host, get_binding_port())
        mcp.run(transport="streamable-http", host=host, port=get_binding_port())
    else:
        logger.info("Starting MCP server with STDIO transport for Claude Desktop")
        mcp.run(transport="stdio")

if __name__ == "__main__":
    run_things_mcp_server()
