#!/usr/bin/env python3
"""
Things MCP Server implementation using the FastMCP pattern.
This provides a more modern and maintainable approach to the Things integration.
"""
import os
import time
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
    launch_things, execute_url
)

# Import and configure enhanced logging
from .logging_config import setup_logging, get_logger, log_operation_start, log_operation_end
# Import caching
from .cache import cached, invalidate_caches_for, get_cache_stats, CACHE_TTL
from .tag_handler import ensure_tags_exist
from .template_storage import (
    save_template_sync as save_template,
    get_template_sync as get_template,
    list_templates_sync as list_templates,
    delete_template_sync as delete_template,
    template_exists_sync as template_exists
)

# Import analytics functions and dataclasses
from .analytics import (
    calculate_productivity_stats,
    calculate_project_velocity,
    calculate_time_to_completion,
    calculate_tag_productivity,
    calculate_stalled_projects,
    calculate_project_health,
    calculate_tag_relationships,
    calculate_tag_suggestions,
    generate_ascii_chart,
    ProductivityStats,  # type: ignore # noqa: F401
    ProjectVelocity,  # type: ignore # noqa: F401
    CompletionTimeStats,  # type: ignore # noqa: F401
    TagProductivityMetric,  # type: ignore # noqa: F401
    StalledProject,  # type: ignore # noqa: F401
    ProjectHealth,  # type: ignore # noqa: F401
    TagRelationship,  # type: ignore # noqa: F401
    TagSuggestion,  # type: ignore # noqa: F401
)

# Import prompts module
from . import prompts

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
    # v3.0.0 Composite Tools
    "list-items": READ_ONLY_ANNOTATIONS,
    "count": READ_ONLY_ANNOTATIONS,
    "search": READ_ONLY_ANNOTATIONS,
    "deadline-items": READ_ONLY_ANNOTATIONS,
    "manage-heading": UPDATE_ANNOTATIONS,
    # v3.0.0 Dynamic Tool Management
    "enable-advanced-features": UPDATE_ANNOTATIONS,
    "disable-advanced-features": UPDATE_ANNOTATIONS,
    "get-tool-categories": READ_ONLY_ANNOTATIONS,
    # Original tools (backward compatibility - deprecated in v3.0.0)
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
    "schedule-assistant": MODIFY_ANNOTATIONS,
    "create-project-template": ADD_ANNOTATIONS,
    "list-project-templates": READ_ONLY_ANNOTATIONS,
    "apply-project-template": ADD_ANNOTATIONS,
    "update-project-template": UPDATE_ANNOTATIONS,
    "delete-project-template": MODIFY_ANNOTATIONS,
    "add-project": ADD_ANNOTATIONS,
    "update-todo": UPDATE_ANNOTATIONS,
    "update-project": UPDATE_ANNOTATIONS,
    "show-item": READ_ONLY_ANNOTATIONS,
    "search-items": READ_ONLY_ANNOTATIONS,
    "get-recent": READ_ONLY_ANNOTATIONS,
    "get-cache-stats": READ_ONLY_ANNOTATIONS,
    # Phase 3: Analytics & Intelligence Layer
    "get-productivity-stats": READ_ONLY_ANNOTATIONS,
    "get-project-velocity": READ_ONLY_ANNOTATIONS,
    "get-time-to-completion": READ_ONLY_ANNOTATIONS,
    "get-tag-productivity": READ_ONLY_ANNOTATIONS,
    "check-stalled-projects": READ_ONLY_ANNOTATIONS,
    "get-project-health-report": READ_ONLY_ANNOTATIONS,
    "analyze-tag-relationships": READ_ONLY_ANNOTATIONS,
    "suggest-tags": READ_ONLY_ANNOTATIONS,
    "parse-natural-date": READ_ONLY_ANNOTATIONS,
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

# ============================================================================
# REGISTER PROMPTS (v4.0.0 Phase 1)
# ============================================================================

logger.info("Registering MCP prompts...")
prompts.register_all_prompts(mcp)
logger.info(f"Registered {len(prompts.PROMPT_REGISTRY)} prompts across 4 categories")

# ============================================================================
# DYNAMIC TOOL MANAGEMENT (v3.0.0 Phase 2)
# ============================================================================

# Storage for tool handles to enable dynamic enable/disable
ADVANCED_TOOL_HANDLES: Dict[str, List[Any]] = {
    "analytics": [],
    "checklists": [],
    "structure": [],
    "deprecated": []
}

# Track which categories are enabled
ENABLED_CATEGORIES: Dict[str, bool] = {
    "analytics": False,
    "checklists": False,
    "structure": False
}

def register_advanced_tool(category: str, tool_handle):
    """Register a tool handle for dynamic management"""
    if category in ADVANCED_TOOL_HANDLES:
        ADVANCED_TOOL_HANDLES[category].append(tool_handle)
        tool_handle.disable()  # Start disabled
    return tool_handle

def enable_tool_category(category: str) -> int:
    """Enable all tools in a category. Returns count of enabled tools."""
    if category not in ADVANCED_TOOL_HANDLES:
        return 0
    
    if category == "all":
        count = 0
        for cat in ["analytics", "checklists", "structure"]:
            count += enable_tool_category(cat)
        return count
    
    ENABLED_CATEGORIES[category] = True
    for tool in ADVANCED_TOOL_HANDLES[category]:
        tool.enable()  # Triggers tools/list_changed notification
    
    return len(ADVANCED_TOOL_HANDLES[category])

def disable_tool_category(category: str) -> int:
    """Disable all tools in a category. Returns count of disabled tools."""
    if category not in ADVANCED_TOOL_HANDLES:
        return 0
    
    if category == "all":
        count = 0
        for cat in ["analytics", "checklists", "structure"]:
            count += disable_tool_category(cat)
        return count
    
    ENABLED_CATEGORIES[category] = False
    for tool in ADVANCED_TOOL_HANDLES[category]:
        tool.disable()  # Triggers tools/list_changed notification
    
    return len(ADVANCED_TOOL_HANDLES[category])

def get_category_status() -> Dict[str, Any]:
    """Get current status of all tool categories"""
    return {
        "analytics": {
            "enabled": ENABLED_CATEGORIES["analytics"],
            "tool_count": len(ADVANCED_TOOL_HANDLES["analytics"])
        },
        "checklists": {
            "enabled": ENABLED_CATEGORIES["checklists"],
            "tool_count": len(ADVANCED_TOOL_HANDLES["checklists"])
        },
        "structure": {
            "enabled": ENABLED_CATEGORIES["structure"],
            "tool_count": len(ADVANCED_TOOL_HANDLES["structure"])
        }
    }

# ============================================================================
# COMPOSITE TOOLS (v3.0.0) - Consolidated from 15 individual tools
# ============================================================================

@mcp.tool(name="list-items", annotations=READ_ONLY_ANNOTATIONS)
async def list_items(
    list_type: str,
    type_filter: Optional[str] = None,
    deadline_filter: Optional[str] = None,
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Get items from a specific Things list (v3.0.0 composite tool).
    
    Replaces: get-inbox, get-today, get-upcoming, get-anytime, get-someday, get-logbook, get-trash
    
    Args:
        list_type: Which list to query - 'inbox', 'today', 'upcoming', 'anytime', 'someday', 'logbook', 'trash'
        type_filter: Filter by type - 'to-do', 'project', 'heading', 'area' (optional)
        deadline_filter: Filter by deadline - 'overdue', 'today', 'upcoming', 'none' (optional)
        limit: Maximum items to return (default: 20, recommended to avoid context overflow)
        sort_by: Sort order - 'title', 'created', 'modified', 'deadline', 'start_date' (optional)
    
    Returns:
        Formatted list of items with metadata
    
    Examples:
        list_items("today", limit=10)
        list_items("inbox", type_filter="to-do", deadline_filter="overdue")
        list_items("logbook", limit=50)
    """
    import time
    start_time = time.time()
    log_operation_start(f"list-items ({list_type})")
    
    # Validate list_type
    valid_types = ["inbox", "today", "upcoming", "anytime", "someday", "logbook", "trash"]
    if list_type not in valid_types:
        log_operation_end(f"list-items ({list_type})", False, time.time() - start_time)
        return f"Error: Invalid list_type '{list_type}'. Must be one of: {', '.join(valid_types)}"
    
    try:
        # Route to appropriate Things API method
        items = []
        if list_type == "inbox":
            items = things.inbox()
        elif list_type == "today":
            items = things.today()
        elif list_type == "upcoming":
            items = things.upcoming()
        elif list_type == "anytime":
            items = things.anytime()
        elif list_type == "someday":
            items = things.someday()
        elif list_type == "logbook":
            items = things.logbook()
        elif list_type == "trash":
            items = things.trash()
        
        if not items:
            log_operation_end(f"list-items ({list_type})", True, time.time() - start_time, count=0)
            return f"No items found in {list_type}"
        
        # Apply filters
        if type_filter:
            items = _apply_type_filter(items, type_filter)
        if deadline_filter:
            items = _apply_deadline_filter(items, deadline_filter)
        
        if not items:
            filter_desc = []
            if type_filter:
                filter_desc.append(f"type={type_filter}")
            if deadline_filter:
                filter_desc.append(f"deadline={deadline_filter}")
            log_operation_end(f"list-items ({list_type})", True, time.time() - start_time, count=0)
            return f"No {list_type} items matching filters: {', '.join(filter_desc)}"
        
        total_count = len(items)
        
        # Warn if returning large result set without limit
        if ctx and not limit and total_count > 20:
            await ctx.warning(
                f"Returning all {total_count} {list_type} items without a limit. "
                f"Consider using limit parameter (e.g., limit=10) to reduce context window usage.",
                extra={"total_items": total_count, "limit_used": False, "list_type": list_type}
            )
        
        # Apply sorting and limiting
        items = _apply_sort_and_limit(items, sort_by, limit)
        
        # Format results
        result_lines = [f"📋 {list_type.capitalize()} Items"]
        for item in items:
            status_icon = "✓" if item.get('status') == 'completed' else "○"
            title = item.get('title', 'Untitled')
            uuid = item.get('uuid', 'unknown')
            item_type = item.get('type', 'to-do')
            
            # Add deadline badge if present
            deadline_badge = ""
            if item.get('deadline'):
                from datetime import datetime, date
                deadline_date = datetime.fromisoformat(item['deadline']).date()
                today = date.today()
                if deadline_date < today:
                    deadline_badge = " ⚠️"
                elif deadline_date == today:
                    deadline_badge = " 🔴"
            
            result_lines.append(f"{status_icon} {title} ({item_type}) {deadline_badge}")
            result_lines.append(f"   ID: {uuid}")
        
        # Add metadata
        extra_info = f"from {total_count} total" if limit and total_count > len(items) else ""
        metadata = _format_metadata(len(items), limit, sort_by, extra=extra_info)
        result_lines.append(f"\n{metadata}")
        
        result = "\n".join(result_lines)
        log_operation_end(f"list-items ({list_type})", True, time.time() - start_time, count=len(items))
        return result
        
    except Exception as e:
        logger.error(f"Error in list-items ({list_type}): {str(e)}")
        log_operation_end(f"list-items ({list_type})", False, time.time() - start_time)
        return _error_result(f"Error getting {list_type} items: {str(e)}")


@mcp.tool(name="count", annotations=READ_ONLY_ANNOTATIONS)
async def count(
    count_type: str,
    query: Optional[str] = None,
    tag: Optional[str] = None,
    project_uuid: Optional[str] = None,
    title_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Count items in various contexts without fetching full data (v3.0.0 composite tool).
    
    Replaces: count-items, count-search, count-tagged-items, count-project-items, count-advanced
    
    Args:
        count_type: What to count - 'lists', 'search', 'tag', 'project', 'advanced'
        query: Search query (required for count_type="search")
        tag: Tag name (required for count_type="tag")
        project_uuid: Project UUID (required for count_type="project")
        title_filter: Title pattern (for count_type="advanced")
        type_filter: Type filter (for count_type="advanced")
        status_filter: Status filter (for count_type="advanced")
    
    Returns:
        Count summary with recommendations for limiting
    
    Examples:
        count("lists")  # Count all lists
        count("search", query="meeting notes")
        count("tag", tag="work")
        count("project", project_uuid="...")
        count("advanced", title_filter="review", status_filter="incomplete")
    """
    import time
    start_time = time.time()
    log_operation_start(f"count ({count_type})")
    
    # Validate count_type
    valid_types = ["lists", "search", "tag", "project", "advanced"]
    if count_type not in valid_types:
        log_operation_end(f"count ({count_type})", False, time.time() - start_time)
        return f"Error: Invalid count_type '{count_type}'. Must be one of: {', '.join(valid_types)}"
    
    try:
        result_lines = ["📊 Item Counts"]
        
        if count_type == "lists":
            # Count all main lists
            inbox_count = len(things.inbox())
            today_count = len(things.today())
            upcoming_count = len(things.upcoming())
            anytime_count = len(things.anytime())
            someday_count = len(things.someday())
            logbook_count = len(things.logbook())
            trash_count = len(things.trash())
            
            result_lines.append(f"\n📥 Inbox: {inbox_count} items")
            result_lines.append(f"☀️ Today: {today_count} items")
            result_lines.append(f"📅 Upcoming: {upcoming_count} items")
            result_lines.append(f"🔵 Anytime: {anytime_count} items")
            result_lines.append(f"💤 Someday: {someday_count} items")
            result_lines.append(f"✅ Logbook: {logbook_count} items")
            result_lines.append(f"🗑️ Trash: {trash_count} items")
            
            # Add recommendations
            high_count_lists = []
            if inbox_count > 20:
                high_count_lists.append(f"inbox ({inbox_count})")
            if today_count > 20:
                high_count_lists.append(f"today ({today_count})")
            if upcoming_count > 20:
                high_count_lists.append(f"upcoming ({upcoming_count})")
            
            if high_count_lists:
                result_lines.append(f"\n💡 Recommendation: Use limit parameter for: {', '.join(high_count_lists)}")
        
        elif count_type == "search":
            if not query:
                log_operation_end(f"count ({count_type})", False, time.time() - start_time)
                return "Error: 'query' parameter required for count_type='search'"
            
            results = things.search(query)
            count = len(results)
            result_lines.append(f"\n🔍 Search '{query}': {count} items")
            
            if count > 20:
                result_lines.append("💡 Recommendation: Use limit parameter when fetching (e.g., limit=20)")
        
        elif count_type == "tag":
            if not tag:
                log_operation_end(f"count ({count_type})", False, time.time() - start_time)
                return "Error: 'tag' parameter required for count_type='tag'"
            
            tagged_todos = things.todos(tag=tag)
            count = len(tagged_todos)
            result_lines.append(f"\n🏷️ Tag '{tag}': {count} items")
            
            if count > 20:
                result_lines.append("💡 Recommendation: Use limit parameter when fetching")
        
        elif count_type == "project":
            if not project_uuid:
                log_operation_end(f"count ({count_type})", False, time.time() - start_time)
                return "Error: 'project_uuid' parameter required for count_type='project'"
            
            project = things.get(project_uuid)
            if not project:
                log_operation_end(f"count ({count_type})", False, time.time() - start_time)
                return f"Error: Project not found: {project_uuid}"
            
            if isinstance(project, dict):
                items = project.get('items', [])
                count = len(items)
                project_title = project.get('title', 'Untitled')
            else:
                count = 0
                project_title = 'Unknown'
            result_lines.append(f"\n📁 Project '{project_title}': {count} items")
        
        elif count_type == "advanced":
            # Count with advanced filters
            all_items = things.todos()
            
            # Apply filters
            if title_filter:
                all_items = [item for item in all_items if title_filter.lower() in item.get('title', '').lower()]
            if type_filter:
                all_items = _apply_type_filter(all_items, type_filter)
            if status_filter:
                all_items = _apply_status_filter(all_items, status_filter)
            
            count = len(all_items)
            filter_desc = []
            if title_filter:
                filter_desc.append(f"title='{title_filter}'")
            if type_filter:
                filter_desc.append(f"type={type_filter}")
            if status_filter:
                filter_desc.append(f"status={status_filter}")
            
            result_lines.append(f"\n🎯 Advanced count ({', '.join(filter_desc)}): {count} items")
            
            if count > 20:
                result_lines.append("💡 Recommendation: Use limit parameter when fetching")
        
        result = "\n".join(result_lines)
        log_operation_end(f"count ({count_type})", True, time.time() - start_time)
        return result
        
    except Exception as e:
        logger.error(f"Error in count ({count_type}): {str(e)}")
        log_operation_end(f"count ({count_type})", False, time.time() - start_time)
        return _error_result(f"Error counting {count_type}: {str(e)}")


@mcp.tool(name="search", annotations=READ_ONLY_ANNOTATIONS)
async def search(
    query: Optional[str] = None,
    title_filter: Optional[str] = None,
    notes_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    deadline_filter: Optional[str] = None,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    sort_by: Optional[str] = "modified",
    ctx: Optional[Context] = None
) -> str:
    """
    Search for items with optional advanced filters (v3.0.0 composite tool).
    
    Replaces: search-todos, search-advanced
    
    Args:
        query: Full-text search query (searches title and notes) - if provided, uses Things search API
        title_filter: Filter by title substring (manual filter)
        notes_filter: Filter by notes substring (manual filter)
        type_filter: Filter by type - 'to-do', 'project', 'heading', 'area'
        status_filter: Filter by status - 'incomplete', 'completed', 'canceled'
        deadline_filter: Filter by deadline - 'overdue', 'today', 'upcoming', 'none'
        limit: Maximum items to return (default: 20)
        offset: Pagination offset (default: 0)
        sort_by: Sort order - 'title', 'created', 'modified', 'deadline' (default: 'modified')
    
    Returns:
        Search results with pagination metadata
    
    Examples:
        search(query="meeting")
        search(title_filter="review", status_filter="incomplete", deadline_filter="overdue")
        search(query="project", type_filter="to-do", limit=10)
    """
    import time
    start_time = time.time()
    log_operation_start("search")
    
    try:
        # Use Things search API if query provided, otherwise get all todos
        if query:
            todos = things.search(query)
        else:
            todos = things.todos()
        
        if not todos:
            log_operation_end("search", True, time.time() - start_time, count=0)
            return "No items found"
        
        # Apply manual filters
        if title_filter:
            todos = [t for t in todos if title_filter.lower() in t.get('title', '').lower()]
        if notes_filter:
            todos = [t for t in todos if notes_filter.lower() in t.get('notes', '').lower()]
        if type_filter:
            todos = _apply_type_filter(todos, type_filter)
        if status_filter:
            todos = _apply_status_filter(todos, status_filter)
        if deadline_filter:
            todos = _apply_deadline_filter(todos, deadline_filter)
        
        if not todos:
            filter_desc = []
            if query:
                filter_desc.append(f"query='{query}'")
            if title_filter:
                filter_desc.append(f"title='{title_filter}'")
            if notes_filter:
                filter_desc.append(f"notes='{notes_filter}'")
            if type_filter:
                filter_desc.append(f"type={type_filter}")
            if status_filter:
                filter_desc.append(f"status={status_filter}")
            if deadline_filter:
                filter_desc.append(f"deadline={deadline_filter}")
            log_operation_end("search", True, time.time() - start_time, count=0)
            return f"No items matching filters: {', '.join(filter_desc)}"
        
        total_count = len(todos)
        
        # Warn if large result set
        if ctx and not limit and total_count > 20:
            await ctx.warning(
                f"Returning all {total_count} search results without a limit. "
                f"Consider using limit parameter (e.g., limit=20) to reduce context window usage.",
                extra={"total_items": total_count, "limit_used": False}
            )
        
        # Apply sorting
        todos = _apply_sort_and_limit(todos, sort_by, None)  # Don't limit yet for pagination
        
        # Apply pagination
        offset_val = offset if offset is not None else 0
        limit_val = limit if limit is not None else len(todos)
        paginated_todos = todos[offset_val:offset_val + limit_val] if limit else todos[offset_val:]
        
        # Format results
        result_lines = ["🔍 Search Results"]
        for todo in paginated_todos:
            status_icon = "✓" if todo.get('status') == 'completed' else "○"
            title = todo.get('title', 'Untitled')
            uuid = todo.get('uuid', 'unknown')
            
            result_lines.append(f"{status_icon} {title}")
            result_lines.append(f"   ID: {uuid}")
            
            # Add snippet of notes if present
            if todo.get('notes'):
                notes_preview = todo['notes'][:60] + "..." if len(todo['notes']) > 60 else todo['notes']
                result_lines.append(f"   Notes: {notes_preview}")
        
        # Add pagination metadata
        showing_count = len(paginated_todos)
        offset_val = offset if offset is not None else 0
        limit_val = limit if limit is not None else len(todos)
        if offset_val > 0 or (limit and total_count > offset_val + limit_val):
            pagination_info = f"Showing items {offset_val + 1}-{offset_val + showing_count} of {total_count} total"
        else:
            pagination_info = f"Found {showing_count} items"
        
        result_lines.append(f"\n📊 {pagination_info}")
        if sort_by:
            result_lines.append(f"   Sorted by: {sort_by}")
        
        result = "\n".join(result_lines)
        log_operation_end("search", True, time.time() - start_time, count=showing_count)
        return result
        
    except Exception as e:
        logger.error(f"Error in search: {str(e)}")
        log_operation_end("search", False, time.time() - start_time)
        return _error_result(f"Error searching: {str(e)}")


@mcp.tool(name="deadline-items", annotations=READ_ONLY_ANNOTATIONS)
async def deadline_items(
    filter_type: str = "overdue",
    days: Optional[int] = 7,
    limit: Optional[int] = None,
    sort_by: Optional[str] = "deadline",
    ctx: Optional[Context] = None
) -> str:
    """
    Get items filtered by deadline status (v3.0.0 composite tool).
    
    Replaces: get-overdue-items, get-items-due-soon
    
    Args:
        filter_type: Type of deadline filter - 'overdue', 'due-soon' (default: 'overdue')
        days: For "due-soon", number of days to look ahead (default: 7)
        limit: Maximum items to return (optional)
        sort_by: Sort order - 'deadline', 'title', 'created', 'modified' (default: 'deadline')
    
    Returns:
        Items with deadline information and urgency badges
    
    Examples:
        deadline_items("overdue")
        deadline_items("due-soon", days=3)
        deadline_items("overdue", limit=10)
    """
    import time
    from datetime import datetime, date, timedelta
    
    start_time = time.time()
    log_operation_start(f"deadline-items ({filter_type})")
    
    # Validate filter_type
    valid_types = ["overdue", "due-soon"]
    if filter_type not in valid_types:
        log_operation_end(f"deadline-items ({filter_type})", False, time.time() - start_time)
        return f"Error: Invalid filter_type '{filter_type}'. Must be one of: {', '.join(valid_types)}"
    
    try:
        # Get all incomplete todos
        todos = [t for t in things.todos() if t.get('status') == 'incomplete']
        
        today = date.today()
        filtered_todos = []
        
        for todo in todos:
            deadline_str = todo.get('deadline')
            if not deadline_str:
                continue
            
            try:
                deadline_date = datetime.fromisoformat(deadline_str).date()
                
                if filter_type == "overdue":
                    if deadline_date < today:
                        days_overdue = (today - deadline_date).days
                        todo['days_overdue'] = days_overdue
                        filtered_todos.append(todo)
                
                elif filter_type == "due-soon":
                    days_val = days if days is not None else 7
                    future_date = today + timedelta(days=days_val)
                    if today <= deadline_date <= future_date:
                        days_until = (deadline_date - today).days
                        todo['days_until'] = days_until
                        filtered_todos.append(todo)
            
            except (ValueError, TypeError):
                continue
        
        if not filtered_todos:
            log_operation_end(f"deadline-items ({filter_type})", True, time.time() - start_time, count=0)
            if filter_type == "overdue":
                return "✅ No overdue items found!"
            else:
                return f"📅 No items due in the next {days} days"
        
        # Sort by deadline by default
        if sort_by == "deadline":
            filtered_todos.sort(key=lambda x: x.get('deadline', ''))
        else:
            filtered_todos = _apply_sort_and_limit(filtered_todos, sort_by, None)
        
        # Apply limit
        if limit:
            filtered_todos = filtered_todos[:limit]
        
        # Format results
        if filter_type == "overdue":
            result_lines = [f"⚠️  Overdue Items ({len(filtered_todos)})"]
            for todo in filtered_todos:
                title = todo.get('title', 'Untitled')
                uuid = todo.get('uuid', 'unknown')
                days_overdue = todo.get('days_overdue', 0)
                deadline_str = todo.get('deadline', '')
                
                urgency_badge = "⚠️"
                if days_overdue > 7:
                    urgency_badge = "🔴"
                
                result_lines.append(f"{urgency_badge} {title}")
                result_lines.append(f"   ID: {uuid}")
                result_lines.append(f"   Overdue by: {days_overdue} days (deadline: {deadline_str[:10]})")
        
        else:  # due-soon
            result_lines = [f"📅 Items Due Soon (next {days} days) - {len(filtered_todos)} items"]
            for todo in filtered_todos:
                title = todo.get('title', 'Untitled')
                uuid = todo.get('uuid', 'unknown')
                days_until = todo.get('days_until', 0)
                deadline_str = todo.get('deadline', '')
                
                if days_until == 0:
                    urgency_badge = "🔴 Due today"
                elif days_until == 1:
                    urgency_badge = "🟠 Due tomorrow"
                else:
                    urgency_badge = f"🟡 Due in {days_until} days"
                
                result_lines.append(f"{urgency_badge}: {title}")
                result_lines.append(f"   ID: {uuid}")
                result_lines.append(f"   Deadline: {deadline_str[:10]}")
        
        result = "\n".join(result_lines)
        log_operation_end(f"deadline-items ({filter_type})", True, time.time() - start_time, count=len(filtered_todos))
        return result
        
    except Exception as e:
        logger.error(f"Error in deadline-items ({filter_type}): {str(e)}")
        log_operation_end(f"deadline-items ({filter_type})", False, time.time() - start_time)
        return _error_result(f"Error getting deadline items: {str(e)}")


@mcp.tool(name="manage-heading", annotations=UPDATE_ANNOTATIONS)
async def manage_heading(
    action: str,
    project_uuid: str,
    heading_title: Optional[str] = None,
    heading_uuid: Optional[str] = None,
    todo_uuid: Optional[str] = None,
    after_uuid: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Add headings or move todos under headings (v3.0.0 composite tool).
    
    Replaces: add-heading, move-todo-under-heading
    
    Args:
        action: Action to perform - 'add', 'move'
        project_uuid: Project UUID (required for both actions)
        heading_title: Heading title (required for action="add")
        heading_uuid: Heading UUID (required for action="move")
        todo_uuid: Todo UUID (required for action="move")
        after_uuid: Item UUID to position after (optional for action="add")
    
    Returns:
        Success message with updated structure
    
    Examples:
        manage_heading("add", project_uuid="...", heading_title="Phase 1")
        manage_heading("add", project_uuid="...", heading_title="Done", after_uuid="...")
        manage_heading("move", project_uuid="...", heading_uuid="...", todo_uuid="...")
    """
    import time
    start_time = time.time()
    log_operation_start(f"manage-heading ({action})")
    
    # Validate action
    valid_actions = ["add", "move"]
    if action not in valid_actions:
        log_operation_end(f"manage-heading ({action})", False, time.time() - start_time)
        return f"Error: Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}"
    
    try:
        if action == "add":
            # Validate required parameters
            if not heading_title:
                log_operation_end(f"manage-heading ({action})", False, time.time() - start_time)
                return "Error: 'heading_title' parameter required for action='add'"
            
            # Build URL scheme
            url = f"things:///add?type=heading&heading={heading_title}&list-id={project_uuid}"
            if after_uuid:
                url += f"&after={after_uuid}"
            
            execute_url(url)
            invalidate_caches_for(["get-project-structure", "get-projects"])
            
            result = f"✓ Added heading '{heading_title}' to project"
            if after_uuid:
                result += f" (positioned after item {after_uuid})"
            
            log_operation_end(f"manage-heading ({action})", True, time.time() - start_time)
            return result
        
        elif action == "move":
            # Validate required parameters
            if not heading_uuid:
                log_operation_end(f"manage-heading ({action})", False, time.time() - start_time)
                return "Error: 'heading_uuid' parameter required for action='move'"
            if not todo_uuid:
                log_operation_end(f"manage-heading ({action})", False, time.time() - start_time)
                return "Error: 'todo_uuid' parameter required for action='move'"
            
            # Verify both items exist and are in the same project
            todo = things.get(todo_uuid)
            heading = things.get(heading_uuid)
            
            if not todo:
                log_operation_end(f"manage-heading ({action})", False, time.time() - start_time)
                return f"Error: Todo not found: {todo_uuid}"
            if not heading:
                log_operation_end(f"manage-heading ({action})", False, time.time() - start_time)
                return f"Error: Heading not found: {heading_uuid}"
            
            # Verify both are in the specified project
            if isinstance(todo, dict) and isinstance(heading, dict):
                todo_project = todo.get('project')
                heading_project = heading.get('project')
            else:
                log_operation_end(f"manage-heading ({action})", False, time.time() - start_time)
                return "Error: Invalid item type returned"
            
            if todo_project != project_uuid or heading_project != project_uuid:
                log_operation_end(f"manage-heading ({action})", False, time.time() - start_time)
                return f"Error: Both todo and heading must be in project {project_uuid}"
            
            # Move todo under heading
            url = f"things:///update?id={todo_uuid}&heading={heading_uuid}"
            execute_url(url)
            invalidate_caches_for(["get-project-structure", "get-todos"])
            
            todo_title = todo.get('title', 'Untitled')
            heading_title = heading.get('title', 'Untitled')
            result = f"✓ Moved '{todo_title}' under heading '{heading_title}'"
            
            log_operation_end(f"manage-heading ({action})", True, time.time() - start_time)
            return result
        
    except Exception as e:
        logger.error(f"Error in manage-heading ({action}): {str(e)}")
        log_operation_end(f"manage-heading ({action})", False, time.time() - start_time)
        return _error_result(f"Error managing heading: {str(e)}")


# ============================================================================
# DYNAMIC TOOL MANAGEMENT CONTROL
# ============================================================================

@mcp.tool(name="enable-advanced-features", annotations=UPDATE_ANNOTATIONS)
async def enable_advanced_features(
    category: str,
    ctx: Optional[Context] = None
) -> str:
    """
    Enable advanced tool categories (v3.0.0 dynamic tool management).
    
    By default, only core tools are visible. Use this tool to enable additional features:
    - analytics: 9 productivity analytics tools (stats, velocity, health monitoring)
    - checklists: 4 checklist management tools
    - structure: 2 project structure tools (headings, organization)
    - all: Enable all advanced features
    
    Args:
        category: Which category to enable - 'analytics', 'checklists', 'structure', 'all'
    
    Returns:
        List of newly enabled tools with category status
    
    Examples:
        enable_advanced_features("analytics")  # Enable 9 analytics tools
        enable_advanced_features("all")  # Enable everything
    """
    import time
    start_time = time.time()
    log_operation_start(f"enable-advanced-features ({category})")
    
    # Validate category
    valid_categories = ["analytics", "checklists", "structure", "all"]
    if category not in valid_categories:
        log_operation_end(f"enable-advanced-features ({category})", False, time.time() - start_time)
        return f"Error: Invalid category '{category}'. Must be one of: {', '.join(valid_categories)}"
    
    try:
        # Enable the category
        enabled_count = enable_tool_category(category)
        
        # Build result message
        result_lines = [f"✅ Advanced Features Enabled: {category}"]
        result_lines.append(f"\n📊 {enabled_count} tools now available")
        
        if category == "all":
            result_lines.append("\n🔬 Analytics Tools:")
            result_lines.append("   • get-productivity-stats")
            result_lines.append("   • get-project-velocity")
            result_lines.append("   • get-time-to-completion")
            result_lines.append("   • get-tag-productivity")
            result_lines.append("   • check-stalled-projects")
            result_lines.append("   • get-project-health-report")
            result_lines.append("   • analyze-tag-relationships")
            result_lines.append("   • suggest-tags")
            result_lines.append("   • parse-natural-date")
            
            result_lines.append("\n☑️  Checklist Tools:")
            result_lines.append("   • get-checklist-items")
            result_lines.append("   • add-checklist-item")
            result_lines.append("   • update-checklist-item")
            result_lines.append("   • get-todos-with-checklists")
            
            result_lines.append("\n📐 Structure Tools:")
            result_lines.append("   • get-project-structure")
            result_lines.append("   • (manage-heading is always available)")
        
        elif category == "analytics":
            result_lines.append("\n🔬 Analytics Tools Enabled:")
            result_lines.append("   • get-productivity-stats - Overall completion metrics")
            result_lines.append("   • get-project-velocity - Time-series completion tracking")
            result_lines.append("   • get-time-to-completion - Average completion time analysis")
            result_lines.append("   • get-tag-productivity - Tag-based productivity rankings")
            result_lines.append("   • check-stalled-projects - Identify inactive projects")
            result_lines.append("   • get-project-health-report - Comprehensive health scoring")
            result_lines.append("   • analyze-tag-relationships - Co-occurrence patterns")
            result_lines.append("   • suggest-tags - AI-powered tag recommendations")
            result_lines.append("   • parse-natural-date - Natural language date parsing")
        
        elif category == "checklists":
            result_lines.append("\n☑️  Checklist Tools Enabled:")
            result_lines.append("   • get-checklist-items - View checklist items for a todo")
            result_lines.append("   • add-checklist-item - Add items to checklists")
            result_lines.append("   • update-checklist-item - Replace entire checklist")
            result_lines.append("   • get-todos-with-checklists - Find todos with checklists")
        
        elif category == "structure":
            result_lines.append("\n📐 Structure Tools Enabled:")
            result_lines.append("   • get-project-structure - Hierarchical project visualization")
            result_lines.append("   • (manage-heading is always available in core tools)")
        
        result_lines.append("\n💡 Use list-tools or tools/list to see all available tools")
        
        result = "\n".join(result_lines)
        log_operation_end(f"enable-advanced-features ({category})", True, time.time() - start_time)
        
        if ctx:
            await ctx.info(f"Enabled {enabled_count} {category} tools")
        
        return result
        
    except Exception as e:
        logger.error(f"Error enabling {category}: {str(e)}")
        log_operation_end(f"enable-advanced-features ({category})", False, time.time() - start_time)
        return _error_result(f"Error enabling advanced features: {str(e)}")


@mcp.tool(name="disable-advanced-features", annotations=UPDATE_ANNOTATIONS)
async def disable_advanced_features(
    category: str,
    ctx: Optional[Context] = None
) -> str:
    """
    Disable advanced tool categories (v3.0.0 dynamic tool management).
    
    Args:
        category: Which category to disable - 'analytics', 'checklists', 'structure', 'all'
    
    Returns:
        Confirmation message with disabled tool count
    
    Examples:
        disable_advanced_features("analytics")
        disable_advanced_features("all")
    """
    import time
    start_time = time.time()
    log_operation_start(f"disable-advanced-features ({category})")
    
    # Validate category
    valid_categories = ["analytics", "checklists", "structure", "all"]
    if category not in valid_categories:
        log_operation_end(f"disable-advanced-features ({category})", False, time.time() - start_time)
        return f"Error: Invalid category '{category}'. Must be one of: {', '.join(valid_categories)}"
    
    try:
        # Disable the category
        disabled_count = disable_tool_category(category)
        
        result = f"✓ Disabled {disabled_count} {category} tools"
        log_operation_end(f"disable-advanced-features ({category})", True, time.time() - start_time)
        
        if ctx:
            await ctx.info(f"Disabled {disabled_count} {category} tools")
        
        return result
        
    except Exception as e:
        logger.error(f"Error disabling {category}: {str(e)}")
        log_operation_end(f"disable-advanced-features ({category})", False, time.time() - start_time)
        return _error_result(f"Error disabling advanced features: {str(e)}")


@mcp.tool(name="get-tool-categories", annotations=READ_ONLY_ANNOTATIONS)
async def get_tool_categories(
    ctx: Optional[Context] = None
) -> str:
    """
    Get status of all tool categories (v3.0.0 dynamic tool management).
    
    Shows which advanced features are enabled and how many tools in each category.
    
    Returns:
        Status summary of all tool categories
    
    Example:
        get_tool_categories()
    """
    import time
    start_time = time.time()
    log_operation_start("get-tool-categories")
    
    try:
        status = get_category_status()
        
        result_lines = ["📊 Tool Categories Status"]
        
        for category, info in status.items():
            status_icon = "✅" if info["enabled"] else "⏸️"
            result_lines.append(f"\n{status_icon} {category.capitalize()}: {info['tool_count']} tools")
            result_lines.append(f"   Status: {'ENABLED' if info['enabled'] else 'DISABLED'}")
        
        result_lines.append("\n💡 Use enable-advanced-features(category) to enable tools")
        result_lines.append("   Categories: analytics, checklists, structure, all")
        
        result = "\n".join(result_lines)
        log_operation_end("get-tool-categories", True, time.time() - start_time)
        return result
        
    except Exception as e:
        logger.error(f"Error getting tool categories: {str(e)}")
        log_operation_end("get-tool-categories", False, time.time() - start_time)
        return _error_result(f"Error getting tool categories: {str(e)}")


# ============================================================================
# ORIGINAL TOOLS (Deprecated in v3.0.0 - kept for backward compatibility)
# Use composite tools above for new code
# ============================================================================

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

@mcp.tool(
    name="add-todo-interactive",
    annotations=ADD_ANNOTATIONS,
    meta={"requires_elicitation": True, "alternative_tool": "add-todo"}
)
async def add_todo_interactive(ctx: Context) -> str:
    """
    ⚠️ REQUIRES ELICITATION SUPPORT - Not currently supported in Claude Desktop
    
    Create a new todo interactively with step-by-step guidance
    
    This tool uses interactive elicitation to guide you through creating a todo,
    asking for each piece of information step by step. This is especially useful
    when you want guidance on what information to provide.
    
    **Alternative:** Use `add-todo` tool instead (provide all parameters directly)
    
    The tool will ask for:
    1. Title (required)
    2. Notes (optional)
    3. When to schedule (optional: today, tomorrow, evening, anytime, someday, or YYYY-MM-DD)
    4. Deadline (optional: YYYY-MM-DD)
    5. Tags (optional: comma-separated list)
    
    **Why This May Fail:**
    This tool requires MCP clients to implement the `elicitation/create` method.
    Claude Desktop does not currently support this (error: "Method not found").
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

@mcp.tool(
    name="bulk-complete-todos",
    annotations=TOOL_ANNOTATIONS["bulk-complete-todos"],
    meta={"requires_elicitation": True, "alternative_tool": "update-todo"}
)
async def bulk_complete_todos(ctx: Context) -> str:
    """
    ⚠️ REQUIRES ELICITATION SUPPORT - Not currently supported in Claude Desktop
    
    Complete multiple todos at once with interactive preview and confirmation
    
    This tool provides a safe way to batch-complete todos by:
    1. Asking what criteria to filter by (tag, project, area, or all inbox items)
    2. Showing a preview of matching incomplete todos
    3. Confirming before making changes
    4. Providing progress updates during execution
    
    **Alternative:** Use `update-todo` for individual todo completion
    
    This is useful for:
    - Completing all todos with a specific tag (e.g., "quick-wins")
    - Marking an entire project complete
    - Clearing out inbox items
    - Bulk operations with safety guardrails
    
    **Why This May Fail:**
    This tool requires MCP clients to implement the `elicitation/create` method.
    Claude Desktop does not currently support this (error: "Method not found").
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

@mcp.tool(
    name="bulk-schedule-todos",
    annotations=TOOL_ANNOTATIONS["bulk-schedule-todos"],
    meta={"requires_elicitation": True, "alternative_tool": "update-todo"}
)
async def bulk_schedule_todos(ctx: Context) -> str:
    """
    ⚠️ REQUIRES ELICITATION SUPPORT - Not currently supported in Claude Desktop
    
    Schedule multiple todos at once using filters (interactive)
    
    This is an interactive bulk operation that:
    1. Asks for filter criteria (tag, project, area, or list)
    2. Fetches matching incomplete todos
    3. Shows preview of items to be scheduled
    4. Asks for schedule destination
    5. Requires explicit confirmation ("yes")
    6. Executes batch scheduling with progress updates
    
    **Alternative:** Use `update-todo` with `when` parameter for individual scheduling
    
    Safety features:
    - Preview before execution (first 10 items shown)
    - Explicit confirmation required
    - 100-item batch limit
    - Progress reporting every 10 items
    - Continues on individual failures
    
    **Why This May Fail:**
    This tool requires MCP clients to implement the `elicitation/create` method.
    Claude Desktop does not currently support this (error: "Method not found").
    
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

@mcp.tool(
    name="bulk-tag-todos",
    annotations=TOOL_ANNOTATIONS["bulk-tag-todos"],
    meta={"requires_elicitation": True, "alternative_tool": "update-todo"}
)
async def bulk_tag_todos(ctx: Context) -> str:
    """
    ⚠️ REQUIRES ELICITATION SUPPORT - Not currently supported in Claude Desktop
    
    Add or remove tags from multiple todos at once (interactive)
    
    This is an interactive bulk operation that:
    1. Asks for filter criteria (tag, project, area, or list)
    2. Fetches matching incomplete todos
    3. Shows preview of items to be tagged
    4. Asks for tag operation (add or remove)
    5. Asks for tag names (comma-separated)
    6. Requires explicit confirmation ("yes")
    7. Executes batch tagging with progress updates
    
    **Alternative:** Use `update-todo` with `tags` parameter for individual tag operations
    
    Safety features:
    - Preview before execution (first 10 items shown)
    - Explicit confirmation required
    - 100-item batch limit
    - Progress reporting every 10 items
    - Continues on individual failures
    
    **Why This May Fail:**
    This tool requires MCP clients to implement the `elicitation/create` method.
    Claude Desktop does not currently support this (error: "Method not found").
    
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

@mcp.tool(
    name="bulk-move-todos",
    annotations=TOOL_ANNOTATIONS["bulk-move-todos"],
    meta={"requires_elicitation": True, "alternative_tool": "move-item-to-project"}
)
async def bulk_move_todos(ctx: Context) -> str:
    """
    ⚠️ REQUIRES ELICITATION SUPPORT - Not currently supported in Claude Desktop
    
    Move multiple todos to a different project or area (interactive)
    
    This is an interactive bulk operation that:
    1. Asks for filter criteria (tag, project, area, or list)
    2. Fetches matching incomplete todos
    3. Shows preview of items to be moved
    4. Asks for destination (project, area, or inbox)
    5. Requires explicit confirmation ("yes")
    6. Executes batch move with progress updates
    
    **Alternative:** Use `move-item-to-project` for individual todo moves
    
    Safety features:
    - Preview before execution (first 10 items shown)
    - Explicit confirmation required
    - 100-item batch limit
    - Progress reporting every 10 items
    - Continues on individual failures
    
    **Why This May Fail:**
    This tool requires MCP clients to implement the `elicitation/create` method.
    Claude Desktop does not currently support this (error: "Method not found").
    
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

@mcp.tool(
    name="schedule-assistant",
    annotations=TOOL_ANNOTATIONS["schedule-assistant"],
    meta={"requires_elicitation": True, "alternative_tool": "update-todo"}
)
async def schedule_assistant(ctx: Context) -> str:
    """
    ⚠️ REQUIRES ELICITATION SUPPORT - Not currently supported in Claude Desktop
    
    Smart scheduling assistant with natural language support (interactive)
    
    This is an advanced interactive tool that:
    1. Helps you select todos to schedule
    2. Accepts natural language dates ("tomorrow at 5pm", "next Monday", "in 3 days")
    3. Shows preview with parsed dates
    4. Handles multiple todos at once
    5. Provides conflict warnings if overloading a day
    
    **Alternative:** Use `update-todo` with `when` parameter (accepts: today, tomorrow, evening, anytime, someday, YYYY-MM-DD)
    
    Natural language examples:
    - "tomorrow at 2pm"
    - "next Monday"
    - "in 3 days"
    - "next week Friday"
    - "today evening" → This Evening
    - "anytime" → Anytime list
    - "someday" → Someday list
    
    **Why This May Fail:**
    This tool requires MCP clients to implement the `elicitation/create` method.
    Claude Desktop does not currently support this (error: "Method not found").
    
    Returns:
        Summary of scheduled todos with parsed dates
    """
    import dateparser
    from datetime import datetime, date
    
    try:
        await ctx.info("🗓️ Smart Scheduling Assistant - Let's schedule some todos!")
        
        # Step 1: Get filter or select specific todos
        selection_method = await ctx.elicit(
            "\nHow would you like to select todos to schedule?\n"
            "  1. Filter (tag:NAME, project:UUID, area:UUID, inbox, today, upcoming)\n"
            "  2. Specific UUIDs (comma-separated todo IDs)\n"
            "Selection method (1 or 2): ",
            response_type=str
        )
        
        if selection_method.action != "accept" or not selection_method.data:
            return "Operation cancelled"
        
        method = selection_method.data.strip()
        todos = []
        selection_description = ""
        
        if method == "1":
            # Filter-based selection
            filter_input = await ctx.elicit(
                "\nEnter filter criteria:\n"
                "  - tag:NAME (e.g., tag:work)\n"
                "  - project:UUID\n"
                "  - area:UUID\n"
                "  - inbox, today, upcoming\n"
                "Filter: ",
                response_type=str
            )
            
            if filter_input.action != "accept" or not filter_input.data:
                return "Operation cancelled"
            
            filter_str = filter_input.data.strip().lower()
            
            if filter_str.startswith("tag:"):
                tag_name = filter_str[4:].strip()
                all_todos = things.todos()
                todos = [t for t in all_todos if t.get('status') == 'incomplete' 
                        and tag_name in [tag.get('title', '').lower() for tag in t.get('tags', [])]]
                selection_description = f"tag '{tag_name}'"
            elif filter_str.startswith("project:"):
                project_uuid = filter_str[8:].strip()
                project = things.get(project_uuid)
                if not project or not isinstance(project, dict):
                    return _error_result(f"Project not found: {project_uuid}")
                todos = things.todos(project=project_uuid)
                todos = [t for t in todos if t.get('status') == 'incomplete']
                selection_description = f"project '{project.get('title', project_uuid)}'"
            elif filter_str.startswith("area:"):
                area_uuid = filter_str[5:].strip()
                area = things.get(area_uuid)
                if not area or not isinstance(area, dict):
                    return _error_result(f"Area not found: {area_uuid}")
                todos = things.todos(area=area_uuid)
                todos = [t for t in todos if t.get('status') == 'incomplete']
                selection_description = f"area '{area.get('title', area_uuid)}'"
            elif filter_str == "inbox":
                todos = things.inbox()
                todos = [t for t in todos if t.get('status') == 'incomplete']
                selection_description = "Inbox"
            elif filter_str == "today":
                todos = things.today()
                todos = [t for t in todos if t.get('status') == 'incomplete']
                selection_description = "Today"
            elif filter_str == "upcoming":
                todos = things.upcoming()
                todos = [t for t in todos if t.get('status') == 'incomplete']
                selection_description = "Upcoming"
            else:
                return _error_result(f"Invalid filter: {filter_str}")
                
        elif method == "2":
            # UUID-based selection
            uuid_input = await ctx.elicit(
                "\nEnter todo UUIDs (comma-separated):\nUUIDs: ",
                response_type=str
            )
            
            if uuid_input.action != "accept" or not uuid_input.data:
                return "Operation cancelled"
            
            uuids = [u.strip() for u in uuid_input.data.split(",") if u.strip()]
            for uuid in uuids:
                todo = things.get(uuid)
                if todo and isinstance(todo, dict):
                    todos.append(todo)
            
            selection_description = f"{len(todos)} specific todo(s)"
        else:
            return _error_result("Invalid selection method. Use 1 or 2.")
        
        if not todos:
            return f"No todos found for: {selection_description}"
        
        # Step 2: Show preview of selected todos
        total_count = len(todos)
        preview_todos = todos[:10]
        
        preview = f"\n📋 Selected {total_count} todo(s) from {selection_description}:\n\n"
        for i, todo in enumerate(preview_todos, 1):
            title = todo.get('title', 'Untitled')
            current_when = todo.get('start_date', 'Not scheduled')
            preview += f"  {i}. {title}\n     Current: {current_when}\n"
        
        if total_count > 10:
            preview += f"\n  ... and {total_count - 10} more\n"
        
        await ctx.info(preview)
        
        # Step 3: Get natural language date
        date_input = await ctx.elicit(
            "\n🗓️ When should these todos be scheduled?\n"
            "Examples:\n"
            "  - 'tomorrow at 2pm'\n"
            "  - 'next Monday'\n"
            "  - 'in 3 days'\n"
            "  - 'today evening' (for This Evening)\n"
            "  - 'anytime' or 'someday' (for lists)\n"
            "\nSchedule to: ",
            response_type=str
        )
        
        if date_input.action != "accept" or not date_input.data:
            return "Operation cancelled"
        
        date_str = date_input.data.strip().lower()
        
        # Parse natural language date
        schedule_param = None
        schedule_description = date_str
        parsed_date = None
        
        # Handle special keywords first
        if date_str in ["anytime", "any time"]:
            schedule_param = "anytime"
            schedule_description = "Anytime"
        elif date_str in ["someday", "some day"]:
            schedule_param = "someday"
            schedule_description = "Someday"
        elif date_str in ["today evening", "this evening", "tonight"]:
            schedule_param = "evening"
            schedule_description = "This Evening"
        elif date_str == "today":
            schedule_param = "today"
            schedule_description = "Today"
        elif date_str == "tomorrow":
            schedule_param = "tomorrow"
            schedule_description = "Tomorrow"
        else:
            # Try to parse as natural language date
            parsed_date = dateparser.parse(
                date_str,
                settings={
                    'PREFER_DATES_FROM': 'future',
                    'RELATIVE_BASE': datetime.now()
                }
            )
            
            if parsed_date:
                # Convert to YYYY-MM-DD format
                schedule_param = parsed_date.strftime("%Y-%m-%d")
                schedule_description = parsed_date.strftime("%A, %B %d, %Y")
                
                # Warn if date is in the past
                if parsed_date.date() < date.today():
                    await ctx.warning(
                        f"⚠️ Parsed date is in the past: {schedule_description}\n"
                        f"   This might not be what you intended."
                    )
            else:
                return _error_result(
                    f"Could not parse date: '{date_str}'\n"
                    f"Try formats like: tomorrow, next Monday, in 3 days, 2025-11-15"
                )
        
        # Step 4: Check for conflicts (if scheduling to a specific date)
        if parsed_date and schedule_param not in ["anytime", "someday", "evening"]:
            # Check how many items are already scheduled for that day
            existing_today_count = len([t for t in things.today() 
                                       if t.get('start_date') == schedule_param])
            
            if existing_today_count + total_count > 20:
                await ctx.warning(
                    f"⚠️ High workload warning:\n"
                    f"   Already {existing_today_count} items scheduled for {schedule_description}\n"
                    f"   Adding {total_count} more = {existing_today_count + total_count} total"
                )
        
        # Step 5: Confirmation
        confirmation = await ctx.elicit(
            f"\n📅 Ready to schedule {total_count} todo(s) to: {schedule_description}\n"
            f"   Source: {selection_description}\n"
            f"   Type 'yes' to confirm: ",
            response_type=str
        )
        
        if confirmation.action != "accept" or confirmation.data.strip().lower() != "yes":
            return "Operation cancelled by user."
        
        # Step 6: Execute batch scheduling
        await ctx.info(f"Scheduling {total_count} todos to {schedule_description}...")
        
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
        
        # Invalidate caches
        cache_keys = ["get-inbox", "get-today", "get-upcoming", "get-anytime", "get-someday", "get-todos"]
        invalidate_caches_for(cache_keys)
        
        # Final report
        result = "✓ Smart scheduling complete!\n"
        result += f"  Successfully scheduled: {scheduled_count} todos\n"
        if failed_count > 0:
            result += f"  Failed: {failed_count} todos\n"
        result += f"  Destination: {schedule_description}\n"
        result += f"  Source: {selection_description}\n"
        if parsed_date:
            result += f"  Parsed from: '{date_str}'"
        
        return result
        
    except Exception as e:
        logger.error(f"Error in schedule assistant: {str(e)}")
        return _error_result(f"Error scheduling todos: {str(e)}")

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
    
    This is the primary tool for modifying todos. All parameters are optional - 
    only provide the ones you want to change.

    Args:
        id: ID of the todo to update
        title: New title for the todo
        notes: New notes/description
        when: Schedule the todo - supports:
              - 'today': Schedule for today
              - 'tomorrow': Schedule for tomorrow  
              - 'evening': Schedule for this evening
              - 'anytime': Move to Anytime list
              - 'someday': Move to Someday list
              - YYYY-MM-DD: Schedule for specific date (e.g., '2025-12-25')
              - Empty string: Move to Inbox (unschedule)
        deadline: Set a deadline - supports:
                 - YYYY-MM-DD: Specific date (e.g., '2025-12-31')
                 - 'today': Today's date
                 - 'tomorrow': Tomorrow's date
                 - Empty string: Clear deadline
        tags: New tags (replaces existing tags). Missing tags will be created automatically.
        completed: Set to True to mark as completed
        canceled: Set to True to mark as canceled
    
    Examples:
        # Schedule for today
        update_todo(id="ABC123", when="today")
        
        # Set deadline to specific date
        update_todo(id="ABC123", deadline="2025-12-31")
        
        # Update multiple fields at once
        update_todo(id="ABC123", when="tomorrow", deadline="2025-12-15", tags=["urgent", "work"])
        
        # Complete a todo
        update_todo(id="ABC123", completed=True)
        
        # Unschedule (move to Inbox)
        update_todo(id="ABC123", when="")
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

        # Execute the search URL command via things.py API
        results = things.search(query=query)

        if not results:
            return _error_result(f"Error: Failed to search for '{query}'")

        return f"Successfully searched for '{query}' in Things - found {len(results)} results"
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

# =============================================================================
# PROJECT TEMPLATE TOOLS
# =============================================================================

@mcp.tool(
    name="create-project-template",
    annotations=TOOL_ANNOTATIONS["create-project-template"],
    meta={"requires_elicitation": True, "alternative_tool": "add-project"}
)
async def create_project_template(ctx: Context) -> str:
    """
    ⚠️ REQUIRES ELICITATION SUPPORT - Not currently supported in Claude Desktop
    
    Create a reusable project template with interactive guidance
    
    This tool helps you save project structures as templates that can be reused later.
    You'll be guided through specifying:
    - Template name (for identification)
    - Project title
    - Project notes (optional)
    - Tags (optional)
    - Area (optional)
    - Todo items to include (optional)
    
    **Alternative:** Use `add-project` to create reference projects that you can copy manually
    
    Templates are stored persistently and can be applied later with variable substitution.
    
    Example use cases:
    - "Weekly Review" template with recurring checklist items
    - "New Client Onboarding" with standard tasks
    - "Blog Post" with writing workflow steps
    - "Event Planning" with preparation tasks
    
    **Why This May Fail:**
    This tool requires MCP clients to implement the `elicitation/create` method.
    Claude Desktop does not currently support this (error: "Method not found").
    """
    try:
        await ctx.info("🎨 Creating a new project template...")
        
        # Step 1: Template name
        result = await ctx.elicit(
            "What should we call this template? (alphanumeric, hyphens, underscores only)",
            response_type=str
        )
        if result.action != "accept":
            return "Template creation cancelled"
        
        template_name = result.data.strip()
        if not template_name:
            return "Error: Template name cannot be empty"
        
        # Check if template already exists
        if template_exists(template_name):
            result = await ctx.elicit(
                f"Template '{template_name}' already exists. Overwrite it? (yes/no)",
                response_type=str
            )
            if result.action != "accept" or result.data.lower() not in ["yes", "y"]:
                return "Template creation cancelled"
        
        # Step 2: Project title
        result = await ctx.elicit(
            "What is the project title? (you can use {{variables}} for substitution later)",
            response_type=str
        )
        if result.action != "accept":
            return "Template creation cancelled"
        
        project_title = result.data.strip()
        if not project_title:
            return "Error: Project title cannot be empty"
        
        # Step 3: Project notes (optional)
        result = await ctx.elicit(
            "Add project notes? (optional, press Enter to skip)",
            response_type=str
        )
        project_notes = result.data.strip() if result.action == "accept" and result.data else ""
        
        # Step 4: Tags (optional)
        result = await ctx.elicit(
            "Add tags? (comma-separated, optional, press Enter to skip)",
            response_type=str
        )
        tags_str = result.data.strip() if result.action == "accept" and result.data else ""
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()] if tags_str else []
        
        # Step 5: Area (optional)
        result = await ctx.elicit(
            "Assign to an area? (area name, optional, press Enter to skip)",
            response_type=str
        )
        area_name = result.data.strip() if result.action == "accept" and result.data else ""
        area_id = None
        
        if area_name:
            # Try to find the area
            areas = things.areas()
            matching_area = next((a for a in areas if a.get('title', '').lower() == area_name.lower()), None)
            if matching_area:
                area_id = matching_area['uuid']
                await ctx.info(f"✓ Found area: {matching_area['title']}")
            else:
                await ctx.warning(f"Area '{area_name}' not found. Template will be saved without area assignment.")
        
        # Step 6: Todo items (optional)
        result = await ctx.elicit(
            "Add todo items? Enter one per line (press Enter twice when done, or skip to add none)",
            response_type=str
        )
        todos_str = result.data.strip() if result.action == "accept" and result.data else ""
        todos = [todo.strip() for todo in todos_str.split("\n") if todo.strip()] if todos_str else []
        
        # Build template data
        template_data = {
            "title": project_title,
            "notes": project_notes,
            "tags": tags,
            "area_id": area_id,
            "area_name": area_name if area_name else None,
            "todos": todos
        }
        
        # Save template
        await ctx.info(f"💾 Saving template '{template_name}'...")
        save_template(template_name, template_data)
        
        # Build summary
        summary = f"✓ Successfully created template: {template_name}\n\n"
        summary += f"Project Title: {project_title}\n"
        if project_notes:
            summary += f"Notes: {project_notes[:100]}{'...' if len(project_notes) > 100 else ''}\n"
        if tags:
            summary += f"Tags: {', '.join(tags)}\n"
        if area_name:
            summary += f"Area: {area_name}\n"
        if todos:
            summary += f"Todos: {len(todos)} items\n"
            for i, todo in enumerate(todos[:5], 1):
                summary += f"  {i}. {todo}\n"
            if len(todos) > 5:
                summary += f"  ... and {len(todos) - 5} more\n"
        
        summary += "\nUse 'apply-project-template' to create projects from this template."
        
        return summary
        
    except Exception as e:
        logger.error(f"Error creating project template: {str(e)}")
        return f"Error creating template: {str(e)}"

@mcp.tool(name="list-project-templates", annotations=TOOL_ANNOTATIONS["list-project-templates"])
def list_project_templates() -> str:
    """
    List all saved project templates
    
    Shows all templates with their metadata:
    - Template name
    - Project title
    - Number of todos
    - Tags
    - Area (if assigned)
    - Created date
    - Version
    
    Use this to browse available templates before applying them.
    """
    try:
        templates = list_templates()
        
        if not templates:
            return "No project templates found.\n\nUse 'create-project-template' to create your first template."
        
        # Build formatted list
        result = f"📋 Found {len(templates)} project template(s):\n\n"
        
        for i, template in enumerate(templates, 1):
            result += f"{i}. **{template['name']}**\n"
            result += f"   Title: {template['title']}\n"
            
            if template.get('todo_count', 0) > 0:
                result += f"   Todos: {template['todo_count']} items\n"
            
            if template.get('tags'):
                result += f"   Tags: {', '.join(template['tags'])}\n"
            
            if template.get('area_name'):
                result += f"   Area: {template['area_name']}\n"
            
            result += f"   Created: {template.get('created', 'Unknown')}\n"
            result += f"   Version: {template.get('version', '1.0')}\n"
            result += "\n"
        
        result += "Use 'apply-project-template' to create a project from any of these templates."
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing project templates: {str(e)}")
        return _error_result(f"Error listing templates: {str(e)}")

@mcp.tool(
    name="apply-project-template",
    annotations=TOOL_ANNOTATIONS["apply-project-template"],
    meta={"requires_elicitation": True, "alternative_tool": "add-project"}
)
async def apply_project_template(ctx: Context) -> str:
    """
    ⚠️ REQUIRES ELICITATION SUPPORT - Not currently supported in Claude Desktop
    
    Create a new project from a saved template with variable substitution
    
    This tool lets you apply a template to create a new project. You can provide
    values for any {{variables}} in the template (like {{client_name}} or {{date}}).
    
    The tool will:
    1. Ask which template to use
    2. Show template details
    3. Ask for variable values (if template has {{variables}})
    4. Create the project with all todos
    5. Return the project UUID for reference
    
    **Alternative:** Create reference projects with `add-project` and manually copy their structure
    
    Example use cases:
    - Apply "Weekly Review" template for current week
    - Use "New Client" template with client name substitution
    - Create "Event Planning" project with specific event details
    
    **Why This May Fail:**
    This tool requires MCP clients to implement the `elicitation/create` method.
    Claude Desktop does not currently support this (error: "Method not found").
    """
    try:
        # Ensure Things app is running
        if not app_state.update_app_state():
            if not launch_things():
                return _error_result("Error: Unable to launch Things app")
        
        await ctx.info("📋 Applying a project template...")
        
        # Step 1: Get template name
        result = await ctx.elicit(
            "Which template would you like to apply? (template name)",
            response_type=str
        )
        if result.action != "accept":
            return "Template application cancelled"
        
        template_name = result.data.strip()
        if not template_name:
            return _error_result("Template name cannot be empty")
        
        # Load template
        await ctx.info(f"Loading template '{template_name}'...")
        template_data = get_template(template_name)
        
        if not template_data:
            return _error_result(f"Template '{template_name}' not found. Use 'list-project-templates' to see available templates.")
        
        # Extract template fields
        title_template = template_data.get("title", "Untitled Project")
        notes_template = template_data.get("notes", "")
        tags = template_data.get("tags", [])
        area_id = template_data.get("area_id")
        todos_templates = template_data.get("todos", [])
        
        # Show template preview
        preview = f"Template: {template_name}\n"
        preview += f"Title: {title_template}\n"
        if notes_template:
            preview += f"Notes: {notes_template[:100]}{'...' if len(notes_template) > 100 else ''}\n"
        if tags:
            preview += f"Tags: {', '.join(tags)}\n"
        if area_id:
            preview += f"Area: {template_data.get('area_name', 'Assigned')}\n"
        if todos_templates:
            preview += f"Todos: {len(todos_templates)} items\n"
        
        await ctx.info(preview)
        
        # Step 2: Check for variables and get substitutions
        import re
        variables = set()
        
        # Find all {{variables}} in title, notes, and todos
        for text in [title_template, notes_template] + todos_templates:
            if text:
                variables.update(re.findall(r'\{\{(\w+)\}\}', text))
        
        substitutions = {}
        if variables:
            await ctx.info(f"This template uses variables: {', '.join(sorted(variables))}")
            
            for var in sorted(variables):
                result = await ctx.elicit(
                    f"Value for {{{{{var}}}}}? (press Enter to leave as-is)",
                    response_type=str
                )
                if result.action == "accept" and result.data:
                    substitutions[var] = result.data.strip()
        
        # Step 3: Apply substitutions
        def substitute_vars(text: str) -> str:
            """Replace {{variables}} with provided values"""
            if not text:
                return text
            result_text = text
            for var, value in substitutions.items():
                result_text = result_text.replace(f"{{{{{var}}}}}", value)
            return result_text
        
        final_title = substitute_vars(title_template)
        final_notes = substitute_vars(notes_template)
        final_todos = [substitute_vars(todo) for todo in todos_templates]
        
        # Step 4: Confirm creation
        result = await ctx.elicit(
            f"Create project '{final_title}' with {len(final_todos)} todo(s)? (yes/no)",
            response_type=str
        )
        if result.action != "accept" or result.data.lower() not in ["yes", "y"]:
            return "Template application cancelled"
        
        # Step 5: Create project
        await ctx.info(f"Creating project: {final_title}")
        
        # Build project URL with tags
        project_url = add_project(
            title=final_title,
            notes=final_notes,
            tags=tags,
            area_id=area_id,
            todos=None  # We'll add todos separately for better control
        )
        
        logger.debug(f"Add project URL: {project_url}")
        success = execute_url(project_url)
        
        if not success:
            return _error_result("Error: Failed to create project")
        
        # Wait a moment for project creation
        import time
        time.sleep(0.5)
        
        # Find the newly created project (it should be the most recent)
        projects = things.projects()
        new_project = None
        
        # Look for project with matching title (created in last few seconds)
        for project in projects:
            if project.get('title') == final_title:
                new_project = project
                break
        
        if not new_project:
            await ctx.warning("Project created but couldn't find UUID. Todos may need to be added manually.")
            project_uuid = None
        else:
            project_uuid = new_project['uuid']
            await ctx.info(f"✓ Project created with UUID: {project_uuid}")
        
        # Step 6: Add todos to project
        if final_todos and project_uuid:
            await ctx.info(f"Adding {len(final_todos)} todo(s)...")
            
            todos_created = 0
            for i, todo_title in enumerate(final_todos, 1):
                todo_url = add_todo(
                    title=todo_title,
                    list_id=project_uuid,
                    tags=None,
                    notes=None,
                    when=None,
                    deadline=None,
                    checklist_items=None,
                    list_title=None,
                    heading=None
                )
                
                if execute_url(todo_url):
                    todos_created += 1
                    if i % 5 == 0:  # Progress update every 5 todos
                        await ctx.info(f"Progress: {i}/{len(final_todos)} todos created")
                else:
                    logger.warning(f"Failed to create todo: {todo_title}")
            
            await ctx.info(f"✓ Created {todos_created}/{len(final_todos)} todos")
        
        # Invalidate caches
        invalidate_caches_for(["get-projects", "get-todos", "get-inbox"])
        
        # Build success summary
        summary = f"✓ Successfully applied template '{template_name}'\n\n"
        summary += f"Project: {final_title}\n"
        if project_uuid:
            summary += f"UUID: {project_uuid}\n"
        if tags:
            summary += f"Tags: {', '.join(tags)}\n"
        if final_todos:
            summary += f"Todos: {len(final_todos)} items created\n"
        if substitutions:
            summary += "\nVariables applied:\n"
            for var, value in substitutions.items():
                summary += f"  {var} → {value}\n"
        
        return summary
        
    except Exception as e:
        logger.error(f"Error applying project template: {str(e)}")
        return _error_result(f"Error applying template: {str(e)}")

@mcp.tool(
    name="update-project-template",
    annotations=TOOL_ANNOTATIONS["update-project-template"],
    meta={"requires_elicitation": True, "alternative_tool": "list-project-templates"}
)
async def update_project_template(ctx: Context) -> str:
    """
    ⚠️ REQUIRES ELICITATION SUPPORT - Not currently supported in Claude Desktop
    
    Update an existing project template
    
    This tool lets you modify a saved template. You can update:
    - Project title
    - Project notes
    - Tags
    - Area assignment
    - Todo items
    
    The tool will:
    1. Ask which template to update
    2. Show current template details
    3. Ask which fields to modify
    4. Save the updated template
    
    **Alternative:** Use `list-project-templates` to view, then recreate with `add-project`
    
    Use this to refine templates based on experience or changing needs.
    
    **Why This May Fail:**
    This tool requires MCP clients to implement the `elicitation/create` method.
    Claude Desktop does not currently support this (error: "Method not found").
    """
    try:
        await ctx.info("✏️ Updating a project template...")
        
        # Step 1: Get template name
        result = await ctx.elicit(
            "Which template would you like to update? (template name)",
            response_type=str
        )
        if result.action != "accept":
            return "Template update cancelled"
        
        template_name = result.data.strip()
        if not template_name:
            return _error_result("Template name cannot be empty")
        
        # Load existing template
        await ctx.info(f"Loading template '{template_name}'...")
        template_data = get_template(template_name)
        
        if not template_data:
            return _error_result(f"Template '{template_name}' not found. Use 'list-project-templates' to see available templates.")
        
        # Show current template
        current = "Current template details:\n"
        current += f"Title: {template_data.get('title', 'Untitled')}\n"
        current += f"Notes: {template_data.get('notes', '(none)')[:100]}\n"
        current += f"Tags: {', '.join(template_data.get('tags', [])) or '(none)'}\n"
        current += f"Area: {template_data.get('area_name', '(none)')}\n"
        current += f"Todos: {len(template_data.get('todos', []))} items\n"
        
        await ctx.info(current)
        
        # Step 2: Update title?
        result = await ctx.elicit(
            f"New project title? (current: '{template_data.get('title')}', press Enter to keep)",
            response_type=str
        )
        new_title = result.data.strip() if result.action == "accept" and result.data else None
        if new_title:
            template_data['title'] = new_title
            await ctx.info(f"✓ Title updated to: {new_title}")
        
        # Step 3: Update notes?
        result = await ctx.elicit(
            "New project notes? (press Enter to keep current, type 'clear' to remove)",
            response_type=str
        )
        if result.action == "accept" and result.data:
            if result.data.strip().lower() == "clear":
                template_data['notes'] = ""
                await ctx.info("✓ Notes cleared")
            else:
                template_data['notes'] = result.data.strip()
                await ctx.info("✓ Notes updated")
        
        # Step 4: Update tags?
        result = await ctx.elicit(
            "New tags? (comma-separated, press Enter to keep current, type 'clear' to remove)",
            response_type=str
        )
        if result.action == "accept" and result.data:
            if result.data.strip().lower() == "clear":
                template_data['tags'] = []
                await ctx.info("✓ Tags cleared")
            else:
                new_tags = [tag.strip() for tag in result.data.split(",") if tag.strip()]
                template_data['tags'] = new_tags
                await ctx.info(f"✓ Tags updated to: {', '.join(new_tags)}")
        
        # Step 5: Update area?
        result = await ctx.elicit(
            "New area? (area name, press Enter to keep current, type 'clear' to remove)",
            response_type=str
        )
        if result.action == "accept" and result.data:
            if result.data.strip().lower() == "clear":
                template_data['area_id'] = None
                template_data['area_name'] = None
                await ctx.info("✓ Area removed")
            else:
                area_name = result.data.strip()
                areas = things.areas()
                matching_area = next((a for a in areas if a.get('title', '').lower() == area_name.lower()), None)
                if matching_area:
                    template_data['area_id'] = matching_area['uuid']
                    template_data['area_name'] = matching_area['title']
                    await ctx.info(f"✓ Area updated to: {matching_area['title']}")
                else:
                    await ctx.warning(f"Area '{area_name}' not found. Keeping current area.")
        
        # Step 6: Update todos?
        result = await ctx.elicit(
            "New todo list? (one per line, press Enter to keep current, type 'clear' to remove all)",
            response_type=str
        )
        if result.action == "accept" and result.data:
            if result.data.strip().lower() == "clear":
                template_data['todos'] = []
                await ctx.info("✓ Todos cleared")
            else:
                new_todos = [todo.strip() for todo in result.data.split("\n") if todo.strip()]
                template_data['todos'] = new_todos
                await ctx.info(f"✓ Todos updated ({len(new_todos)} items)")
        
        # Save updated template
        await ctx.info(f"💾 Saving updated template '{template_name}'...")
        save_template(template_name, template_data)
        
        # Build summary
        summary = f"✓ Successfully updated template: {template_name}\n\n"
        summary += f"Project Title: {template_data['title']}\n"
        if template_data.get('notes'):
            summary += f"Notes: {template_data['notes'][:100]}{'...' if len(template_data['notes']) > 100 else ''}\n"
        if template_data.get('tags'):
            summary += f"Tags: {', '.join(template_data['tags'])}\n"
        if template_data.get('area_name'):
            summary += f"Area: {template_data['area_name']}\n"
        if template_data.get('todos'):
            summary += f"Todos: {len(template_data['todos'])} items\n"
        
        return summary
        
    except Exception as e:
        logger.error(f"Error updating project template: {str(e)}")
        return _error_result(f"Error updating template: {str(e)}")

@mcp.tool(
    name="delete-project-template",
    annotations=TOOL_ANNOTATIONS["delete-project-template"],
    meta={"requires_elicitation": True, "alternative_tool": "list-project-templates"}
)
async def delete_project_template(ctx: Context) -> str:
    """
    ⚠️ REQUIRES ELICITATION SUPPORT - Not currently supported in Claude Desktop
    
    Delete a saved project template with confirmation
    
    This tool permanently removes a template from storage.
    
    The tool will:
    1. Ask which template to delete
    2. Show template details
    3. Require explicit "yes" confirmation
    4. Delete the template
    
    **Alternative:** Templates are stored in ~/.things-fastmcp/templates/ as JSON files
    
    Use this to clean up unused or outdated templates.
    This action cannot be undone.
    
    **Why This May Fail:**
    This tool requires MCP clients to implement the `elicitation/create` method.
    Claude Desktop does not currently support this (error: "Method not found").
    """
    try:
        await ctx.info("🗑️ Deleting a project template...")
        
        # Step 1: Get template name
        result = await ctx.elicit(
            "Which template would you like to delete? (template name)",
            response_type=str
        )
        if result.action != "accept":
            return "Template deletion cancelled"
        
        template_name = result.data.strip()
        if not template_name:
            return _error_result("Template name cannot be empty")
        
        # Load template to show details
        await ctx.info(f"Loading template '{template_name}'...")
        template_data = get_template(template_name)
        
        if not template_data:
            return _error_result(f"Template '{template_name}' not found. Use 'list-project-templates' to see available templates.")
        
        # Show template details before deletion
        details = f"Template to delete: {template_name}\n"
        details += f"Title: {template_data.get('title', 'Untitled')}\n"
        details += f"Todos: {len(template_data.get('todos', []))} items\n"
        if template_data.get('tags'):
            details += f"Tags: {', '.join(template_data['tags'])}\n"
        
        await ctx.warning(details)
        await ctx.warning("⚠️ This action cannot be undone!")
        
        # Step 2: Require explicit confirmation
        result = await ctx.elicit(
            "Type 'yes' to confirm deletion:",
            response_type=str
        )
        
        if result.action != "accept" or result.data.lower() != "yes":
            return "Template deletion cancelled"
        
        # Delete template
        await ctx.info(f"Deleting template '{template_name}'...")
        deleted = delete_template(template_name)
        
        if deleted:
            return f"✓ Successfully deleted template: {template_name}"
        else:
            return _error_result(f"Failed to delete template '{template_name}'")
        
    except Exception as e:
        logger.error(f"Error deleting project template: {str(e)}")
        return _error_result(f"Error deleting template: {str(e)}")


# ============================================================================
# ANALYTICS & INTELLIGENCE LAYER (Phase 3)
# ============================================================================

@mcp.tool(name="get-productivity-stats", annotations=TOOL_ANNOTATIONS["get-productivity-stats"])
@cached(ttl=300)  # 5 minute cache
async def get_productivity_stats(days: int = 30) -> str:
    """
    Get productivity statistics for the specified time period.
    
    Analyzes completion rates, trends, and top productive tags across
    all tasks to provide insights into your productivity patterns.
    
    Args:
        days: Number of days to analyze (default: 30)
        
    Returns:
        Formatted statistics with emoji indicators
        
    Examples:
        get_productivity_stats(30)  # Last 30 days
        get_productivity_stats(7)   # Last week
        get_productivity_stats(90)  # Last quarter
    """
    start_time = time.time()
    log_operation_start("get-productivity-stats")
    
    try:
        # Fetch data
        logbook = things.logbook()
        incomplete = things.todos()
        
        # Calculate stats
        stats = calculate_productivity_stats(
            days=days,
            logbook_items=logbook,
            incomplete_items=incomplete
        )
        
        # Format output
        result = f"""📊 Productivity Stats (Last {days} days)

✅ Completed: {stats.completed_count} tasks
📝 Incomplete: {stats.incomplete_count} tasks
📈 Completion Rate: {stats.completion_rate * 100:.1f}%
⏱️  Avg Time to Complete: {stats.avg_completion_hours / 24:.1f} days
⚠️  Overdue: {stats.overdue_count} tasks

📊 Trend: {stats.trend.capitalize()} {
    '📈' if stats.trend == 'improving' else '📉' if stats.trend == 'declining' else '➡️'
}

🏆 Most Productive Tags:"""
        
        if stats.top_productive_tags:
            for i, (tag, count) in enumerate(stats.top_productive_tags, 1):
                result += f"\n   {i}. {tag}: {count} tasks"
        else:
            result += "\n   (No tagged tasks)"
        
        # Add structured data for LLM parsing
        from dataclasses import asdict
        result += f"\n\n_Structured data: {asdict(stats)}_"
        
        log_operation_end("get-productivity-stats", True, time.time() - start_time)
        return result
        
    except Exception as e:
        logger.error(f"Error calculating productivity stats: {e}")
        return _error_result(f"Error calculating productivity stats: {str(e)}")


@mcp.tool(name="get-project-velocity", annotations=TOOL_ANNOTATIONS["get-project-velocity"])
async def get_project_velocity(
    project_uuid: str,
    interval: str = "weekly",
    periods: int = 4
) -> str:
    """
    Analyze project velocity (task completion rate over time).
    
    Tracks how quickly tasks are being completed in a project over
    multiple time periods to identify productivity trends.
    
    Args:
        project_uuid: Project UUID
        interval: Time interval - "daily", "weekly", or "monthly" (default: "weekly")
        periods: Number of periods to analyze (default: 4)
        
    Returns:
        Velocity chart with ASCII visualization and trend analysis
        
    Examples:
        get_project_velocity("PROJECT-UUID", "weekly", 4)  # Last 4 weeks
        get_project_velocity("PROJECT-UUID", "daily", 7)   # Last 7 days
        get_project_velocity("PROJECT-UUID", "monthly", 3) # Last 3 months
    """
    start_time = time.time()
    log_operation_start("get-project-velocity")
    
    try:
        # Get project with items
        project = things.get(project_uuid)
        if not project or not isinstance(project, dict):
            return _error_result(f"Project not found: {project_uuid}")
        
        # Get full items
        project_with_items = things.projects(uuid=project_uuid, include_items=True)
        if not project_with_items:
            return _error_result(f"Could not retrieve project items: {project_uuid}")
        
        # Calculate velocity
        velocity = calculate_project_velocity(
            project=project_with_items,  # type: ignore
            interval=interval,
            periods=periods
        )
        
        # Format output with ASCII chart
        result = f"""📈 Project Velocity: {velocity.project_title}

"""
        
        # Generate ASCII chart
        period_labels = []
        period_values = []
        for i, period in enumerate(velocity.periods, 1):
            label = f"{interval.capitalize()} {i}"
            period_labels.append(label)
            period_values.append(period.completed_count)
        
        chart = generate_ascii_chart(period_values, period_labels, max_width=40)
        result += chart + "\n\n"
        
        # Add statistics
        trend_emoji = "🚀" if velocity.trend == "accelerating" else "📉" if velocity.trend == "decelerating" else "➡️"
        result += f"Avg: {velocity.avg_velocity:.1f} tasks/{interval}\n"
        result += f"Trend: {velocity.trend.capitalize()} {trend_emoji}"
        
        # Add structured data
        from dataclasses import asdict
        result += f"\n\n_Structured data: {asdict(velocity)}_"
        
        log_operation_end("get-project-velocity", True, time.time() - start_time)
        return result
        
    except Exception as e:
        logger.error(f"Error calculating project velocity: {e}")
        return _error_result(f"Error calculating project velocity: {str(e)}")


@mcp.tool(name="get-time-to-completion", annotations=TOOL_ANNOTATIONS["get-time-to-completion"])
@cached(ttl=600)  # 10 minute cache
async def get_time_to_completion(
    group_by: str = "overall",
    limit: int = 100
) -> str:
    """
    Calculate average time to completion for tasks.
    
    Analyzes how long tasks take from creation to completion,
    grouped by different dimensions for comparison.
    
    Args:
        group_by: How to group results - "overall", "tag", "project", or "area" (default: "overall")
        limit: Max number of completed tasks to analyze (default: 100)
        
    Returns:
        Time-to-completion statistics with speed indicators
        
    Examples:
        get_time_to_completion("overall", 100)  # Overall average
        get_time_to_completion("tag", 200)      # Compare tags
        get_time_to_completion("project", 50)   # Compare projects
    """
    start_time = time.time()
    log_operation_start("get-time-to-completion")
    
    try:
        # Get completed items
        logbook = things.logbook()
        
        # Calculate statistics
        stats_list = calculate_time_to_completion(
            completed_items=logbook,
            group_by=group_by,
            limit=limit
        )
        
        if not stats_list:
            return "No completion data available for analysis"
        
        # Format output
        result = f"""⏱️  Average Time to Completion (Last {limit} tasks)

"""
        
        if group_by == "overall":
            stats = stats_list[0]
            result += f"""Overall: {stats.avg_hours / 24:.1f} days (median: {stats.median_hours / 24:.1f} days)
   {stats.count} tasks analyzed
   Min: {stats.min_hours / 24:.1f} days, Max: {stats.max_hours / 24:.1f} days, P90: {stats.p90_hours / 24:.1f} days"""
        else:
            result += f"By {group_by.capitalize()}:\n"
            for i, stats in enumerate(stats_list[:10], 1):  # Top 10
                avg_days = stats.avg_hours / 24
                median_days = stats.median_hours / 24
                speed_indicator = "⚡" if avg_days < 1 else "🐢" if avg_days > 7 else ""
                
                result += f"   {i}. {stats.group_name}: {avg_days:.1f} days (median: {median_days:.1f}) {speed_indicator}\n"
                result += f"      {stats.count} tasks analyzed\n"
            
            # Add insight
            if len(stats_list) >= 2:
                fastest = stats_list[0]
                slowest = stats_list[-1]
                ratio = (slowest.avg_hours / fastest.avg_hours) if fastest.avg_hours > 0 else 0
                result += f"\n💡 Insight: '{fastest.group_name}' is {ratio:.1f}x faster than '{slowest.group_name}'!"
        
        log_operation_end("get-time-to-completion", True, time.time() - start_time)
        return result
        
    except Exception as e:
        logger.error(f"Error calculating time to completion: {e}")
        return _error_result(f"Error calculating time to completion: {str(e)}")


@mcp.tool(name="get-tag-productivity", annotations=TOOL_ANNOTATIONS["get-tag-productivity"])
@cached(ttl=600)  # 10 minute cache
async def get_tag_productivity(min_tasks: int = 3) -> str:
    """
    Analyze productivity metrics by tag.
    
    Compares completion rates and average time to completion across
    different tags to identify your most productive work categories.
    
    Args:
        min_tasks: Minimum tasks required for tag to be included (default: 3)
        
    Returns:
        Tag productivity rankings with visual indicators
        
    Examples:
        get_tag_productivity(3)   # Tags with 3+ tasks
        get_tag_productivity(10)  # Tags with 10+ tasks (more reliable)
    """
    start_time = time.time()
    log_operation_start("get-tag-productivity")
    
    try:
        # Get all items
        logbook = things.logbook()
        incomplete = things.todos()
        all_items = logbook + incomplete
        
        # Calculate productivity
        metrics = calculate_tag_productivity(
            all_items=all_items,
            min_tasks=min_tasks
        )
        
        if not metrics:
            return f"No tags found with at least {min_tasks} tasks"
        
        # Format output
        result = f"""🏷️  Tag Productivity Analysis (min {min_tasks} tasks)

"""
        
        for i, metric in enumerate(metrics[:20], 1):  # Top 20
            rate = metric.completion_rate * 100
            
            # Productivity indicator
            if rate >= 80:
                indicator = "🏆"
            elif rate >= 50:
                indicator = "✓"
            elif rate < 25:
                indicator = "⚠️"
            else:
                indicator = ""
            
            result += f"   {i}. {metric.tag_name} {indicator}\n"
            result += f"      Completion: {rate:.1f}% ({metric.completed_tasks}/{metric.total_tasks} tasks)\n"
            
            if metric.avg_completion_hours > 0:
                avg_days = metric.avg_completion_hours / 24
                speed = "⚡" if avg_days < 1 else "🐢" if avg_days > 7 else ""
                result += f"      Avg time: {avg_days:.1f} days {speed}\n"
        
        # Add insights
        if metrics:
            top = metrics[0]
            result += f"\n💡 Top Performer: '{top.tag_name}' with {top.completion_rate * 100:.1f}% completion rate"
            
            low_completion = [m for m in metrics if m.completion_rate < 0.25]
            if low_completion:
                low_tags = ", ".join([m.tag_name for m in low_completion[:3]])
                result += f"\n⚠️  Tags needing attention: {low_tags}"
        
        log_operation_end("get-tag-productivity", True, time.time() - start_time)
        return result
        
    except Exception as e:
        logger.error(f"Error calculating tag productivity: {e}")
        return _error_result(f"Error calculating tag productivity: {str(e)}")


@mcp.tool(name="check-stalled-projects", annotations=TOOL_ANNOTATIONS["check-stalled-projects"])
async def check_stalled_projects(min_inactive_days: int = 14) -> str:
    """
    Find projects with no recent activity (stalled).
    
    Identifies projects that haven't had any task completions or
    modifications in the specified time period.
    
    Args:
        min_inactive_days: Days without activity to be considered stalled (default: 14)
        
    Returns:
        List of stalled projects with last activity date and recommendations
        
    Examples:
        check_stalled_projects(14)  # 2+ weeks inactive
        check_stalled_projects(30)  # 1+ month inactive
        check_stalled_projects(7)   # 1+ week inactive
    """
    start_time = time.time()
    log_operation_start("check-stalled-projects")
    
    try:
        # Get all projects with items
        projects = things.projects(include_items=True)
        
        # Calculate stalled projects
        stalled = calculate_stalled_projects(
            projects=projects,
            min_inactive_days=min_inactive_days
        )
        
        if not stalled:
            return f"✓ No stalled projects found (inactive >{min_inactive_days} days)"
        
        # Format output
        result = f"""⚠️  Stalled Projects (No activity in {min_inactive_days}+ days)

"""
        
        for i, project in enumerate(stalled, 1):
            # Urgency indicator
            if project.days_inactive > 60:
                urgency = "⚠️ Very stalled"
            elif project.days_inactive > 30:
                urgency = "⏸️  Moderately stalled"
            else:
                urgency = ""
            
            result += f"{i}. {project.title} {urgency}\n"
            result += f"   Last activity: {project.last_activity_date} ({project.days_inactive} days ago)\n"
            result += f"   Status: {project.incomplete_count} incomplete task(s)\n"
            
            if project.notes:
                notes_preview = project.notes[:100] + "..." if len(project.notes) > 100 else project.notes
                result += f"   Notes: {notes_preview}\n"
            
            result += "\n"
        
        # Summary
        total_incomplete = sum(p.incomplete_count for p in stalled)
        result += f"Found {len(stalled)} stalled project(s) with {total_incomplete} incomplete task(s) total.\n"
        result += "💡 Consider reviewing these projects - archive, complete, or re-energize them."
        
        log_operation_end("check-stalled-projects", True, time.time() - start_time)
        return result
        
    except Exception as e:
        logger.error(f"Error checking stalled projects: {e}")
        return _error_result(f"Error checking stalled projects: {str(e)}")


@mcp.tool(name="get-project-health-report", annotations=TOOL_ANNOTATIONS["get-project-health-report"])
async def get_project_health_report() -> str:
    """
    Generate comprehensive health report for all active projects.
    
    Analyzes completion rates, velocity, inactivity, overdue tasks,
    and scope creep to generate 0-100 health scores with actionable
    recommendations for each project.
    
    Returns:
        Detailed health reports sorted by health score (worst first)
        
    Example:
        get_project_health_report()  # Analyze all active projects
    """
    start_time = time.time()
    log_operation_start("get-project-health-report")
    
    try:
        # Get all projects with items
        projects = things.projects(include_items=True)
        
        # Calculate health for all projects
        health_reports = calculate_project_health(projects=projects)
        
        if not health_reports:
            return "No active projects to analyze"
        
        # Format output
        result = """🏥 Project Health Report

"""
        
        for i, health in enumerate(health_reports[:10], 1):  # Top 10 worst
            # Health indicator
            if health.health_score < 50:
                indicator = "🔴 Critical"
            elif health.health_score < 75:
                indicator = "🟡 Needs Attention"
            else:
                indicator = "🟢 Healthy"
            
            result += f"{i}. {health.project_title}\n"
            result += f"   Overall Health: {health.health_score}/100 {indicator}\n\n"
            
            result += "   📊 Metrics:\n"
            result += f"      ✅ Completion: {health.completion_rate * 100:.0f}%\n"
            result += f"      📈 Velocity: {health.velocity:.1f} tasks/week\n"
            result += f"      ⏱️  Last Activity: {health.days_inactive} days ago\n"
            
            if health.overdue_count > 0:
                result += f"      ⚠️  Overdue: {health.overdue_count} task(s)\n"
            
            result += f"      📊 Scope Creep: {health.scope_creep_ratio:.2f}x\n"
            
            if health.estimated_completion_date:
                result += f"      🎯 Est. Completion: {health.estimated_completion_date}\n"
            
            if health.recommendations:
                result += "\n   💡 Recommendations:\n"
                for rec in health.recommendations[:3]:  # Top 3
                    result += f"      - {rec}\n"
            
            result += "\n"
        
        # Overall statistics
        avg_health = sum(h.health_score for h in health_reports) / len(health_reports)
        total_overdue = sum(h.overdue_count for h in health_reports)
        
        result += "📊 Overall Statistics:\n"
        result += f"   Average Health: {avg_health:.0f}/100\n"
        result += f"   Total Overdue Tasks: {total_overdue}\n"
        result += f"   Projects Analyzed: {len(health_reports)}"
        
        log_operation_end("get-project-health-report", True, time.time() - start_time)
        return result
        
    except Exception as e:
        logger.error(f"Error generating project health report: {e}")
        return _error_result(f"Error generating project health report: {str(e)}")


@mcp.tool(name="analyze-tag-relationships", annotations=TOOL_ANNOTATIONS["analyze-tag-relationships"])
@cached(ttl=600)  # 10 minute cache
async def analyze_tag_relationships(
    min_cooccurrence: int = 3,
    limit: int = 20
) -> str:
    """
    Analyze which tags frequently appear together.
    
    Discovers implicit connections between work categories by analyzing
    how often different tags appear on the same tasks.
    
    Args:
        min_cooccurrence: Minimum times tags must appear together (default: 3)
        limit: Max number of relationships to return (default: 20, max: 50)
        
    Returns:
        Tag co-occurrence patterns with strength indicators
        
    Examples:
        analyze_tag_relationships(3, 20)   # Standard analysis
        analyze_tag_relationships(5, 10)   # High confidence, fewer results
    """
    start_time = time.time()
    log_operation_start("analyze-tag-relationships")
    
    try:
        # Limit to max 50
        limit = min(limit, 50)
        
        # Get all items
        logbook = things.logbook()
        incomplete = things.todos()
        
        # Calculate relationships
        relationships = calculate_tag_relationships(
            logbook_items=logbook,
            incomplete_items=incomplete,
            min_cooccurrence=min_cooccurrence
        )
        
        if not relationships:
            return f"No tag relationships found (min {min_cooccurrence} co-occurrences)"
        
        # Format output
        result = f"""🏷️  Tag Relationship Analysis (min {min_cooccurrence} co-occurrences)

"""
        
        for i, rel in enumerate(relationships[:limit], 1):
            # Strength indicator
            if rel.strength >= 0.7:
                strength_indicator = "🔴"
            elif rel.strength >= 0.4:
                strength_indicator = "🟠"
            else:
                strength_indicator = "🟡"
            
            result += f"   {i}. {rel.tag1} + {rel.tag2} {strength_indicator}\n"
            result += f"      Co-occurrence: {rel.co_occurrence_count} times\n"
            result += f"      Strength: {rel.strength:.2f} ({rel.tag1}: {rel.tag1_total}, {rel.tag2}: {rel.tag2_total})\n\n"
        
        # Add insights
        if relationships:
            strongest = max(relationships, key=lambda r: r.strength)
            most_common = max(relationships, key=lambda r: r.co_occurrence_count)
            
            result += f"💡 Strongest relationship: '{strongest.tag1}' + '{strongest.tag2}' ({strongest.strength:.2f})\n"
            result += f"📊 Most common: '{most_common.tag1}' + '{most_common.tag2}' ({most_common.co_occurrence_count} times)"
        
        log_operation_end("analyze-tag-relationships", True, time.time() - start_time)
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing tag relationships: {e}")
        return _error_result(f"Error analyzing tag relationships: {str(e)}")


@mcp.tool(name="suggest-tags", annotations=TOOL_ANNOTATIONS["suggest-tags"])
@cached(ttl=300)  # 5 minute cache
async def suggest_tags(
    title: str,
    notes: str = "",
    max_suggestions: int = 10
) -> str:
    """
    Suggest relevant tags based on task content.
    
    Uses keyword extraction and historical tag relationships to recommend
    tags that might be relevant for a new task.
    
    Args:
        title: Task title
        notes: Task notes (optional)
        max_suggestions: Maximum suggestions to return (default: 10)
        
    Returns:
        Suggested tags with confidence scores and examples
        
    Examples:
        suggest_tags("Buy groceries", "milk, eggs, bread")
        suggest_tags("Schedule dentist appointment")
        suggest_tags("Review Q4 budget proposal", "annual planning meeting")
    """
    start_time = time.time()
    log_operation_start("suggest-tags")
    
    try:
        # Get all items
        logbook = things.logbook()
        incomplete = things.todos()
        
        # Calculate suggestions
        suggestions = calculate_tag_suggestions(
            item_title=title,
            item_notes=notes,
            existing_tags=[],  # No existing tags for new item
            logbook_items=logbook,
            incomplete_items=incomplete,
            max_suggestions=max_suggestions
        )
        
        if not suggestions:
            return f"No tag suggestions available for: '{title}'"
        
        # Format output
        result = f"""🏷️  Tag Suggestions for: "{title}"

"""
        
        for i, suggestion in enumerate(suggestions, 1):
            confidence_pct = suggestion.confidence * 100
            
            # Confidence indicator
            if confidence_pct >= 80:
                indicator = "⭐⭐⭐"
            elif confidence_pct >= 50:
                indicator = "⭐⭐"
            else:
                indicator = "⭐"
            
            result += f"   {i}. {suggestion.tag_name} ({confidence_pct:.0f}% confidence) {indicator}\n"
            
            if suggestion.matching_keywords:
                result += f"      Matches: {', '.join(suggestion.matching_keywords)}\n"
            
            if suggestion.example_tasks:
                examples = ", ".join([f'"{t}"' for t in suggestion.example_tasks[:3]])
                result += f"      Similar: {examples}\n"
            
            result += "\n"
        
        # Add recommendation
        if suggestions:
            top_tags = [s.tag_name for s in suggestions[:3] if s.confidence > 0.5]
            if top_tags:
                result += f"💡 Recommendation: Consider adding {', '.join(top_tags)}"
        
        log_operation_end("suggest-tags", True, time.time() - start_time)
        return result
        
    except Exception as e:
        logger.error(f"Error suggesting tags: {e}")
        return _error_result(f"Error suggesting tags: {str(e)}")


@mcp.tool(name="parse-natural-date", annotations=TOOL_ANNOTATIONS["parse-natural-date"])
async def parse_natural_date(date_input: str) -> str:
    """
    Parse natural language date expressions to ISO format.
    
    Converts human-friendly date expressions like "tomorrow" or "next Monday"
    into ISO dates (YYYY-MM-DD) compatible with Things URL scheme.
    
    Args:
        date_input: Natural language date (e.g., "next Monday", "in 3 days", "Dec 25")
        
    Returns:
        ISO formatted date (YYYY-MM-DD) with interpretation
        
    Examples:
        parse_natural_date("tomorrow")           # → 2025-11-03
        parse_natural_date("next Monday")        # → 2025-11-09
        parse_natural_date("in 3 days")          # → 2025-11-05
        parse_natural_date("Dec 25")             # → 2025-12-25
        parse_natural_date("2 weeks from now")   # → 2025-11-16
    """
    start_time = time.time()
    log_operation_start("parse-natural-date")
    
    try:
        import dateparser
        from datetime import datetime, date
        
        # Configure dateparser to prefer future dates
        settings = {
            'PREFER_DATES_FROM': 'future',
            'RETURN_AS_TIMEZONE_AWARE': False,
            'RELATIVE_BASE': datetime.now()
        }
        
        # Try parsing
        parsed = dateparser.parse(date_input, settings=settings)  # type: ignore
        
        if not parsed:
            # Check if it's a Things-specific keyword
            if date_input.lower() in ['anytime', 'someday']:
                return f"Special keyword: {date_input}\n(Use directly in Things URL scheme)"
            
            return _error_result(
                f"Could not parse date: '{date_input}'\n"
                "Try formats like: 'tomorrow', 'next Monday', 'in 3 days', 'Dec 25', 'YYYY-MM-DD'"
            )
        
        # Convert to ISO date
        parsed_date = parsed.date()
        iso_date = parsed_date.isoformat()
        
        # Build interpretation
        today = date.today()
        days_diff = (parsed_date - today).days
        
        if days_diff < 0:
            warning = f"⚠️  Warning: This date is in the past ({abs(days_diff)} days ago)"
        else:
            warning = ""
        
        # Format result
        result = f"""Input: "{date_input}"
Parsed: {iso_date}
Interpretation: {parsed.strftime('%A, %B %d, %Y')} ({days_diff} days from today)
{warning}

Usage examples:
  things:///add?title=Task&when={iso_date}
  things:///update?id=UUID&deadline={iso_date}"""
        
        log_operation_end("parse-natural-date", True, time.time() - start_time)
        return result
        
    except ImportError:
        return _error_result(
            "dateparser library not installed.\n"
            "Install with: pip install dateparser"
        )
    except Exception as e:
        logger.error(f"Error parsing natural date: {e}")
        return _error_result(f"Error parsing date: {str(e)}")


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
