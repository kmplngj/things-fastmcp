# Migration Guide: v2.x → v3.0.0

**Effective Date**: TBD (v3.0.0 release)  
**Transition Period**: v2.4.0 → v3.0.0 (2-3 weeks)  
**Status**: Documentation ready, awaiting testing

---

## Overview

Version 3.0.0 consolidates 15 tools into 5 composite tools for a cleaner, more discoverable API. This guide shows you how to migrate from v2.x tool calls to v3.0.0.

**What's changing**:
- 15 granular tools → 5 composite tools
- 15 advanced tools move to opt-in categories
- 11 deprecated elicitation tools will be removed

**What's NOT changing**:
- All functionality preserved
- Same data returned
- Same filtering capabilities
- Same Things 3 integration

---

## Quick Reference Table

| Old Tool | New Tool | Parameters |
|----------|----------|------------|
| `get-inbox` | `list-items` | `list_type="inbox"` |
| `get-today` | `list-items` | `list_type="today"` |
| `get-upcoming` | `list-items` | `list_type="upcoming"` |
| `get-anytime` | `list-items` | `list_type="anytime"` |
| `get-someday` | `list-items` | `list_type="someday"` |
| `get-logbook` | `list-items` | `list_type="logbook"` |
| `get-trash` | `list-items` | `list_type="trash"` |
| `count-items` | `count` | `count_type="lists"` |
| `count-search` | `count` | `count_type="search", query="..."` |
| `count-tagged-items` | `count` | `count_type="tag", tag="..."` |
| `count-project-items` | `count` | `count_type="project", project_uuid="..."` |
| `count-advanced` | `count` | `count_type="advanced", ...filters` |
| `search-todos` | `search` | `query="..."` |
| `search-advanced` | `search` | Use filter parameters |
| `get-overdue-items` | `deadline-items` | `filter_type="overdue"` |
| `get-items-due-soon` | `deadline-items` | `filter_type="due-soon"` |
| `add-heading` | `manage-heading` | `action="add", ...` |
| `move-todo-under-heading` | `manage-heading` | `action="move", ...` |

---

## Detailed Migration Examples

### 1. List Views → `list-items`

#### Before (v2.x)
```python
# Get inbox
get_inbox(limit=20, sort_by="created")

# Get today's tasks
get_today(type_filter="to-do")

# Get upcoming
get_upcoming(deadline_filter="overdue")
```

#### After (v3.0.0)
```python
# Get inbox
list_items(list_type="inbox", limit=20, sort_by="created")

# Get today's tasks
list_items(list_type="today", type_filter="to-do")

# Get upcoming
list_items(list_type="upcoming", deadline_filter="overdue")
```

**All parameters preserved**:
- `type_filter`: Filter by type (to-do, project, heading)
- `deadline_filter`: Filter by deadline status (overdue, today, upcoming, none)
- `limit`: Limit number of results
- `sort_by`: Sort order (title, created, modified, deadline, start_date)

---

### 2. Counting → `count`

#### Before (v2.x)
```python
# Count all items in all lists
count_items()

# Count search results
count_search(query="meeting notes")

# Count items with tag
count_tagged_items(tag="urgent")

# Count project items
count_project_items(project_uuid="abc123")

# Count with filters
count_advanced(title_filter="report", status_filter="incomplete")
```

#### After (v3.0.0)
```python
# Count all items in all lists
count(count_type="lists")

# Count search results
count(count_type="search", query="meeting notes")

# Count items with tag
count(count_type="tag", tag="urgent")

# Count project items
count(count_type="project", project_uuid="abc123")

# Count with filters
count(count_type="advanced", title_filter="report", status_filter="incomplete")
```

**All parameters preserved**:
- `query`: Search query string
- `tag`: Tag name
- `project_uuid`: Project UUID
- `title_filter`, `type_filter`, `status_filter`: Advanced filters

---

### 3. Search → `search`

#### Before (v2.x)
```python
# Full-text search
search_todos(query="meeting", limit=20, offset=0)

# Advanced search with filters
search_advanced(
    title_filter="project",
    status_filter="incomplete",
    type_filter="to-do",
    deadline_filter="upcoming"
)
```

#### After (v3.0.0)
```python
# Full-text search (same)
search(query="meeting", limit=20, offset=0)

# Advanced search with filters (merged into search)
search(
    title_filter="project",
    status_filter="incomplete",
    type_filter="to-do",
    deadline_filter="upcoming"
)

# Combined full-text + filters (NEW!)
search(
    query="meeting",  # Full-text search
    status_filter="incomplete",  # Plus filters
    limit=20
)
```

**Enhanced capabilities**:
- Can now combine full-text search with advanced filters
- All parameters work together
- Same pagination support (offset, limit)
- Same sorting options

---

### 4. Deadline Tracking → `deadline-items`

#### Before (v2.x)
```python
# Get overdue items
get_overdue_items(limit=50, sort_by="deadline")

# Get items due soon
get_items_due_soon(days=7, limit=20)
```

#### After (v3.0.0)
```python
# Get overdue items
deadline_items(filter_type="overdue", limit=50, sort_by="deadline")

# Get items due soon
deadline_items(filter_type="due-soon", days=7, limit=20)
```

**All parameters preserved**:
- `days`: Lookahead days for "due-soon" (default: 7)
- `limit`: Limit number of results
- `sort_by`: Sort order
- Same urgency badges (🔴 🟠 🟡)
- Same days_overdue/days_until calculations

---

### 5. Heading Management → `manage-heading`

#### Before (v2.x)
```python
# Add heading
add_heading(
    project_uuid="abc123",
    heading_title="Phase 1",
    after_uuid="xyz789"
)

# Move todo under heading
move_todo_under_heading(
    todo_uuid="def456",
    heading_uuid="ghi789"
)
```

#### After (v3.0.0)
```python
# Add heading
manage_heading(
    action="add",
    project_uuid="abc123",
    heading_title="Phase 1",
    after_uuid="xyz789"
)

# Move todo under heading
manage_heading(
    action="move",
    todo_uuid="def456",
    heading_uuid="ghi789",
    project_uuid="abc123"  # Required for validation
)
```

**Changes**:
- Added `action` parameter: "add" or "move"
- Move action now requires `project_uuid` for validation
- All other parameters preserved
- Same error handling and validation

---

## Advanced Features (Opt-in Categories)

### Before v3.0.0
All 51 tools visible in Claude Desktop tool list.

### After v3.0.0
18 core tools visible by default. Enable advanced features as needed:

```python
# Enable analytics tools (9 tools)
enable_advanced_features("analytics")
# Now have: get-productivity-stats, get-project-velocity, etc.

# Enable checklist tools (4 tools)
enable_advanced_features("checklists")
# Now have: get-checklist-items, add-checklist-item, etc.

# Enable structure tools (2 tools)
enable_advanced_features("structure")
# Now have: get-project-structure

# Enable all advanced features
enable_advanced_features("all")

# Check status
get_tool_categories()

# Disable when done
disable_advanced_features("analytics")
```

---

## Tool Categories Breakdown

### Core Tools (Always Visible) - 18 tools
✅ Available by default, no action needed

**Data Access**:
- get-todos, get-projects, get-areas, get-tags
- show-item, get-recent, get-tagged-items

**Modification**:
- add-todo, add-project
- update-todo, update-project
- move-item-to-project

**New Composite Tools**:
- list-items (replaces 7 list tools)
- count (replaces 5 count tools)
- search (replaces 2 search tools)
- deadline-items (replaces 2 deadline tools)
- manage-heading (replaces 2 heading tools)

**Utilities**:
- search-items (URL scheme search)
- get-cache-stats

---

### Analytics (Opt-in) - 9 tools
🔓 Enable with: `enable_advanced_features("analytics")`

**Productivity Metrics**:
- get-productivity-stats
- get-project-velocity
- get-time-to-completion
- get-tag-productivity

**Project Health**:
- check-stalled-projects
- get-project-health-report

**Tag Intelligence**:
- analyze-tag-relationships
- suggest-tags

**Smart Scheduling**:
- parse-natural-date

---

### Checklists (Opt-in) - 4 tools
🔓 Enable with: `enable_advanced_features("checklists")`

- get-checklist-items
- add-checklist-item
- update-checklist-item
- get-todos-with-checklists

---

### Structure (Opt-in) - 2 tools
🔓 Enable with: `enable_advanced_features("structure")`

- get-project-structure
- (manage-heading is in core tools)

---

### Deprecated (Will be removed in v3.0.0) - 11 tools
❌ These tools will be removed

**Reason**: All require elicitation API, which Claude Desktop doesn't support

- add-todo-interactive
- bulk-complete-todos
- bulk-schedule-todos
- bulk-tag-todos
- bulk-move-todos
- schedule-assistant
- create-project-template
- list-project-templates
- apply-project-template
- update-project-template
- delete-project-template

**Migration Path**: Use non-interactive equivalents (add-todo, update-todo, etc.)

---

## Common Migration Patterns

### Pattern 1: Multiple List Queries
#### Before
```python
inbox = get_inbox()
today = get_today()
upcoming = get_upcoming()
```

#### After
```python
inbox = list_items("inbox")
today = list_items("today")
upcoming = list_items("upcoming")
```

---

### Pattern 2: Count Before Fetch
#### Before
```python
total = count_items()
if total["inbox"] > 20:
    items = get_inbox(limit=20)
```

#### After
```python
total = count("lists")
if total["inbox"] > 20:
    items = list_items("inbox", limit=20)
```

---

### Pattern 3: Search + Filter
#### Before
```python
# Had to use search-advanced, couldn't combine with full-text
results = search_advanced(
    title_filter="project",
    status_filter="incomplete"
)
```

#### After
```python
# Can now combine full-text + filters!
results = search(
    query="meeting",  # Full-text
    status_filter="incomplete"  # Plus filter
)
```

---

### Pattern 4: Conditional Tool Enabling
#### Before
```python
# All 51 tools always visible
```

#### After
```python
# Start with 18 core tools
# Enable analytics only when needed
if user_wants_analytics:
    enable_advanced_features("analytics")
    stats = get_productivity_stats(days=30)
    velocity = get_project_velocity(interval="weekly")
    disable_advanced_features("analytics")
```

---

## Testing Your Migration

### Step 1: Check Current Version
```python
# In Claude Desktop or your MCP client
# Look for "things-fastmcp v3.0.0" in tool list
```

### Step 2: Test Core Tools
```python
# Test list-items with all list types
list_items("inbox")
list_items("today")
list_items("upcoming")

# Test count with all count types
count("lists")
count("search", query="test")

# Test search
search(query="meeting")

# Test deadline-items
deadline_items("overdue")

# Test manage-heading
manage_heading("add", project_uuid="...", heading_title="Test")
```

### Step 3: Test Advanced Features
```python
# Enable and test each category
enable_advanced_features("analytics")
get_productivity_stats(days=30)
disable_advanced_features("analytics")

enable_advanced_features("checklists")
get_todos_with_checklists()
disable_advanced_features("checklists")
```

### Step 4: Verify Functionality
- All data returned matches v2.x behavior
- Filters work correctly
- Sorting works correctly
- Pagination works correctly
- No errors in Claude Desktop logs

---

## Breaking Changes Summary

### Removed Tools (15 total)
| Old Tool | Replacement |
|----------|-------------|
| get-inbox | list-items("inbox") |
| get-today | list-items("today") |
| get-upcoming | list-items("upcoming") |
| get-anytime | list-items("anytime") |
| get-someday | list-items("someday") |
| get-logbook | list-items("logbook") |
| get-trash | list-items("trash") |
| count-items | count("lists") |
| count-search | count("search", query="...") |
| count-tagged-items | count("tag", tag="...") |
| count-project-items | count("project", project_uuid="...") |
| count-advanced | count("advanced", ...filters) |
| search-advanced | search(...filters) |
| get-overdue-items | deadline-items("overdue") |
| get-items-due-soon | deadline-items("due-soon") |

### Deprecated Tools (11 total)
Will be removed in v3.0.0 final release:
- All *-interactive tools (require elicitation)
- All *-template tools (require elicitation)
- bulk-* tools (require elicitation)
- schedule-assistant (requires elicitation)

### Opt-in Tools (15 total)
Now require enable_advanced_features():
- Analytics: 9 tools
- Checklists: 4 tools
- Structure: 2 tools

---

## Transition Timeline

### v2.4.0 (Transition Release)
**Date**: TBD  
**What happens**:
- Both old and new tools work
- Old tools show deprecation warnings
- New composite tools available
- Documentation shows migration examples

**Action Required**:
- Test new composite tools
- Update your workflows
- Report any issues

---

### v3.0.0 (Final Release)
**Date**: TBD (2-3 weeks after v2.4.0)  
**What happens**:
- Old tools removed
- Only composite tools available
- 11 deprecated tools removed
- Advanced features opt-in by default

**Action Required**:
- Complete migration before this date
- Update any saved prompts/workflows
- Enable advanced features as needed

---

## Rollback Plan

If you encounter issues with v3.0.0:

### Option 1: Stay on v2.4.0
```bash
# In your MCP client config
"version": "2.4.0"  # Pin to transition version
```

### Option 2: Report Issues
- GitHub Issues: https://github.com/jankampling/things-fastmcp/issues
- Include: Tool name, parameters, error message, expected vs actual behavior

### Option 3: Use Legacy Branch
```bash
git checkout v2.3.0  # Last version before consolidation
```

---

## FAQ

### Q: Will my existing prompts break?
**A**: Yes, if they reference old tool names. Update them to use composite tools.

### Q: Can I use both old and new tools during transition?
**A**: Yes, in v2.4.0 both work. In v3.0.0, only new tools.

### Q: Do I lose any functionality?
**A**: No, all functionality preserved. Just different tool names.

### Q: Why consolidate?
**A**: 51 tools overwhelmed new users. 18 core tools + opt-in advanced features = better UX.

### Q: How do I enable analytics?
**A**: `enable_advanced_features("analytics")` - adds 9 analytics tools to your tool list.

### Q: Can I enable multiple categories?
**A**: Yes! `enable_advanced_features("all")` or enable each separately.

### Q: Do enabled categories persist?
**A**: Not in v3.0.0. Need to re-enable each session. Future versions may add persistence.

### Q: Why remove elicitation tools?
**A**: Claude Desktop doesn't support MCP elicitation API. Tools never worked there.

### Q: What if I used elicitation tools?
**A**: Migrate to non-interactive equivalents:
- add-todo-interactive → add-todo
- bulk-complete-todos → update-todo with for loop
- schedule-assistant → update-todo with when parameter
- *-template tools → use add-project and manual copying

---

## Support

### Documentation
- README.md: Full tool documentation
- CHANGELOG.md: Version history
- IMPLEMENTATION_SUMMARY.md: Technical details

### Community
- GitHub Issues: Bug reports, feature requests
- Discussions: Questions, best practices

### Testing Help Needed
We need testers for:
- Claude Desktop integration
- VS Code integration
- Cursor integration
- Windsurf integration
- Various MCP clients

Report findings in GitHub Issues with "migration" label.

---

**Last Updated**: 2025-11-02  
**Version**: 3.0.0 (in development)  
**Status**: Documentation ready, awaiting testing
