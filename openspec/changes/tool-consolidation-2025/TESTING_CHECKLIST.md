# Testing Checklist: Tool Consolidation v3.0.0

**Date**: 2025-11-02  
**Version**: v3.0.0  
**Tester**: _____________  
**MCP Client**: _____________  
**Status**: ⏳ Not Started

---

## Pre-Testing Setup

### Environment Verification
- [ ] Fast server compiles without errors
- [ ] MCP client configured correctly (Claude Desktop/VS Code/Cursor/Windsurf)
- [ ] Things 3 database accessible
- [ ] Test data available (projects, todos, tags, areas)

### Expected Tool Count
- [ ] Before enabling advanced features: **18 tools visible**
- [ ] After enabling "analytics": **27 tools visible** (+9)
- [ ] After enabling "checklists": **31 tools visible** (+4)
- [ ] After enabling "structure": **33 tools visible** (+2)
- [ ] After enabling "all": **33 tools visible**

---

## Phase 1: Composite Tool Testing

### Tool 1: `list-items` (7 list types)

#### Test 1.1: Inbox
- [ ] Call: `list_items(list_type="inbox")`
- [ ] Returns inbox items
- [ ] Shows correct count
- [ ] Formatted correctly
- [ ] **Expected**: List of inbox todos/projects

#### Test 1.2: Today
- [ ] Call: `list_items(list_type="today")`
- [ ] Returns today's items
- [ ] Shows scheduled items only
- [ ] **Expected**: Today's scheduled tasks

#### Test 1.3: Upcoming
- [ ] Call: `list_items(list_type="upcoming")`
- [ ] Returns upcoming items
- [ ] Shows future scheduled items
- [ ] **Expected**: Future scheduled tasks

#### Test 1.4: Anytime
- [ ] Call: `list_items(list_type="anytime")`
- [ ] Returns anytime items
- [ ] Shows items in Anytime list
- [ ] **Expected**: Anytime todos

#### Test 1.5: Someday
- [ ] Call: `list_items(list_type="someday")`
- [ ] Returns someday items
- [ ] Shows items in Someday list
- [ ] **Expected**: Someday todos/projects

#### Test 1.6: Logbook
- [ ] Call: `list_items(list_type="logbook")`
- [ ] Returns completed items
- [ ] Shows completion dates
- [ ] **Expected**: Completed tasks

#### Test 1.7: Trash
- [ ] Call: `list_items(list_type="trash")`
- [ ] Returns trashed items
- [ ] Shows trashed status
- [ ] **Expected**: Trashed items

#### Test 1.8: Filters
- [ ] Call: `list_items("inbox", type_filter="to-do")`
- [ ] Filters by type correctly
- [ ] **Expected**: Only todos, no projects

- [ ] Call: `list_items("inbox", deadline_filter="overdue")`
- [ ] Filters by deadline correctly
- [ ] **Expected**: Only overdue items

#### Test 1.9: Sorting & Limiting
- [ ] Call: `list_items("inbox", sort_by="title", limit=10)`
- [ ] Sorts alphabetically
- [ ] Limits to 10 items
- [ ] Shows "from X total" in metadata
- [ ] **Expected**: 10 items, sorted by title

#### Test 1.10: Context Warnings
- [ ] Create >20 items in inbox
- [ ] Call: `list_items("inbox")` without limit
- [ ] Context warning appears
- [ ] Recommends using limit parameter
- [ ] **Expected**: Warning message about large result set

#### Test 1.11: Invalid List Type
- [ ] Call: `list_items("invalid_type")`
- [ ] Returns error message
- [ ] Lists valid list types
- [ ] **Expected**: Error with valid options

**list-items Status**: ⬜ Not Tested | 🟡 Partial | ✅ Complete

---

### Tool 2: `count` (5 count types)

#### Test 2.1: Lists Count
- [ ] Call: `count(count_type="lists")`
- [ ] Returns counts for all 7 lists
- [ ] Shows: inbox, today, upcoming, anytime, someday, logbook, trash
- [ ] **Expected**: JSON with 7 counts

#### Test 2.2: Search Count
- [ ] Call: `count(count_type="search", query="meeting")`
- [ ] Returns count of search results
- [ ] Shows recommendation if count >20
- [ ] **Expected**: Count + optional recommendation

#### Test 2.3: Tag Count
- [ ] Call: `count(count_type="tag", tag="work")`
- [ ] Returns count of items with tag
- [ ] Shows recommendation if count >20
- [ ] **Expected**: Count + optional recommendation

#### Test 2.4: Project Count
- [ ] Call: `count(count_type="project", project_uuid="<valid_uuid>")`
- [ ] Returns count of items in project
- [ ] Shows recommendation if count >20
- [ ] **Expected**: Count + optional recommendation

#### Test 2.5: Advanced Count
- [ ] Call: `count(count_type="advanced", title_filter="report", status_filter="incomplete")`
- [ ] Returns count matching filters
- [ ] Applies all filters correctly
- [ ] **Expected**: Filtered count

#### Test 2.6: Invalid Count Type
- [ ] Call: `count(count_type="invalid")`
- [ ] Returns error message
- [ ] Lists valid count types
- [ ] **Expected**: Error with valid options

#### Test 2.7: Missing Required Parameters
- [ ] Call: `count(count_type="search")` without query
- [ ] Returns error about missing query
- [ ] **Expected**: Error message

**count Status**: ⬜ Not Tested | 🟡 Partial | ✅ Complete

---

### Tool 3: `search` (full-text + filters)

#### Test 3.1: Full-Text Search
- [ ] Call: `search(query="meeting")`
- [ ] Returns search results
- [ ] Uses Things.search() API
- [ ] Shows default 20 results
- [ ] **Expected**: List of matching todos

#### Test 3.2: Title Filter Only
- [ ] Call: `search(title_filter="project")`
- [ ] Returns todos with "project" in title
- [ ] No full-text search
- [ ] **Expected**: Filtered by title

#### Test 3.3: Notes Filter Only
- [ ] Call: `search(notes_filter="important")`
- [ ] Returns todos with "important" in notes
- [ ] **Expected**: Filtered by notes

#### Test 3.4: Combined Full-Text + Filters
- [ ] Call: `search(query="meeting", status_filter="incomplete")`
- [ ] First does full-text search
- [ ] Then applies status filter
- [ ] **Expected**: Incomplete todos matching "meeting"

#### Test 3.5: Multiple Filters
- [ ] Call: `search(type_filter="to-do", status_filter="incomplete", deadline_filter="overdue")`
- [ ] Applies all filters
- [ ] Returns overdue incomplete todos only
- [ ] **Expected**: Filtered results

#### Test 3.6: Pagination
- [ ] Call: `search(query="test", limit=10, offset=0)`
- [ ] Returns first 10 results
- [ ] Shows "Showing 1-10 of X"

- [ ] Call: `search(query="test", limit=10, offset=10)`
- [ ] Returns next 10 results
- [ ] Shows "Showing 11-20 of X"
- [ ] **Expected**: Pagination working

#### Test 3.7: Sorting
- [ ] Call: `search(query="test", sort_by="title")`
- [ ] Results sorted alphabetically by title
- [ ] **Expected**: Alphabetical order

#### Test 3.8: Context Warnings
- [ ] Search with >20 results
- [ ] No limit parameter
- [ ] Context warning appears
- [ ] **Expected**: Warning about large result set

**search Status**: ⬜ Not Tested | 🟡 Partial | ✅ Complete

---

### Tool 4: `deadline-items` (overdue + due-soon)

#### Test 4.1: Overdue Items
- [ ] Create overdue todo (deadline in past)
- [ ] Call: `deadline_items(filter_type="overdue")`
- [ ] Returns overdue todos
- [ ] Shows days overdue with ⚠️ badge
- [ ] Sorted by deadline (oldest first)
- [ ] **Expected**: List with urgency badges

#### Test 4.2: Due Soon Items (Default 7 days)
- [ ] Create todo due in 3 days
- [ ] Call: `deadline_items(filter_type="due-soon")`
- [ ] Returns todos due in next 7 days
- [ ] Shows urgency badges: 🔴 (today), 🟠 (tomorrow), 🟡 (future)
- [ ] **Expected**: List with days_until

#### Test 4.3: Due Soon with Custom Days
- [ ] Call: `deadline_items(filter_type="due-soon", days=14)`
- [ ] Returns todos due in next 14 days
- [ ] **Expected**: Extended lookahead

#### Test 4.4: Sorting
- [ ] Call: `deadline_items("overdue", sort_by="title")`
- [ ] Results sorted by title instead of deadline
- [ ] **Expected**: Alphabetical order

#### Test 4.5: Limiting
- [ ] Call: `deadline_items("overdue", limit=5)`
- [ ] Returns only 5 results
- [ ] Shows "from X total" if more available
- [ ] **Expected**: Limited results

#### Test 4.6: No Deadlines Scenario
- [ ] Remove all deadlines from todos
- [ ] Call: `deadline_items("overdue")`
- [ ] Returns empty result with message
- [ ] **Expected**: "No overdue items"

**deadline-items Status**: ⬜ Not Tested | 🟡 Partial | ✅ Complete

---

### Tool 5: `manage-heading` (add + move)

#### Test 5.1: Add Heading (No Positioning)
- [ ] Call: `manage_heading(action="add", project_uuid="<uuid>", heading_title="Test Heading")`
- [ ] Heading created in project
- [ ] Appears at bottom of project
- [ ] **Expected**: Success message + heading UUID

#### Test 5.2: Add Heading (With Positioning)
- [ ] Get UUID of existing item
- [ ] Call: `manage_heading(action="add", project_uuid="<uuid>", heading_title="Test", after_uuid="<item_uuid>")`
- [ ] Heading appears after specified item
- [ ] **Expected**: Positioned correctly

#### Test 5.3: Move Todo Under Heading
- [ ] Create heading in project
- [ ] Create todo in same project
- [ ] Call: `manage_heading(action="move", todo_uuid="<todo>", heading_uuid="<heading>", project_uuid="<project>")`
- [ ] Todo moves under heading
- [ ] **Expected**: Todo grouped under heading

#### Test 5.4: Move Todo - Different Projects (Should Fail)
- [ ] Create heading in Project A
- [ ] Create todo in Project B
- [ ] Call: `manage_heading(action="move", todo_uuid="<todo>", heading_uuid="<heading>", project_uuid="<projectA>")`
- [ ] Returns error
- [ ] **Expected**: Error - items must be in same project

#### Test 5.5: Invalid Action
- [ ] Call: `manage_heading(action="invalid", project_uuid="<uuid>")`
- [ ] Returns error
- [ ] Lists valid actions: "add", "move"
- [ ] **Expected**: Error message

#### Test 5.6: Missing Required Parameters
- [ ] Call: `manage_heading(action="add")` without project_uuid
- [ ] Returns error about missing parameter
- [ ] **Expected**: Parameter error

**manage-heading Status**: ⬜ Not Tested | 🟡 Partial | ✅ Complete

---

## Phase 2: Dynamic Tool Management Testing

### Tool 6: `enable-advanced-features`

#### Test 6.1: Enable Analytics
- [ ] Call: `enable_advanced_features("analytics")`
- [ ] Returns list of 9 analytics tools
- [ ] Tools appear in Claude Desktop tool list
- [ ] Can call analytics tools (e.g., get-productivity-stats)
- [ ] **Expected**: 9 tools enabled + listed

#### Test 6.2: Enable Checklists
- [ ] Call: `enable_advanced_features("checklists")`
- [ ] Returns list of 4 checklist tools
- [ ] Tools appear in tool list
- [ ] Can call checklist tools
- [ ] **Expected**: 4 tools enabled + listed

#### Test 6.3: Enable Structure
- [ ] Call: `enable_advanced_features("structure")`
- [ ] Returns list of 2 structure tools
- [ ] Tools appear in tool list
- [ ] **Expected**: 2 tools enabled + listed

#### Test 6.4: Enable All
- [ ] Call: `enable_advanced_features("all")`
- [ ] Returns lists for all 3 categories
- [ ] All 15 advanced tools appear
- [ ] Can call any advanced tool
- [ ] **Expected**: All categories enabled

#### Test 6.5: Already Enabled
- [ ] Enable analytics
- [ ] Call `enable_advanced_features("analytics")` again
- [ ] Returns message that it's already enabled
- [ ] **Expected**: No duplicate enabling

#### Test 6.6: Invalid Category
- [ ] Call: `enable_advanced_features("invalid")`
- [ ] Returns error
- [ ] Lists valid categories
- [ ] **Expected**: Error with valid options

#### Test 6.7: MCP tools/list_changed Notification
- [ ] Watch Claude Desktop logs
- [ ] Call `enable_advanced_features("analytics")`
- [ ] Verify tools/list_changed notification sent
- [ ] Tool list refreshes in UI
- [ ] **Expected**: UI updates automatically

**enable-advanced-features Status**: ⬜ Not Tested | 🟡 Partial | ✅ Complete

---

### Tool 7: `disable-advanced-features`

#### Test 7.1: Disable Analytics
- [ ] Enable analytics first
- [ ] Call: `disable_advanced_features("analytics")`
- [ ] Returns count of disabled tools (9)
- [ ] Tools disappear from tool list
- [ ] Cannot call analytics tools anymore
- [ ] **Expected**: 9 tools disabled

#### Test 7.2: Disable Checklists
- [ ] Enable checklists first
- [ ] Call: `disable_advanced_features("checklists")`
- [ ] Returns count (4)
- [ ] Tools disappear
- [ ] **Expected**: 4 tools disabled

#### Test 7.3: Disable All
- [ ] Enable all categories
- [ ] Call: `disable_advanced_features("all")`
- [ ] Returns total count (15)
- [ ] All advanced tools disappear
- [ ] Back to 18 core tools
- [ ] **Expected**: All categories disabled

#### Test 7.4: Already Disabled
- [ ] Disable analytics
- [ ] Call `disable_advanced_features("analytics")` again
- [ ] Returns message that it's already disabled
- [ ] **Expected**: No error, informative message

#### Test 7.5: tools/list_changed Notification
- [ ] Watch logs
- [ ] Disable category
- [ ] Verify notification sent
- [ ] UI updates
- [ ] **Expected**: Automatic UI refresh

**disable-advanced-features Status**: ⬜ Not Tested | 🟡 Partial | ✅ Complete

---

### Tool 8: `get-tool-categories`

#### Test 8.1: All Disabled (Initial State)
- [ ] Call: `get_tool_categories()`
- [ ] Shows all 3 categories with ⏸️ disabled icons
- [ ] Shows tool counts: Analytics (9), Checklists (4), Structure (2)
- [ ] **Expected**: All disabled status

#### Test 8.2: Some Enabled
- [ ] Enable analytics
- [ ] Call: `get_tool_categories()`
- [ ] Analytics shows ✅ ENABLED
- [ ] Others show ⏸️ DISABLED
- [ ] **Expected**: Mixed status

#### Test 8.3: All Enabled
- [ ] Enable all categories
- [ ] Call: `get_tool_categories()`
- [ ] All show ✅ ENABLED
- [ ] **Expected**: All enabled status

#### Test 8.4: Usage Instructions
- [ ] Check output includes usage instructions
- [ ] Shows how to enable/disable
- [ ] **Expected**: Clear instructions

**get-tool-categories Status**: ⬜ Not Tested | 🟡 Partial | ✅ Complete

---

## Phase 3: Integration Testing

### Workflow Test 1: Progressive Disclosure
1. [ ] Start with default 18 core tools
2. [ ] Need analytics → enable_advanced_features("analytics")
3. [ ] Use get-productivity-stats
4. [ ] Use get-project-velocity
5. [ ] Done with analytics → disable_advanced_features("analytics")
6. [ ] Back to 18 core tools
7. [ ] **Expected**: Smooth enable/disable cycle

### Workflow Test 2: Multiple Categories
1. [ ] Enable analytics
2. [ ] Enable checklists (without disabling analytics)
3. [ ] Both categories visible (27 tools total)
4. [ ] Disable analytics (checklists still enabled)
5. [ ] Only checklists visible (22 tools)
6. [ ] **Expected**: Independent category management

### Workflow Test 3: Complex Query
1. [ ] Count items: `count("lists")`
2. [ ] See >20 in inbox
3. [ ] List with limit: `list_items("inbox", limit=20)`
4. [ ] Search specific: `search(query="meeting", status_filter="incomplete")`
5. [ ] Check deadlines: `deadline_items("overdue")`
6. [ ] **Expected**: Seamless workflow

### Workflow Test 4: Project Organization
1. [ ] Create project
2. [ ] Add heading: `manage_heading("add", project_uuid="...", heading_title="Phase 1")`
3. [ ] Add todo to project
4. [ ] Move todo under heading: `manage_heading("move", todo_uuid="...", heading_uuid="...", project_uuid="...")`
5. [ ] Verify structure: Enable structure category, call `get-project-structure`
6. [ ] **Expected**: Organized project with heading

---

## Phase 4: Error Handling Testing

### Error Test 1: Invalid Parameters
- [ ] Call with wrong parameter types
- [ ] Call with missing required parameters
- [ ] Call with invalid enum values
- [ ] **Expected**: Clear error messages

### Error Test 2: Non-Existent UUIDs
- [ ] Call tools with fake UUIDs
- [ ] Should return "not found" errors
- [ ] **Expected**: Graceful error handling

### Error Test 3: Empty Results
- [ ] Search for non-existent query
- [ ] Filter to empty set
- [ ] **Expected**: "No items found" message

### Error Test 4: Large Result Sets
- [ ] Query without limit on large dataset
- [ ] Context warning should appear
- [ ] **Expected**: Warning but still returns results

---

## Phase 5: Performance Testing

### Performance Test 1: Response Times
- [ ] list-items: < 200ms
- [ ] count: < 100ms
- [ ] search (no query): < 300ms
- [ ] search (with query): < 500ms
- [ ] deadline-items: < 200ms
- [ ] manage-heading: < 200ms
- [ ] enable/disable: < 100ms

### Performance Test 2: Large Datasets
- [ ] Test with 100+ todos in inbox
- [ ] Test with 50+ projects
- [ ] Test with 100+ logbook items
- [ ] **Expected**: Reasonable performance, warnings shown

### Performance Test 3: Pagination Performance
- [ ] Test offset=0, limit=20
- [ ] Test offset=100, limit=20
- [ ] Compare performance
- [ ] **Expected**: Similar times (no full scan)

---

## Phase 6: MCP Client Testing

### Claude Desktop
- [ ] All 8 composite/management tools appear
- [ ] Tool descriptions clear
- [ ] Can call all tools successfully
- [ ] Context warnings displayed
- [ ] Enable/disable updates tool list
- [ ] No errors in Claude logs

### VS Code MCP Extension
- [ ] Tools appear in MCP panel
- [ ] Can invoke tools
- [ ] Results formatted correctly
- [ ] No errors in Output panel

### Cursor
- [ ] Tools available in Copilot++
- [ ] Can use in chat
- [ ] Results integrated correctly

### Windsurf
- [ ] Tools appear in Cascade
- [ ] Can invoke via commands
- [ ] Results displayed properly

---

## Phase 7: Regression Testing

### Verify Unaffected Tools Still Work
- [ ] get-todos
- [ ] get-projects
- [ ] get-areas
- [ ] get-tags
- [ ] add-todo
- [ ] add-project
- [ ] update-todo
- [ ] update-project
- [ ] move-item-to-project
- [ ] show-item
- [ ] get-recent
- [ ] get-tagged-items
- [ ] search-items
- [ ] get-cache-stats

**All core tools still functional**: ⬜ Not Tested | ✅ Verified

---

## Final Verification

### Code Quality
- [ ] Zero compilation errors
- [ ] Zero runtime errors during testing
- [ ] All type hints working
- [ ] No unexpected warnings in logs

### Documentation
- [ ] README.md updated
- [ ] CHANGELOG.md updated
- [ ] Migration guide clear
- [ ] Examples work as documented

### User Experience
- [ ] Tool names intuitive
- [ ] Error messages helpful
- [ ] Warnings actionable
- [ ] Progressive disclosure works well

---

## Bug Report Template

**Bug #**: ___  
**Tool**: _______________  
**Parameters**: _______________  
**Expected**: _______________  
**Actual**: _______________  
**Error Message**: _______________  
**Steps to Reproduce**:
1. 
2. 
3. 

**Logs**: (Attach Claude Desktop logs or MCP client logs)

**Environment**:
- MCP Client: _______________
- Version: _______________
- OS: _______________

---

## Sign-Off

### Testing Complete
- [ ] All composite tools tested
- [ ] All management tools tested
- [ ] Integration workflows tested
- [ ] Error handling verified
- [ ] Performance acceptable
- [ ] All MCP clients verified
- [ ] Regression tests passed
- [ ] Documentation reviewed

### Approval
**Tester Name**: _____________  
**Date**: _____________  
**Status**: ⬜ Failed | ⏸️ Issues Found | ✅ Approved  

**Issues Found**: _______________

**Recommendation**: ⬜ Do Not Release | ⏸️ Fix Issues First | ✅ Ready for Release

---

**Last Updated**: 2025-11-02  
**Version**: v3.0.0 Testing Checklist  
**Status**: Ready for QA
