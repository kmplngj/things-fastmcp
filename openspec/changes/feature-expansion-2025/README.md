# Feature Expansion 2025 - Implementation Guide

## Quick Reference

**Goal**: Expand things-fastmcp from 21 to 51-55 MCP tools over 3 phases  
**Timeline**: 5-8 weeks  
**Current Version**: v2.0.0 → Target: v2.3.0

---

## Phase Overview

| Phase | Version | Timeline | Tools Added | Key Deliverables |
|-------|---------|----------|-------------|------------------|
| **Phase 1: Critical Gaps** | v2.1.0 | 1-2 weeks | 13 | Checklists, headings, filters, deadlines |
| **Phase 2: Interactive** | v2.2.0 | 2-3 weeks | 8-10 | Bulk ops, templates, smart scheduling |
| **Phase 3: Intelligence** | v2.3.0 | 2-3 weeks | 9-11 | Analytics, health, NLP scheduling |

---

## Phase 1: Critical Gaps (v2.1.0)

### What & Why
Fill missing basic functionality that users expect from Things 3:
- **Checklists**: Major Things 3 feature, completely absent
- **Headings**: Organizational tool, currently treated as generic tasks
- **Enhanced Filters**: API supports them, we don't expose them
- **Deadlines**: Overdue tracking missing

### Implementation Checklist

#### Week 1: Checklists & Headings
- [ ] **Day 1-2**: Implement 4 checklist tools
  - `get-checklist-items`, `add-checklist-item`, `complete-checklist-item`, `get-todos-with-checklists`
  - Test with Things URL scheme
  
- [ ] **Day 3-4**: Implement 3 heading tools
  - `add-heading`, `get-project-structure`, `move-todo-under-heading`
  - Test hierarchical formatting
  
- [ ] **Day 5**: Testing & documentation
  - End-to-end tests for all 7 tools
  - Update README with new tools

#### Week 2: Enhanced Filters & Deadlines
- [ ] **Day 1-2**: Add parameters to 11 existing tools
  - Parameters: `type`, `status`, `last`, `include_items`
  - Update validation helpers
  - Test backward compatibility
  
- [ ] **Day 3**: Implement 3 deadline tools
  - `get-overdue-items`, `get-items-due-soon`, `set-deadline`
  
- [ ] **Day 4-5**: Integration & release
  - Full ruff check
  - Update AGENTS.md, CHANGELOG.md
  - Version bump to 2.1.0
  - Create git tag

### Success Criteria
✅ 13 new/enhanced tools working  
✅ Zero ruff warnings  
✅ All existing tools still functional  
✅ Response times < 200ms (p95)  
✅ Documentation complete

---

## Phase 2: Interactive Workflows (v2.2.0)

### What & Why
Leverage FastMCP's elicitation API for safe, intelligent automation:
- **Bulk Operations**: Act on multiple items with preview + confirm
- **Smart Scheduling**: Guide users through scheduling decisions
- **Templates**: Features Things lacks but users need

### Implementation Checklist

#### Week 1: Bulk Operations
- [ ] **Day 1-2**: Implement `bulk-complete-todos`
  - Elicitation workflow: filter → preview → confirm → execute
  - Test with various filters (tag, project, area)
  - Validate 100-item limit
  
- [ ] **Day 2-3**: Implement `bulk-schedule-todos`
  - Multi-step elicitation
  - Natural date input support
  - Test scheduling patterns
  
- [ ] **Day 4-5**: Implement `bulk-tag-todos` and `bulk-move-todos`
  - Reuse established patterns
  - Test error handling

#### Week 2: Templates & Smart Scheduling
- [ ] **Day 1-3**: Template system
  - Design JSON format
  - Implement `save-project-as-template`
  - Implement `create-from-template`
  - Add `list-templates`, `delete-template`
  - Test state management persistence
  
- [ ] **Day 4-5**: Smart scheduling assistant
  - Implement `schedule-assistant` tool
  - Design priority heuristics
  - Test workflow UX

#### Week 3: Integration & Release
- [ ] **Day 1-2**: Testing
  - All interactive workflows
  - State management edge cases
  - Performance testing
  
- [ ] **Day 3-5**: Documentation & release
  - Update README with interactive tool examples
  - Document elicitation patterns
  - Update CHANGELOG.md
  - Version bump to 2.2.0
  - Create git tag

### Success Criteria
✅ 3+ bulk operations with safe elicitation  
✅ Template system working reliably  
✅ State persists across sessions  
✅ User feedback positive (test with users)  
✅ Documentation includes workflow examples

---

## Phase 3: Intelligence Layer (v2.3.0)

### What & Why
Add analytics and power features for advanced users:
- **Analytics**: Expose productivity insights from database
- **Health Monitoring**: Identify stalled projects, bottlenecks
- **NLP Scheduling**: Natural language date parsing

### Implementation Checklist

#### Week 1: Analytics
- [ ] **Day 1-2**: Productivity stats
  - Implement `get-productivity-stats`
  - Implement `get-completion-rate-by-project`
  - Test calculations
  
- [ ] **Day 3-4**: Tag analytics
  - Implement `get-tag-usage-stats`
  - Implement `get-time-to-completion`
  
- [ ] **Day 5**: Performance testing
  - Measure analytics query times
  - Optimize if needed

#### Week 2: Health & Insights
- [ ] **Day 1-2**: Project health
  - Implement `get-stalled-projects`
  - Implement `get-project-health-report`
  - Define health scoring algorithm
  
- [ ] **Day 3-4**: Tag relationships
  - Implement `get-tag-relationships`
  - Implement `suggest-tag-cleanup`
  - Test co-occurrence calculations

#### Week 3: NLP & Release
- [ ] **Day 1-2**: Natural language parsing
  - Add `dateparser` dependency
  - Implement date parser helper
  - Implement `schedule-with-natural-language`
  - Test common date formats
  
- [ ] **Day 3**: Performance optimization
  - Profile slow queries
  - Add caching if needed (via state management)
  
- [ ] **Day 4-5**: Documentation & release
  - Complete documentation
  - Update CHANGELOG.md
  - Version bump to 2.3.0
  - Create git tag
  - Announce release

### Success Criteria
✅ Analytics provide actionable insights  
✅ Health monitoring identifies real issues  
✅ NLP parsing 90%+ accurate  
✅ Server handles 50+ tools without degradation  
✅ All documentation complete

---

## Development Workflow

### For Each Tool

1. **Design**
   - Define input parameters
   - Define output format
   - Identify Things API calls needed
   - Determine URL scheme structure (if write operation)

2. **Implement**
   ```python
   @mcp.tool(annotations=READ_ONLY_ANNOTATIONS)  # or MODIFY_ANNOTATIONS
   async def tool_name(
       param1: str,
       param2: Optional[int] = None,
       ctx: Optional[Context] = None
   ) -> str:
       """Clear docstring explaining what tool does."""
       try:
           # Validate inputs
           # Query Things API or build URL scheme
           # Format output
           # Return result
       except Exception as e:
           return handle_mcp_error("tool_name", e)
   ```

3. **Test**
   - Manual testing with real Things database
   - Unit tests for logic
   - Integration tests for workflows
   - Performance measurement

4. **Document**
   - Update README tool inventory
   - Add examples
   - Update AGENTS.md with changes

### Code Quality Standards

```bash
# Before committing
uv tool run ruff check .                    # No warnings
uv tool run ruff format .                   # Format code
python3 -m py_compile src/things_mcp/*.py   # Syntax check

# Run tests (when available)
pytest tests/

# Check performance
# Middleware automatically logs timing
```

---

## File Organization

```
src/things_mcp/
  fast_server.py          # Main server (will grow to ~2500 lines)
  handlers.py             # URL scheme, AppleScript
  formatters.py           # Output formatting
  cache.py                # Cache management
  utils.py                # Validation, helpers
  
  # NEW files to add:
  analytics.py            # Analytics calculations (Phase 3)
  template_manager.py     # Template operations (Phase 2)
  date_parser.py          # Natural language parsing (Phase 3)

openspec/changes/feature-expansion-2025/
  proposal.md             # Strategic overview
  tasks.md                # Detailed task breakdown
  design.md               # Technical design
  README.md               # This file
```

---

## Dependencies to Add

### Phase 2 (v2.2.0)
No new dependencies (uses FastMCP state management)

### Phase 3 (v2.3.0)
```toml
# Add to pyproject.toml
[project]
dependencies = [
    # ... existing ...
    "dateparser>=1.2.0",  # Natural language date parsing
]
```

---

## Testing Strategy

### Manual Testing Checklist (Per Phase)

#### Phase 1
- [ ] Create todo with checklist, fetch items, complete one
- [ ] Create project with headings, move todos under headings
- [ ] Test each new filter parameter combination
- [ ] Query overdue items, schedule some, verify changes

#### Phase 2
- [ ] Bulk complete 20 todos via elicitation
- [ ] Save project as template, create new project from it
- [ ] Run smart scheduling assistant with unscheduled items
- [ ] Test template persistence (restart server)

#### Phase 3
- [ ] Generate productivity stats for week/month
- [ ] Identify stalled projects, verify accuracy
- [ ] Parse various natural language dates
- [ ] Verify analytics performance acceptable

### Automated Testing (Future)
```python
# tests/test_checklists.py
def test_get_checklist_items():
    # Mock things.checklist_items
    result = get_checklist_items("test_uuid")
    assert "Checklist for" in result

# tests/test_bulk_operations.py
async def test_bulk_complete_workflow():
    # Mock elicitation
    # Verify URL scheme construction
    # Assert cache cleared
```

---

## Performance Monitoring

### Using Existing Middleware
```python
# DetailedTimingMiddleware already logs all operation timings
# Watch logs for slow operations

# Example log output:
# INFO: get-inbox completed in 87ms
# INFO: get-productivity-stats completed in 423ms  # Optimize if > 500ms
# INFO: bulk-complete-todos completed in 1843ms   # OK for bulk ops
```

### Optimization Triggers
- Analytics > 500ms → Add caching
- Simple queries > 200ms → Review Things API usage
- Bulk ops > 2s → Reduce batch size or optimize URL construction

---

## Release Process

### For Each Phase Release

1. **Pre-release checks**
   ```bash
   # Code quality
   uv tool run ruff check .
   uv tool run ruff format .
   
   # Manual testing
   # Run through manual test checklist
   
   # Performance check
   # Review middleware logs
   ```

2. **Documentation**
   - Update README.md tool inventory
   - Update AGENTS.md with changes
   - Update CHANGELOG.md with version entry
   - Review all docstrings

3. **Version bump**
   ```bash
   # Edit pyproject.toml
   version = "2.1.0"  # or 2.2.0, 2.3.0
   
   # Edit smithery.yaml
   version: "2.1.0"
   ```

4. **Git operations**
   ```bash
   git add .
   git commit -m "feat: Phase 1 - Critical Gaps (v2.1.0)"
   git tag v2.1.0
   git push origin source
   git push origin v2.1.0
   ```

5. **Announcement** (optional)
   - Update README with release highlights
   - Share on relevant platforms

---

## Troubleshooting

### Common Issues

#### Tool Not Found
**Problem**: MCP client doesn't see new tool  
**Solution**: Check TOOL_ANNOTATIONS dict, restart server

#### URL Scheme Not Working
**Problem**: Things doesn't respond to URL scheme  
**Solution**: Check URL encoding, validate UUID exists, check Things running

#### State Not Persisting
**Problem**: Templates disappear after restart  
**Solution**: Verify state management configuration, check file permissions

#### Performance Degradation
**Problem**: Response times increasing  
**Solution**: Review middleware logs, profile slow queries, add caching

---

## Success Metrics

### Quantitative
- **Code Quality**: 0 ruff warnings
- **Performance**: 
  - Simple queries < 100ms (p95)
  - Complex queries < 500ms (p95)
  - Bulk operations < 2s
- **Coverage**: 30-34 new tools (21 → 51-55 total)
- **Reliability**: No regression in existing tools

### Qualitative
- **User Feedback**: Positive reception for interactive workflows
- **Documentation**: All tools documented with examples
- **Maintainability**: Code follows established patterns
- **Showcase**: FastMCP features (elicitation, state) well demonstrated

---

## Next Steps After Phase 3

### Potential Future Enhancements
1. **Caching Layer**: Redis or file-based cache for analytics
2. **Webhooks**: Real-time updates via Things Cloud
3. **AI Integration**: LLM-powered task suggestions
4. **Collaboration**: Share templates, export data
5. **Mobile Shortcuts**: iOS Shortcuts integration

### Maintenance Plan
- Monitor performance metrics
- Gather user feedback
- Address bugs promptly
- Consider quarterly feature releases

---

## Questions or Issues?

1. Review design.md for technical details
2. Check tasks.md for specific implementation steps
3. Refer to proposal.md for strategic context
4. See AGENTS.md for historical decisions
5. Consult FastMCP docs via Context7

---

## Appendix: Key Resources

### Documentation
- Things API: https://github.com/thingsapi/things.py
- Things URL Scheme: https://culturedcode.com/things/support/articles/2803573/
- FastMCP Docs: Via Context7 (/jlowin/fastmcp)
- Things 3 Features: https://culturedcode.com/things/features/

### Code References
- Current Implementation: `src/things_mcp/fast_server.py`
- Middleware Examples: Lines 295-300 in fast_server.py
- Elicitation Example: `add-todo-interactive` tool (lines 1080-1180)

### Tools
- Linting: `uv tool run ruff check .`
- Formatting: `uv tool run ruff format .`
- Type Checking: Pyright (configured in pyproject.toml)
- Testing: pytest (to be set up)
