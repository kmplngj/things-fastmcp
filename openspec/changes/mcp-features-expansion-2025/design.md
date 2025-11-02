# Design Document: MCP Features Expansion

**Proposal**: mcp-features-expansion-2025  
**Version**: v4.0.0  
**Author**: GitHub Copilot AI Assistant  
**Date**: 2025-11-02  
**Status**: 📐 Design Phase

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prompts Design](#prompts-design)
3. [Resources Design](#resources-design)
4. [Sampling Design](#sampling-design)
5. [Notifications Design](#notifications-design)
6. [Data Models](#data-models)
7. [API Specifications](#api-specifications)
8. [Performance Considerations](#performance-considerations)
9. [Security Considerations](#security-considerations)
10. [Testing Strategy](#testing-strategy)

---

## Architecture Overview

### Current Architecture (v3.0.0)
```
things-fastmcp/
├── src/things_mcp/
│   ├── fast_server.py       # 43 tools (18 core + 25 advanced)
│   ├── handlers.py           # Tool implementations
│   ├── applescript_bridge.py # Things database access
│   ├── cache.py              # Caching layer
│   ├── url_scheme.py         # Things URL scheme
│   └── utils.py              # Utilities
```

### Enhanced Architecture (v4.0.0)
```
things-fastmcp/
├── src/things_mcp/
│   ├── fast_server.py       # MCP server initialization
│   ├── tools/               # Tool implementations (43 tools)
│   │   ├── core.py
│   │   ├── analytics.py
│   │   └── sampling.py      # NEW: 5 sampling tools
│   ├── prompts.py           # NEW: 15 prompt templates
│   ├── resources.py         # NEW: 22 resources
│   ├── handlers.py          # Existing handlers
│   ├── applescript_bridge.py
│   ├── cache.py
│   ├── url_scheme.py
│   └── utils.py
```

### Component Interaction Diagram
```
┌─────────────────────────────────────────────────────────┐
│                    MCP Client                           │
│              (Claude Desktop, VS Code, etc.)            │
└────────────┬───────────┬──────────┬──────────┬──────────┘
             │           │          │          │
             │           │          │          │
        ┌────▼────┐ ┌────▼────┐ ┌──▼───┐ ┌────▼─────┐
        │ Tools   │ │ Prompts │ │Resour│ │ Sampling │
        │ (43)    │ │ (15)    │ │ces   │ │ Handler  │
        └────┬────┘ └────┬────┘ │(22)  │ └────┬─────┘
             │           │      └──┬───┘      │
             │           │         │          │
             └───────────┴─────────┴──────────┘
                         │
                    ┌────▼────┐
                    │FastMCP  │
                    │ Server  │
                    └────┬────┘
                         │
             ┌───────────┴────────────┐
             │                        │
        ┌────▼────┐            ┌─────▼──────┐
        │ Things  │            │   Cache    │
        │Database │            │            │
        │(SQLite) │            │ (DiskStore)│
        └─────────┘            └────────────┘
```

---

## Prompts Design

### Prompt Structure

#### Base Prompt Template
```python
from fastmcp import FastMCP
from fastmcp.prompts import PromptMessage, TextContent
from typing import Optional

@mcp.prompt(
    name="prompt-name",
    description="Clear description of what this prompt does",
    tags={"category", "subcategory", "feature"}
)
async def prompt_function(
    required_param: str,
    optional_param: Optional[str] = None,
    ctx: Optional[Context] = None  # For logging/progress
) -> PromptMessage:
    """
    Docstring with:
    - Purpose
    - Parameters explained
    - Example usage
    - Expected LLM behavior
    """
    
    # Build message content
    content = f"Generated prompt text..."
    
    # Optional: Use ctx for logging
    if ctx:
        await ctx.info(f"Generated prompt for {required_param}")
    
    return PromptMessage(
        role="user",  # or "assistant" for multi-turn
        content=TextContent(type="text", text=content)
    )
```

### Prompt Categories

#### 1. Task Creation Prompts

**Design Pattern**: Structured input → Natural language task request
```python
@mcp.prompt(
    name="create-task-with-deadline",
    tags={"things3", "task_creation", "deadline"}
)
async def create_task_with_deadline_prompt(
    task_name: str,
    deadline: str,
    project: Optional[str] = None,
    tags: Optional[list[str]] = None,
    notes: Optional[str] = None
) -> PromptMessage:
    content = f"""Create a task in Things 3 with the following details:

**Task**: {task_name}
**Deadline**: {deadline} (format: YYYY-MM-DD or 'today'/'tomorrow')
"""
    if project:
        content += f"**Project**: {project}\n"
    if tags:
        content += f"**Tags**: {', '.join(tags)}\n"
    if notes:
        content += f"**Notes**: {notes}\n"
    
    content += """
Please use the `add-todo` tool with these parameters:
- title: The task name
- deadline: The deadline date
- project: The project name (optional)
- tags: List of tags (optional)
- notes: Additional notes (optional)
"""
    
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
```

#### 2. Project Planning Prompts

**Design Pattern**: Goal-oriented → Structured project setup
```python
@mcp.prompt(
    name="start-new-project",
    tags={"things3", "project_planning", "setup"}
)
async def start_new_project_prompt(
    project_name: str,
    goal: str,
    deadline: Optional[str] = None,
    area: Optional[str] = None
) -> PromptMessage:
    content = f"""Create a new project in Things 3 for: {project_name}

**Goal**: {goal}
"""
    if deadline:
        content += f"**Target Completion**: {deadline}\n"
    if area:
        content += f"**Area**: {area}\n"
    
    content += """
Please help me:
1. Break down this goal into major phases (3-5 phases)
2. Create the project with appropriate headings
3. Suggest initial tasks for the first phase
4. Recommend relevant tags

Use these tools:
- `add-project` to create the project
- `manage-heading` with action="add" to create phase headings
- `add-todo` to create initial tasks
"""
    
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
```

#### 3. Review & Reflection Prompts

**Design Pattern**: Context gathering → Analytical questions
```python
@mcp.prompt(
    name="reflect-on-completed-tasks",
    tags={"things3", "review", "reflection"}
)
async def reflect_on_completed_tasks_prompt(
    days: int = 7,
    project: Optional[str] = None
) -> PromptMessage:
    content = f"""Let's review my completed tasks from the last {days} days.

Please use the `list-items` tool with:
- list_type: "logbook"
- limit: {days * 5}  # Estimate ~5 tasks/day

Then analyze:
1. **Productivity Patterns**: What types of tasks did I complete most?
2. **Time Allocation**: Which projects/areas got the most attention?
3. **Completion Speed**: Any tasks that took longer than expected?
4. **Success Factors**: What helped me complete these tasks?
5. **Improvement Areas**: What could I do better?
"""
    
    if project:
        content += f"\nFocus specifically on the project: {project}"
    
    return PromptMessage(role="user", content=TextContent(type="text", text=content))
```

### Prompt Metadata Schema

```python
from dataclasses import dataclass
from typing import Set, Optional

@dataclass
class PromptMetadata:
    """Metadata for prompt categorization and filtering."""
    name: str
    description: str
    tags: Set[str]
    category: str  # TaskCreation, ProjectPlanning, Review, Workflow
    estimated_tokens: int  # Estimated output size
    requires_tools: list[str]  # Tools that prompt recommends using
    examples: list[str]  # Usage examples
```

---

## Resources Design

### URI Namespace Design

#### Hierarchical Structure
```
things://                           # Root namespace
├── projects/                       # Project resources
│   ├── list                       # Static: all projects
│   └── {uuid}/                    # Template: single project
│       ├── info                   # Static: project details
│       ├── todos                  # Static: project todos
│       ├── structure              # Static: hierarchy
│       └── notes                  # Static: project notes (text/plain)
├── areas/                          # Area resources
│   ├── list                       # Static: all areas
│   └── {uuid}/                    # Template: single area
│       ├── info                   # Static: area details
│       └── projects               # Static: projects in area
├── tags/                           # Tag resources
│   ├── list                       # Static: all tags
│   └── {name}/                    # Template: tag by name
│       └── items                  # Static: items with tag
├── todos/                          # Todo list resources
│   ├── inbox                      # Static: inbox items
│   ├── today                      # Static: today's tasks
│   ├── upcoming                   # Static: upcoming scheduled
│   ├── anytime                    # Static: anytime list
│   ├── someday                    # Static: someday/maybe
│   ├── logbook                    # Static: completed (paginated)
│   └── {uuid}/                    # Template: single todo
│       ├── info                   # Static: todo details
│       ├── checklist              # Static: checklist items
│       └── notes                  # Static: todo notes (text/plain)
├── search/                         # Search resources
│   └── {query}/                   # Template: search results
│       ├── todos                  # Static: matching todos
│       ├── projects               # Static: matching projects
│       └── all                    # Static: all results
├── deadlines/                      # Deadline resources
│   ├── overdue                    # Static: overdue items
│   └── due-soon                   # Static: due in next 7 days
└── analytics/                      # Analytics resources
    ├── summary                    # Static: overall stats
    ├── velocity                   # Static: completion rate
    └── tags                       # Static: tag usage stats
```

### Resource Implementation Patterns

#### Pattern 1: Static List Resource
```python
@mcp.resource(
    uri="things://projects/list",
    name="All Projects",
    description="Complete list of all projects in Things 3",
    mime_type="application/json",
    annotations={
        "readOnlyHint": True,
        "idempotentHint": True,
        "cacheable": True,
        "cacheMaxAge": 300  # 5 minutes
    }
)
async def get_projects_list_resource(ctx: Optional[Context] = None) -> dict:
    """Returns all projects with metadata."""
    
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
                    "todo_count": len(things.todos(project=p["uuid"])),
                    "created": p.get("created"),
                    "modified": p.get("modified")
                }
                for p in projects
            ]
        }
        
        if ctx:
            await ctx.info(f"Returned {len(projects)} projects")
        
        return result
        
    except Exception as e:
        return {"error": str(e), "resource_uri": "things://projects/list"}
```

#### Pattern 2: Resource Template with Single Parameter
```python
@mcp.resource(
    uri="things://projects/{project_uuid}/info",
    name="Project Details",
    description="Complete details for a specific project",
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True}
)
async def get_project_info_resource(
    project_uuid: str,
    ctx: Optional[Context] = None
) -> dict:
    """Returns full project details."""
    
    try:
        project = things.get(uuid=project_uuid)
        
        if not project:
            return {
                "error": "Project not found",
                "uuid": project_uuid,
                "resource_uri": f"things://projects/{project_uuid}/info"
            }
        
        if not isinstance(project, dict):
            return {"error": "Invalid project data"}
        
        # Enrich with additional data
        todos = things.todos(project=project_uuid)
        incomplete_count = len([t for t in todos if t["status"] == "incomplete"])
        completed_count = len([t for t in todos if t["status"] == "completed"])
        
        result = {
            **project,  # All project fields
            "resource_uri": f"things://projects/{project_uuid}/info",
            "todo_stats": {
                "total": len(todos),
                "incomplete": incomplete_count,
                "completed": completed_count,
                "completion_rate": (completed_count / len(todos) * 100) if todos else 0
            }
        }
        
        return result
        
    except Exception as e:
        return {"error": str(e), "uuid": project_uuid}
```

#### Pattern 3: Resource Template with Multiple Parameters
```python
@mcp.resource(
    uri="things://search/{query}/todos",
    name="Search Todos",
    description="Search results filtered to todos only",
    mime_type="application/json",
    annotations={"readOnlyHint": True}
)
async def search_todos_resource(
    query: str,
    ctx: Optional[Context] = None
) -> dict:
    """Returns search results for todos."""
    
    try:
        # URL decode query
        import urllib.parse
        decoded_query = urllib.parse.unquote(query)
        
        # Search
        results = things.search(decoded_query)
        
        # Filter to todos only
        todos = [r for r in results if r.get("type") == "to-do"]
        
        result = {
            "resource_uri": f"things://search/{query}/todos",
            "query": decoded_query,
            "count": len(todos),
            "results": todos
        }
        
        if ctx:
            await ctx.info(f"Found {len(todos)} todos for query: {decoded_query}")
        
        return result
        
    except Exception as e:
        return {"error": str(e), "query": query}
```

#### Pattern 4: Text Resource (Notes)
```python
@mcp.resource(
    uri="things://todos/{todo_uuid}/notes",
    name="Todo Notes",
    description="Notes content for a specific todo",
    mime_type="text/plain",
    annotations={"readOnlyHint": True, "idempotentHint": True}
)
async def get_todo_notes_resource(
    todo_uuid: str,
    ctx: Optional[Context] = None
) -> str:
    """Returns todo notes as plain text."""
    
    try:
        todo = things.get(uuid=todo_uuid)
        
        if not todo:
            return f"Error: Todo not found (uuid: {todo_uuid})"
        
        if not isinstance(todo, dict):
            return "Error: Invalid todo data"
        
        notes = todo.get("notes", "")
        
        if not notes:
            return "(No notes)"
        
        return notes
        
    except Exception as e:
        return f"Error: {str(e)}"
```

#### Pattern 5: Binary Resource (Export)
```python
@mcp.resource(
    uri="things://projects/{project_uuid}/export",
    name="Project Export",
    description="Export project as JSON file",
    mime_type="application/json"
)
async def export_project_resource(
    project_uuid: str,
    ctx: Optional[Context] = None
) -> bytes:
    """Export project as downloadable JSON."""
    
    try:
        project = things.get(uuid=project_uuid)
        
        if not project:
            error_data = {"error": "Project not found", "uuid": project_uuid}
            return json.dumps(error_data, indent=2).encode('utf-8')
        
        # Get all related data
        todos = things.todos(project=project_uuid)
        
        export_data = {
            "project": project,
            "todos": todos,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format_version": "1.0"
        }
        
        # Convert to JSON bytes
        json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
        return json_str.encode('utf-8')
        
    except Exception as e:
        error_data = {"error": str(e)}
        return json.dumps(error_data).encode('utf-8')
```

### Resource Metadata Schema

```python
@dataclass
class ResourceMetadata:
    """Metadata for resource documentation."""
    uri: str
    name: str
    description: str
    mime_type: str
    is_template: bool  # Has {parameters}
    parameters: list[str]  # Parameter names
    read_only: bool
    idempotent: bool
    cacheable: bool
    cache_max_age: int  # Seconds
    example_uris: list[str]
```

---

## Sampling Design

### Sampling Architecture

```
┌──────────────────┐
│   MCP Client     │ ← Provides sampling_handler
│ (Claude Desktop) │
└─────────┬────────┘
          │
          │ 1. Tool call with ctx
          ▼
┌──────────────────┐
│  Sampling Tool   │
│  (Server-side)   │
└─────────┬────────┘
          │
          │ 2. ctx.sample(messages, params)
          ▼
┌──────────────────┐
│  FastMCP Server  │
└─────────┬────────┘
          │
          │ 3. MCP sampling request
          ▼
┌──────────────────┐
│  MCP Client      │ → Calls sampling_handler
│  sampling_handler│ → Calls LLM API (Claude/GPT)
└─────────┬────────┘
          │
          │ 4. LLM response
          ▼
┌──────────────────┐
│  Sampling Tool   │ ← Parses response
│  Returns result  │
└──────────────────┘
```

### Sampling Tool Pattern

```python
from fastmcp.server.context import Context
from mcp.types import SamplingMessage

@mcp.tool(
    name="tool-with-sampling",
    description="Uses LLM for intelligent processing"
)
async def tool_with_sampling(
    input_data: str,
    ctx: Context  # Required for sampling
) -> dict:
    """Tool that uses server-initiated LLM requests."""
    
    try:
        # 1. Gather context from Things database
        context_data = things.get_relevant_data()
        
        # 2. Build sampling prompt
        prompt = f"""Analyze this data and provide insights:

Input: {input_data}

Context: {context_data}

Provide your analysis in JSON format with keys: insights, recommendations, confidence.
"""
        
        # 3. Request LLM sampling
        response = await ctx.sample(
            messages=prompt,
            model_preferences=["claude-3-5-sonnet-20241022", "gpt-4o"],
            temperature=0.3,  # Lower = more deterministic
            max_tokens=500
        )
        
        # 4. Parse LLM response
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            result = {
                "raw_response": response.text,
                "parsed": False
            }
        
        return result
        
    except AttributeError as e:
        # Missing sampling handler
        return {
            "error": "Sampling not available",
            "message": "This tool requires LLM sampling support. Please configure a sampling_handler in your MCP client.",
            "fallback": "Use non-AI version of this tool instead."
        }
    except Exception as e:
        return {"error": str(e)}
```

### Error Handling Strategy

```python
async def safe_sample(
    ctx: Context,
    prompt: str,
    fallback_value: Any = None,
    **kwargs
) -> dict:
    """Wrapper for safe sampling with fallback."""
    
    try:
        response = await ctx.sample(messages=prompt, **kwargs)
        return {"success": True, "data": response.text}
    except AttributeError:
        # No sampling handler configured
        return {
            "success": False,
            "error": "sampling_unavailable",
            "message": "Sampling handler not configured in MCP client",
            "fallback": fallback_value
        }
    except Exception as e:
        # Other sampling errors
        return {
            "success": False,
            "error": "sampling_failed",
            "message": str(e),
            "fallback": fallback_value
        }
```

---

## Notifications Design

### Notification Types

#### 1. Auto-Notifications (FastMCP Built-in)
- `notifications/prompts/list_changed` - Automatic when prompts added/removed/enabled/disabled
- `notifications/resources/list_changed` - Automatic when resources added/removed/enabled/disabled
- `notifications/tools/list_changed` - Automatic when tools added/removed/enabled/disabled

#### 2. Progress Notifications (Manual)
```python
@mcp.tool(name="long-running-operation")
async def long_running_operation(ctx: Context) -> str:
    """Example of progress reporting."""
    
    total_steps = 100
    
    for i in range(total_steps):
        # Do work
        await asyncio.sleep(0.1)
        
        # Report progress
        if i % 10 == 0:
            await ctx.report_progress(
                progress=i,
                total=total_steps,
                message=f"Processing step {i}/{total_steps}"
            )
    
    await ctx.report_progress(total_steps, total_steps, "Complete!")
    return "✅ Operation complete"
```

---

## Data Models

### Prompt Data Models

```python
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class PromptMetadata:
    name: str
    description: str
    tags: set[str]
    category: str
    requires_tools: List[str]
    estimated_tokens: int

@dataclass
class PromptResult:
    role: str  # "user" or "assistant"
    content: str
    metadata: PromptMetadata
```

### Resource Data Models

```python
@dataclass
class ResourceInfo:
    uri: str
    name: str
    description: str
    mime_type: str
    is_template: bool
    parameters: List[str]
    annotations: dict

@dataclass
class ResourceResult:
    uri: str
    data: dict | str | bytes
    mime_type: str
    timestamp: str
```

### Sampling Data Models

```python
@dataclass
class SamplingRequest:
    prompt: str
    model_preferences: List[str]
    temperature: float
    max_tokens: int
    
@dataclass
class SamplingResponse:
    text: str
    model_used: str
    tokens_used: int
    success: bool
```

---

## API Specifications

### Prompt API

```python
# List all prompts
GET /prompts
Response: List[PromptInfo]

# Get single prompt
GET /prompts/{name}
Response: PromptInfo

# Execute prompt
POST /prompts/{name}
Body: {parameters}
Response: PromptMessage
```

### Resource API

```python
# List all resources
GET /resources
Response: List[ResourceInfo]

# Read resource
GET /resources/{uri}
Response: ResourceData (JSON/text/binary)

# Resource templates
GET /resources/things://projects/{uuid}/info
Response: ProjectData
```

### Sampling API (Client-side)

```python
# Client must provide this
async def sampling_handler(
    messages: List[SamplingMessage],
    params: SamplingParams,
    context: RequestContext
) -> str:
    # User's LLM integration
    return llm_response_text
```

---

## Performance Considerations

### Caching Strategy

```python
# Resource caching
@cached(ttl=300)  # 5 minutes
async def expensive_resource(): ...

# Tool caching (existing)
@cached(ttl=600)  # 10 minutes
async def expensive_analytics(): ...
```

### Pagination

```python
# Logbook resource with pagination
@mcp.resource("things://todos/logbook")
async def logbook_resource(
    limit: int = 100,
    offset: int = 0
) -> dict:
    todos = things.todos(area="logbook")[offset:offset+limit]
    return {
        "items": todos,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": len(todos) == limit
        }
    }
```

### Performance Targets

| Feature | Target | Notes |
|---------|--------|-------|
| Prompt generation | <50ms | Template rendering |
| Resource read (small) | <200ms | Single project |
| Resource read (large) | <500ms | All projects |
| Sampling | 2-5s | Depends on LLM API |
| Notification | <10ms | Async, non-blocking |

---

## Security Considerations

### Access Control
- All operations read-only except tools (no new security risks)
- Things database access via existing AppleScript bridge
- No network access (local database only)
- No authentication needed (macOS security model)

### Data Sanitization
```python
def sanitize_uri_param(param: str) -> str:
    """Sanitize URI parameters to prevent injection."""
    # Remove path traversal attempts
    param = param.replace("..", "")
    param = param.replace("/", "")
    return param
```

### Error Handling
- Never expose database paths
- Sanitize error messages
- Log security events

---

## Testing Strategy

### Unit Tests
```python
# Test prompt generation
async def test_create_task_prompt():
    result = await create_task_with_deadline_prompt(
        task_name="Test",
        deadline="2025-12-31"
    )
    assert "Test" in result.content.text
    assert "2025-12-31" in result.content.text

# Test resource read
async def test_projects_list_resource():
    result = await get_projects_list_resource()
    assert "projects" in result
    assert isinstance(result["projects"], list)

# Test sampling (mocked)
async def test_sampling_tool():
    mock_ctx = MockContext()
    mock_ctx.sample = AsyncMock(return_value=MockResponse("test"))
    result = await suggest_tags_ai("task", ctx=mock_ctx)
    assert "suggested_tags" in result
```

### Integration Tests
- Test in Claude Desktop
- Test with real Things database
- Test sampling with real LLM API
- Test notification delivery

### Performance Tests
- Measure resource read times
- Measure prompt generation times
- Measure sampling response times
- Load test with 1000+ items

---

**Status**: 📐 Design Complete  
**Next**: Begin implementation Phase 1 (Prompts)  
**Review**: Design approved, ready to code
