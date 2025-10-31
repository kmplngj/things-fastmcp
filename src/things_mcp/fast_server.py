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

from mcp.server.fastmcp import FastMCP, Context
import mcp.types as types

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
    "search-todos": READ_ONLY_ANNOTATIONS,
    "search-advanced": READ_ONLY_ANNOTATIONS,
    "add-todo": ADD_ANNOTATIONS,
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
        "host": get_binding_host(),
        "port": get_binding_port(),
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

# LIST VIEWS

@mcp.tool(name="get-inbox", annotations=TOOL_ANNOTATIONS["get-inbox"])
async def get_inbox(limit: Optional[int] = None, sort_by: Optional[str] = None, ctx: Optional[Context] = None) -> str:
    """
    Get todos from Inbox
    
    IMPORTANT: Use the 'limit' parameter to avoid overwhelming the context window.
    For targeted queries (e.g., "find 10 items with URLs"), always specify a limit.
    
    Args:
        limit: Maximum number of results to return. Recommended: 10-50 for focused tasks. (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
    """
    import time
    start_time = time.time()
    log_operation_start("get-inbox")

    try:
        todos = things.inbox()

        if not todos:
            log_operation_end("get-inbox", True, time.time() - start_time, count=0)
            return "No items found in Inbox"

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
        metadata = _format_metadata(total_count, limit, sort_by, extra=f"from {total_count} total")
        return f"{metadata}\n\n{result}"
    except Exception as e:
        log_operation_end("get-inbox", False, time.time() - start_time, error=str(e))
        raise

@mcp.tool(name="get-today", annotations=TOOL_ANNOTATIONS["get-today"])
@cached(ttl=CACHE_TTL.get("today", 30))
async def get_today(limit: Optional[int] = None, sort_by: Optional[str] = None, ctx: Optional[Context] = None) -> str:
    """
    Get todos due today
    
    IMPORTANT: Use the 'limit' parameter to avoid overwhelming the context window.
    For targeted queries, always specify a limit.
    
    Args:
        limit: Maximum number of results to return. Recommended: 10-50 for focused tasks. (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
    """
    import time
    start_time = time.time()
    log_operation_start("get-today")

    try:
        todos = things.today()

        if not todos:
            log_operation_end("get-today", True, time.time() - start_time, count=0)
            return "No items due today"

        total_count = len(todos)
        
        # Warn if returning large result set without limit
        if ctx and not limit and total_count > 20:
            await ctx.warning(
                f"Returning all {total_count} today items without a limit. "
                f"Consider using limit parameter (e.g., limit=10) to reduce context window usage.",
                extra={"total_items": total_count, "limit_used": False}
            )

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
async def get_upcoming(limit: Optional[int] = None, sort_by: Optional[str] = None, ctx: Optional[Context] = None) -> str:
    """
    Get upcoming todos
    
    IMPORTANT: Use the 'limit' parameter to avoid overwhelming the context window.
    For targeted queries, always specify a limit.
    
    Args:
        limit: Maximum number of results to return. Recommended: 10-50 for focused tasks. (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
    """
    todos = things.upcoming()

    if not todos:
        return "No upcoming items"

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
async def get_anytime(limit: Optional[int] = None, sort_by: Optional[str] = None, ctx: Optional[Context] = None) -> str:
    """
    Get todos from Anytime list
    
    IMPORTANT: Use the 'limit' parameter to avoid overwhelming the context window.
    For targeted queries, always specify a limit.
    
    Args:
        limit: Maximum number of results to return. Recommended: 10-50 for focused tasks. (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
    """
    todos = things.anytime()

    if not todos:
        return "No items in Anytime list"

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
async def get_someday(limit: Optional[int] = None, sort_by: Optional[str] = None, ctx: Optional[Context] = None) -> str:
    """
    Get todos from Someday list
    
    IMPORTANT: Use the 'limit' parameter to avoid overwhelming the context window.
    For targeted queries, always specify a limit.
    
    Args:
        limit: Maximum number of results to return. Recommended: 10-50 for focused tasks. (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
    """
    todos = things.someday()

    if not todos:
        return "No items in Someday list"

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
async def get_logbook(period: str = "7d", limit: int = 50, sort_by: Optional[str] = None, ctx: Optional[Context] = None) -> str:
    """
    Get completed todos from Logbook, defaults to last 7 days

    IMPORTANT: Use the 'limit' parameter to avoid overwhelming the context window.
    For targeted queries, always specify a limit.

    Args:
        period: Time period to look back (e.g., '3d', '1w', '2m', '1y'). Defaults to '7d'
        limit: Maximum number of entries to return. Defaults to 50. Recommended: 10-50 for focused tasks.
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
    """
    todos = things.last(period, status='completed')

    if not todos:
        return "No completed items found"

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
async def get_trash(limit: Optional[int] = None, sort_by: Optional[str] = None, ctx: Optional[Context] = None) -> str:
    """
    Get trashed todos
    
    IMPORTANT: Use the 'limit' parameter to avoid overwhelming the context window.
    For targeted queries, always specify a limit.
    
    Args:
        limit: Maximum number of results to return. Recommended: 10-50 for focused tasks. (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
    """
    todos = things.trash()

    if not todos:
        return "No items in trash"

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
def get_tagged_items(tag: str) -> str:
    """
    Get items with a specific tag

    Args:
        tag: Tag title to filter by
    """
    todos = things.todos(tag=tag)

    if not todos:
        return f"No items found with tag '{tag}'"

    formatted_todos = [format_todo(todo) for todo in todos]
    return "\n\n---\n\n".join(formatted_todos)

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
    """
    try:
        counts = {
            'inbox': len(things.inbox()),
            'today': len(things.today()),
            'upcoming': len(things.upcoming()),
            'anytime': len(things.anytime()),
            'someday': len(things.someday()),
            'logbook': len(things.logbook()),
            'trash': len(things.trash())
        }
        
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
        return _error_result(f"Error getting item counts: {str(e)}")

@mcp.tool(name="search-todos", annotations=TOOL_ANNOTATIONS["search-todos"])
async def search_todos(
    query: str,
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Search todos by title or notes
    
    IMPORTANT: Use the 'limit' parameter to prevent overwhelming the context window when
    searching across large todo collections. Without a limit, all matching results are returned.

    Args:
        query: Search term to look for in todo titles and notes
        limit: Maximum number of results to return (optional, recommended for large result sets)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
        ctx: Context object for progress reporting (internal use)
    """
    todos = things.search(query)

    if not todos:
        return f"No todos found matching '{query}'"

    # Store total count before limiting
    total_count = len(todos)
    
    # Warn if returning large result set without limit
    if ctx and not limit and total_count > 20:
        await ctx.warning(
            f"Search returned {total_count} items without a limit. "
            "Consider using the 'limit' parameter to reduce context window usage."
        )

    # Apply sorting and limiting using the shared helper
    todos = _apply_sort_and_limit(todos, sort_by, limit)

    formatted_todos = [format_todo(todo) for todo in todos]
    result = "\n\n---\n\n".join(formatted_todos)
    
    # Add metadata with total count information
    extra_info = f"from {total_count} total" if limit and total_count > len(todos) else ""
    metadata = _format_metadata(len(todos), limit, sort_by, extra=extra_info)
    
    return f"{metadata}\n\n{result}"

@mcp.tool(name="search-advanced", annotations=TOOL_ANNOTATIONS["search-advanced"])
async def search_advanced(
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    deadline: Optional[str] = None,
    tag: Optional[str] = None,
    area: Optional[str] = None,
    type: Optional[str] = None,
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Advanced todo search with multiple filters
    
    IMPORTANT: Use the 'limit' parameter to prevent overwhelming the context window when
    searching across large todo collections. Without a limit, all matching results are returned.

    Args:
        status: Filter by todo status (incomplete/completed/canceled)
        start_date: Filter by start date (YYYY-MM-DD)
        deadline: Filter by deadline (YYYY-MM-DD)
        tag: Filter by tag
        area: Filter by area UUID
        type: Filter by item type (to-do/project/heading)
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

        # Store total count before limiting
        total_count = len(todos)
        
        # Warn if returning large result set without limit
        if ctx and not limit and total_count > 20:
            await ctx.warning(
                f"Advanced search returned {total_count} items without a limit. "
                "Consider using the 'limit' parameter to reduce context window usage."
            )

        # Apply sorting and limiting using the shared helper
        todos = _apply_sort_and_limit(todos, sort_by, limit)

        formatted_todos = [format_todo(todo) for todo in todos]
        result = "\n\n---\n\n".join(formatted_todos)
        
        # Add metadata with total count information
        extra_info = f"from {total_count} total" if limit and total_count > len(todos) else ""
        metadata = _format_metadata(len(todos), limit, sort_by, extra=extra_info)
        
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
    tags: Optional[List[str]] = None,
    checklist_items: Optional[List[str]] = None,
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

        # Ensure tags exist before using them
        if tags:
            ensure_tags_exist(tags)

        # Build the add_todo URL command and execute it
        url = add_todo(
            title=title,
            notes=notes,
            when=when,
            deadline=deadline,
            tags=tags,
            checklist_items=checklist_items,
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

@mcp.tool(name="add-project", annotations=TOOL_ANNOTATIONS["add-project"])
def add_new_project(
    title: str,
    notes: Optional[str] = None,
    when: Optional[str] = None,
    deadline: Optional[str] = None,
    tags: Optional[List[str]] = None,
    area_id: Optional[str] = None,
    area_title: Optional[str] = None,
    todos: Optional[List[str]] = None
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

        # Build the add_project URL command and execute it
        url = add_project(
            title=title,
            notes=notes,
            when=when,
            deadline=deadline,
            tags=tags,
            area_id=area_id,
            area_title=area_title,
            todos=todos
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
    tags: Optional[List[str]] = None,
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

        # Ensure tags exist before using them
        if tags:
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
    tags: Optional[List[str]] = None,
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

        # Build the update_project URL command and execute it
        url = update_project(
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
    filter_tags: Optional[List[str]] = None
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

        # Execute the show URL command
        result = show(
            id=id,
            query=query,
            filter_tags=filter_tags
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
    sort_by: Optional[str] = None
) -> str:
    """
    Get recently created items

    Args:
        period: Time period (e.g., '3d', '1w', '2m', '1y')
        limit: Maximum number of results to return (optional)
        sort_by: Sort results by field - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
    """
    try:
        # Check if period format is valid
        if not period or not any(period.endswith(unit) for unit in ['d', 'w', 'm', 'y']):
            return _error_result("Error: Period must be in format '3d', '1w', '2m', '1y'")

        # Get recent items
        items = things.last(period)

        if not items:
            return f"No items found in the last {period}"

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
        total_found = len(items)
        metadata = f"Found {total_found} item(s) from last {period}"
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
        mcp.run(transport="streamable-http")
    else:
        logger.info("Starting MCP server with STDIO transport for Claude Desktop")
        mcp.run(transport="stdio")

if __name__ == "__main__":
    run_things_mcp_server()
