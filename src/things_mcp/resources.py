"""
MCP Resources for Things 3 Task Management.

This module exposes Things 3 data through MCP resources using the things:// URI scheme.
Resources are organized into 5 categories:
1. Hierarchical Structure - Projects, areas, and tags
2. Todo Lists - Inbox, today, upcoming, anytime, someday, logbook
3. Individual Items - Detailed info for specific todos and projects
4. Search & Discovery - Search functionality and filtered views
5. Analytics - Productivity metrics and summaries

All resources use FastMCP's @mcp.resource decorator with URI templates.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
import urllib.parse
import things
from fastmcp import FastMCP, Context

# Import the FastMCP instance (will be set by fast_server.py)
mcp: Optional[FastMCP] = None


def init_resources(fastmcp_instance: FastMCP) -> None:
    """
    Initialize resources module with FastMCP instance.
    
    Args:
        fastmcp_instance: The FastMCP server instance
    """
    global mcp
    mcp = fastmcp_instance


# ============================================================================
# CATEGORY 1: HIERARCHICAL STRUCTURE RESOURCES
# ============================================================================

async def projects_list_resource() -> Dict[str, Any]:
    """
    Complete list of all projects in Things 3.
    
    URI: things://projects/list
    MIME: application/json
    
    Returns:
        Dict with projects list and metadata
    """
    try:
        projects = things.projects()
        
        result = {
            "resource_uri": "things://projects/list",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(projects),
            "projects": [
                {
                    "uuid": p["uuid"],
                    "title": p["title"],
                    "status": p["status"],
                    "area": p.get("area"),
                    "area_id": p.get("area_id"),
                    "tags": p.get("tags", []),
                    "created": p.get("created"),
                    "modified": p.get("modified"),
                    "deadline": p.get("deadline"),
                    "notes": p.get("notes")
                }
                for p in projects
            ]
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "resource_uri": "things://projects/list",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def project_info_resource(
    project_uuid: str,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Complete details for a specific project.
    
    URI: things://projects/{project_uuid}/info
    MIME: application/json
    
    Args:
        project_uuid: UUID of the project
        
    Returns:
        Dict with project details and todo statistics
    """
    try:
        project = things.get(uuid=project_uuid)
        
        if not project or not isinstance(project, dict):
            return {
                "error": "Project not found",
                "uuid": project_uuid,
                "resource_uri": f"things://projects/{project_uuid}/info",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Get todos for statistics
        todos = things.todos(project=project_uuid)
        incomplete_count = len([t for t in todos if t.get("status") == "incomplete"])
        completed_count = len([t for t in todos if t.get("status") == "completed"])
        
        result = {
            **project,
            "resource_uri": f"things://projects/{project_uuid}/info",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "todo_stats": {
                "total": len(todos),
                "incomplete": incomplete_count,
                "completed": completed_count,
                "completion_rate": (completed_count / len(todos) * 100) if todos else 0
            }
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "uuid": project_uuid,
            "resource_uri": f"things://projects/{project_uuid}/info"
        }


async def project_todos_resource(
    project_uuid: str,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    All todos within a specific project.
    
    URI: things://projects/{project_uuid}/todos
    MIME: application/json
    
    Args:
        project_uuid: UUID of the project
        
    Returns:
        Dict with todos list
    """
    try:
        todos = things.todos(project=project_uuid)
        
        result = {
            "resource_uri": f"things://projects/{project_uuid}/todos",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_uuid": project_uuid,
            "count": len(todos),
            "todos": todos
        }
        
        if ctx:
            await ctx.info(f"Returned {len(todos)} todos for project {project_uuid}")
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "project_uuid": project_uuid,
            "resource_uri": f"things://projects/{project_uuid}/todos"
        }


async def areas_list_resource() -> Dict[str, Any]:
    """
    Complete list of all areas in Things 3.
    
    URI: things://areas/list
    MIME: application/json
    
    Returns:
        Dict with areas list and metadata
    """
    try:
        areas = things.areas()
        
        result = {
            "resource_uri": "things://areas/list",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(areas),
            "areas": [
                {
                    "uuid": a["uuid"],
                    "title": a["title"],
                    "tags": a.get("tags", []),
                    "visible": a.get("visible", True)
                }
                for a in areas
            ]
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "resource_uri": "things://areas/list",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def area_info_resource(
    area_uuid: str,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Complete details for a specific area.
    
    URI: things://areas/{area_uuid}/info
    MIME: application/json
    
    Args:
        area_uuid: UUID of the area
        
    Returns:
        Dict with area details
    """
    try:
        area = things.get(uuid=area_uuid)
        
        if not area or not isinstance(area, dict):
            return {
                "error": "Area not found",
                "uuid": area_uuid,
                "resource_uri": f"things://areas/{area_uuid}/info",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Get projects in this area
        projects = [p for p in things.projects() if p.get("area_id") == area_uuid]
        
        result = {
            **area,
            "resource_uri": f"things://areas/{area_uuid}/info",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_count": len(projects),
            "projects": [{"uuid": p["uuid"], "title": p["title"]} for p in projects]
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "uuid": area_uuid,
            "resource_uri": f"things://areas/{area_uuid}/info"
        }


async def tags_list_resource() -> Dict[str, Any]:
    """
    Complete list of all tags in Things 3.
    
    URI: things://tags/list
    MIME: application/json
    
    Returns:
        Dict with tags list and usage statistics
    """
    try:
        tags = things.tags()
        
        # Calculate usage statistics for each tag
        tags_with_stats = []
        for tag in tags:
            tag_title = tag.get("title", "")
            # Count items with this tag
            todos = things.todos(tag=tag_title)
            projects = [p for p in things.projects() if tag_title in p.get("tags", [])]
            
            tags_with_stats.append({
                "title": tag_title,
                "shortcut": tag.get("shortcut"),
                "usage_count": len(todos) + len(projects),
                "todo_count": len(todos),
                "project_count": len(projects)
            })
        
        # Sort by usage count
        tags_with_stats.sort(key=lambda t: t["usage_count"], reverse=True)
        
        result = {
            "resource_uri": "things://tags/list",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(tags_with_stats),
            "tags": tags_with_stats
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "resource_uri": "things://tags/list",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def tag_items_resource(
    tag_name: str,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    All items (todos and projects) with a specific tag.
    
    URI: things://tags/{tag_name}/items
    MIME: application/json
    
    Args:
        tag_name: Name of the tag (URL encoded)
        
    Returns:
        Dict with tagged items
    """
    try:
        # URL decode tag name
        decoded_tag = urllib.parse.unquote(tag_name)
        
        # Get all items with this tag
        todos = things.todos(tag=decoded_tag)
        projects = [p for p in things.projects() if decoded_tag in p.get("tags", [])]
        
        result = {
            "resource_uri": f"things://tags/{tag_name}/items",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tag": decoded_tag,
            "total_count": len(todos) + len(projects),
            "todos": {
                "count": len(todos),
                "items": todos
            },
            "projects": {
                "count": len(projects),
                "items": projects
            }
        }
        
        if ctx:
            await ctx.info(f"Returned {len(todos) + len(projects)} items for tag '{decoded_tag}'")
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "tag": tag_name,
            "resource_uri": f"things://tags/{tag_name}/items"
        }


# ============================================================================
# CATEGORY 2: TODO LISTS RESOURCES
# ============================================================================

async def inbox_resource() -> Dict[str, Any]:
    """
    All items in the inbox.
    
    URI: things://todos/inbox
    MIME: application/json
    
    Returns:
        Dict with inbox items
    """
    try:
        inbox_items = things.inbox()
        
        result = {
            "resource_uri": "things://todos/inbox",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(inbox_items),
            "items": inbox_items
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "resource_uri": "things://todos/inbox",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def today_resource() -> Dict[str, Any]:
    """
    All tasks scheduled for today.
    
    URI: things://todos/today
    MIME: application/json
    
    Returns:
        Dict with today's tasks
    """
    try:
        today_items = things.today()
        
        result = {
            "resource_uri": "things://todos/today",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(today_items),
            "items": today_items
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "resource_uri": "things://todos/today",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def upcoming_resource() -> Dict[str, Any]:
    """
    All tasks scheduled for upcoming days.
    
    URI: things://todos/upcoming
    MIME: application/json
    
    Returns:
        Dict with upcoming tasks
    """
    try:
        upcoming_items = things.upcoming()
        
        result = {
            "resource_uri": "things://todos/upcoming",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(upcoming_items),
            "items": upcoming_items
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "resource_uri": "things://todos/upcoming",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def anytime_resource() -> Dict[str, Any]:
    """
    All tasks in the Anytime list.
    
    URI: things://todos/anytime
    MIME: application/json
    
    Returns:
        Dict with anytime tasks
    """
    try:
        anytime_items = things.anytime()
        
        result = {
            "resource_uri": "things://todos/anytime",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(anytime_items),
            "items": anytime_items
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "resource_uri": "things://todos/anytime",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def someday_resource() -> Dict[str, Any]:
    """
    All tasks in the Someday list.
    
    URI: things://todos/someday
    MIME: application/json
    
    Returns:
        Dict with someday tasks
    """
    try:
        someday_items = things.someday()
        
        result = {
            "resource_uri": "things://todos/someday",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(someday_items),
            "items": someday_items
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "resource_uri": "things://todos/someday",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def logbook_resource() -> Dict[str, Any]:
    """
    Completed tasks (logbook) - returns last 100 items.
    
    URI: things://todos/logbook
    MIME: application/json
        
    Returns:
        Dict with logbook tasks
    """
    # Default pagination
    limit = 100
    offset = 0
    try:
        all_logbook = things.logbook()
        
        # Apply pagination
        paginated_items = all_logbook[offset:offset + limit]
        
        result = {
            "resource_uri": "things://todos/logbook",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_count": len(all_logbook),
            "returned_count": len(paginated_items),
            "note": "Showing last 100 completed items",
            "items": paginated_items
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "resource_uri": "things://todos/logbook",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# ============================================================================
# CATEGORY 3: INDIVIDUAL ITEMS RESOURCES
# ============================================================================

async def todo_info_resource(
    todo_uuid: str,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Complete details for a specific todo.
    
    URI: things://todos/{todo_uuid}/info
    MIME: application/json
    
    Args:
        todo_uuid: UUID of the todo
        
    Returns:
        Dict with todo details
    """
    try:
        todo = things.get(uuid=todo_uuid)
        
        if not todo or not isinstance(todo, dict):
            return {
                "error": "Todo not found",
                "uuid": todo_uuid,
                "resource_uri": f"things://todos/{todo_uuid}/info",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Get checklist items if any
        checklist = things.checklist_items(todo_uuid) if todo.get("type") == "to-do" else []
        
        result = {
            **todo,
            "resource_uri": f"things://todos/{todo_uuid}/info",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checklist": checklist,
            "checklist_count": len(checklist)
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "uuid": todo_uuid,
            "resource_uri": f"things://todos/{todo_uuid}/info"
        }


async def todo_notes_resource(
    todo_uuid: str,
    ctx: Optional[Context] = None
) -> str:
    """
    Notes content for a specific todo (plain text).
    
    URI: things://todos/{todo_uuid}/notes
    MIME: text/plain
    
    Args:
        todo_uuid: UUID of the todo
        
    Returns:
        Notes as plain text
    """
    try:
        todo = things.get(uuid=todo_uuid)
        
        if not todo or not isinstance(todo, dict):
            return f"Error: Todo not found (uuid: {todo_uuid})"
        
        notes = todo.get("notes", "")
        
        if not notes:
            return "(No notes)"
        
        return notes
        
    except Exception as e:
        return f"Error: {str(e)}"


async def project_notes_resource(
    project_uuid: str,
    ctx: Optional[Context] = None
) -> str:
    """
    Notes content for a specific project (plain text).
    
    URI: things://projects/{project_uuid}/notes
    MIME: text/plain
    
    Args:
        project_uuid: UUID of the project
        
    Returns:
        Notes as plain text
    """
    try:
        project = things.get(uuid=project_uuid)
        
        if not project or not isinstance(project, dict):
            return f"Error: Project not found (uuid: {project_uuid})"
        
        notes = project.get("notes", "")
        
        if not notes:
            return "(No notes)"
        
        return notes
        
    except Exception as e:
        return f"Error: {str(e)}"


async def todo_checklist_resource(
    todo_uuid: str,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Checklist items for a specific todo.
    
    URI: things://todos/{todo_uuid}/checklist
    MIME: application/json
    
    Args:
        todo_uuid: UUID of the todo
        
    Returns:
        Dict with checklist items
    """
    try:
        checklist = things.checklist_items(todo_uuid)
        
        completed_count = len([item for item in checklist if item.get("status") == "completed"])
        
        result = {
            "resource_uri": f"things://todos/{todo_uuid}/checklist",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "todo_uuid": todo_uuid,
            "count": len(checklist),
            "completed_count": completed_count,
            "completion_rate": (completed_count / len(checklist) * 100) if checklist else 0,
            "items": checklist
        }
        
        if ctx:
            await ctx.info(f"Returned {len(checklist)} checklist items for todo {todo_uuid}")
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "todo_uuid": todo_uuid,
            "resource_uri": f"things://todos/{todo_uuid}/checklist"
        }


# ============================================================================
# CATEGORY 4: SEARCH & DISCOVERY RESOURCES
# ============================================================================

async def search_resource(
    query: str,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Search results for a query across all items.
    
    URI: things://search/{query}
    MIME: application/json
    
    Args:
        query: Search query (URL encoded)
        
    Returns:
        Dict with search results
    """
    try:
        # URL decode query
        decoded_query = urllib.parse.unquote(query)
        
        # Search
        results = things.search(decoded_query)
        
        # Categorize results
        todos = [r for r in results if r.get("type") == "to-do"]
        projects = [r for r in results if r.get("type") == "project"]
        other = [r for r in results if r.get("type") not in ["to-do", "project"]]
        
        result = {
            "resource_uri": f"things://search/{query}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": decoded_query,
            "total_count": len(results),
            "todos": {
                "count": len(todos),
                "items": todos
            },
            "projects": {
                "count": len(projects),
                "items": projects
            },
            "other": {
                "count": len(other),
                "items": other
            }
        }
        
        if ctx:
            await ctx.info(f"Found {len(results)} items for query: {decoded_query}")
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "query": query,
            "resource_uri": f"things://search/{query}"
        }


async def overdue_resource() -> Dict[str, Any]:
    """
    All items with past deadlines.
    
    URI: things://deadlines/overdue
    MIME: application/json
    
    Returns:
        Dict with overdue items
    """
    try:
        from datetime import date
        
        all_todos = things.todos()
        today = date.today()
        
        overdue_items = []
        for todo in all_todos:
            if todo.get("status") != "incomplete":
                continue
                
            deadline_str = todo.get("deadline")
            if not deadline_str:
                continue
            
            try:
                # Parse deadline (format: YYYY-MM-DD)
                deadline_date = date.fromisoformat(deadline_str)
                if deadline_date < today:
                    days_overdue = (today - deadline_date).days
                    todo_with_overdue = {**todo, "days_overdue": days_overdue}
                    overdue_items.append(todo_with_overdue)
            except (ValueError, AttributeError):
                continue
        
        # Sort by most overdue first
        overdue_items.sort(key=lambda t: t["days_overdue"], reverse=True)
        
        result = {
            "resource_uri": "things://deadlines/overdue",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(overdue_items),
            "items": overdue_items
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "resource_uri": "things://deadlines/overdue",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def due_soon_resource() -> Dict[str, Any]:
    """
    Items due in the next 7 days.
    
    URI: things://deadlines/due-soon
    MIME: application/json
        
    Returns:
        Dict with items due soon
    """
    # Default to 7 days
    days = 7
    try:
        from datetime import date, timedelta
        
        all_todos = things.todos()
        today = date.today()
        future_date = today + timedelta(days=days)
        
        due_soon_items = []
        for todo in all_todos:
            if todo.get("status") != "incomplete":
                continue
                
            deadline_str = todo.get("deadline")
            if not deadline_str:
                continue
            
            try:
                deadline_date = date.fromisoformat(deadline_str)
                if today <= deadline_date <= future_date:
                    days_until = (deadline_date - today).days
                    todo_with_countdown = {**todo, "days_until": days_until}
                    due_soon_items.append(todo_with_countdown)
            except (ValueError, AttributeError):
                continue
        
        # Sort by soonest first
        due_soon_items.sort(key=lambda t: t["days_until"])
        
        result = {
            "resource_uri": "things://deadlines/due-soon",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "days_ahead": days,
            "count": len(due_soon_items),
            "items": due_soon_items
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "resource_uri": "things://deadlines/due-soon",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# ============================================================================
# CATEGORY 5: ANALYTICS RESOURCES
# ============================================================================

async def productivity_summary_resource() -> Dict[str, Any]:
    """
    Productivity summary and statistics for last 30 days.
    
    URI: things://analytics/summary
    MIME: application/json
        
    Returns:
        Dict with productivity metrics
    """
    # Default to 30 days
    days = 30
    try:
        from datetime import date, timedelta
        
        # Get data
        logbook = things.logbook()
        all_todos = things.todos()
        projects = things.projects()
        
        # Calculate date range
        today = date.today()
        start_date = today - timedelta(days=days)
        
        # Count completed in period
        completed_in_period = []
        for item in logbook:
            stop_date_str = item.get("stop_date")
            if stop_date_str:
                try:
                    stop_date = date.fromisoformat(stop_date_str.split("T")[0])
                    if stop_date >= start_date:
                        completed_in_period.append(item)
                except (ValueError, AttributeError):
                    continue
        
        # Count incomplete items
        incomplete_todos = [t for t in all_todos if t.get("status") == "incomplete"]
        
        # Count overdue
        overdue_count = 0
        for todo in incomplete_todos:
            deadline_str = todo.get("deadline")
            if deadline_str:
                try:
                    deadline_date = date.fromisoformat(deadline_str)
                    if deadline_date < today:
                        overdue_count += 1
                except (ValueError, AttributeError):
                    continue
        
        # Calculate completion rate
        total_items = len(completed_in_period) + len(incomplete_todos)
        completion_rate = (len(completed_in_period) / total_items * 100) if total_items > 0 else 0
        
        # Top tags analysis
        tag_counts: Dict[str, int] = {}
        for item in completed_in_period:
            for tag in item.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        result = {
            "resource_uri": "things://analytics/summary",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "period_days": days,
            "metrics": {
                "completed": len(completed_in_period),
                "incomplete": len(incomplete_todos),
                "overdue": overdue_count,
                "completion_rate": round(completion_rate, 1),
                "avg_per_day": round(len(completed_in_period) / days, 1),
                "active_projects": len([p for p in projects if p.get("status") == "active"]),
                "total_projects": len(projects)
            },
            "top_tags": [{"tag": tag, "count": count} for tag, count in top_tags],
            "summary": f"Completed {len(completed_in_period)} tasks in {days} days ({round(completion_rate, 1)}% completion rate)"
        }
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "resource_uri": "things://analytics/summary",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# ============================================================================
# RESOURCE REGISTRATION
# ============================================================================

RESOURCE_REGISTRY = {
    # Hierarchical Structure
    "things://projects/list": {
        "function": projects_list_resource,
        "name": "All Projects",
        "description": "Complete list of all projects in Things 3",
        "mime_type": "application/json",
        "category": "hierarchical"
    },
    "things://projects/{project_uuid}/info": {
        "function": project_info_resource,
        "name": "Project Details",
        "description": "Complete details for a specific project",
        "mime_type": "application/json",
        "category": "hierarchical"
    },
    "things://projects/{project_uuid}/todos": {
        "function": project_todos_resource,
        "name": "Project Todos",
        "description": "All todos within a specific project",
        "mime_type": "application/json",
        "category": "hierarchical"
    },
    "things://areas/list": {
        "function": areas_list_resource,
        "name": "All Areas",
        "description": "Complete list of all areas in Things 3",
        "mime_type": "application/json",
        "category": "hierarchical"
    },
    "things://areas/{area_uuid}/info": {
        "function": area_info_resource,
        "name": "Area Details",
        "description": "Complete details for a specific area",
        "mime_type": "application/json",
        "category": "hierarchical"
    },
    "things://tags/list": {
        "function": tags_list_resource,
        "name": "All Tags",
        "description": "Complete list of all tags with usage statistics",
        "mime_type": "application/json",
        "category": "hierarchical"
    },
    "things://tags/{tag_name}/items": {
        "function": tag_items_resource,
        "name": "Tagged Items",
        "description": "All items with a specific tag",
        "mime_type": "application/json",
        "category": "hierarchical"
    },
    
    # Todo Lists
    "things://todos/inbox": {
        "function": inbox_resource,
        "name": "Inbox",
        "description": "All items in the inbox",
        "mime_type": "application/json",
        "category": "lists"
    },
    "things://todos/today": {
        "function": today_resource,
        "name": "Today",
        "description": "All tasks scheduled for today",
        "mime_type": "application/json",
        "category": "lists"
    },
    "things://todos/upcoming": {
        "function": upcoming_resource,
        "name": "Upcoming",
        "description": "All tasks scheduled for upcoming days",
        "mime_type": "application/json",
        "category": "lists"
    },
    "things://todos/anytime": {
        "function": anytime_resource,
        "name": "Anytime",
        "description": "All tasks in the Anytime list",
        "mime_type": "application/json",
        "category": "lists"
    },
    "things://todos/someday": {
        "function": someday_resource,
        "name": "Someday",
        "description": "All tasks in the Someday list",
        "mime_type": "application/json",
        "category": "lists"
    },
    "things://todos/logbook": {
        "function": logbook_resource,
        "name": "Logbook",
        "description": "Completed tasks (last 100 items)",
        "mime_type": "application/json",
        "category": "lists"
    },
    
    # Individual Items
    "things://todos/{todo_uuid}/info": {
        "function": todo_info_resource,
        "name": "Todo Details",
        "description": "Complete details for a specific todo",
        "mime_type": "application/json",
        "category": "items"
    },
    "things://todos/{todo_uuid}/notes": {
        "function": todo_notes_resource,
        "name": "Todo Notes",
        "description": "Notes content for a specific todo",
        "mime_type": "text/plain",
        "category": "items"
    },
    "things://projects/{project_uuid}/notes": {
        "function": project_notes_resource,
        "name": "Project Notes",
        "description": "Notes content for a specific project",
        "mime_type": "text/plain",
        "category": "items"
    },
    "things://todos/{todo_uuid}/checklist": {
        "function": todo_checklist_resource,
        "name": "Todo Checklist",
        "description": "Checklist items for a specific todo",
        "mime_type": "application/json",
        "category": "items"
    },
    
    # Search & Discovery
    "things://search/{query}": {
        "function": search_resource,
        "name": "Search",
        "description": "Search results across all items",
        "mime_type": "application/json",
        "category": "search"
    },
    "things://deadlines/overdue": {
        "function": overdue_resource,
        "name": "Overdue Items",
        "description": "All overdue items",
        "mime_type": "application/json",
        "category": "search"
    },
    "things://deadlines/due-soon": {
        "function": due_soon_resource,
        "name": "Due Soon",
        "description": "Items due in the next 7 days",
        "mime_type": "application/json",
        "category": "search"
    },
    
    # Analytics
    "things://analytics/summary": {
        "function": productivity_summary_resource,
        "name": "Productivity Summary",
        "description": "Productivity metrics for last 30 days",
        "mime_type": "application/json",
        "category": "analytics"
    },
}


def register_all_resources(mcp_instance: FastMCP) -> None:
    """
    Register all resources with the FastMCP server.
    
    Args:
        mcp_instance: The FastMCP server instance
    """
    global mcp
    mcp = mcp_instance
    
    # Register each resource using the decorator
    for resource_uri, resource_info in RESOURCE_REGISTRY.items():
        function = resource_info["function"]
        name = resource_info["name"]
        description = resource_info["description"]
        mime_type = resource_info["mime_type"]
        
        # Apply the @mcp.resource decorator dynamically
        decorated_function = mcp.resource(
            uri=resource_uri,
            name=name,
            description=description,
            mime_type=mime_type
        )(function)
        
        # Store the decorated function back
        RESOURCE_REGISTRY[resource_uri]["decorated"] = decorated_function
