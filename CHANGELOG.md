# Changelog

All notable changes to Things 3 Enhanced MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`move-item-to-project`** - Move todos to projects/areas, optionally under a specific heading
  - Move todos between projects
  - Move projects to areas
  - Place items directly under headings in destination project
  - Supports both simple moves and targeted placement

## [2.1.0] - 2025-11-01

### Added - Phase 1: Critical Gaps

#### Checklist Operations (4 new tools)
- **`get-checklist-items`** - Retrieve all checklist items for a todo with completion status
- **`add-checklist-item`** - Add new checklist items (supports multiple items via newlines)
- **`update-checklist-item`** - Replace entire checklist (Things URL scheme limitation)
- **`get-todos-with-checklists`** - Find all todos containing checklists with progress tracking

#### Heading Management (3 new tools)
- **`add-heading`** - Add organizational headings to projects with optional positioning
- **`get-project-structure`** - View hierarchical project structure with headings and grouped todos
- **`move-todo-under-heading`** - Reorganize todos by moving them under specific headings

#### Deadline Management (3 new tools)
- **`get-overdue-items`** - Find incomplete items with past deadlines (shows days overdue with ⚠️ badges)
- **`get-items-due-soon`** - Get items with deadlines in next N days (color-coded urgency: 🔴🟠🟡)
- **`set-deadline`** - Set or update deadline with natural language support ('today', 'tomorrow', ISO dates, 'none')

#### Enhanced Filtering
- Added `type_filter` parameter to search tools (filter by 'to-do', 'project', 'heading', 'area')
- Added `status_filter` parameter to search tools (filter by 'incomplete', 'completed', 'canceled')
- Added `deadline_filter` parameter to search tools (filter by 'overdue', 'today', 'upcoming', 'none')
- Enhanced 4 existing tools: `search-todos`, `get-tagged-items`, `get-recent`, `get-inbox`

#### Smart Counting (5 new helper tools)
- **`count-items`** - Get counts for all main areas (lightweight alternative to full queries)
- **`count-search`** - Count search results before fetching full data
- **`count-tagged-items`** - Count items with specific tag
- **`count-project-items`** - Count items in project
- **`count-advanced`** - Count advanced search results

### Changed

- **FastMCP Dependency** - Added `fastmcp>=2.9.0` for middleware support
- **FastMCP 2.x API** - Upgraded from `mcp.server.fastmcp` to `fastmcp` import (2.x API)
- **Middleware Enabled** - Added DetailedTimingMiddleware and ErrorHandlingMiddleware
  - Per-operation timing metrics for all 31 tools
  - Consistent error handling with tracebacks
  - Performance monitoring via `fastmcp.timing.detailed` logger
- **Context Management** - Added limit and sort_by parameters to 11 query tools
- **Tool Count** - Increased from 21 to 31 tools (48% increase)

### Fixed

- Removed deprecated host/port from FastMCP constructor (now passed to run() method)
- Fixed bare `except` clauses to `except Exception` for proper error handling
- Proper cache invalidation using `invalidate_caches_for()` for deadline updates

### Technical Details

- File size: 2619 lines (from 1533 baseline, +1086 lines, ~71% increase)
- All changes compile successfully with zero ruff warnings
- Server starts successfully with FastMCP 2.13.0.2 banner
- Follows existing patterns: error handling, cache invalidation, URL scheme usage
- Comprehensive docstrings with examples for all new tools

## [2.0.0] - 2025-10-16

### BREAKING CHANGES

- **Removed legacy MCP implementation** - Consolidated to FastMCP-only implementation
  - Deleted `/things_server.py` - Legacy entry point
  - Deleted `/src/things_mcp/things_server.py` - Legacy MCP server
  - Deleted `/src/things_mcp/simple_server.py` - Simple server variant
  - Deleted `/src/things_mcp/simple_url_scheme.py` - Legacy URL scheme
  - Deleted `/src/things_mcp/mcp_tools.py` - Legacy tool registration

### Migration Guide

If upgrading from 1.x:

1. **Update MCP client configuration:**
   - Old: `"command": "things_server.py"`
   - New: `"command": "things_fast_server.py"`

2. **Update any scripts or automation:**
   - Old: `mcp dev things_server.py`
   - New: `mcp dev things_fast_server.py`

3. **No tool changes required** - All 19 MCP tools remain with identical signatures

### Benefits of 2.0

- ✅ **Simpler codebase** - Removed ~714 lines of duplicate code
- ✅ **Better reliability** - All users now get circuit breaker, caching, and retry logic automatically
- ✅ **Easier maintenance** - Single implementation to test and update
- ✅ **Clearer documentation** - No more confusion about which implementation to use

### Changed

- Updated project description to emphasize production-ready nature
- Bumped version to 2.0.0 across all configuration files
- Streamlined documentation with consolidated migration guide

## [1.0.0] - 2025-05-30

### Added
- 🚀 **FastMCP Implementation**: Complete rewrite using FastMCP pattern for better maintainability
- 🔄 **Reliability Features**:
  - Circuit breaker pattern to prevent cascading failures
  - Exponential backoff retry logic for transient failures
  - Dead letter queue for failed operations
- ⚡ **Performance Optimizations**:
  - Intelligent caching system with TTL management
  - Rate limiting to prevent overwhelming Things app
  - Automatic cache invalidation on data modifications
- 🍎 **AppleScript Bridge**: Fallback mechanism when URL schemes fail
- 📊 **Enhanced Monitoring**:
  - Structured JSON logging
  - Performance metrics and statistics
  - Comprehensive error tracking
  - Debug-friendly output
- 🛡️ **Error Handling**: Comprehensive exception management and recovery
- 🧪 **Test Suite**: Extensive tests for reliability
- 📦 **Smithery Support**: Full configuration for Smithery registry deployment
- 📝 **Documentation**: Enhanced README with detailed setup and troubleshooting guides

### Changed
- Rebranded to "Things 3 Enhanced MCP" for clear differentiation
- Updated package name to `things3-enhanced-mcp`
- Improved configuration token handling
- Enhanced URL scheme operations with better error recovery

### Fixed
- Token configuration import issues
- URL scheme reliability problems
- Various edge cases in task/project operations

### Attribution
Based on the original [things-mcp](https://github.com/hald/things-mcp) by Harald Lindstrøm

[1.0.0]: https://github.com/CaseyRo/things-fastmcp/releases/tag/v1.0.0
