# MCP Features Expansion: Prompts, Resources, Sampling, Notifications

**Proposal ID**: `mcp-features-expansion-2025`  
**Created**: 2025-11-02  
**Status**: 📋 Planning  
**Target Version**: v4.0.0  
**Estimated Timeline**: 4-6 weeks

---

## Executive Summary

Expand things-fastmcp to leverage the full MCP protocol specification by adding:
1. **Prompts** - Reusable message templates for task creation and workflows
2. **Resources** - Expose Things 3 data as structured resources with URI templates
3. **Sampling** - Enable server-initiated LLM requests for intelligent suggestions
4. **Notifications** - Real-time updates for data changes

**Impact**: Transform from tool-only server → full-featured MCP server with all protocol capabilities

---

## Motivation

### Current State (v3.0.0)
- ✅ **Tools**: 43 tools (18 core + 25 advanced via opt-in)
- ❌ **Prompts**: None - users manually write creation prompts
- ❌ **Resources**: None - data only accessible via tools
- ❌ **Sampling**: None - no server-initiated intelligence
- ❌ **Notifications**: Partial - only tools/list_changed for dynamic management

### Problems This Solves

1. **Prompt Fatigue**: Users repeatedly write similar task creation prompts
   - "Create a task called X with deadline Y in project Z"
   - "Add a weekly review task every Monday"
   - Manual prompt engineering for common workflows

2. **Data Access Pattern Mismatch**: Tools require function calls for everything
   - Want to read project notes → must call `show-item` tool
   - Want to access all tags → must call `get-tags` tool
   - No way for AI to "browse" Things 3 data structure

3. **Lack of Intelligence**: Server can't use LLM for smart features
   - No AI-powered tag suggestions based on task content
   - No intelligent deadline recommendations
   - No natural language parsing for complex requests

4. **Limited Interactivity**: One-way communication (client → server)
   - No proactive notifications when tasks complete
   - No alerts when deadlines approach
   - No real-time sync feedback

---

## Goals

### Primary Goals
1. **Add 10-15 Prompts** for common Things 3 workflows
2. **Add 20-25 Resources** exposing Things 3 data hierarchy
3. **Add 3-5 Sampling Tools** for intelligent features
4. **Enhance Notifications** for real-time updates

### Non-Goals
- ❌ Build web UI (MCP is protocol-level)
- ❌ Replace existing tools (tools stay, resources complement)
- ❌ Implement full Things 3 sync protocol
- ❌ Add authentication (macOS security model sufficient)

---

## Proposed Architecture

### Feature 1: Prompts (Message Templates)

#### Categories (4 categories, ~12-15 prompts)

**1. Task Creation (5 prompts)**
- `create-simple-task` - Basic task creation prompt
- `create-task-with-deadline` - Task with due date
- `create-recurring-task` - Weekly/monthly recurring tasks
- `create-task-with-checklist` - Task with subtasks
- `brainstorm-project-tasks` - Generate task list for a project goal

**2. Project Planning (4 prompts)**
- `start-new-project` - Comprehensive project setup
- `create-project-with-phases` - Multi-phase project with headings
- `daily-standup-review` - Morning review prompt
- `weekly-review` - GTD-style weekly review

**3. Review & Reflection (3 prompts)**
- `reflect-on-completed-tasks` - Analyze productivity patterns
- `identify-stalled-projects` - Find projects needing attention
- `review-overdue-items` - Triage overdue tasks

**4. Workflow Automation (3 prompts)**
- `batch-schedule-tasks` - Schedule multiple tasks intelligently
- `organize-inbox` - AI-assisted inbox processing
- `suggest-next-actions` - Context-aware task recommendations

#### Technical Implementation
```python
from fastmcp import FastMCP
from fastmcp.prompts import PromptMessage, TextContent

@mcp.prompt(
    name="create-task-with-deadline",
    description="Generate a prompt to create a task with a deadline in Things 3",
    tags={"things3", "task_creation", "productivity"}
)
async def create_task_with_deadline_prompt(
    task_name: str,
    deadline: str,
    project: str | None = None,
    tags: list[str] | None = None,
    notes: str | None = None
) -> PromptMessage:
    """Creates a structured prompt for task creation with deadline."""
    
    content = f"Create a task in Things 3:\n\n"
    content += f"**Task**: {task_name}\n"
    content += f"**Deadline**: {deadline}\n"
    
    if project:
        content += f"**Project**: {project}\n"
    if tags:
        content += f"**Tags**: {', '.join(tags)}\n"
    if notes:
        content += f"**Notes**: {notes}\n"
    
    content += "\nPlease use the `add-todo` tool to create this task."
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )
```

---

### Feature 2: Resources (Data Exposure)

#### URI Scheme Design
```
things://                        Root namespace
├── projects/                    All projects
│   ├── list                    Project list resource
│   └── {uuid}/                 Individual project
│       ├── info                Project metadata
│       ├── todos               Project todos
│       ├── structure           Headings + todos hierarchy
│       └── notes               Project notes
├── areas/                       All areas
│   ├── list                    Area list resource
│   └── {uuid}/                 Individual area
│       ├── info                Area metadata
│       └── projects            Projects in area
├── tags/                        All tags
│   ├── list                    Tag list resource
│   └── {name}/                 Individual tag
│       └── items               Items with tag
├── todos/                       All todos
│   ├── inbox                   Inbox items
│   ├── today                   Today's tasks
│   ├── upcoming                Upcoming scheduled
│   ├── anytime                 Anytime list
│   ├── someday                 Someday/Maybe
│   ├── logbook                 Completed tasks
│   └── {uuid}/                 Individual todo
│       ├── info                Todo metadata
│       ├── checklist           Checklist items
│       └── notes               Todo notes
└── search/                      Search resources
    └── {query}                 Search results
```

#### Resource Categories (5 categories, ~22 resources)

**1. Hierarchical Structure (8 resources)**
- `things://projects/list` - All projects with metadata
- `things://projects/{uuid}/info` - Single project details
- `things://projects/{uuid}/todos` - Todos in project
- `things://projects/{uuid}/structure` - Headings hierarchy
- `things://areas/list` - All areas
- `things://areas/{uuid}/info` - Single area details
- `things://areas/{uuid}/projects` - Projects in area
- `things://tags/list` - All tags with usage stats

**2. Todo Lists (6 resources)**
- `things://todos/inbox` - Inbox items
- `things://todos/today` - Today's scheduled tasks
- `things://todos/upcoming` - Upcoming scheduled
- `things://todos/anytime` - Anytime list
- `things://todos/someday` - Someday/Maybe
- `things://todos/logbook` - Completed tasks (paginated)

**3. Individual Items (4 resources)**
- `things://todos/{uuid}/info` - Todo full details
- `things://todos/{uuid}/checklist` - Todo checklist
- `things://projects/{uuid}/notes` - Project notes
- `things://todos/{uuid}/notes` - Todo notes

**4. Search & Discovery (3 resources)**
- `things://search/{query}` - Full-text search results
- `things://tags/{name}/items` - Items with specific tag
- `things://deadlines/overdue` - All overdue items

**5. Analytics & Stats (1 resource)**
- `things://analytics/summary` - Overall productivity stats

#### Technical Implementation
```python
from fastmcp import FastMCP

@mcp.resource(
    uri="things://projects/{project_uuid}/todos",
    name="Project Todos",
    description="All todos in a specific project",
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True}
)
async def get_project_todos_resource(project_uuid: str, ctx: Context) -> dict:
    """Returns todos for a project as a resource."""
    
    try:
        project = things.projects(uuid=project_uuid)
        if not project:
            return {"error": "Project not found", "uuid": project_uuid}
        
        todos = things.todos(project=project_uuid, status="incomplete")
        
        return {
            "project_uuid": project_uuid,
            "project_title": project.get("title"),
            "todo_count": len(todos),
            "todos": [
                {
                    "uuid": todo["uuid"],
                    "title": todo["title"],
                    "status": todo["status"],
                    "deadline": todo.get("deadline"),
                    "tags": todo.get("tags", [])
                }
                for todo in todos
            ]
        }
    except Exception as e:
        return {"error": str(e)}
```

**Binary Resource Example** (Project export):
```python
@mcp.resource(
    uri="things://projects/{project_uuid}/export",
    name="Project Export",
    description="Export project as JSON file",
    mime_type="application/json"
)
async def export_project_resource(project_uuid: str) -> bytes:
    """Export project as downloadable JSON."""
    project_data = things.get(uuid=project_uuid)
    json_str = json.dumps(project_data, indent=2)
    return json_str.encode('utf-8')
```

---

### Feature 3: Sampling (Server-Initiated LLM Requests)

#### Use Cases (3-5 sampling-enabled tools)

**1. Intelligent Tag Suggestions**
```python
@mcp.tool(
    name="suggest-tags-ai",
    description="Use LLM to suggest relevant tags based on task content"
)
async def suggest_tags_ai(
    title: str,
    notes: str | None = None,
    ctx: Context
) -> dict:
    """Uses Claude/GPT to suggest appropriate tags."""
    
    # Existing tags from Things database
    existing_tags = things.tags()
    tag_names = [tag["title"] for tag in existing_tags]
    
    # Build sampling prompt
    prompt = f"""Analyze this task and suggest 2-3 relevant tags from the existing tag list.

Task Title: {title}
"""
    if notes:
        prompt += f"Task Notes: {notes}\n"
    
    prompt += f"\nExisting Tags: {', '.join(tag_names)}\n"
    prompt += "\nReturn only a comma-separated list of tag names."
    
    # Sample LLM via client
    response = await ctx.sample(
        messages=prompt,
        model_preferences=["claude-3-5-sonnet", "gpt-4o"],
        temperature=0.3,
        max_tokens=100
    )
    
    suggested_tags = [tag.strip() for tag in response.text.split(',')]
    
    return {
        "suggested_tags": suggested_tags,
        "existing_tags": tag_names,
        "task_analyzed": title
    }
```

**2. Smart Deadline Recommendations**
```python
@mcp.tool(
    name="recommend-deadline",
    description="Use LLM to recommend a realistic deadline based on task complexity"
)
async def recommend_deadline(
    title: str,
    notes: str | None = None,
    project_context: str | None = None,
    ctx: Context
) -> dict:
    """Analyzes task and suggests realistic deadline."""
    
    prompt = f"""Analyze this task and recommend a realistic deadline.

Task: {title}
"""
    if notes:
        prompt += f"Details: {notes}\n"
    if project_context:
        prompt += f"Project Context: {project_context}\n"
    
    prompt += """
Consider typical task durations:
- Simple tasks: 1-2 days
- Medium complexity: 3-7 days
- Complex tasks: 1-2 weeks
- Research/Planning: 2-4 weeks

Return format: "YYYY-MM-DD (reasoning)"
"""
    
    response = await ctx.sample(
        messages=prompt,
        model_preferences=["claude-3-5-sonnet"],
        temperature=0.5,
        max_tokens=150
    )
    
    return {
        "recommended_deadline": response.text,
        "task": title
    }
```

**3. Natural Language Task Parser**
```python
@mcp.tool(
    name="parse-task-description",
    description="Parse natural language task description into structured data"
)
async def parse_task_description(
    description: str,
    ctx: Context
) -> dict:
    """Converts natural language to Things 3 task fields."""
    
    prompt = f"""Parse this natural language task description into structured fields.

Input: "{description}"

Extract:
1. Title (short task name)
2. Project (if mentioned)
3. Tags (inferred from context)
4. Deadline (if mentioned, format as YYYY-MM-DD)
5. When to schedule (today/tomorrow/anytime/someday)
6. Notes (additional details)

Return as JSON:
{{
  "title": "...",
  "project": "..." or null,
  "tags": ["tag1", "tag2"],
  "deadline": "YYYY-MM-DD" or null,
  "when": "today|tomorrow|anytime|someday",
  "notes": "..."
}}
"""
    
    response = await ctx.sample(
        messages=prompt,
        model_preferences=["claude-3-5-sonnet", "gpt-4o"],
        temperature=0.2,
        max_tokens=300
    )
    
    try:
        parsed = json.loads(response.text)
        return parsed
    except json.JSONDecodeError:
        return {"error": "Failed to parse LLM response", "raw": response.text}
```

**4. Project Health Analysis**
```python
@mcp.tool(
    name="analyze-project-health-ai",
    description="Use LLM to analyze project health and suggest improvements"
)
async def analyze_project_health_ai(
    project_uuid: str,
    ctx: Context
) -> str:
    """Deep analysis of project health using LLM."""
    
    # Get project data
    project = things.get(uuid=project_uuid)
    todos = things.todos(project=project_uuid)
    
    incomplete = [t for t in todos if t["status"] == "incomplete"]
    completed = [t for t in todos if t["status"] == "completed"]
    overdue = [t for t in incomplete if t.get("deadline") and 
               datetime.fromisoformat(t["deadline"]).date() < date.today()]
    
    # Build context for LLM
    prompt = f"""Analyze this project's health and provide insights.

Project: {project['title']}
Total Tasks: {len(todos)}
Completed: {len(completed)} ({len(completed)/len(todos)*100:.1f}%)
Incomplete: {len(incomplete)}
Overdue: {len(overdue)}

Incomplete Tasks:
"""
    for todo in incomplete[:10]:  # First 10
        prompt += f"- {todo['title']}"
        if todo.get('deadline'):
            prompt += f" (deadline: {todo['deadline']})"
        prompt += "\n"
    
    prompt += """
Provide:
1. Overall health assessment (Healthy/At Risk/Critical)
2. Key concerns
3. Specific recommendations
4. Priority next actions

Keep response under 300 words.
"""
    
    response = await ctx.sample(
        messages=prompt,
        model_preferences=["claude-3-5-sonnet"],
        temperature=0.7,
        max_tokens=500
    )
    
    return response.text
```

**5. Inbox Triage Assistant**
```python
@mcp.tool(
    name="triage-inbox-ai",
    description="Use LLM to suggest organization for inbox items"
)
async def triage_inbox_ai(
    limit: int = 10,
    ctx: Context
) -> list[dict]:
    """AI-powered inbox triage suggestions."""
    
    inbox_items = things.todos(area="inbox", status="incomplete")[:limit]
    
    suggestions = []
    for item in inbox_items:
        prompt = f"""Analyze this inbox item and suggest organization.

Title: {item['title']}
Notes: {item.get('notes', 'None')}

Suggest:
1. Project (if it fits an existing workflow) or "Standalone"
2. When to schedule (today/tomorrow/this-week/anytime/someday)
3. Tags (2-3 relevant tags)
4. Priority (high/medium/low)

Return as JSON with keys: project, when, tags, priority, reasoning
"""
        
        response = await ctx.sample(
            messages=prompt,
            model_preferences=["claude-3-5-sonnet"],
            temperature=0.4,
            max_tokens=200
        )
        
        try:
            suggestion = json.loads(response.text)
            suggestion["todo_uuid"] = item["uuid"]
            suggestion["todo_title"] = item["title"]
            suggestions.append(suggestion)
        except json.JSONDecodeError:
            continue
    
    return suggestions
```

#### Client-Side Handler (Documentation)
```python
# User must provide sampling handler when using MCP client
from fastmcp import Client

async def my_sampling_handler(messages, params, context):
    """User's LLM integration - calls their preferred API."""
    # Example: Claude API integration
    import anthropic
    client = anthropic.Anthropic(api_key="...")
    
    response = client.messages.create(
        model=params.model_preferences[0] if params.model_preferences else "claude-3-5-sonnet",
        messages=[{"role": "user", "content": m.content.text} for m in messages],
        temperature=params.temperature or 0.7,
        max_tokens=params.max_tokens or 1024
    )
    
    return response.content[0].text

client = Client(
    "things-fastmcp",
    sampling_handler=my_sampling_handler
)
```

---

### Feature 4: Enhanced Notifications

#### Current State
- ✅ `tools/list_changed` - When tools enabled/disabled (v3.0.0)

#### New Notifications (4 notification types)

**1. Prompts List Changed**
```python
# Automatically sent by FastMCP when prompts added/removed/enabled/disabled
# No custom implementation needed - FastMCP handles this
```

**2. Resources List Changed**
```python
# Automatically sent by FastMCP when resources added/removed/enabled/disabled
# No custom implementation needed - FastMCP handles this
```

**3. Custom Progress Notifications** (Enhanced)
```python
@mcp.tool(
    name="sync-with-things-cloud",
    description="Sync local Things database with Things Cloud"
)
async def sync_with_things_cloud(ctx: Context) -> str:
    """Long-running sync operation with progress updates."""
    
    # Phase 1: Upload changes
    await ctx.info("🔄 Syncing with Things Cloud...")
    await ctx.report_progress(0, 100, "Uploading local changes")
    
    # Simulate upload
    await asyncio.sleep(2)
    await ctx.report_progress(33, 100, "Upload complete")
    
    # Phase 2: Download changes
    await ctx.report_progress(34, 100, "Downloading remote changes")
    await asyncio.sleep(2)
    await ctx.report_progress(66, 100, "Download complete")
    
    # Phase 3: Merge
    await ctx.report_progress(67, 100, "Merging changes")
    await asyncio.sleep(1)
    await ctx.report_progress(100, 100, "Sync complete")
    
    return "✅ Sync successful"
```

**4. Custom Notifications** (Future consideration)
```python
# Not directly supported by MCP protocol yet
# Would require custom notification types:
# - things3/task_completed
# - things3/deadline_approaching
# - things3/project_stalled

# Implementation would use FastMCP's notification system
# when/if MCP protocol adds custom notification types
```

---

## Implementation Plan

### Phase 1: Prompts (Week 1-2)
**Goal**: Add 12-15 prompt templates for common workflows

#### Tasks
1. ✅ Research FastMCP prompt API (DONE via DeepWiki)
2. Create prompt categories structure
3. Implement Task Creation prompts (5 prompts)
   - create-simple-task
   - create-task-with-deadline
   - create-recurring-task
   - create-task-with-checklist
   - brainstorm-project-tasks
4. Implement Project Planning prompts (4 prompts)
   - start-new-project
   - create-project-with-phases
   - daily-standup-review
   - weekly-review
5. Implement Review & Reflection prompts (3 prompts)
   - reflect-on-completed-tasks
   - identify-stalled-projects
   - review-overdue-items
6. Implement Workflow Automation prompts (3 prompts)
   - batch-schedule-tasks
   - organize-inbox
   - suggest-next-actions
7. Add tags for categorization
8. Test prompts in Claude Desktop
9. Document prompt usage in README

**Deliverables**:
- 12-15 prompts registered
- Prompts appear in Claude Desktop prompt list
- Documentation with examples

---

### Phase 2: Resources (Week 3-4)
**Goal**: Expose Things 3 data as 20-25 resources

#### Tasks
1. ✅ Research FastMCP resource API (DONE via DeepWiki)
2. Design URI scheme hierarchy
3. Implement Hierarchical Structure resources (8 resources)
   - things://projects/list
   - things://projects/{uuid}/info
   - things://projects/{uuid}/todos
   - things://projects/{uuid}/structure
   - things://areas/list
   - things://areas/{uuid}/info
   - things://areas/{uuid}/projects
   - things://tags/list
4. Implement Todo Lists resources (6 resources)
   - things://todos/inbox
   - things://todos/today
   - things://todos/upcoming
   - things://todos/anytime
   - things://todos/someday
   - things://todos/logbook
5. Implement Individual Items resources (4 resources)
   - things://todos/{uuid}/info
   - things://todos/{uuid}/checklist
   - things://projects/{uuid}/notes
   - things://todos/{uuid}/notes
6. Implement Search & Discovery resources (3 resources)
   - things://search/{query}
   - things://tags/{name}/items
   - things://deadlines/overdue
7. Implement Analytics resource (1 resource)
   - things://analytics/summary
8. Add resource annotations (readOnlyHint, idempotentHint)
9. Test resources in Claude Desktop
10. Document resource URIs in README

**Deliverables**:
- 20-25 resources registered
- URI template patterns working
- Resources browsable in MCP clients
- Documentation with URI examples

---

### Phase 3: Sampling (Week 5)
**Goal**: Add 3-5 AI-powered tools using server-initiated LLM requests

#### Tasks
1. ✅ Research FastMCP sampling API (DONE via DeepWiki)
2. Document client-side handler requirements
3. Implement sampling tools:
   - suggest-tags-ai (intelligent tag suggestions)
   - recommend-deadline (smart deadline estimation)
   - parse-task-description (NL to structured data)
   - analyze-project-health-ai (deep project analysis)
   - triage-inbox-ai (AI-powered inbox organization)
4. Add error handling for missing sampling handler
5. Test with Claude Desktop (requires sampling_handler)
6. Add fallback behavior when sampling unavailable
7. Document sampling setup in README

**Deliverables**:
- 3-5 sampling-enabled tools
- Client handler documentation
- Error handling for missing handler
- Usage examples

---

### Phase 4: Enhanced Notifications (Week 6)
**Goal**: Enhance notification system for better real-time feedback

#### Tasks
1. ✅ Research FastMCP notification system (DONE via DeepWiki)
2. Verify prompts/list_changed auto-notification
3. Verify resources/list_changed auto-notification
4. Add progress notifications to long-running tools:
   - Bulk operations (if still present)
   - Search operations with large result sets
   - Analytics calculations
5. Document notification behavior in README
6. Test notification delivery in Claude Desktop

**Deliverables**:
- Automatic MCP protocol notifications working
- Enhanced progress reporting
- Documentation

---

### Phase 5: Integration & Testing (Week 6)
**Goal**: Integration testing, documentation, release

#### Tasks
1. Test all prompts in Claude Desktop
2. Test all resources in Claude Desktop
3. Test sampling tools with handler
4. Test notifications
5. Update README.md with:
   - Prompts section (list all prompts)
   - Resources section (URI hierarchy)
   - Sampling section (handler setup)
   - Notifications section
6. Update CHANGELOG.md for v4.0.0
7. Create migration guide from v3.0.0
8. Update AGENTS.md
9. Version bump to v4.0.0
10. Create release notes

**Deliverables**:
- All features tested and working
- Complete documentation
- v4.0.0 ready for release

---

## Success Metrics

### Quantitative
- ✅ 12-15 prompts registered
- ✅ 20-25 resources available
- ✅ 3-5 sampling tools functional
- ✅ Automatic notifications working
- ✅ Zero compilation errors
- ✅ All tests passing

### Qualitative
- 🎯 Prompts reduce task creation friction
- 🎯 Resources enable data browsing
- 🎯 Sampling provides intelligent suggestions
- 🎯 Notifications improve real-time feedback
- 🎯 Documentation clear and comprehensive
- 🎯 User feedback positive

---

## Technical Considerations

### Dependencies
- **FastMCP**: Already on 2.13.0.2 ✅
- **MCP Protocol**: Client must support prompts/resources/sampling
- **Claude Desktop**: Testing platform (supports all features)

### Performance
- **Prompts**: Instant (no execution, just template rendering)
- **Resources**: <200ms per resource read
- **Sampling**: Depends on client LLM API (2-5 seconds typical)
- **Notifications**: Async, non-blocking

### Compatibility
- **Breaking Changes**: None (additive only)
- **Backward Compatibility**: All v3.0.0 tools remain functional
- **MCP Clients**: Requires MCP 1.0+ for full feature support

---

## Risk Mitigation

### Risk 1: Sampling Handler Missing
**Mitigation**: 
- Detect missing handler, return clear error message
- Provide fallback non-AI versions of tools
- Document handler setup prominently

### Risk 2: Resource URI Conflicts
**Mitigation**:
- Use `things://` namespace exclusively
- Document URI scheme clearly
- Validate no overlapping patterns

### Risk 3: Performance with Large Datasets
**Mitigation**:
- Paginate logbook resource (limit 100 items)
- Add limit parameters to list resources
- Cache frequently accessed resources

### Risk 4: Prompt Overload
**Mitigation**:
- Use tags for categorization
- Disable less-used prompts by default
- Document enabling/disabling prompts

---

## Future Enhancements (Post-v4.0.0)

### v4.1.0: Advanced Prompts
- Multi-turn conversation prompts
- Prompt templates with LLM-generated variations
- Context-aware prompts (adjust based on time of day, workload)

### v4.2.0: Enhanced Resources
- Binary resources (project exports as JSON files)
- Resource subscriptions (real-time updates)
- Resource filtering (query parameters)

### v4.3.0: Advanced Sampling
- Multi-step sampling workflows
- Sampling with tool calls (agentic behavior)
- Model preference negotiation

### v5.0.0: Real-Time Sync
- Custom notification types for Things 3 events
- WebSocket support for live updates
- Things Cloud sync integration

---

## Open Questions

1. **Prompt Naming**: Use verb-noun (create-task) or noun-verb (task-create)?
   - **Decision**: Verb-noun for consistency with tools

2. **Resource Pagination**: Automatically paginate or require limit parameter?
   - **Decision**: Auto-paginate at 100 items, allow override

3. **Sampling Fallback**: What to return when no handler available?
   - **Decision**: Clear error + suggestion to use non-AI tool

4. **Tag Organization**: Use MCP tags or custom metadata?
   - **Decision**: MCP tags for filtering, metadata for additional info

---

## References

### FastMCP Documentation
- DeepWiki: https://deepwiki.com/jlowin/fastmcp
- GitHub: https://github.com/jlowin/fastmcp
- API Reference: Component System Architecture

### MCP Protocol
- Specification: https://spec.modelcontextprotocol.io/
- Features: Prompts, Resources, Sampling, Notifications

### Related Work
- OpenSpec Proposal: tool-consolidation-2025 (v3.0.0)
- Implementation Summary: v3.0.0 complete
- Migration Guide: v2.x → v3.0.0

---

**Status**: 📋 Planning Complete  
**Next Step**: Begin Phase 1 implementation (Prompts)  
**Approval**: Awaiting user confirmation to proceed
