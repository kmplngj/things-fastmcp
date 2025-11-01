# Phase 2 Implementation Plan: Interactive Workflows (v2.2.0)

## Overview
Phase 2 focuses on building interactive, multi-step workflows using FastMCP's elicitation API. These tools will showcase the power of conversational AI by guiding users through complex operations with previews and confirmations.

## Timeline
**Estimated Duration**: 2-3 weeks  
**Start Date**: November 1, 2025  
**Target Completion**: November 22, 2025

## Goals
1. **Bulk Operations**: Enable safe, efficient batch modifications with preview + confirm pattern
2. **Smart Scheduling**: Provide intelligent scheduling suggestions based on context
3. **Templates**: Allow users to save and reuse complex project structures

## Implementation Order

### Week 1: Bulk Operations (4 tools)
**Focus**: Establish elicitation patterns, preview + confirm workflow

#### Task 2.1.1: bulk-complete-todos (Day 1-2)
**Priority**: HIGH - Demonstrates basic elicitation pattern

**Implementation Steps**:
1. Add elicitation workflow:
   - Step 1: Ask for filter criteria (tag, project, area, or inbox)
   - Step 2: Fetch matching incomplete todos
   - Step 3: Show preview: "Found X todos: [titles...]"
   - Step 4: Confirm: "Complete all X todos? (yes/no)"
   - Step 5: Batch execute via URL scheme
2. Add progress reporting via `ctx.info()`
3. Handle errors gracefully (partial failures)
4. Register in TOOL_ANNOTATIONS with MODIFY_ANNOTATIONS

**Validation**:
- [ ] Elicitation prompts are clear
- [ ] Preview shows accurate count and sample titles
- [ ] Confirmation prevents accidental bulk operations
- [ ] Progress updates work correctly
- [ ] Handles edge cases (no matches, user cancels)

#### Task 2.1.2: bulk-schedule-todos (Day 3-4)
**Priority**: HIGH - Natural language date input

**Implementation Steps**:
1. Add elicitation workflow:
   - Step 1: Ask for source (tag/project/inbox/unscheduled)
   - Step 2: Show unscheduled items
   - Step 3: Ask for target date (today, tomorrow, YYYY-MM-DD, "next week")
   - Step 4: Preview scheduling
   - Step 5: Confirm and batch execute
2. Parse natural date strings (today, tomorrow, next Monday)
3. Use existing `when` parameter logic
4. Add to MODIFY_ANNOTATIONS

**Validation**:
- [ ] Natural language dates parse correctly
- [ ] Unscheduled items filter works
- [ ] Preview shows before/after state
- [ ] Batch scheduling succeeds

#### Task 2.1.3: bulk-tag-todos (Day 5)
**Priority**: MEDIUM - Tag management at scale

**Implementation Steps**:
1. Add elicitation workflow:
   - Step 1: Ask for source criteria
   - Step 2: Show matching todos
   - Step 3: Ask for tag action (add/remove) and tag name
   - Step 4: Preview changes
   - Step 5: Confirm and batch execute
2. Use existing ensure_tags_exist() for new tags
3. Handle tag removal (clear tags, re-add others)
4. Add to MODIFY_ANNOTATIONS

**Validation**:
- [ ] Both add and remove operations work
- [ ] New tags created automatically
- [ ] Existing tags preserved when adding
- [ ] Preview shows tag changes clearly

#### Task 2.1.4: bulk-move-todos (Day 6)
**Priority**: MEDIUM - Reorganization workflow

**Implementation Steps**:
1. Add elicitation workflow:
   - Step 1: Ask for source criteria
   - Step 2: Show matching todos
   - Step 3: List available destination projects/areas
   - Step 4: Ask for destination
   - Step 5: Preview move operation
   - Step 6: Confirm and batch execute
2. Reuse move-item-to-project logic
3. Add batch limit (100 items)
4. Add to MODIFY_ANNOTATIONS

**Validation**:
- [ ] Destinations list is accurate
- [ ] Move preserves other properties
- [ ] Batch limit enforced
- [ ] Error handling for invalid destinations

### Week 2: Smart Scheduling & Templates (6 tools)

#### Task 2.2.1: schedule-assistant (Day 7-9)
**Priority**: MEDIUM - Intelligent workflow

**Implementation Steps**:
1. Design elicitation workflow:
   - Step 1: Fetch all unscheduled items
   - Step 2: Show count, ask "Schedule how many? (all/10/20)"
   - Step 3: For each batch, analyze priority signals
   - Step 4: Suggest scheduling based on analysis
   - Step 5: User can accept/modify/skip
   - Step 6: Execute batch with progress updates
2. Implement priority heuristics:
   - Check deadline (urgent if < 3 days)
   - Check tags (important, urgent, priority)
   - Check project type (work area → today/tomorrow)
   - Suggest: today (urgent), tomorrow (high), this week (normal), someday (low)
3. Add smart suggestions via `ctx.info()`
4. Add to MODIFY_ANNOTATIONS

**Validation**:
- [ ] Priority analysis makes sense
- [ ] Suggestions are helpful
- [ ] User can override easily
- [ ] Handles no unscheduled items
- [ ] Progress reporting works

#### Task 2.3.1-2.3.5: Template System (Day 10-15)
**Priority**: MEDIUM - Power user feature

**Day 10-11: Template Storage Design**
1. Design JSON format:
   ```json
   {
     "name": "Product Launch",
     "description": "Standard product launch workflow",
     "variables": ["product_name", "launch_date", "area_uuid"],
     "project": {
       "title": "Launch {{product_name}}",
       "notes": "Launch by {{launch_date}}",
       "area": "{{area_uuid}}"
     },
     "headings": [
       {
         "title": "Planning",
         "todos": [
           {"title": "Define scope", "tags": ["Planning"]},
           {"title": "Set timeline", "tags": ["Planning"]}
         ]
       }
     ]
   }
   ```
2. Implement state management:
   - Store: `ctx.set_state(f"template_{name}", json.dumps(template))`
   - List: `ctx.list_state_keys(prefix="template_")`
   - Retrieve: `json.loads(ctx.get_state(f"template_{name}"))`
3. Add variable substitution logic

**Day 12-13: save-project-as-template**
1. Implement elicitation workflow:
   - Step 1: Ask for project UUID
   - Step 2: Fetch project with include_items=True
   - Step 3: Extract structure (project → headings → todos)
   - Step 4: Ask which fields to parameterize ({{var}})
   - Step 5: Ask for template name and description
   - Step 6: Save to state
2. Add to MODIFY_ANNOTATIONS

**Day 14: create-from-template**
1. Implement elicitation workflow:
   - Step 1: List available templates
   - Step 2: Ask which template to use
   - Step 3: Ask for variable values (one by one)
   - Step 4: Perform substitution
   - Step 5: Show preview of structure
   - Step 6: Confirm and create via batch URL scheme
2. Add to MODIFY_ANNOTATIONS

**Day 15: list-templates & delete-template**
1. list-templates:
   - Query state for template_* keys
   - Show name, description, variables
   - Add to READ_ONLY_ANNOTATIONS
2. delete-template:
   - Elicit template name
   - Confirm deletion
   - Remove from state
   - Add to MODIFY_ANNOTATIONS

**Validation**:
- [ ] Templates persist across sessions
- [ ] Variable substitution works correctly
- [ ] Complex structures create properly
- [ ] State management doesn't conflict
- [ ] Templates can be exported/imported (JSON)

### Week 3: Integration & Testing

#### Phase 2 Integration Tasks (Day 16-18)
- [ ] Update TOOL_ANNOTATIONS with all 10 new tools
- [ ] Test all interactive workflows end-to-end
- [ ] Update README.md (32 → 42 tools)
- [ ] Update AGENTS.md with Phase 2 summary
- [ ] Create comprehensive CHANGELOG entry for v2.2.0
- [ ] Version bump in pyproject.toml, smithery.yaml, __init__.py
- [ ] Create git tag v2.2.0

#### User Testing (Day 19-21)
- [ ] Test in Claude Desktop
- [ ] Test in VS Code Copilot Chat
- [ ] Document any edge cases
- [ ] Fix any discovered bugs
- [ ] Update documentation based on user feedback

## Technical Patterns

### Elicitation Pattern
```python
async def bulk_operation_tool(ctx: Context) -> str:
    # Step 1: Get criteria
    filter_result = await ctx.elicit("What should I filter by? (tag/project/inbox)")
    
    # Step 2: Fetch and preview
    items = fetch_items(filter_result.data)
    await ctx.info(f"Found {len(items)} items: {[item['title'] for item in items[:5]]}")
    
    # Step 3: Confirm
    confirm = await ctx.elicit("Proceed with operation? (yes/no)")
    if confirm.data.lower() != "yes":
        return "Operation cancelled"
    
    # Step 4: Execute with progress
    for i, item in enumerate(items):
        await ctx.report_progress(i, len(items))
        execute_operation(item)
    
    return f"Successfully processed {len(items)} items"
```

### State Management Pattern
```python
# Save template
template_data = {"name": "...", "project": {...}}
ctx.set_state(f"template_{name}", json.dumps(template_data))

# List templates
keys = ctx.list_state_keys(prefix="template_")
templates = [json.loads(ctx.get_state(key)) for key in keys]

# Retrieve template
template_json = ctx.get_state(f"template_{name}")
template = json.loads(template_json) if template_json else None
```

### Batch URL Scheme Pattern
```python
# Build batch of URL commands
urls = []
for item in items[:100]:  # Limit 100
    url = f"things:///update?id={item['uuid']}&completed=true&auth-token={token}"
    urls.append(url)

# Execute batch
for url in urls:
    execute_url(url)
    invalidate_caches_for(["get-todos"])
```

## Success Metrics

### Quantitative
- [ ] 10 new interactive tools functional
- [ ] All elicitation workflows complete successfully
- [ ] Batch operations handle 100+ items
- [ ] Template system supports 5+ complexity levels
- [ ] Performance: Bulk ops < 2s for 20 items, < 5s for 100 items
- [ ] Zero regressions in existing 32 tools

### Qualitative
- [ ] User feedback: "Workflows feel natural"
- [ ] User feedback: "Previews prevent mistakes"
- [ ] User feedback: "Templates save significant time"
- [ ] User feedback: "Smart scheduling suggestions are helpful"

## Risk Mitigation

### Risk: State management conflicts between users
**Mitigation**: Use user-specific state keys (include user ID if available)

### Risk: Batch operations timeout or partially fail
**Mitigation**: 
- Implement 100-item limit
- Add retry logic for failed items
- Report partial success clearly

### Risk: Elicitation workflows feel clunky
**Mitigation**:
- Keep prompts concise and clear
- Show progress indicators
- Allow cancellation at any step
- Provide helpful defaults

### Risk: Templates too complex to create/use
**Mitigation**:
- Start with simple templates (no nesting)
- Add comprehensive examples
- Guide users through variable selection
- Provide template library in docs

## Next Steps After Phase 2
Upon completion of Phase 2 (v2.2.0), proceed to:
- **Phase 3**: Intelligence Layer (v2.3.0) - Analytics, insights, NLP scheduling
- **Alternative**: User testing period to gather feedback on interactive workflows
- **Alternative**: Focus on documentation and real-world usage examples

## Notes
- Phase 2 prioritizes user experience over feature count
- Elicitation workflows should feel conversational, not scripted
- Preview + Confirm pattern prevents accidental data loss
- Progress reporting keeps users informed during long operations
- State management enables new classes of features (templates, preferences)
