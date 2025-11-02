# Implementation Tasks: MCP Features Expansion

**Proposal**: mcp-features-expansion-2025  
**Target Version**: v4.0.0  
**Timeline**: 6 weeks  
**Status**: 📋 Ready to Start

---

## Phase 1: Prompts Implementation (Week 1-2)

### Task 1.1: Setup & Infrastructure
- [ ] Create `src/things_mcp/prompts.py` module
- [ ] Define PromptCategory enum (TaskCreation, ProjectPlanning, Review, Workflow)
- [ ] Create PROMPT_ANNOTATIONS constant for metadata
- [ ] Add prompt registration helper function
- [ ] Import FastMCP prompt types (PromptMessage, TextContent)

**Estimated Time**: 2 hours  
**Files**: `src/things_mcp/prompts.py` (new), `src/things_mcp/fast_server.py` (imports)

---

### Task 1.2: Task Creation Prompts (5 prompts)

#### 1.2.1: create-simple-task
- [ ] Implement prompt function
- [ ] Parameters: task_name, project?, tags?
- [ ] Add docstring with example
- [ ] Add tags: {"things3", "task_creation", "simple"}
- [ ] Test in Claude Desktop

#### 1.2.2: create-task-with-deadline
- [ ] Implement prompt function
- [ ] Parameters: task_name, deadline, project?, tags?, notes?
- [ ] Add deadline validation guidance
- [ ] Add tags: {"things3", "task_creation", "deadline"}
- [ ] Test in Claude Desktop

#### 1.2.3: create-recurring-task
- [ ] Implement prompt function
- [ ] Parameters: task_name, frequency (daily/weekly/monthly), project?, tags?
- [ ] Add recurrence pattern examples
- [ ] Add tags: {"things3", "task_creation", "recurring"}
- [ ] Test in Claude Desktop

#### 1.2.4: create-task-with-checklist
- [ ] Implement prompt function
- [ ] Parameters: task_name, checklist_items (list), project?, deadline?
- [ ] Format checklist as markdown
- [ ] Add tags: {"things3", "task_creation", "checklist"}
- [ ] Test in Claude Desktop

#### 1.2.5: brainstorm-project-tasks
- [ ] Implement prompt function
- [ ] Parameters: project_goal, project_name?, deadline?, context?
- [ ] Generate comprehensive brainstorming prompt
- [ ] Add tags: {"things3", "task_creation", "brainstorming"}
- [ ] Test in Claude Desktop

**Estimated Time**: 4 hours (5 prompts × ~45 min each)  
**Files**: `src/things_mcp/prompts.py`

---

### Task 1.3: Project Planning Prompts (4 prompts)

#### 1.3.1: start-new-project
- [ ] Implement prompt function
- [ ] Parameters: project_name, goal, deadline?, area?, tags?
- [ ] Include project setup checklist
- [ ] Add tags: {"things3", "project_planning", "setup"}
- [ ] Test in Claude Desktop

#### 1.3.2: create-project-with-phases
- [ ] Implement prompt function
- [ ] Parameters: project_name, phases (list), deadline?
- [ ] Generate heading structure prompt
- [ ] Add tags: {"things3", "project_planning", "phases"}
- [ ] Test in Claude Desktop

#### 1.3.3: daily-standup-review
- [ ] Implement prompt function
- [ ] Parameters: focus_areas? (list)
- [ ] Generate morning review questions
- [ ] Add tags: {"things3", "review", "daily"}
- [ ] Test in Claude Desktop

#### 1.3.4: weekly-review
- [ ] Implement prompt function
- [ ] Parameters: None (template-based)
- [ ] GTD-style weekly review structure
- [ ] Add tags: {"things3", "review", "weekly", "gtd"}
- [ ] Test in Claude Desktop

**Estimated Time**: 3 hours (4 prompts × ~45 min each)  
**Files**: `src/things_mcp/prompts.py`

---

### Task 1.4: Review & Reflection Prompts (3 prompts)

#### 1.4.1: reflect-on-completed-tasks
- [ ] Implement prompt function
- [ ] Parameters: days (default 7), project?
- [ ] Generate reflection questions
- [ ] Add tags: {"things3", "review", "reflection"}
- [ ] Test in Claude Desktop

#### 1.4.2: identify-stalled-projects
- [ ] Implement prompt function
- [ ] Parameters: min_inactive_days (default 14)
- [ ] Generate project health questions
- [ ] Add tags: {"things3", "review", "projects"}
- [ ] Test in Claude Desktop

#### 1.4.3: review-overdue-items
- [ ] Implement prompt function
- [ ] Parameters: None
- [ ] Generate triage questions
- [ ] Add tags: {"things3", "review", "deadlines"}
- [ ] Test in Claude Desktop

**Estimated Time**: 2 hours (3 prompts × ~40 min each)  
**Files**: `src/things_mcp/prompts.py`

---

### Task 1.5: Workflow Automation Prompts (3 prompts)

#### 1.5.1: batch-schedule-tasks
- [ ] Implement prompt function
- [ ] Parameters: task_filter (tag/project/area), schedule_strategy?
- [ ] Generate batch scheduling prompt
- [ ] Add tags: {"things3", "workflow", "scheduling"}
- [ ] Test in Claude Desktop

#### 1.5.2: organize-inbox
- [ ] Implement prompt function
- [ ] Parameters: limit (default 10)
- [ ] Generate inbox processing prompt
- [ ] Add tags: {"things3", "workflow", "inbox"}
- [ ] Test in Claude Desktop

#### 1.5.3: suggest-next-actions
- [ ] Implement prompt function
- [ ] Parameters: context? (time_of_day, energy_level, available_time)
- [ ] Generate context-aware action suggestions
- [ ] Add tags: {"things3", "workflow", "productivity"}
- [ ] Test in Claude Desktop

**Estimated Time**: 2 hours (3 prompts × ~40 min each)  
**Files**: `src/things_mcp/prompts.py`

---

### Task 1.6: Prompt Registration & Testing

- [ ] Register all 15 prompts in fast_server.py
- [ ] Add prompts to MCP server initialization
- [ ] Test prompt listing in Claude Desktop
- [ ] Test each prompt execution
- [ ] Verify tags are visible
- [ ] Document prompt usage in README.md
- [ ] Add examples to documentation

**Estimated Time**: 2 hours  
**Files**: `src/things_mcp/fast_server.py`, `README.md`

---

**Phase 1 Total Time**: ~15 hours (2 weeks part-time)

---

## Phase 2: Resources Implementation (Week 3-4)

### Task 2.1: Setup & Infrastructure

- [ ] Create `src/things_mcp/resources.py` module
- [ ] Define ResourceCategory enum
- [ ] Create RESOURCE_ANNOTATIONS constant
- [ ] Add resource helper functions
- [ ] Design URI namespace hierarchy
- [ ] Document URI scheme

**Estimated Time**: 2 hours  
**Files**: `src/things_mcp/resources.py` (new)

---

### Task 2.2: Hierarchical Structure Resources (8 resources)

#### 2.2.1: things://projects/list
- [ ] Implement resource function
- [ ] Return all projects with metadata
- [ ] Include: uuid, title, status, area, todo_count, created, modified
- [ ] Add pagination (limit parameter)
- [ ] Test in Claude Desktop

#### 2.2.2: things://projects/{uuid}/info
- [ ] Implement resource template function
- [ ] Return single project full details
- [ ] Include all project fields
- [ ] Handle not found error
- [ ] Test in Claude Desktop

#### 2.2.3: things://projects/{uuid}/todos
- [ ] Implement resource template function
- [ ] Return todos in project
- [ ] Include status filter option
- [ ] Add sorting options
- [ ] Test in Claude Desktop

#### 2.2.4: things://projects/{uuid}/structure
- [ ] Implement resource template function
- [ ] Return headings + todos hierarchy
- [ ] Use tree structure format
- [ ] Include completion stats per heading
- [ ] Test in Claude Desktop

#### 2.2.5: things://areas/list
- [ ] Implement resource function
- [ ] Return all areas with metadata
- [ ] Include: uuid, title, project_count, visible
- [ ] Test in Claude Desktop

#### 2.2.6: things://areas/{uuid}/info
- [ ] Implement resource template function
- [ ] Return single area details
- [ ] Include all area fields
- [ ] Handle not found error
- [ ] Test in Claude Desktop

#### 2.2.7: things://areas/{uuid}/projects
- [ ] Implement resource template function
- [ ] Return projects in area
- [ ] Include project status
- [ ] Add sorting options
- [ ] Test in Claude Desktop

#### 2.2.8: things://tags/list
- [ ] Implement resource function
- [ ] Return all tags with usage stats
- [ ] Include: title, item_count, shortcut
- [ ] Sort by usage (most used first)
- [ ] Test in Claude Desktop

**Estimated Time**: 6 hours (8 resources × ~45 min each)  
**Files**: `src/things_mcp/resources.py`

---

### Task 2.3: Todo Lists Resources (6 resources)

#### 2.3.1: things://todos/inbox
- [ ] Implement resource function
- [ ] Return inbox items
- [ ] Add limit parameter (default 100)
- [ ] Include type filter
- [ ] Test in Claude Desktop

#### 2.3.2: things://todos/today
- [ ] Implement resource function
- [ ] Return today's scheduled tasks
- [ ] Include deadline info
- [ ] Add type filter
- [ ] Test in Claude Desktop

#### 2.3.3: things://todos/upcoming
- [ ] Implement resource function
- [ ] Return upcoming scheduled items
- [ ] Group by date
- [ ] Add lookahead parameter (days)
- [ ] Test in Claude Desktop

#### 2.3.4: things://todos/anytime
- [ ] Implement resource function
- [ ] Return anytime list items
- [ ] Add limit parameter
- [ ] Include type filter
- [ ] Test in Claude Desktop

#### 2.3.5: things://todos/someday
- [ ] Implement resource function
- [ ] Return someday/maybe items
- [ ] Add type filter
- [ ] Include project context
- [ ] Test in Claude Desktop

#### 2.3.6: things://todos/logbook
- [ ] Implement resource function
- [ ] Return completed items
- [ ] Add pagination (important for large logbook)
- [ ] Add date range filter
- [ ] Limit default to 100 items
- [ ] Test in Claude Desktop

**Estimated Time**: 4 hours (6 resources × ~40 min each)  
**Files**: `src/things_mcp/resources.py`

---

### Task 2.4: Individual Items Resources (4 resources)

#### 2.4.1: things://todos/{uuid}/info
- [ ] Implement resource template function
- [ ] Return complete todo details
- [ ] Include all fields (created, modified, deadline, etc.)
- [ ] Handle not found error
- [ ] Test in Claude Desktop

#### 2.4.2: things://todos/{uuid}/checklist
- [ ] Implement resource template function
- [ ] Return checklist items
- [ ] Include completion status
- [ ] Format as structured list
- [ ] Test in Claude Desktop

#### 2.4.3: things://projects/{uuid}/notes
- [ ] Implement resource template function
- [ ] Return project notes as text
- [ ] MIME type: text/plain
- [ ] Handle empty notes
- [ ] Test in Claude Desktop

#### 2.4.4: things://todos/{uuid}/notes
- [ ] Implement resource template function
- [ ] Return todo notes as text
- [ ] MIME type: text/plain
- [ ] Handle empty notes
- [ ] Test in Claude Desktop

**Estimated Time**: 2.5 hours (4 resources × ~35 min each)  
**Files**: `src/things_mcp/resources.py`

---

### Task 2.5: Search & Discovery Resources (3 resources)

#### 2.5.1: things://search/{query}
- [ ] Implement resource template function
- [ ] Use things.search() API
- [ ] Return results with highlights
- [ ] Add limit parameter
- [ ] Test in Claude Desktop

#### 2.5.2: things://tags/{name}/items
- [ ] Implement resource template function
- [ ] Return all items with tag
- [ ] Include type filter
- [ ] Add status filter
- [ ] Test in Claude Desktop

#### 2.5.3: things://deadlines/overdue
- [ ] Implement resource function
- [ ] Return all overdue items
- [ ] Sort by deadline (oldest first)
- [ ] Include urgency badges
- [ ] Test in Claude Desktop

**Estimated Time**: 2 hours (3 resources × ~40 min each)  
**Files**: `src/things_mcp/resources.py`

---

### Task 2.6: Analytics Resource (1 resource)

#### 2.6.1: things://analytics/summary
- [ ] Implement resource function
- [ ] Return productivity summary
- [ ] Include: completion rate, velocity, overdue count
- [ ] Add trend analysis
- [ ] Cache for 5 minutes
- [ ] Test in Claude Desktop

**Estimated Time**: 1 hour  
**Files**: `src/things_mcp/resources.py`

---

### Task 2.7: Resource Registration & Testing

- [ ] Register all 22 resources in fast_server.py
- [ ] Add resources to MCP server initialization
- [ ] Test resource listing in Claude Desktop
- [ ] Test each resource URI
- [ ] Test resource templates with parameters
- [ ] Verify MIME types correct
- [ ] Document URI scheme in README.md
- [ ] Add URI examples to documentation

**Estimated Time**: 2 hours  
**Files**: `src/things_mcp/fast_server.py`, `README.md`

---

**Phase 2 Total Time**: ~19.5 hours (2 weeks part-time)

---

## Phase 3: Sampling Implementation (Week 5)

### Task 3.1: Setup & Infrastructure

- [ ] Create `src/things_mcp/sampling.py` module
- [ ] Document sampling handler requirements
- [ ] Add error handling for missing handler
- [ ] Create fallback behavior utilities
- [ ] Add sampling to README prerequisites

**Estimated Time**: 1 hour  
**Files**: `src/things_mcp/sampling.py` (new), `README.md`

---

### Task 3.2: Sampling Tools

#### 3.2.1: suggest-tags-ai
- [ ] Implement tool function
- [ ] Parameters: title, notes?, ctx
- [ ] Build sampling prompt with existing tags
- [ ] Parse LLM response
- [ ] Handle missing handler error
- [ ] Test with Claude Desktop + handler
- [ ] Document handler setup

#### 3.2.2: recommend-deadline
- [ ] Implement tool function
- [ ] Parameters: title, notes?, project_context?, ctx
- [ ] Build sampling prompt with complexity analysis
- [ ] Parse deadline + reasoning
- [ ] Handle missing handler error
- [ ] Test with Claude Desktop + handler
- [ ] Document usage

#### 3.2.3: parse-task-description
- [ ] Implement tool function
- [ ] Parameters: description, ctx
- [ ] Build structured parsing prompt
- [ ] Parse JSON response
- [ ] Handle parse errors
- [ ] Handle missing handler error
- [ ] Test with various inputs
- [ ] Document format

#### 3.2.4: analyze-project-health-ai
- [ ] Implement tool function
- [ ] Parameters: project_uuid, ctx
- [ ] Gather project metrics
- [ ] Build comprehensive analysis prompt
- [ ] Return formatted analysis
- [ ] Handle missing handler error
- [ ] Test with real projects
- [ ] Document output format

#### 3.2.5: triage-inbox-ai
- [ ] Implement tool function
- [ ] Parameters: limit (default 10), ctx
- [ ] Build triage prompt per item
- [ ] Batch sampling requests
- [ ] Parse suggestions
- [ ] Handle missing handler error
- [ ] Test with inbox items
- [ ] Document suggestions format

**Estimated Time**: 8 hours (5 tools × ~1.5 hours each)  
**Files**: `src/things_mcp/sampling.py`, `src/things_mcp/fast_server.py`

---

### Task 3.3: Client Handler Documentation

- [ ] Write detailed handler setup guide
- [ ] Provide Claude API example
- [ ] Provide OpenAI API example
- [ ] Document error handling
- [ ] Document fallback behavior
- [ ] Add to README.md
- [ ] Create troubleshooting section

**Estimated Time**: 2 hours  
**Files**: `README.md`, `docs/SAMPLING.md` (new)

---

### Task 3.4: Testing & Validation

- [ ] Test all 5 sampling tools
- [ ] Test with missing handler
- [ ] Test error handling
- [ ] Test with different LLM providers
- [ ] Validate response parsing
- [ ] Performance testing
- [ ] Document test results

**Estimated Time**: 2 hours

---

**Phase 3 Total Time**: ~13 hours (1 week part-time)

---

## Phase 4: Enhanced Notifications (Week 6)

### Task 4.1: Verify Auto-Notifications

- [ ] Test prompts/list_changed notification
- [ ] Test resources/list_changed notification
- [ ] Test tools/list_changed notification (existing)
- [ ] Document when notifications fire
- [ ] Test in Claude Desktop

**Estimated Time**: 1 hour

---

### Task 4.2: Enhanced Progress Reporting

- [ ] Add progress to bulk operations (if any remain)
- [ ] Add progress to large searches
- [ ] Add progress to analytics calculations
- [ ] Add progress to sampling operations
- [ ] Test progress display in Claude Desktop

**Estimated Time**: 2 hours  
**Files**: Various tool files

---

### Task 4.3: Documentation

- [ ] Document notification system in README
- [ ] Document when notifications fire
- [ ] Document client handling requirements
- [ ] Add troubleshooting section
- [ ] Document progress reporting

**Estimated Time**: 1 hour  
**Files**: `README.md`

---

**Phase 4 Total Time**: ~4 hours (part of Week 6)

---

## Phase 5: Integration & Release (Week 6)

### Task 5.1: Integration Testing

- [ ] Test all 15 prompts
- [ ] Test all 22 resources
- [ ] Test all 5 sampling tools
- [ ] Test all notifications
- [ ] Test prompt + resource interaction
- [ ] Test resource + tool interaction
- [ ] Test sampling + tool interaction
- [ ] Performance testing
- [ ] Memory leak testing

**Estimated Time**: 4 hours

---

### Task 5.2: Documentation

#### 5.2.1: README.md Updates
- [ ] Add Prompts section with full list
- [ ] Add Resources section with URI hierarchy
- [ ] Add Sampling section with handler setup
- [ ] Add Notifications section
- [ ] Update Features section
- [ ] Update Quick Start
- [ ] Update Tool Inventory (add prompt/resource counts)

#### 5.2.2: CHANGELOG.md
- [ ] Create v4.0.0 section
- [ ] List all new prompts
- [ ] List all new resources
- [ ] List all new sampling tools
- [ ] Document enhanced notifications
- [ ] Document breaking changes (none expected)

#### 5.2.3: Migration Guide
- [ ] Create v3.0.0 → v4.0.0 guide
- [ ] Document new features
- [ ] Document how to enable features
- [ ] Provide usage examples
- [ ] Document handler setup

#### 5.2.4: AGENTS.md
- [ ] Update implementation log
- [ ] Document feature counts
- [ ] Update code statistics
- [ ] Add v4.0.0 milestone

**Estimated Time**: 4 hours

---

### Task 5.3: Code Quality

- [ ] Run ruff check
- [ ] Fix all warnings
- [ ] Run type checker
- [ ] Fix type issues
- [ ] Test compilation
- [ ] Code review

**Estimated Time**: 2 hours

---

### Task 5.4: Release Preparation

- [ ] Version bump to v4.0.0
- [ ] Update pyproject.toml
- [ ] Update smithery.yaml
- [ ] Update __init__.py
- [ ] Git commit with comprehensive message
- [ ] Create GitHub release draft
- [ ] Write release notes

**Estimated Time**: 1 hour

---

**Phase 5 Total Time**: ~11 hours (remainder of Week 6)

---

## Total Effort Estimate

| Phase | Tasks | Estimated Hours | Timeline |
|-------|-------|-----------------|----------|
| Phase 1: Prompts | 15 prompts | 15 hours | Week 1-2 |
| Phase 2: Resources | 22 resources | 19.5 hours | Week 3-4 |
| Phase 3: Sampling | 5 tools | 13 hours | Week 5 |
| Phase 4: Notifications | Enhancement | 4 hours | Week 6 |
| Phase 5: Integration | Testing & Docs | 11 hours | Week 6 |
| **Total** | **All Phases** | **62.5 hours** | **6 weeks** |

**Assumptions**:
- Part-time work (~10-12 hours/week)
- Testing as you go (not separate phase)
- Documentation concurrent with implementation
- Claude Desktop available for testing

---

## Checkpoints

### Week 2 Checkpoint: Prompts Complete
- [ ] 15 prompts registered and tested
- [ ] Documentation updated
- [ ] No blocking issues
- **Decision Point**: Proceed to Resources or iterate on Prompts?

### Week 4 Checkpoint: Resources Complete
- [ ] 22 resources registered and tested
- [ ] URI scheme working
- [ ] Documentation updated
- [ ] No blocking issues
- **Decision Point**: Proceed to Sampling or iterate on Resources?

### Week 5 Checkpoint: Sampling Complete
- [ ] 5 sampling tools working
- [ ] Handler documentation complete
- [ ] Error handling tested
- [ ] No blocking issues
- **Decision Point**: Proceed to final integration or iterate?

### Week 6 Checkpoint: Ready for Release
- [ ] All features tested
- [ ] Documentation complete
- [ ] No critical bugs
- [ ] Code quality verified
- **Decision Point**: Release v4.0.0 or add polish?

---

## Success Criteria

### Must Have (Required for v4.0.0)
- ✅ All 15 prompts functional
- ✅ All 22 resources functional
- ✅ At least 3 sampling tools functional
- ✅ Notifications working
- ✅ Zero compilation errors
- ✅ Documentation complete

### Should Have (Nice to Have)
- ✅ All 5 sampling tools functional
- ✅ Comprehensive examples in docs
- ✅ Performance optimizations
- ✅ Error handling edge cases

### Could Have (Future Enhancement)
- ⏳ Custom notification types
- ⏳ Resource subscriptions
- ⏳ Prompt variations
- ⏳ Binary resources

---

## Risk Management

### High Risk
- **Sampling handler missing**: Document clearly, provide fallback
- **Performance issues**: Add caching, pagination
- **URI conflicts**: Design careful namespace

### Medium Risk
- **Too many prompts**: Use tags, enable/disable feature
- **Resource format inconsistency**: Define clear schema
- **Testing coverage**: Test each feature thoroughly

### Low Risk
- **Documentation lag**: Write docs as you go
- **Version conflicts**: FastMCP already compatible
- **Client support**: Claude Desktop supports all features

---

**Status**: 📋 Ready to Start  
**Next Action**: Begin Phase 1, Task 1.1 (Setup & Infrastructure)  
**Approval**: Awaiting user confirmation to proceed
