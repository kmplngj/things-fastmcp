# Feature Expansion 2025 - Proposal

## Summary
Expand things-fastmcp server to expose missing Things API capabilities and add intelligent automation features leveraging FastMCP's elicitation and state management capabilities.

## Context

### Current State (v2.0.0)
- 21 MCP tools covering basic CRUD operations
- FastMCP middleware (timing, error handling) implemented
- One interactive tool (add-todo-interactive)
- ~60% coverage of Things API capabilities

### Gap Analysis
After analyzing `thingsapi/things.py` API and Things 3 features, we identified critical gaps:

1. **Checklists**: Completely missing despite being major Things 3 feature
2. **Headings**: Treated as generic tasks, not as organizational tool
3. **Advanced Filters**: API supports type/status/last/deadline filters not exposed
4. **Bulk Operations**: No way to act on multiple items at once
5. **Templates**: Users need this, Things doesn't provide it
6. **Analytics**: Database contains rich data not surfaced

## Motivation

### User Pain Points
Based on Things 3 feature emphasis and common automation needs:
- "I want to manage my grocery checklist via AI assistant"
- "Schedule my 20 unscheduled tasks for next week"
- "Create a new project with standard structure"
- "Show me all overdue items across all projects"
- "Which projects have stalled?"

### Technical Drivers
- Things API provides capabilities we're not exposing
- FastMCP v2.10+ elicitation enables safe bulk operations
- FastMCP v2.11+ state management enables features Things lacks
- Current middleware provides performance insights for optimization

## Goals

### Primary
1. **Close capability gaps**: Expose all major Things API features
2. **Enable bulk workflows**: Safe multi-item operations via elicitation
3. **Add intelligence**: Analytics, templates, smart scheduling

### Secondary
1. **Showcase FastMCP features**: Demonstrate elicitation, state management
2. **Maintain quality**: All features follow existing patterns
3. **Performance**: Keep response times under 200ms (middleware monitors)

## Non-Goals
- Replacing Things 3 app
- Implementing features Things API doesn't support (recurring tasks, collaboration)
- Real-time sync (Things Cloud handles this)
- Database writes (URL scheme only, maintain read-only DB pattern)

## Proposed Solution

### Three-Phase Rollout

#### Phase 1: Critical Gaps (v2.1.0)
**Timeline**: 1-2 weeks  
**Goal**: Fill missing basic functionality

Core additions:
1. Checklist operations (4 tools)
2. Heading management (3 tools)
3. Enhanced filters (parameter additions to 11 existing tools)
4. Deadline/overdue tools (3 tools)

**Why first**: These are missing Things 3 features users expect. Low-hanging fruit.

#### Phase 2: Interactive Workflows (v2.2.0)
**Timeline**: 2-3 weeks  
**Goal**: Leverage FastMCP elicitation for safe automation

Additions:
1. Bulk complete/schedule/tag operations (3 interactive tools)
2. Smart scheduling assistant (1 comprehensive tool)
3. Project template system (2 tools + state management)

**Why second**: Builds on Phase 1 foundation. Showcases FastMCP's unique capabilities.

#### Phase 3: Intelligence Layer (v2.3.0)
**Timeline**: 2-3 weeks  
**Goal**: Add analytics and power user features

Additions:
1. Productivity analytics (4 tools)
2. Project health monitoring (2 tools)
3. Tag relationship analysis (2 tools)
4. Natural language scheduling (1 tool)

**Why last**: Requires solid foundation. Less critical but high value for power users.

## Impact Assessment

### Breaking Changes
**None.** All changes are additive:
- New tools
- Optional parameters to existing tools
- State management is isolated per-user

### Performance Impact
**Minimal:**
- Checklist/heading queries same pattern as existing
- Bulk operations use URL scheme (one call)
- Analytics computed on-demand, not cached (first iteration)
- Middleware already monitoring timing

### Maintenance Impact
**Moderate increase:**
- ~25-30 new tools (21 → 46-51 total)
- State management needs documentation
- Interactive tools require more testing
- Analytics may need optimization over time

### User Migration
**Seamless:**
- All existing tools unchanged
- New tools opt-in
- No config changes required
- Backward compatible

## Success Metrics

### Phase 1
- All Things API core functions exposed
- Zero ruff warnings
- All tests pass
- Response times < 200ms (p95)

### Phase 2
- 3+ interactive tools with elicitation
- State management working reliably
- User feedback positive on bulk operations

### Phase 3
- Analytics tools provide actionable insights
- Natural language parsing 90%+ accuracy
- Server handles 50+ tools without performance degradation

## Alternatives Considered

### Alternative 1: Big Bang Release
**Rejected:** Too risky, harder to test, delays value delivery

### Alternative 2: User-Driven (wait for requests)
**Rejected:** Gap analysis shows clear missing features users expect

### Alternative 3: Fork for Power Users
**Rejected:** Fragments ecosystem, harder to maintain

## Open Questions

1. **State storage**: Use file-based or in-memory for templates?
   - **Recommendation**: JSON files in `~/.things-fastmcp/templates/` for persistence
   
2. **Analytics caching**: Cache results or compute on-demand?
   - **Recommendation**: Start with on-demand, add caching if slow
   
3. **Natural language parser**: Build custom or use library?
   - **Recommendation**: Use `dateparser` library (Python), proven solution

4. **Bulk operation limits**: Cap at 50 items? 100?
   - **Recommendation**: 100 items max, warn at 50 via ctx.warning()

## References
- Things API: https://github.com/thingsapi/things.py
- Things 3 Features: https://culturedcode.com/things/features/
- FastMCP Docs: /jlowin/fastmcp (via Context7)
- Current Implementation: `src/things_mcp/fast_server.py`
