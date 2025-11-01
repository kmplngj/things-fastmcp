# Feature Expansion 2025 - Tasks

## Phase 1: Critical Gaps (v2.1.0)

### 1.1: Checklist Operations
**Priority**: HIGH  
**Estimated effort**: 3 days  
**Dependencies**: None

#### Sub-tasks:
- [ ] 1.1.1: Add `get-checklist-items` tool
  - Use `things.checklist_items(todo_uuid)` API
  - Return list of checklist items with title, status, uuid
  - Add to READ_ONLY_ANNOTATIONS
  
- [ ] 1.1.2: Add `add-checklist-item` tool
  - Use URL scheme: `things:///update?id=todo_uuid&checklist-items=...`
  - Support adding multiple items at once (newline separated)
  - Validate todo exists first
  - Add to MODIFY_ANNOTATIONS
  
- [ ] 1.1.3: Add `complete-checklist-item` tool
  - Use URL scheme update with checklist item modification
  - Mark specific checklist item as completed
  - Add to MODIFY_ANNOTATIONS
  
- [ ] 1.1.4: Add `get-todos-with-checklists` tool
  - Filter for todos where `checklist=True`
  - Use `include_items=True` to get full checklist data
  - Add to READ_ONLY_ANNOTATIONS

**Validation:**
- [ ] All 4 tools compile without errors
- [ ] Ruff check passes
- [ ] Manual test: Create todo with checklist, fetch, complete item
- [ ] Documentation updated in README

---

### 1.2: Heading Management
**Priority**: HIGH  
**Estimated effort**: 3 days  
**Dependencies**: None

#### Sub-tasks:
- [ ] 1.2.1: Add `add-heading` tool
  - Use URL scheme: `things:///add?type=heading&list-id=project_uuid&heading=title`
  - Validate project exists
  - Support positioning (before/after UUID)
  - Add to MODIFY_ANNOTATIONS
  
- [ ] 1.2.2: Add `get-project-structure` tool
  - Use `include_items=True` with project query
  - Format output to show headings with todos grouped underneath
  - Make hierarchy clear (indent todos under headings)
  - Add to READ_ONLY_ANNOTATIONS
  
- [ ] 1.2.3: Add `move-todo-under-heading` tool
  - Use URL scheme update to change todo's heading assignment
  - Validate both todo and heading exist in same project
  - Add to MODIFY_ANNOTATIONS

**Validation:**
- [ ] All 3 tools compile without errors
- [ ] Ruff check passes
- [ ] Manual test: Create heading, add todos under it, fetch structure
- [ ] Documentation updated in README

---

### 1.3: Enhanced Filter Parameters
**Priority**: MEDIUM  
**Estimated effort**: 2 days  
**Dependencies**: None

#### Sub-tasks:
- [ ] 1.3.1: Add `type` parameter to query tools
  - Affected tools: get-inbox, get-today, get-upcoming, get-anytime, get-someday, get-logbook, get-trash
  - Options: 'to-do', 'project', 'heading', None (default)
  - Update tool annotations
  
- [ ] 1.3.2: Add `status` parameter to query tools
  - Same tools as 1.3.1
  - Options: 'incomplete' (default), 'completed', 'canceled', None
  - Override hardcoded status filters
  
- [ ] 1.3.3: Add `last` parameter to query tools
  - Same tools as 1.3.1 plus search tools
  - Format: '3d', '5w', '1y' (X[d/w/y])
  - Validate format with regex
  
- [ ] 1.3.4: Add `include_items` parameter to get-todos, get-projects
  - Boolean, default False
  - When True, include checklists for todos, sub-items for projects
  - Update formatters to handle nested data
  
- [ ] 1.3.5: Update `_apply_sort_and_limit` helper
  - Support sorting by deadline (new field)
  - Handle None values gracefully

**Validation:**
- [ ] All tools compile with new parameters
- [ ] Ruff check passes
- [ ] Test each new parameter combination
- [ ] Metadata shows applied filters
- [ ] Documentation updated

---

### 1.4: Deadline & Overdue Management
**Priority**: MEDIUM  
**Estimated effort**: 2 days  
**Dependencies**: 1.3 (enhanced filters)

#### Sub-tasks:
- [ ] 1.4.1: Add `get-overdue-items` tool
  - Use `deadline="past"` filter with `status="incomplete"`
  - Sort by deadline (most overdue first)
  - Show days overdue in metadata
  - Add to READ_ONLY_ANNOTATIONS
  
- [ ] 1.4.2: Add `get-items-due-soon` tool
  - Use deadline filter: `deadline="<=7d from today"`
  - Configurable days param (default 7)
  - Sort by deadline ascending
  - Add to READ_ONLY_ANNOTATIONS
  
- [ ] 1.4.3: Add `set-deadline` tool
  - Use URL scheme: `things:///update?id=uuid&deadline=YYYY-MM-DD`
  - Support natural date input via parsing
  - Add to MODIFY_ANNOTATIONS

**Validation:**
- [ ] All 3 tools compile without errors
- [ ] Ruff check passes
- [ ] Test with todos at various deadline states
- [ ] Date parsing works correctly
- [ ] Documentation updated

---

### Phase 1 Integration Tasks
- [ ] 1.5.1: Update TOOL_ANNOTATIONS dict with all new tools
- [ ] 1.5.2: Run full ruff check on fast_server.py
- [ ] 1.5.3: Update AGENTS.md with Phase 1 changes
- [ ] 1.5.4: Update README.md with new tool inventory (21 → 34 tools)
- [ ] 1.5.5: Test all new tools end-to-end
- [ ] 1.5.6: Update version to 2.1.0 in pyproject.toml
- [ ] 1.5.7: Create git tag v2.1.0
- [ ] 1.5.8: Update CHANGELOG.md

---

## Phase 2: Interactive Workflows (v2.2.0)

### 2.1: Bulk Operations with Elicitation
**Priority**: HIGH  
**Estimated effort**: 4 days  
**Dependencies**: Phase 1 complete

#### Sub-tasks:
- [ ] 2.1.1: Add `bulk-complete-todos` interactive tool
  - Elicit filter criteria (tag, project, area)
  - Show preview: "Found X todos matching..."
  - Confirm via elicitation: "Complete all X? (yes/no)"
  - Batch URL scheme calls (max 100 items)
  - Progress updates via ctx.info()
  - Add to MODIFY_ANNOTATIONS
  
- [ ] 2.1.2: Add `bulk-schedule-todos` interactive tool
  - Elicit: source (tag/project/inbox)
  - Show unscheduled items
  - Elicit: target date/time (use natural language)
  - Confirm and batch schedule
  - Add to MODIFY_ANNOTATIONS
  
- [ ] 2.1.3: Add `bulk-tag-todos` interactive tool
  - Elicit: source criteria
  - Show matching todos
  - Elicit: tag to add/remove
  - Confirm and batch update
  - Add to MODIFY_ANNOTATIONS
  
- [ ] 2.1.4: Add `bulk-move-todos` interactive tool
  - Elicit: source criteria
  - Show matching todos
  - Elicit: destination (project/area)
  - Confirm and batch move
  - Add to MODIFY_ANNOTATIONS

**Validation:**
- [ ] All elicitation prompts clear and helpful
- [ ] Preview shows accurate counts
- [ ] Confirmation step prevents accidents
- [ ] Batch operations respect 100-item limit
- [ ] Progress updates work correctly
- [ ] Error handling for partial failures

---

### 2.2: Smart Scheduling Assistant
**Priority**: MEDIUM  
**Estimated effort**: 3 days  
**Dependencies**: 2.1 (elicitation pattern established)

#### Sub-tasks:
- [ ] 2.2.1: Design elicitation workflow
  - Step 1: Fetch unscheduled items (start_date=False)
  - Step 2: Show count, ask "Schedule how many? (all/X)"
  - Step 3: For each batch, ask priority level
  - Step 4: Suggest scheduling based on priority
  - Step 5: Confirm batch scheduling
  
- [ ] 2.2.2: Implement priority heuristics
  - Check for deadline presence (urgent)
  - Check for tag patterns ("important", "urgent")
  - Check project type (work vs personal)
  - Suggest: today (urgent), tomorrow (high), this week (normal), next week (low)
  
- [ ] 2.2.3: Add `schedule-assistant` tool
  - Multi-step elicitation workflow
  - Smart suggestions via ctx.info()
  - Batch scheduling with preview
  - Add to MODIFY_ANNOTATIONS

**Validation:**
- [ ] Workflow feels natural and helpful
- [ ] Suggestions make sense for different scenarios
- [ ] User can override suggestions
- [ ] Handles edge cases (no unscheduled items)

---

### 2.3: Project Template System
**Priority**: MEDIUM  
**Estimated effort**: 4 days  
**Dependencies**: Phase 1 complete (headings needed)

#### Sub-tasks:
- [ ] 2.3.1: Design template storage format
  ```json
  {
    "name": "Product Launch",
    "project": {
      "title": "Launch {{product_name}}",
      "notes": "Standard launch process",
      "area": "{{area_uuid}}"
    },
    "headings": [
      {
        "title": "Planning",
        "todos": [
          {"title": "Define scope", "tags": ["Planning"]},
          {"title": "Set timeline", "tags": ["Planning"]}
        ]
      },
      {
        "title": "Execution",
        "todos": [...]
      }
    ]
  }
  ```
  - Support variable substitution {{var}}
  - Store in state management: `ctx.set_state(f"template_{name}", template_json)`
  
- [ ] 2.3.2: Add `save-project-as-template` tool
  - Input: project_uuid, template_name
  - Fetch project with include_items=True
  - Extract structure (headings + todos)
  - Identify variables (prompt user which fields to parameterize)
  - Save to state
  - Add to MODIFY_ANNOTATIONS
  
- [ ] 2.3.3: Add `create-from-template` interactive tool
  - List available templates from state
  - Elicit: which template?
  - Elicit: variable values ({{product_name}}, {{area}})
  - Show preview of structure
  - Confirm and create via URL scheme batch
  - Add to MODIFY_ANNOTATIONS
  
- [ ] 2.3.4: Add `list-templates` tool
  - Query state for all template_* keys
  - Show name, description, variable list
  - Add to READ_ONLY_ANNOTATIONS
  
- [ ] 2.3.5: Add `delete-template` tool
  - Confirm deletion via elicitation
  - Remove from state
  - Add to MODIFY_ANNOTATIONS

**Validation:**
- [ ] Templates persist across sessions
- [ ] Variable substitution works correctly
- [ ] Complex structures (multi-heading) create properly
- [ ] State management doesn't conflict between users
- [ ] Templates can be shared (export/import JSON)

---

### Phase 2 Integration Tasks
- [ ] 2.4.1: Update TOOL_ANNOTATIONS with all new tools
- [ ] 2.4.2: Test all interactive workflows end-to-end
- [ ] 2.4.3: Update documentation (README, AGENTS.md)
- [ ] 2.4.4: Version bump to 2.2.0
- [ ] 2.4.5: Update CHANGELOG.md
- [ ] 2.4.6: Create git tag v2.2.0

---

## Phase 3: Intelligence Layer (v2.3.0)

### 3.1: Productivity Analytics
**Priority**: LOW  
**Estimated effort**: 3 days  
**Dependencies**: Phase 1 complete

#### Sub-tasks:
- [ ] 3.1.1: Add `get-productivity-stats` tool
  - Count completed items by day/week/month
  - Use `stop_date` filters and SQL COUNT
  - Group by period
  - Calculate trends (up/down)
  - Add to READ_ONLY_ANNOTATIONS
  
- [ ] 3.1.2: Add `get-completion-rate-by-project` tool
  - For each project: completed vs total
  - Sort by completion rate
  - Show projects near 100% (ready to archive)
  - Add to READ_ONLY_ANNOTATIONS
  
- [ ] 3.1.3: Add `get-tag-usage-stats` tool
  - Count items per tag
  - Show most/least used tags
  - Identify orphaned tags (unused)
  - Add to READ_ONLY_ANNOTATIONS
  
- [ ] 3.1.4: Add `get-time-to-completion` tool
  - Calculate days between created and completed
  - Group by project/area/tag
  - Identify bottlenecks
  - Add to READ_ONLY_ANNOTATIONS

**Validation:**
- [ ] Stats calculate correctly
- [ ] Performance acceptable (< 500ms for analytics)
- [ ] Output formatted clearly
- [ ] Handles edge cases (no data)

---

### 3.2: Project Health Monitoring
**Priority**: LOW  
**Estimated effort**: 2 days  
**Dependencies**: 3.1 (analytics foundation)

#### Sub-tasks:
- [ ] 3.2.1: Add `get-stalled-projects` tool
  - Find projects with no completed items in X days (configurable, default 14)
  - Check for todos with no recent modifications
  - Sort by staleness
  - Add to READ_ONLY_ANNOTATIONS
  
- [ ] 3.2.2: Add `get-project-health-report` tool
  - For given project or all projects:
    - Progress percentage
    - Overdue item count
    - Days since last activity
    - Todo/heading ratio (structure health)
    - Health score (0-100)
  - Add to READ_ONLY_ANNOTATIONS

**Validation:**
- [ ] Health scores meaningful and actionable
- [ ] Stalled project detection accurate
- [ ] Reports identify real issues

---

### 3.3: Tag Relationship Analysis
**Priority**: LOW  
**Estimated effort**: 2 days  
**Dependencies**: None

#### Sub-tasks:
- [ ] 3.3.1: Add `get-tag-relationships` tool
  - Find tags that commonly appear together
  - Use co-occurrence matrix
  - Show top 10 pairs
  - Add to READ_ONLY_ANNOTATIONS
  
- [ ] 3.3.2: Add `suggest-tag-cleanup` tool
  - Find similar tag names (fuzzy match)
  - Identify single-use tags
  - Suggest consolidation
  - Add to READ_ONLY_ANNOTATIONS

**Validation:**
- [ ] Co-occurrence calculations correct
- [ ] Fuzzy matching works well
- [ ] Suggestions make sense

---

### 3.4: Natural Language Scheduling
**Priority**: LOW  
**Estimated effort**: 3 days  
**Dependencies**: None (but uses 2.1 pattern)

#### Sub-tasks:
- [ ] 3.4.1: Install `dateparser` library
  - Add to pyproject.toml dependencies
  - Test parsing capabilities
  
- [ ] 3.4.2: Create date parsing helper
  - Wrap dateparser with Things-specific logic
  - Handle relative dates ("tomorrow", "next Monday")
  - Handle times ("8pm", "17:00")
  - Return tuple: (date, time, reminder)
  
- [ ] 3.4.3: Add `schedule-with-natural-language` tool
  - Input: todo_uuid, natural_text
  - Parse date/time
  - Show interpretation: "I understood: Wed Nov 6, 8:00 PM"
  - Confirm via elicitation
  - Schedule via URL scheme
  - Add to MODIFY_ANNOTATIONS

**Validation:**
- [ ] Parses common formats correctly
- [ ] Ambiguity handled via confirmation
- [ ] Edge cases graceful (invalid input)

---

### Phase 3 Integration Tasks
- [ ] 3.5.1: Performance testing with 50+ tools
- [ ] 3.5.2: Optimize slow analytics queries (add caching if needed)
- [ ] 3.5.3: Update all documentation
- [ ] 3.5.4: Version bump to 2.3.0
- [ ] 3.5.5: Update CHANGELOG.md
- [ ] 3.5.6: Create git tag v2.3.0
- [ ] 3.5.7: Consider caching strategy for analytics (Phase 3.1 optimization)

---

## Cross-Phase Tasks

### Testing
- [ ] Create test suite for new tools
- [ ] Add integration tests for elicitation workflows
- [ ] Performance benchmarks (before/after each phase)
- [ ] Load testing (100+ concurrent requests)

### Documentation
- [ ] Update README with full tool inventory
- [ ] Document elicitation patterns for other contributors
- [ ] Create examples for each new tool
- [ ] Update API documentation

### Maintenance
- [ ] Set up monitoring for state management
- [ ] Create migration guide (if needed)
- [ ] Plan for future caching layer
- [ ] Consider rate limiting for analytics

---

## Timeline Summary

| Phase | Duration | Tools Added | Key Features |
|-------|----------|-------------|--------------|
| Phase 1 | 1-2 weeks | 13 tools | Checklists, headings, filters, deadlines |
| Phase 2 | 2-3 weeks | 8-10 tools | Bulk ops, scheduling, templates |
| Phase 3 | 2-3 weeks | 9-11 tools | Analytics, health, NLP |
| **Total** | **5-8 weeks** | **30-34 tools** | **From 21 → 51-55 tools** |

---

## Risk Mitigation

### Performance Risks
- **Risk**: 50+ tools slow down server startup
- **Mitigation**: Middleware already monitoring, lazy-load analytics

### State Management Risks
- **Risk**: State conflicts between users
- **Mitigation**: Scope state by user/session

### URL Scheme Limits
- **Risk**: Batch operations hit URL length limits
- **Mitigation**: Cap at 100 items, chunk if needed

### Parsing Accuracy
- **Risk**: Natural language date parsing ambiguous
- **Mitigation**: Always confirm via elicitation before applying
