# Feature Expansion 2025 - Design Document

## Architecture Overview

### Current Architecture (v2.0.0)
```
┌─────────────────────────────────────────────────────────┐
│                    FastMCP Server                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Middleware Layer                      │  │
│  │  - DetailedTimingMiddleware (performance)         │  │
│  │  - ErrorHandlingMiddleware (consistency)          │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │              21 MCP Tools                          │  │
│  │  - Read: 14 tools (get-*, search-*, count-*)     │  │
│  │  - Write: 6 tools (add-*, update-*)               │  │
│  │  - Interactive: 1 tool (add-todo-interactive)     │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │         Data Access Layer                          │  │
│  │  - things.py API (read-only DB)                   │  │
│  │  - URL Scheme (write operations)                  │  │
│  │  - AppleScript Bridge (show operations)           │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Target Architecture (v2.3.0)
```
┌─────────────────────────────────────────────────────────────────────┐
│                         FastMCP Server                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Middleware Layer                            │  │
│  │  - DetailedTimingMiddleware (performance monitoring)          │  │
│  │  - ErrorHandlingMiddleware (consistent errors)                │  │
│  │  - [Future] CachingMiddleware (analytics optimization)        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    Tool Categories                             │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  Core Operations (27 tools)                             │  │  │
│  │  │  - Read: 20 tools (collections, filters, searches)      │  │  │
│  │  │  - Write: 6 tools (add, update, delete)                 │  │  │
│  │  │  - NEW: Checklists (4), Headings (3)                    │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  Interactive Workflows (8-10 tools)                      │  │  │
│  │  │  - Bulk Operations: complete, schedule, tag, move       │  │  │
│  │  │  - Smart Assistant: scheduling workflow                 │  │  │
│  │  │  - Templates: save, create, list, delete                │  │  │
│  │  │  - Uses: Elicitation API (preview + confirm pattern)    │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │  Intelligence Layer (9-11 tools)                         │  │  │
│  │  │  - Analytics: productivity, completion rate, tag usage  │  │  │
│  │  │  - Health: stalled projects, project health reports     │  │  │
│  │  │  - Insights: tag relationships, cleanup suggestions     │  │  │
│  │  │  - NLP: natural language scheduling                     │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │               State Management Layer (NEW)                     │  │
│  │  - Template Storage: JSON serialization                       │  │
│  │  - User Scoping: Per-user state isolation                     │  │
│  │  - Persistence: File-based (~/.things-fastmcp/state/)         │  │
│  │  - FastMCP v2.11+ state API                                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │            Data Access & Helpers Layer                         │  │
│  │  - things.py API (read operations)                            │  │
│  │  - URL Scheme Builder (write operations)                      │  │
│  │  - Date Parser (natural language → dates)                     │  │
│  │  - Analytics Calculator (stats computation)                   │  │
│  │  - AppleScript Bridge (UI operations)                         │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Critical Gaps

### 1.1 Checklist Operations Design

#### Data Model
```python
# Things.py checklist item structure
{
    "uuid": "checklist_item_uuid",
    "title": "Item text",
    "status": "incomplete" | "completed",
    "stop_date": "2025-11-01 14:30:00" | None,
    # Part of parent todo
}
```

#### Implementation Pattern
```python
@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def get_checklist_items(todo_uuid: str) -> str:
    """Get all checklist items for a specific todo."""
    try:
        items = things.checklist_items(todo_uuid)
        if not items:
            return f"No checklist found for todo {todo_uuid}"
        
        # Format output
        lines = [f"Checklist for {todo_uuid}:"]
        for item in items:
            status_icon = "✓" if item["status"] == "completed" else "○"
            lines.append(f"  {status_icon} {item['title']}")
        
        return "\n".join(lines)
    except Exception as e:
        return handle_mcp_error("get-checklist-items", e)

@mcp.tool(annotations=MODIFY_ANNOTATIONS)
async def add_checklist_item(
    todo_uuid: str,
    items: str,  # Newline-separated list
    ctx: Optional[Context] = None
) -> str:
    """Add checklist items to an existing todo."""
    # Validate todo exists
    todo = things.get(todo_uuid)
    if not todo:
        return f"Todo {todo_uuid} not found"
    
    # Build URL scheme
    # things:///update?id=uuid&checklist-items=item1%0Aitem2
    items_encoded = urllib.parse.quote(items.replace("\n", "%0A"))
    url = f"things:///update?id={todo_uuid}&checklist-items={items_encoded}"
    
    result = execute_url(url)
    
    if ctx:
        item_count = len(items.split("\n"))
        await ctx.info(f"Added {item_count} checklist items")
    
    # Invalidate cache
    cache.clear()
    
    return f"✓ Added checklist items to {todo['title']}"
```

#### URL Scheme Reference
```
Add checklist:
  things:///update?id=<uuid>&checklist-items=<newline-separated>

Update checklist item:
  things:///update?id=<uuid>&checklist-items=<full-list>
  (Must include ALL items, modified ones marked)
```

---

### 1.2 Heading Management Design

#### Data Model
```python
# Things.py heading structure (type of task)
{
    "uuid": "heading_uuid",
    "type": "heading",
    "title": "Heading Title",
    "project": "project_uuid",
    "index": 42,  # Position in project
    # No notes, tags, dates for headings
}
```

#### Implementation Pattern
```python
@mcp.tool(annotations=MODIFY_ANNOTATIONS)
async def add_heading(
    project_uuid: str,
    title: str,
    after_uuid: Optional[str] = None,  # Position after this item
    ctx: Optional[Context] = None
) -> str:
    """Add a heading to a project for organization."""
    # Validate project exists
    project = things.get(project_uuid)
    if not project or project["type"] != "project":
        return f"Project {project_uuid} not found"
    
    # Build URL
    url = f"things:///add?type=heading&list-id={project_uuid}&heading={urllib.parse.quote(title)}"
    if after_uuid:
        url += f"&after={after_uuid}"
    
    result = execute_url(url)
    
    if ctx:
        await ctx.info(f"Added heading '{title}' to {project['title']}")
    
    cache.clear()
    return f"✓ Created heading: {title}"

@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def get_project_structure(project_uuid: str) -> str:
    """Get project with headings and todos organized hierarchically."""
    project = things.projects(uuid=project_uuid, include_items=True)
    
    if not project:
        return f"Project {project_uuid} not found"
    
    # Format with hierarchy
    lines = [f"# {project['title']}", ""]
    
    current_heading = None
    for item in project.get("items", []):
        if item["type"] == "heading":
            current_heading = item["title"]
            lines.append(f"\n## {current_heading}")
        elif item["type"] == "to-do":
            prefix = "    -" if current_heading else "-"
            status = "✓" if item["status"] == "completed" else "○"
            lines.append(f"{prefix} {status} {item['title']}")
    
    return "\n".join(lines)
```

#### URL Scheme Reference
```
Add heading:
  things:///add?type=heading&list-id=<project_uuid>&heading=<title>[&after=<uuid>]

Move todo under heading:
  things:///update?id=<todo_uuid>&heading=<heading_uuid>
```

---

### 1.3 Enhanced Filters Design

#### Implementation Strategy
1. **Extend existing tools** rather than creating new ones
2. **Optional parameters** maintain backward compatibility
3. **Validation layer** ensures correct parameter combinations

```python
# Example: Enhanced get-inbox
@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def get_inbox(
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    type: Optional[str] = None,  # NEW
    status: Optional[str] = "incomplete",  # NEW (was hardcoded)
    last: Optional[str] = None,  # NEW
    include_items: bool = False,  # NEW
    ctx: Optional[Context] = None
) -> str:
    """Get items in Inbox with enhanced filtering."""
    
    # Validate new parameters
    if type and type not in ["to-do", "project", "heading"]:
        return f"Invalid type: {type}. Must be to-do, project, or heading"
    
    if last and not re.match(r"^\d+[dwy]$", last):
        return f"Invalid last format: {last}. Use format: 3d, 5w, 1y"
    
    # Build query with new parameters
    items = things.inbox(
        type=type,
        status=status,
        last=last,
        include_items=include_items
    )
    
    # Rest of implementation...
```

#### Parameter Validation
```python
# Shared validation helpers
def validate_type(type_val: Optional[str]) -> bool:
    return type_val in ["to-do", "project", "heading", None]

def validate_status(status_val: Optional[str]) -> bool:
    return status_val in ["incomplete", "completed", "canceled", None]

def validate_last(last_val: Optional[str]) -> bool:
    if not last_val:
        return True
    return bool(re.match(r"^\d+[dwy]$", last_val))

def validate_deadline_filter(deadline: Optional[str]) -> bool:
    """Validate deadline parameter format."""
    if not deadline:
        return True
    
    # Boolean
    if deadline in [True, False]:
        return True
    
    # Operators: "<=2025-11-01", ">2025-11-01", "2025-11-01"
    pattern = r"^(<=|>=|<|>)?\d{4}-\d{2}-\d{2}$"
    return bool(re.match(pattern, str(deadline)))
```

---

## Phase 2: Interactive Workflows

### 2.1 Bulk Operations Pattern

#### Elicitation Workflow Design
```python
@mcp.tool(annotations=MODIFY_ANNOTATIONS)
async def bulk_complete_todos(ctx: Context) -> str:
    """Complete multiple todos at once with preview and confirmation."""
    
    # Step 1: Elicit filter criteria
    await ctx.info("Let's find todos to complete...")
    
    filter_type = await ctx.elicit(
        "How to filter? (tag/project/area/all)",
        response_type=str
    )
    
    if filter_type["action"] != "accept":
        return "Operation cancelled"
    
    filter_value = None
    if filter_type["value"] != "all":
        filter_value = await ctx.elicit(
            f"Which {filter_type['value']}?",
            response_type=str
        )
        if filter_value["action"] != "accept":
            return "Operation cancelled"
        filter_value = filter_value["value"]
    
    # Step 2: Find matching todos
    if filter_type["value"] == "tag":
        items = things.tasks(tag=filter_value, status="incomplete")
    elif filter_type["value"] == "project":
        items = things.tasks(project=filter_value, status="incomplete")
    elif filter_type["value"] == "area":
        items = things.tasks(area=filter_value, status="incomplete")
    else:
        items = things.tasks(status="incomplete")
    
    # Step 3: Preview
    count = len(items)
    await ctx.info(f"Found {count} matching todos")
    
    if count == 0:
        return "No todos found matching criteria"
    
    if count > 100:
        return f"Too many items ({count}). Please refine your filter (max 100)"
    
    # Show preview (first 10)
    preview_lines = ["Preview of items to complete:"]
    for item in items[:10]:
        preview_lines.append(f"  - {item['title']}")
    if count > 10:
        preview_lines.append(f"  ... and {count - 10} more")
    
    await ctx.info("\n".join(preview_lines))
    
    # Step 4: Confirm
    confirm = await ctx.elicit(
        f"Complete all {count} todos? (yes/no)",
        response_type=str
    )
    
    if confirm["action"] != "accept" or confirm["value"].lower() != "yes":
        return "Operation cancelled"
    
    # Step 5: Execute
    await ctx.info(f"Completing {count} todos...")
    
    # Batch URL scheme call
    url_parts = ["things:///update"]
    for i, item in enumerate(items):
        separator = "?" if i == 0 else "&"
        url_parts.append(f"{separator}id={item['uuid']}&completed=true")
    
    url = "".join(url_parts)
    result = execute_url(url)
    
    # Step 6: Report
    cache.clear()
    return f"✓ Completed {count} todos"
```

#### Safety Features
1. **Preview before action**: Show what will be affected
2. **Count limits**: Max 100 items per operation
3. **Explicit confirmation**: User must type "yes"
4. **Progress updates**: ctx.info() at each step
5. **Cancellation**: User can cancel at any elicitation step

---

### 2.2 Template System Design

#### Template Storage Format
```json
{
  "template_product_launch": {
    "name": "Product Launch",
    "description": "Standard process for launching new products",
    "version": "1.0",
    "variables": {
      "product_name": {
        "type": "string",
        "description": "Name of the product being launched",
        "required": true
      },
      "area_uuid": {
        "type": "area",
        "description": "Area to create project in",
        "required": false,
        "default": null
      },
      "launch_date": {
        "type": "date",
        "description": "Target launch date",
        "required": false,
        "default": null
      }
    },
    "structure": {
      "project": {
        "title": "Launch {{product_name}}",
        "notes": "Launch scheduled for {{launch_date}}",
        "area": "{{area_uuid}}",
        "tags": ["Launch", "Important"]
      },
      "headings": [
        {
          "title": "Planning Phase",
          "todos": [
            {
              "title": "Define {{product_name}} scope",
              "tags": ["Planning"],
              "notes": "Create detailed scope document"
            },
            {
              "title": "Set timeline and milestones",
              "tags": ["Planning"]
            }
          ]
        },
        {
          "title": "Development Phase",
          "todos": [
            {
              "title": "Build core features",
              "tags": ["Development"],
              "checklist": [
                "Feature 1",
                "Feature 2",
                "Feature 3"
              ]
            }
          ]
        },
        {
          "title": "Launch Phase",
          "todos": [
            {
              "title": "Launch {{product_name}}",
              "deadline": "{{launch_date}}",
              "tags": ["Launch", "Critical"]
            }
          ]
        }
      ]
    }
  }
}
```

#### Template Creation Workflow
```python
@mcp.tool(annotations=MODIFY_ANNOTATIONS)
async def save_project_as_template(
    project_uuid: str,
    template_name: str,
    ctx: Context
) -> str:
    """Save an existing project as a reusable template."""
    
    # Step 1: Fetch project structure
    await ctx.info(f"Fetching project structure...")
    project = things.projects(uuid=project_uuid, include_items=True)
    
    if not project:
        return f"Project {project_uuid} not found"
    
    # Step 2: Extract structure
    template = {
        "name": template_name,
        "description": "",
        "version": "1.0",
        "variables": {},
        "structure": {
            "project": {
                "title": project["title"],
                "notes": project.get("notes", ""),
                "area": project.get("area"),
                "tags": project.get("tags", [])
            },
            "headings": []
        }
    }
    
    # Parse items into headings structure
    current_heading = None
    for item in project.get("items", []):
        if item["type"] == "heading":
            current_heading = {
                "title": item["title"],
                "todos": []
            }
            template["structure"]["headings"].append(current_heading)
        elif item["type"] == "to-do" and current_heading:
            todo_data = {
                "title": item["title"],
                "tags": item.get("tags", []),
                "notes": item.get("notes", "")
            }
            if item.get("checklist"):
                checklist_items = things.checklist_items(item["uuid"])
                todo_data["checklist"] = [ci["title"] for ci in checklist_items]
            current_heading["todos"].append(todo_data)
    
    # Step 3: Identify variables (elicit which fields to parameterize)
    await ctx.info("Template structure extracted. Now let's identify variables...")
    
    parameterize = await ctx.elicit(
        "Would you like to add variables (e.g., {{project_name}})? (yes/no)",
        response_type=str
    )
    
    if parameterize["action"] == "accept" and parameterize["value"].lower() == "yes":
        # Interactive variable definition
        # (Simplified here - full version would elicit each field)
        template["variables"]["project_name"] = {
            "type": "string",
            "description": "Name for this project",
            "required": True
        }
        template["structure"]["project"]["title"] = f"{template_name} {{{{project_name}}}}"
    
    # Step 4: Add description
    desc = await ctx.elicit(
        "Enter template description:",
        response_type=str
    )
    if desc["action"] == "accept":
        template["description"] = desc["value"]
    
    # Step 5: Save to state
    await ctx.set_state(f"template_{template_name}", template)
    
    return f"✓ Saved template: {template_name}"
```

#### Template Usage Workflow
```python
@mcp.tool(annotations=MODIFY_ANNOTATIONS)
async def create_from_template(
    template_name: str,
    ctx: Context
) -> str:
    """Create a new project from a saved template."""
    
    # Step 1: Load template
    template = await ctx.get_state(f"template_{template_name}")
    
    if not template:
        return f"Template '{template_name}' not found"
    
    # Step 2: Collect variable values
    await ctx.info(f"Creating from template: {template['name']}")
    await ctx.info(f"Description: {template['description']}")
    
    variables = {}
    for var_name, var_config in template["variables"].items():
        value = await ctx.elicit(
            f"{var_config['description']} ({var_name}):",
            response_type=str
        )
        
        if value["action"] != "accept":
            return "Template creation cancelled"
        
        variables[var_name] = value["value"]
    
    # Step 3: Substitute variables in structure
    structure = _substitute_template_variables(
        template["structure"],
        variables
    )
    
    # Step 4: Show preview
    preview = f"""
Project: {structure['project']['title']}
Headings: {len(structure['headings'])}
Total Todos: {sum(len(h['todos']) for h in structure['headings'])}
"""
    await ctx.info(preview)
    
    confirm = await ctx.elicit(
        "Create this project? (yes/no)",
        response_type=str
    )
    
    if confirm["action"] != "accept" or confirm["value"].lower() != "yes":
        return "Template creation cancelled"
    
    # Step 5: Create via URL scheme
    await ctx.info("Creating project structure...")
    
    # Build complex URL scheme call
    url = _build_project_creation_url(structure)
    result = execute_url(url)
    
    cache.clear()
    return f"✓ Created project from template: {template['name']}"

def _substitute_template_variables(structure: dict, variables: dict) -> dict:
    """Replace {{variable}} placeholders with actual values."""
    import json
    import re
    
    # Serialize to JSON, do regex substitution, deserialize
    json_str = json.dumps(structure)
    
    for var_name, var_value in variables.items():
        pattern = r"\{\{" + re.escape(var_name) + r"\}\}"
        json_str = re.sub(pattern, var_value, json_str)
    
    return json.loads(json_str)
```

#### State Management Configuration
```python
# In server initialization
# State stored in: ~/.things-fastmcp/state/
# Format: JSON files per user/session
# FastMCP handles persistence automatically

# State keys:
# - template_{name}: Template definitions
# - cache_stats: Analytics cache (future)
# - user_preferences: User settings (future)
```

---

## Phase 3: Intelligence Layer

### 3.1 Analytics Design

#### Computation Strategy
```python
# Option 1: On-demand computation (Phase 3 initial)
@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def get_productivity_stats(
    period: str = "week",  # day, week, month
    ctx: Optional[Context] = None
) -> str:
    """Calculate productivity statistics."""
    
    # Compute on each call
    stats = _compute_productivity_stats(period)
    
    # Format and return
    return _format_stats(stats)

# Option 2: Cached computation (future optimization)
@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def get_productivity_stats_cached(
    period: str = "week",
    ctx: Context = None
) -> str:
    """Calculate productivity statistics (cached)."""
    
    cache_key = f"stats_{period}_{date.today()}"
    
    # Check cache
    cached = await ctx.get_state(cache_key)
    if cached:
        return cached
    
    # Compute
    stats = _compute_productivity_stats(period)
    result = _format_stats(stats)
    
    # Cache for 1 hour (state expiry)
    await ctx.set_state(cache_key, result, ttl=3600)
    
    return result
```

#### Analytics Calculations
```python
def _compute_productivity_stats(period: str) -> dict:
    """Compute completion statistics."""
    
    # Determine date range
    today = date.today()
    if period == "day":
        start_date = today
    elif period == "week":
        start_date = today - timedelta(days=7)
    elif period == "month":
        start_date = today - timedelta(days=30)
    
    # Query completed items
    completed = things.completed(
        stop_date=f">={start_date.isoformat()}",
        count_only=False
    )
    
    # Group by day
    by_day = {}
    for item in completed:
        day = item["stop_date"][:10]  # YYYY-MM-DD
        by_day[day] = by_day.get(day, 0) + 1
    
    # Calculate statistics
    total = len(completed)
    avg_per_day = total / (today - start_date).days
    
    # Trend (compare to previous period)
    prev_start = start_date - timedelta(days=(today - start_date).days)
    prev_completed = things.completed(
        stop_date=f">={prev_start.isoformat()}",
        count_only=True
    )
    trend = "up" if total > prev_completed else "down"
    trend_pct = abs((total - prev_completed) / prev_completed * 100) if prev_completed else 0
    
    return {
        "period": period,
        "total": total,
        "avg_per_day": avg_per_day,
        "by_day": by_day,
        "trend": trend,
        "trend_pct": trend_pct
    }
```

---

### 3.2 Natural Language Parsing

#### Date Parser Implementation
```python
import dateparser
from datetime import datetime, time

def parse_natural_date(text: str) -> dict:
    """Parse natural language into Things-compatible date/time."""
    
    # Use dateparser library
    parsed = dateparser.parse(
        text,
        settings={
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': datetime.now()
        }
    )
    
    if not parsed:
        return {"success": False, "error": "Could not parse date"}
    
    # Extract components
    result = {
        "success": True,
        "date": parsed.date().isoformat(),  # YYYY-MM-DD
        "time": None,
        "has_time": False,
        "interpretation": None
    }
    
    # Check if time was specified
    if parsed.hour != 0 or parsed.minute != 0:
        result["time"] = parsed.time().isoformat()[:5]  # HH:MM
        result["has_time"] = True
    
    # Generate human-readable interpretation
    if result["has_time"]:
        result["interpretation"] = parsed.strftime("%A, %B %d, %Y at %I:%M %p")
    else:
        result["interpretation"] = parsed.strftime("%A, %B %d, %Y")
    
    return result

# Usage examples:
# parse_natural_date("tomorrow") → 2025-11-02
# parse_natural_date("next Monday at 5pm") → 2025-11-04, 17:00
# parse_natural_date("in 3 days") → 2025-11-04
# parse_natural_date("Aug 15") → 2025-08-15
```

#### Integration with Elicitation
```python
@mcp.tool(annotations=MODIFY_ANNOTATIONS)
async def schedule_with_natural_language(
    todo_uuid: str,
    natural_text: str,
    ctx: Context
) -> str:
    """Schedule a todo using natural language."""
    
    # Step 1: Parse
    parsed = parse_natural_date(natural_text)
    
    if not parsed["success"]:
        return f"Could not understand date: {natural_text}"
    
    # Step 2: Confirm interpretation
    await ctx.info(f"I understood: {parsed['interpretation']}")
    
    confirm = await ctx.elicit(
        "Is this correct? (yes/no/retry)",
        response_type=str
    )
    
    if confirm["action"] != "accept":
        return "Cancelled"
    
    if confirm["value"].lower() == "retry":
        new_text = await ctx.elicit(
            "Enter new date/time:",
            response_type=str
        )
        if new_text["action"] == "accept":
            return await schedule_with_natural_language(
                todo_uuid,
                new_text["value"],
                ctx
            )
        return "Cancelled"
    
    if confirm["value"].lower() != "yes":
        return "Cancelled"
    
    # Step 3: Build URL
    url = f"things:///update?id={todo_uuid}&when={parsed['date']}"
    
    if parsed["has_time"]:
        # Add reminder
        reminder_time = f"{parsed['date']} {parsed['time']}"
        url += f"&remind-at={urllib.parse.quote(reminder_time)}"
    
    # Step 4: Execute
    result = execute_url(url)
    cache.clear()
    
    return f"✓ Scheduled for {parsed['interpretation']}"
```

---

## Error Handling

### Consistent Error Pattern
```python
def handle_mcp_error(tool_name: str, error: Exception) -> CallToolResult:
    """Standardized error handling for all tools."""
    
    error_msg = f"Error in {tool_name}: {str(error)}"
    logger.error(error_msg, exc_info=True)
    
    return CallToolResult(
        content=[TextContent(type="text", text=error_msg)],
        isError=True
    )
```

### Validation Errors
```python
# Parameter validation
if not validate_type(type_param):
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=f"Invalid type: {type_param}. Must be to-do, project, or heading"
        )],
        isError=True
    )

# Resource not found
if not item:
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=f"Item {uuid} not found"
        )],
        isError=True
    )

# Operation limits
if count > 100:
    return CallToolResult(
        content=[TextContent(
            type="text",
            text=f"Too many items ({count}). Please refine filter (max 100)"
        )],
        isError=True
    )
```

---

## Performance Considerations

### Response Time Targets
- Simple queries (get-inbox): < 100ms
- Complex queries (analytics): < 500ms
- Interactive workflows: No limit (user-driven)
- Bulk operations: < 2s for 100 items

### Optimization Strategies

#### 1. Database Queries
```python
# Use count_only when possible
count = things.inbox(count_only=True)  # Fast

# vs
items = things.inbox()
count = len(items)  # Slower (fetches all data)
```

#### 2. Analytics Caching
```python
# Phase 3.1: No caching (acceptable for initial release)
# Future: Cache analytics results for 1 hour
# Use state management with TTL
```

#### 3. Batch Operations
```python
# Single URL scheme call for multiple items
# vs multiple AppleScript calls
url = "things:///update?id=uuid1&completed=true&id=uuid2&completed=true"
```

---

## Testing Strategy

### Unit Tests
```python
# Test each new tool independently
def test_get_checklist_items():
    # Mock things.checklist_items
    # Assert output format
    pass

def test_add_heading():
    # Mock URL scheme execution
    # Assert correct URL construction
    pass
```

### Integration Tests
```python
# Test workflows end-to-end
async def test_bulk_complete_workflow():
    # Mock elicitation responses
    # Assert correct execution
    # Verify cache invalidation
    pass
```

### Performance Tests
```python
def test_response_times():
    # Measure p50, p95, p99
    # Assert under targets
    pass
```

---

## Migration & Rollback

### Version Migration
- **v2.0.0 → v2.1.0**: No migration needed (additive changes)
- **v2.1.0 → v2.2.0**: State management initialized automatically
- **v2.2.0 → v2.3.0**: No migration needed

### Rollback Strategy
- All changes are backward compatible
- State files can be deleted safely (templates lost)
- No database schema changes

---

## Security Considerations

### State Management
- Templates stored per-user (isolation)
- No sensitive data in templates (UUIDs only)
- State files readable only by user

### URL Scheme
- All operations go through Things security
- No direct database writes
- AppleScript bridge maintains audit trail

### Input Validation
- All user input sanitized before URL encoding
- Parameter validation before queries
- Elicitation prevents accidental destructive operations
