# Tool Consolidation & Dynamic Management (v3.0.0)

## Executive Summary

**Goal**: Simplify tool interface from 51 → 30-35 tools through consolidation and dynamic management

**Motivation**: 
- Current 51 tools overwhelming for users (mcp-obsidian has only 2 tools)
- 15 tools have clear duplication (7 list tools, 5 count tools)
- 11 tools are non-functional (require elicitation, not supported in Claude Desktop)
- Need progressive disclosure mechanism for advanced features

**Impact**: 
- **Breaking change** → v3.0.0 major version bump
- Tool count reduction: 51 → 30-35 tools (~35% reduction)
- Improved discoverability and user experience
- Better alignment with MCP best practices

---

## Phase 1: Tool Consolidation

### 1.1 List Tools Consolidation (7 → 1)

**Merge into**: `list-items`

**Remove**:
- get-inbox
- get-today
- get-upcoming
- get-anytime
- get-someday
- get-logbook
- get-trash

**New Tool Signature**:
```python
@mcp.tool()
async def list_items(
    list_type: Literal["inbox", "today", "upcoming", "anytime", "someday", "logbook", "trash"],
    type_filter: Optional[str] = None,
    deadline_filter: Optional[str] = None,
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Get items from a specific Things list.
    
    Args:
        list_type: Which list to query (inbox, today, upcoming, anytime, someday, logbook, trash)
        type_filter: Filter by type (to-do, project, heading, area)
        deadline_filter: Filter by deadline (overdue, today, upcoming, none)
        limit: Maximum items to return (default: 20)
        sort_by: Sort order (title, created, modified, deadline, start_date)
    
    Returns:
        Formatted list of items with metadata
    
    Example:
        list_items("today", limit=10)
        list_items("inbox", type_filter="to-do", deadline_filter="overdue")
    """
```

### 1.2 Count Tools Consolidation (5 → 1)

**Merge into**: `count`

**Remove**:
- count-items
- count-search
- count-tagged-items
- count-project-items
- count-advanced

**New Tool Signature**:
```python
@mcp.tool()
async def count(
    count_type: Literal["lists", "search", "tag", "project", "advanced"],
    query: Optional[str] = None,
    tag: Optional[str] = None,
    project_uuid: Optional[str] = None,
    title_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Count items in various contexts without fetching full data.
    
    Args:
        count_type: What to count (lists, search, tag, project, advanced)
        query: Search query (for count_type="search")
        tag: Tag name (for count_type="tag")
        project_uuid: Project UUID (for count_type="project")
        title_filter: Title pattern (for count_type="advanced")
        type_filter: Type filter (for count_type="advanced")
        status_filter: Status filter (for count_type="advanced")
    
    Returns:
        Count summary with recommendations for limiting
    
    Example:
        count("lists")  # Count all lists
        count("search", query="meeting notes")
        count("tag", tag="work")
        count("advanced", title_filter="review", status_filter="incomplete")
    """
```

### 1.3 Search Tools Consolidation (2 → 1)

**Merge into**: `search`

**Remove**:
- search-todos
- search-advanced

**New Tool Signature**:
```python
@mcp.tool()
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
    Search for items with optional advanced filters.
    
    Args:
        query: Full-text search query (searches title and notes)
        title_filter: Filter by title substring
        notes_filter: Filter by notes substring
        type_filter: Filter by type (to-do, project, heading, area)
        status_filter: Filter by status (incomplete, completed, canceled)
        deadline_filter: Filter by deadline (overdue, today, upcoming, none)
        limit: Maximum items to return (default: 20)
        offset: Pagination offset (default: 0)
        sort_by: Sort order (title, created, modified, deadline)
    
    Returns:
        Search results with pagination metadata
    
    Example:
        search(query="meeting")
        search(title_filter="review", status_filter="incomplete", deadline_filter="overdue")
    """
```

### 1.4 Deadline Tools Consolidation (2 → 1)

**Merge into**: `deadline-items`

**Remove**:
- get-overdue-items
- get-items-due-soon

**New Tool Signature**:
```python
@mcp.tool()
async def deadline_items(
    filter_type: Literal["overdue", "due-soon"] = "overdue",
    days: Optional[int] = 7,
    limit: Optional[int] = None,
    sort_by: Optional[str] = "deadline",
    ctx: Optional[Context] = None
) -> str:
    """
    Get items filtered by deadline status.
    
    Args:
        filter_type: Type of deadline filter (overdue, due-soon)
        days: For "due-soon", number of days to look ahead (default: 7)
        limit: Maximum items to return
        sort_by: Sort order (deadline, title, created, modified)
    
    Returns:
        Items with deadline information and urgency badges
    
    Example:
        deadline_items("overdue")
        deadline_items("due-soon", days=3)
    """
```

### 1.5 Heading Tools Consolidation (2 → 1)

**Merge into**: `manage-heading`

**Remove**:
- add-heading
- move-todo-under-heading

**New Tool Signature**:
```python
@mcp.tool()
async def manage_heading(
    action: Literal["add", "move"],
    project_uuid: str,
    heading_title: Optional[str] = None,
    heading_uuid: Optional[str] = None,
    todo_uuid: Optional[str] = None,
    after_uuid: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Add headings or move todos under headings.
    
    Args:
        action: Action to perform (add, move)
        project_uuid: Project UUID (required for both actions)
        heading_title: Heading title (required for action="add")
        heading_uuid: Heading UUID (required for action="move")
        todo_uuid: Todo UUID (required for action="move")
        after_uuid: Item UUID to position after (optional for action="add")
    
    Returns:
        Success message with updated structure
    
    Example:
        manage_heading("add", project_uuid="...", heading_title="Phase 1")
        manage_heading("move", project_uuid="...", heading_uuid="...", todo_uuid="...")
    """
```

---

## Phase 2: Dynamic Tool Management

### 2.1 Tool Categories

**Core Tools** (always enabled):
- get-todos, get-projects, get-areas, get-tags
- update-todo, update-project
- add-todo, add-project
- search, list-items, count
- deadline-items, get-recent, show-item, search-items
- get-tagged-items
- move-item-to-project
- get-cache-stats
- **Total: 18 core tools**

**Advanced - Analytics** (opt-in):
- get-productivity-stats
- get-project-velocity
- get-time-to-completion
- get-tag-productivity
- check-stalled-projects
- get-project-health-report
- analyze-tag-relationships
- suggest-tags
- parse-natural-date
- **Total: 9 analytics tools**

**Advanced - Checklists** (opt-in):
- get-checklist-items
- add-checklist-item
- update-checklist-item
- get-todos-with-checklists
- **Total: 4 checklist tools**

**Advanced - Structure** (opt-in):
- manage-heading
- get-project-structure
- **Total: 2 structure tools**

**Deprecated** (will be removed):
- All elicitation-based tools (11 tools)
  - add-todo-interactive
  - bulk-complete-todos, bulk-schedule-todos, bulk-tag-todos, bulk-move-todos
  - schedule-assistant
  - create-project-template, list-project-templates, apply-project-template, update-project-template, delete-project-template

### 2.2 New Tool: enable-advanced-features

```python
@mcp.tool()
async def enable_advanced_features(
    category: Literal["analytics", "checklists", "structure", "all"],
    ctx: Optional[Context] = None
) -> str:
    """
    Enable advanced tool categories.
    
    Args:
        category: Which category to enable (analytics, checklists, structure, all)
    
    Returns:
        List of newly enabled tools
    
    Example:
        enable_advanced_features("analytics")
        enable_advanced_features("all")
    """
```

### 2.3 Implementation Pattern

```python
# Store tool handles for dynamic management
ADVANCED_TOOLS: Dict[str, List[Any]] = {
    "analytics": [],
    "checklists": [],
    "structure": []
}

# Register tools and store handles
analytics_tool_1 = mcp.tool(...)(get_productivity_stats)
ADVANCED_TOOLS["analytics"].append(analytics_tool_1)
analytics_tool_1.disable()  # Start disabled

# Enable category
def enable_category(category: str):
    for tool in ADVANCED_TOOLS[category]:
        tool.enable()  # Triggers tools/list_changed notification
```

---

## Migration Strategy

### 3.1 Deprecation Timeline

**v2.3.0** (current):
- All 51 tools functional
- No deprecation warnings yet

**v2.4.0** (next release, 2 weeks):
- Add deprecation warnings to old tools
- New composite tools available alongside old tools
- Documentation updated with migration guide
- Both old and new tools work (transition period)

**v3.0.0** (major release, 1 month):
- Remove old tools completely
- Only composite tools + dynamic management
- Breaking changes documented in CHANGELOG

### 3.2 Migration Guide Template

```markdown
## Migrating from v2.x to v3.0.0

### Removed Tools

| Old Tool | New Tool | Example |
|----------|----------|---------|
| get-inbox | list-items | `list_items("inbox", limit=20)` |
| get-today | list-items | `list_items("today")` |
| count-items | count | `count("lists")` |
| search-todos | search | `search(query="meeting")` |
| search-advanced | search | `search(title_filter="...", status_filter="...")` |
| get-overdue-items | deadline-items | `deadline_items("overdue")` |
| add-heading | manage-heading | `manage_heading("add", project_uuid="...", heading_title="...")` |

### Enabling Advanced Features

```python
# Analytics tools (9 tools)
enable_advanced_features("analytics")

# Checklist tools (4 tools)
enable_advanced_features("checklists")

# All advanced features
enable_advanced_features("all")
```
```

---

## Success Metrics

### 4.1 Quantitative

- Tool count: 51 → 30-35 (30-35% reduction)
- Core tools (always visible): 18 tools
- Average Claude Desktop tool list length: <20 tools (vs 51 currently)
- Documentation pages updated: README, CHANGELOG, migration guide

### 4.2 Qualitative

- Cleaner tool list in Claude Desktop UI
- Easier discovery of core functionality
- Progressive disclosure reduces cognitive load
- Advanced users can still access all features
- Migration path clear and documented

---

## Risks & Mitigations

### 5.1 Breaking Changes

**Risk**: Users' existing scripts/integrations break
**Mitigation**: 
- 1-month transition period (v2.4.0 with both old and new)
- Clear migration guide with 1:1 mapping
- Deprecation warnings in v2.4.0

### 5.2 Parameter Complexity

**Risk**: Composite tools have more complex parameters
**Mitigation**:
- Comprehensive docstrings with examples
- Type hints for auto-completion
- Default values for common use cases
- Error messages suggest correct parameters

### 5.3 MCP Client Support

**Risk**: Claude Desktop may not support dynamic tool management
**Mitigation**:
- Test `tools/list_changed` notifications
- Fallback: Enable all tools if notifications not supported
- Document client compatibility

---

## Implementation Plan

### Phase 1: Tool Consolidation (Week 1)
- [ ] Implement 5 composite tools
- [ ] Add deprecation warnings to old tools (v2.4.0)
- [ ] Update TOOL_ANNOTATIONS
- [ ] Test all new tools
- [ ] Update docstrings

### Phase 2: Dynamic Management (Week 1)
- [ ] Implement tool handle storage
- [ ] Create enable-advanced-features tool
- [ ] Add disable() calls for advanced tools
- [ ] Test enable/disable in Claude Desktop
- [ ] Document client compatibility

### Phase 3: Documentation (Week 2)
- [ ] Update README with new tool inventory
- [ ] Create migration guide
- [ ] Update CHANGELOG for v3.0.0
- [ ] Add examples for all composite tools
- [ ] Update smithery.yaml

### Phase 4: Testing & Release (Week 2)
- [ ] Manual testing of all 5 composite tools
- [ ] Test dynamic enable/disable
- [ ] Verify deprecation warnings
- [ ] Release v2.4.0 (transition)
- [ ] Wait 2 weeks for feedback
- [ ] Release v3.0.0 (breaking changes)

---

## Approval Required

**Author**: AI Assistant (GitHub Copilot)  
**Date**: 2025-11-02  
**Version**: Draft 1.0

**Awaiting user approval to proceed with implementation.**
