# Phase 3: Intelligence Layer - Detailed Implementation Plan

## Overview
**Version**: v2.3.0  
**Timeline**: 2-3 weeks  
**Goal**: Add analytics and power user features leveraging FastMCP's progress reporting, structured outputs, and data aggregation capabilities  
**Dependencies**: Phase 1 complete, Phase 2 optional (can implement independently)

## Research Findings from FastMCP Best Practices

### 1. Progress Reporting for Analytics
- **Pattern**: Use `ctx.report_progress(progress, total, message)` for long computations
- **When**: Analytics queries that iterate over large datasets (>100 items)
- **Example**: "Analyzed 150/500 todos... Computing completion rates..."
- **Client Support**: Clients can set `progress_handler` to monitor updates

### 2. Structured Outputs for Analytics
- **Pattern**: Return dataclasses or TypedDicts for machine-readable results
- **Benefit**: LLMs can parse structured data reliably + JSON schemas auto-generated
- **Format**: Use `ToolResult` to provide both human-readable summary AND structured data
- **Example**:
  ```python
  @dataclass
  class ProductivityStats:
      completed_count: int
      completion_rate: float
      overdue_count: int
      ...
  
  return ToolResult(
      content=[TextContent(text="📊 Summary: 85% completion rate...")],
      structured_content=asdict(stats)  # For programmatic access
  )
  ```

### 3. Natural Language Date Parsing
- **Library**: Use `dateparser` (proven Python library)
- **Error Handling**: Raise `ToolError` for unparseable dates
- **Ambiguity**: Use `ctx.elicit()` to request clarification
- **Pattern**: 
  ```python
  import dateparser
  parsed = dateparser.parse(date_input, settings={'PREFER_DATES_FROM': 'future'})
  if not parsed:
      raise ToolError(f"Could not parse date: {date_input}")
  ```

### 4. Performance Optimization
- **Caching**: Use existing `@cached` decorator for expensive queries
- **Timeouts**: Set reasonable timeouts (30-60s for analytics)
- **Batch Processing**: Process data in chunks, report progress every 50-100 items
- **Middleware**: DetailedTimingMiddleware already monitors all operations

## Tool Inventory (9-11 New Tools)

### Category 1: Productivity Analytics (4 tools)
1. **get-productivity-stats** - Overall completion metrics
2. **get-project-velocity** - Project completion trends over time
3. **get-time-to-completion** - Average time from creation to completion
4. **get-tag-productivity** - Completion rates by tag

### Category 2: Project Health Monitoring (2 tools)
5. **check-stalled-projects** - Projects with no activity
6. **get-project-health-report** - Comprehensive project status

### Category 3: Tag Intelligence (2 tools)
7. **analyze-tag-relationships** - Co-occurrence patterns
8. **suggest-tags** - Recommend tags based on title/notes

### Category 4: Smart Scheduling (1-3 tools)
9. **parse-natural-date** - Convert "next Monday" to YYYY-MM-DD
10. **smart-schedule-assistant** (optional - may overlap with Phase 2)
11. **forecast-completion-dates** (optional - ML-based prediction)

## Detailed Tool Specifications

### Tool 1: get-productivity-stats

**Purpose**: Provide high-level productivity metrics across all tasks

**Signature**:
```python
@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
@cached(ttl=300)  # 5 minute cache
async def get_productivity_stats(
    days: int = 30,
    ctx: Optional[Context] = None
) -> str:
    """
    Get productivity statistics for the specified time period.
    
    Args:
        days: Number of days to analyze (default: 30)
        ctx: FastMCP context for progress reporting
        
    Returns:
        Formatted statistics with structured data
    """
```

**Implementation Strategy**:
1. Query logbook for completed items in date range
2. Query all incomplete items
3. Calculate metrics:
   - Total completed
   - Completion rate (completed / total)
   - Average completion time
   - Overdue count
   - Completion trend (comparing to previous period)
4. Use `ctx.report_progress()` for queries >100 items
5. Return `ToolResult` with:
   - **Content**: Human-readable summary with emoji indicators
   - **Structured**: JSON with all metrics for programmatic access

**Data Structure**:
```python
@dataclass
class ProductivityStats:
    period_days: int
    completed_count: int
    incomplete_count: int
    completion_rate: float  # 0-1
    avg_completion_hours: float
    overdue_count: int
    trend: str  # "improving", "declining", "stable"
    top_productive_tags: List[Tuple[str, int]]  # (tag, count)
```

**Performance**:
- Expected: 200-500ms for 30 days
- Use progress reporting if >500 items analyzed
- Cache for 5 minutes (frequent queries expected)

**Output Format**:
```
📊 Productivity Stats (Last 30 days)

✅ Completed: 127 tasks
📝 Incomplete: 43 tasks
📈 Completion Rate: 74.7%
⏱️  Avg Time to Complete: 2.3 days
⚠️  Overdue: 8 tasks

📊 Trend: Improving (+12% vs previous period)

🏆 Most Productive Tags:
   1. work: 45 tasks
   2. personal: 32 tasks
   3. errands: 18 tasks
```

---

### Tool 2: get-project-velocity

**Purpose**: Track project completion trends over time

**Signature**:
```python
@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def get_project_velocity(
    project_uuid: str,
    interval: str = "weekly",  # daily, weekly, monthly
    periods: int = 4,
    ctx: Optional[Context] = None
) -> str:
    """
    Analyze project velocity (task completion rate over time).
    
    Args:
        project_uuid: Project UUID
        interval: Time interval (daily, weekly, monthly)
        periods: Number of periods to analyze
        ctx: FastMCP context for progress reporting
        
    Returns:
        Velocity chart and structured data
    """
```

**Implementation Strategy**:
1. Get project with `include_items=True`
2. Filter completed todos, group by time period
3. Calculate completion count per period
4. Compute velocity trend (accelerating/decelerating/stable)
5. Generate ASCII chart for visualization
6. Return structured data with all period metrics

**Data Structure**:
```python
@dataclass
class VelocityPeriod:
    period_start: str  # ISO date
    period_end: str
    completed_count: int
    created_count: int
    
@dataclass
class ProjectVelocity:
    project_uuid: str
    project_title: str
    interval: str
    periods: List[VelocityPeriod]
    avg_velocity: float  # tasks/period
    trend: str  # "accelerating", "decelerating", "stable"
```

**ASCII Chart Example**:
```
📈 Project Velocity: Work Sprint

Week 1: ████████░░ 8 tasks
Week 2: ██████████ 10 tasks  ⬆️
Week 3: ████████░░ 8 tasks   ⬇️
Week 4: ████████████ 12 tasks ⬆️

Avg: 9.5 tasks/week
Trend: Accelerating 🚀
```

---

### Tool 3: get-time-to-completion

**Purpose**: Analyze average time from task creation to completion

**Signature**:
```python
@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
@cached(ttl=600)  # 10 minute cache
async def get_time_to_completion(
    group_by: str = "overall",  # overall, tag, project, area
    limit: int = 100,
    ctx: Optional[Context] = None
) -> str:
    """
    Calculate average time to completion for tasks.
    
    Args:
        group_by: How to group results (overall, tag, project, area)
        limit: Max number of completed tasks to analyze
        ctx: FastMCP context for progress reporting
        
    Returns:
        Time-to-completion statistics
    """
```

**Implementation Strategy**:
1. Query logbook for recently completed items (limit)
2. For each item, calculate: `stop_date - created_date`
3. Group by specified dimension (tag/project/area)
4. Calculate statistics:
   - Mean time to completion
   - Median (50th percentile)
   - P90 (90th percentile)
   - Min/max
5. Report progress every 50 items
6. Return ranked list with structured data

**Data Structure**:
```python
@dataclass
class CompletionTimeStats:
    group_name: str  # "overall", or specific tag/project
    count: int
    avg_hours: float
    median_hours: float
    p90_hours: float
    min_hours: float
    max_hours: float
```

**Output Format**:
```
⏱️  Average Time to Completion (Last 100 tasks)

Overall: 2.3 days (median: 1.5 days)

By Tag:
   1. quick-wins: 0.5 days ⚡
   2. errands: 1.2 days
   3. work: 2.8 days
   4. projects: 7.3 days 🐢

Insight: Quick-wins tag is 5x faster than average!
```

---

### Tool 4: get-tag-productivity

**Purpose**: Compare completion rates across different tags

**Signature**:
```python
@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def get_tag_productivity(
    min_tasks: int = 5,
    sort_by: str = "completion_rate",  # completion_rate, count
    ctx: Optional[Context] = None
) -> str:
    """
    Analyze productivity metrics by tag.
    
    Args:
        min_tasks: Minimum tasks required for tag to be included
        sort_by: Sort order (completion_rate, count)
        ctx: FastMCP context
        
    Returns:
        Tag productivity rankings
    """
```

**Implementation Strategy**:
1. Get all tasks (completed + incomplete)
2. Group by tags
3. For each tag, calculate:
   - Total tasks
   - Completed tasks
   - Completion rate
   - Average time to completion
4. Filter tags with < min_tasks
5. Sort by specified metric
6. Return ranked list with visual indicators

**Data Structure**:
```python
@dataclass
class TagProductivityMetric:
    tag_name: str
    total_tasks: int
    completed_tasks: int
    completion_rate: float  # 0-1
    avg_completion_hours: float
```

**Output Format**:
```
🏆 Tag Productivity Rankings

1. quick-wins: 92% completion (23/25 tasks) ⭐⭐⭐
   Avg time: 0.5 days ⚡

2. errands: 78% completion (39/50 tasks) ⭐⭐
   Avg time: 1.2 days

3. work: 65% completion (130/200 tasks) ⭐
   Avg time: 2.8 days

4. someday: 15% completion (3/20 tasks) ⚠️
   Avg time: 45.2 days 🐢

Insight: Consider reviewing 'someday' tagged tasks!
```

---

### Tool 5: check-stalled-projects

**Purpose**: Identify projects with no recent activity

**Signature**:
```python
@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def check_stalled_projects(
    days_inactive: int = 30,
    include_completed: bool = False,
    ctx: Optional[Context] = None
) -> str:
    """
    Find projects with no recent activity (stalled).
    
    Args:
        days_inactive: Days without any todo activity
        include_completed: Include completed projects
        ctx: FastMCP context
        
    Returns:
        List of stalled projects with last activity date
    """
```

**Implementation Strategy**:
1. Get all projects (optionally exclude completed)
2. For each project:
   - Get todos with `include_items=True`
   - Find most recent activity (created/modified/completed)
   - Calculate days since last activity
3. Filter projects inactive > threshold
4. Sort by inactivity duration (longest first)
5. Return formatted list with recommendations

**Data Structure**:
```python
@dataclass
class StalledProject:
    uuid: str
    title: str
    last_activity_date: str  # ISO date
    days_inactive: int
    incomplete_count: int
    notes: Optional[str]
```

**Output Format**:
```
⚠️  Stalled Projects (No activity in 30+ days)

1. Website Redesign
   Last activity: 2025-09-15 (48 days ago)
   Status: 7 incomplete tasks
   Recommendation: Review or archive?

2. Garden Planning  
   Last activity: 2025-09-28 (35 days ago)
   Status: 3 incomplete tasks
   Recommendation: Seasonal project? Move to Someday?

3. Learning Spanish
   Last activity: 2025-10-01 (32 days ago)
   Status: 12 incomplete tasks
   Recommendation: Still interested? Schedule next lesson?

Found 3 stalled projects. Consider reviewing these!
```

---

### Tool 6: get-project-health-report

**Purpose**: Comprehensive project status and health metrics

**Signature**:
```python
@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def get_project_health_report(
    project_uuid: str,
    ctx: Optional[Context] = None
) -> str:
    """
    Generate comprehensive health report for a project.
    
    Args:
        project_uuid: Project UUID
        ctx: FastMCP context
        
    Returns:
        Detailed health report with metrics and recommendations
    """
```

**Implementation Strategy**:
1. Get project with all items
2. Calculate multiple health indicators:
   - **Completion Progress**: X/Y tasks complete (%)
   - **Velocity**: Tasks completed per week (last 4 weeks)
   - **Stall Risk**: Days since last activity
   - **Overdue Risk**: Number of overdue tasks
   - **Scope Creep**: New tasks added vs completed (last 2 weeks)
   - **Estimated Completion**: Based on current velocity
3. Compute overall health score (0-100)
4. Generate recommendations based on metrics
5. Return comprehensive report with structured data

**Health Score Algorithm**:
```python
def calculate_health_score(metrics):
    score = 100
    
    # Deduct for overdue tasks
    score -= min(metrics.overdue_count * 5, 30)
    
    # Deduct for inactivity
    if metrics.days_inactive > 14:
        score -= min((metrics.days_inactive - 14) * 2, 20)
    
    # Bonus for high completion rate
    if metrics.completion_rate > 0.75:
        score += 10
    
    # Deduct for scope creep
    if metrics.scope_creep_ratio > 1.5:  # Adding faster than completing
        score -= 15
    
    return max(0, min(100, score))
```

**Data Structure**:
```python
@dataclass
class ProjectHealth:
    project_uuid: str
    project_title: str
    health_score: int  # 0-100
    completion_rate: float
    velocity: float  # tasks/week
    days_inactive: int
    overdue_count: int
    scope_creep_ratio: float  # added/completed ratio
    estimated_completion_date: Optional[str]
    recommendations: List[str]
```

**Output Format**:
```
🏥 Project Health Report: Q4 Planning

Overall Health: 72/100 ⚠️  (Needs Attention)

📊 Metrics:
   ✅ Completion: 12/30 tasks (40%)
   📈 Velocity: 2.5 tasks/week
   ⏱️  Last Activity: 3 days ago
   ⚠️  Overdue: 4 tasks
   📊 Scope Creep: 1.2x (adding slightly faster than completing)
   
🎯 Estimated Completion: 2025-12-15 (7 weeks)

💡 Recommendations:
   1. Address 4 overdue tasks to improve health score
   2. Current velocity is healthy (2.5 tasks/week)
   3. Consider limiting new task additions until completion rate improves
   4. Review task priorities - 40% completion suggests good progress
```

---

### Tool 7: analyze-tag-relationships

**Purpose**: Discover which tags commonly appear together

**Signature**:
```python
@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
@cached(ttl=600)
async def analyze_tag_relationships(
    min_co_occurrences: int = 3,
    limit: int = 20,
    ctx: Optional[Context] = None
) -> str:
    """
    Analyze which tags frequently appear together.
    
    Args:
        min_co_occurrences: Minimum times tags must appear together
        limit: Max number of relationships to return
        ctx: FastMCP context
        
    Returns:
        Tag co-occurrence patterns and insights
    """
```

**Implementation Strategy**:
1. Get all tasks (all statuses)
2. Build co-occurrence matrix: `{(tag1, tag2): count}`
3. Filter pairs with < min_co_occurrences
4. Calculate co-occurrence strength: `count / min(tag1_count, tag2_count)`
5. Sort by strength (strongest relationships first)
6. Generate insights about tag usage patterns
7. Return formatted list with structured data

**Data Structure**:
```python
@dataclass
class TagRelationship:
    tag1: str
    tag2: str
    co_occurrence_count: int
    tag1_total: int
    tag2_total: int
    strength: float  # 0-1, how often they appear together
```

**Output Format**:
```
🔗 Tag Relationship Analysis

Strong Relationships (80%+ co-occurrence):
   1. work + urgent: 23 tasks (92% of urgent tasks)
      Insight: Urgent tasks are almost always work-related
   
   2. errands + weekend: 18 tasks (85% of weekend tasks)
      Insight: Errands typically scheduled for weekends
   
   3. learning + evening: 15 tasks (83% of learning tasks)
      Insight: Learning happens in evening hours

Moderate Relationships (50-80%):
   4. home + diy: 12 tasks (67%)
   5. fitness + morning: 10 tasks (55%)

💡 Insights:
   - Consider creating combined tags: "work-urgent", "weekend-errands"
   - "learning" tasks have consistent time pattern (evening)
   - "fitness" tag could benefit from default schedule (morning)
```

---

### Tool 8: suggest-tags

**Purpose**: Recommend tags based on task title and notes

**Signature**:
```python
@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def suggest_tags(
    title: str,
    notes: Optional[str] = None,
    max_suggestions: int = 5,
    ctx: Optional[Context] = None
) -> str:
    """
    Suggest relevant tags based on task content.
    
    Args:
        title: Task title
        notes: Task notes (optional)
        max_suggestions: Maximum suggestions to return
        ctx: FastMCP context
        
    Returns:
        Suggested tags with confidence scores
    """
```

**Implementation Strategy**:
1. Get all existing tags
2. Get all tasks with tags
3. Build keyword → tag mapping from historical data:
   - Extract keywords from titles/notes of tagged tasks
   - Build term frequency for each tag
4. For input title/notes:
   - Extract keywords (lowercase, remove common words)
   - Match against historical patterns
   - Calculate confidence scores
5. Return top suggestions sorted by confidence

**Simple Algorithm** (v1):
```python
def suggest_tags(title, notes, all_tagged_tasks):
    scores = defaultdict(float)
    input_words = set(extract_keywords(title + " " + (notes or "")))
    
    for task in all_tagged_tasks:
        task_words = set(extract_keywords(task.title + " " + (task.notes or "")))
        overlap = input_words & task_words
        
        if overlap:
            for tag in task.tags:
                scores[tag] += len(overlap) / len(input_words)
    
    # Normalize scores to 0-1 range
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**Data Structure**:
```python
@dataclass
class TagSuggestion:
    tag_name: str
    confidence: float  # 0-1
    matching_keywords: List[str]
    example_tasks: List[str]  # Similar task titles
```

**Output Format**:
```
🏷️  Tag Suggestions for: "Schedule dentist appointment for next week"

High Confidence (80%+):
   1. health (92% confidence) ⭐⭐⭐
      Matches: dentist, appointment
      Similar: "Book doctor appointment", "Pharmacy pickup"
   
   2. errands (85% confidence) ⭐⭐⭐
      Matches: appointment, schedule
      Similar: "Car service appointment", "Bank appointment"

Medium Confidence (50-80%):
   3. personal (65% confidence) ⭐⭐
      Matches: appointment
      Similar: "Haircut appointment", "Pet grooming"

💡 Recommendation: Add 'health' and 'errands' tags
```

---

### Tool 9: parse-natural-date

**Purpose**: Convert natural language dates to ISO format

**Signature**:
```python
@mcp.tool(annotations=READ_ONLY_ANNOTATIONS)
async def parse_natural_date(
    date_input: str,
    base_date: Optional[str] = None,
    ctx: Optional[Context] = None
) -> str:
    """
    Parse natural language date expressions to ISO format.
    
    Args:
        date_input: Natural language date (e.g., "next Monday", "in 3 days")
        base_date: Reference date for relative expressions (default: today)
        ctx: FastMCP context for elicitation on ambiguous dates
        
    Returns:
        ISO formatted date (YYYY-MM-DD) or error message
    """
```

**Implementation Strategy**:
1. Use `dateparser` library with appropriate settings
2. Configure to prefer future dates
3. Handle special keywords: "today", "tomorrow", "evening"
4. If ambiguous, use `ctx.elicit()` to request clarification
5. Validate parsed date is reasonable (not too far in past/future)
6. Return ISO date or detailed error

**Dateparser Configuration**:
```python
import dateparser

settings = {
    'PREFER_DATES_FROM': 'future',  # Prefer future for ambiguous dates
    'RETURN_AS_TIMEZONE_AWARE': False,
    'RELATIVE_BASE': base_date or datetime.now()
}

parsed = dateparser.parse(date_input, settings=settings)
```

**Error Handling**:
```python
if not parsed:
    # Check if it's a Things-specific keyword
    if date_input.lower() in ['anytime', 'someday']:
        return f"Special keyword: {date_input}"
    
    # Try to give helpful error
    raise ToolError(
        f"Could not parse '{date_input}'. "
        f"Try formats like: 'tomorrow', 'next Monday', 'Dec 25', '2025-12-25'"
    )

# Warn if date is in the past
if parsed.date() < datetime.now().date():
    await ctx.warning(f"Parsed date {parsed.date()} is in the past")
```

**Ambiguity Handling with Elicitation**:
```python
# Example: "1/2" could be Jan 2 or Feb 1
if is_ambiguous(date_input, parsed):
    result = await ctx.elicit(
        message=f"Did you mean {format1} or {format2}?",
        response_type=str
    )
    
    if result.action == "accept":
        return result.data
```

**Data Structure**:
```python
@dataclass
class ParsedDate:
    original_input: str
    parsed_date: str  # ISO format
    confidence: str  # "high", "medium", "low"
    interpretation: str  # Explanation of how it was parsed
```

**Output Format**:
```
Input: "next Monday at 5pm"
Parsed: 2025-11-09
Interpretation: Next occurrence of Monday (Nov 9, 2025)
Note: Time component (5pm) not supported in Things dates

---

Input: "in 3 days"
Parsed: 2025-11-05
Interpretation: 3 days from today (Nov 2, 2025)

---

Input: "Dec 25"
Parsed: 2025-12-25
Interpretation: Next occurrence of December 25

---

Input: "last week"  ⚠️
Parsed: 2025-10-26
Warning: This date is in the past
```

---

## Implementation Phases

### Week 1: Foundation & Analytics Tools 1-2
**Days 1-2**: Setup and Tool 1
- Add `dateparser>=1.2.0` dependency to pyproject.toml
- Create `src/things_mcp/analytics.py` module
- Implement `get_productivity_stats()` with progress reporting
- Add comprehensive tests
- Update TOOL_ANNOTATIONS dict

**Days 3-5**: Tool 2 - Project Velocity
- Implement `get_project_velocity()` with ASCII chart generation
- Add time period grouping logic
- Create helper functions for trend analysis
- Test with various intervals and projects

### Week 2: Analytics Tools 3-4 & Health Monitoring
**Days 6-7**: Tools 3-4 - Time & Tag Analytics
- Implement `get_time_to_completion()`
- Implement `get_tag_productivity()`
- Add statistical calculations (median, percentiles)
- Create visual ranking displays

**Days 8-10**: Tools 5-6 - Project Health
- Implement `check_stalled_projects()`
- Implement `get_project_health_report()` with scoring algorithm
- Add recommendation engine
- Create comprehensive health metrics

### Week 3: Tag Intelligence & Smart Scheduling
**Days 11-12**: Tools 7-8 - Tag Analysis
- Implement `analyze_tag_relationships()` with co-occurrence matrix
- Implement `suggest_tags()` with keyword extraction
- Add pattern matching algorithms
- Test with various tag combinations

**Days 13-14**: Tool 9 - Natural Language Dates
- Implement `parse_natural_date()` with dateparser integration
- Add ambiguity detection and elicitation
- Test edge cases (past dates, far future, invalid input)
- Document supported formats

**Day 15**: Integration & Testing
- Run full test suite
- Update AGENTS.md with all changes
- Update README.md with new tools
- Create CHANGELOG entry for v2.3.0
- Manual testing in Claude Desktop

## Code Organization

### New File: `src/things_mcp/analytics.py`
```python
"""
Analytics and intelligence layer for Things MCP server.
Provides productivity insights, project health monitoring, and tag analysis.
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict
import things
from .cache import cached
from .formatters import format_date

# Analytics dataclasses
@dataclass
class ProductivityStats:
    """Overall productivity metrics"""
    ...

@dataclass
class ProjectVelocity:
    """Project completion velocity over time"""
    ...

# Analytics functions
def calculate_productivity_stats(...) -> ProductivityStats:
    """Calculate overall productivity metrics"""
    ...

def calculate_project_velocity(...) -> ProjectVelocity:
    """Calculate project completion velocity"""
    ...

# Helper functions
def extract_keywords(text: str) -> List[str]:
    """Extract keywords from text for tag suggestion"""
    ...

def build_cooccurrence_matrix(tasks: List[Dict]) -> Dict[Tuple[str, str], int]:
    """Build tag co-occurrence matrix"""
    ...
```

### Updated File: `src/things_mcp/fast_server.py`
- Import from `analytics` module
- Add 9 new tool functions
- Register in TOOL_ANNOTATIONS dict
- Add to tool count (42 → 51 total)

### New File: `src/things_mcp/date_parser.py`
```python
"""
Natural language date parsing for Things MCP server.
Wraps dateparser with Things-specific handling.
"""
import dateparser
from datetime import datetime, date
from typing import Optional, Tuple
from fastmcp.exceptions import ToolError

def parse_natural_date(
    date_input: str,
    base_date: Optional[date] = None
) -> Tuple[date, str, str]:
    """
    Parse natural language date.
    
    Returns:
        (parsed_date, confidence, interpretation)
    """
    ...

def is_ambiguous(date_input: str, parsed: datetime) -> bool:
    """Detect ambiguous date inputs"""
    ...
```

## Testing Strategy

### Unit Tests
```python
# tests/test_analytics.py
def test_productivity_stats():
    """Test productivity calculation"""
    ...

def test_project_velocity():
    """Test velocity calculation with different intervals"""
    ...

def test_tag_relationships():
    """Test co-occurrence matrix building"""
    ...

def test_natural_date_parsing():
    """Test various date formats"""
    assert parse_natural_date("tomorrow") == ...
    assert parse_natural_date("next Monday") == ...
    assert parse_natural_date("in 3 days") == ...
```

### Integration Tests
```python
# tests/test_analytics_integration.py
async def test_productivity_stats_with_real_data():
    """Test with actual Things database"""
    ...

async def test_stalled_projects_detection():
    """Test stalled project identification"""
    ...
```

### Manual Test Plan
1. **Productivity Stats**:
   - Query 30-day stats
   - Verify completion rate calculation
   - Check trend detection

2. **Project Health**:
   - Test with active project
   - Test with stalled project
   - Verify health score accuracy

3. **Tag Analysis**:
   - Test tag suggestions on new task
   - Verify relationship detection
   - Check confidence scores

4. **Natural Language Dates**:
   - Test "tomorrow", "next Monday", "in 3 days"
   - Test ambiguous dates (trigger elicitation)
   - Test invalid inputs (proper errors)

## Performance Targets

| Tool | Target Time | Max Items | Progress Reporting |
|------|-------------|-----------|-------------------|
| get-productivity-stats | < 500ms | 1000 | Yes (>100 items) |
| get-project-velocity | < 300ms | N/A | No |
| get-time-to-completion | < 400ms | 500 | Yes (>100 items) |
| get-tag-productivity | < 600ms | All tags | Yes (>200 items) |
| check-stalled-projects | < 400ms | All projects | No |
| get-project-health-report | < 200ms | N/A | No |
| analyze-tag-relationships | < 800ms | All tasks | Yes (>500 items) |
| suggest-tags | < 300ms | All tags | No |
| parse-natural-date | < 50ms | N/A | No |

**Monitoring**: DetailedTimingMiddleware will track all actual times

## Dependencies

### New Python Packages
```toml
[project.dependencies]
dateparser = ">=1.2.0"  # Natural language date parsing
```

**Total Dependency Count**: 6 new transitive dependencies (dateparser brings: python-dateutil, regex, tzlocal, pytz)

### Existing Infrastructure
- ✅ FastMCP context system (ctx.report_progress, ctx.elicit)
- ✅ Caching system (@cached decorator)
- ✅ Middleware (DetailedTimingMiddleware for monitoring)
- ✅ Error handling (ToolError, ErrorHandlingMiddleware)
- ✅ Formatters (format_date, format_todo, etc.)

## Documentation Updates

### README.md Changes
Add new section after Phase 2 tools:

```markdown
#### Analytics & Intelligence

| Tool | Description | Read Only |
|------|-------------|-----------|
| get-productivity-stats | Overall completion metrics and trends | ✓ |
| get-project-velocity | Project completion rate over time | ✓ |
| get-time-to-completion | Average time from creation to completion | ✓ |
| get-tag-productivity | Completion rates by tag | ✓ |
| check-stalled-projects | Find projects with no recent activity | ✓ |
| get-project-health-report | Comprehensive project status | ✓ |
| analyze-tag-relationships | Tag co-occurrence patterns | ✓ |
| suggest-tags | Recommend tags based on content | ✓ |
| parse-natural-date | Convert "next Monday" to ISO dates | ✓ |
```

### CHANGELOG.md Entry
```markdown
## [2.3.0] - 2025-11-XX

### Added - Intelligence Layer
- **Analytics Tools**: 4 new productivity analysis tools
  - `get-productivity-stats`: Overall metrics with trend analysis
  - `get-project-velocity`: Completion rate tracking over time
  - `get-time-to-completion`: Average completion time analysis
  - `get-tag-productivity`: Tag-based productivity rankings

- **Project Health**: 2 monitoring tools
  - `check-stalled-projects`: Identify inactive projects
  - `get-project-health-report`: Comprehensive health scoring

- **Tag Intelligence**: 2 analysis tools
  - `analyze-tag-relationships`: Co-occurrence pattern detection
  - `suggest-tags`: AI-powered tag recommendations

- **Smart Scheduling**: Natural language date support
  - `parse-natural-date`: Convert "next Monday" to YYYY-MM-DD
  - Supports elicitation for ambiguous dates
  - Powered by dateparser library

### Technical
- Added `dateparser>=1.2.0` dependency
- Progress reporting for long analytics queries
- Structured outputs for all analytics tools
- ASCII chart generation for velocity visualization
- Caching for expensive analytics queries (5-10 min TTL)

### Performance
- All analytics tools complete in <1 second
- Progress reporting for queries analyzing >100 items
- Middleware monitoring confirms targets met
```

## Risk Mitigation

### Risk 1: Performance Degradation
**Mitigation**:
- Use `@cached` decorator with appropriate TTLs
- Implement progress reporting for long queries
- Add early termination if context window exceeded
- Monitor with DetailedTimingMiddleware

### Risk 2: dateparser Dependency Issues
**Mitigation**:
- Pin to stable version (>=1.2.0)
- Add fallback to simple date parsing if import fails
- Test thoroughly with edge cases
- Document supported formats clearly

### Risk 3: Analytics Accuracy
**Mitigation**:
- Use actual Things database data (not synthetic)
- Add validation checks for data quality
- Document calculation methods in docstrings
- Provide raw numbers alongside computed metrics

### Risk 4: Context Window Overflow
**Mitigation**:
- Default to reasonable limits (30 days, 100 tasks)
- Provide `limit` parameters on all list-returning tools
- Use structured outputs to reduce token usage
- Warn users via ctx.warning() when results are large

## Success Criteria

### Functional Requirements
- [ ] All 9 tools implemented and working
- [ ] Natural language date parsing covers 90%+ common formats
- [ ] Analytics calculations mathematically correct
- [ ] Progress reporting works for long queries
- [ ] Structured outputs parseable by LLMs

### Quality Requirements
- [ ] Zero ruff warnings
- [ ] All unit tests pass
- [ ] Integration tests with real Things data pass
- [ ] Code coverage >80% for analytics module
- [ ] Documentation complete and clear

### Performance Requirements
- [ ] All tools complete within target times
- [ ] DetailedTimingMiddleware confirms no regressions
- [ ] Memory usage reasonable (<100MB increase)
- [ ] No blocking operations (all async)

### User Experience
- [ ] Analytics provide actionable insights
- [ ] Health scores match intuitive expectations
- [ ] Tag suggestions are relevant
- [ ] Natural date parsing handles edge cases gracefully
- [ ] Error messages are clear and helpful

## Post-Release Plan

### v2.3.1 - Refinements (2-3 weeks after release)
- Tune health scoring algorithm based on feedback
- Add more date parsing formats
- Optimize slow analytics queries
- Add caching to more expensive operations

### v2.4.0 - Advanced Analytics (Future)
- Machine learning for tag suggestions
- Predictive completion date forecasting
- Burndown chart generation
- Custom analytics queries (user-defined)

### v3.0.0 - Real-time Features (Future)
- Live project health monitoring
- Automatic stalled project notifications
- Productivity dashboard (via resource)
- Integration with calendar systems

## Appendix: FastMCP Best Practices Applied

### 1. Progress Reporting Pattern
```python
async def expensive_analytics(ctx: Context):
    items = get_all_items()
    total = len(items)
    
    for i, item in enumerate(items):
        if i % 50 == 0:  # Report every 50 items
            await ctx.report_progress(
                progress=i,
                total=total,
                message=f"Analyzing {i}/{total} items..."
            )
        # Process item
    
    await ctx.report_progress(progress=total, total=total)
```

### 2. Structured Output Pattern
```python
from dataclasses import dataclass, asdict
from fastmcp import types

@dataclass
class AnalyticsResult:
    metric1: float
    metric2: int
    insights: List[str]

@mcp.tool()
async def analytics_tool() -> str:
    # Calculate metrics
    result = AnalyticsResult(...)
    
    # Return both human-readable AND structured data
    return types.ToolResult(
        content=[types.TextContent(text="📊 Summary...")],
        structured_content=asdict(result)
    )
```

### 3. Error Handling with Elicitation
```python
from fastmcp.exceptions import ToolError

async def parse_date(date_input: str, ctx: Context):
    parsed = dateparser.parse(date_input)
    
    if not parsed:
        raise ToolError(f"Invalid date: {date_input}")
    
    if is_ambiguous(date_input):
        result = await ctx.elicit(
            message="Did you mean... ?",
            response_type=str
        )
        if result.action == "accept":
            return result.data
```

### 4. Caching Expensive Operations
```python
from .cache import cached

@mcp.tool()
@cached(ttl=600)  # 10 minute cache
async def expensive_analytics():
    # Heavy computation here
    ...
```

## Implementation Checklist

### Pre-Implementation
- [ ] Read this plan thoroughly
- [ ] Review FastMCP docs on progress reporting
- [ ] Review dateparser documentation
- [ ] Set up testing environment

### Week 1
- [ ] Add dateparser dependency
- [ ] Create analytics.py module
- [ ] Implement Tool 1: get-productivity-stats
- [ ] Implement Tool 2: get-project-velocity
- [ ] Write unit tests for Tools 1-2
- [ ] Update AGENTS.md

### Week 2
- [ ] Implement Tool 3: get-time-to-completion
- [ ] Implement Tool 4: get-tag-productivity
- [ ] Implement Tool 5: check-stalled-projects
- [ ] Implement Tool 6: get-project-health-report
- [ ] Write unit tests for Tools 3-6
- [ ] Update AGENTS.md

### Week 3
- [ ] Implement Tool 7: analyze-tag-relationships
- [ ] Implement Tool 8: suggest-tags
- [ ] Create date_parser.py module
- [ ] Implement Tool 9: parse-natural-date
- [ ] Write unit tests for Tools 7-9
- [ ] Integration testing with real Things data

### Final Week
- [ ] Performance testing and optimization
- [ ] Update README.md
- [ ] Create CHANGELOG entry
- [ ] Manual testing in Claude Desktop
- [ ] Version bump to 2.3.0
- [ ] Git commit and tag
- [ ] Update AGENTS.md with completion notes

---

**Plan Status**: Ready for Implementation  
**Dependencies**: Phase 1 complete (required), Phase 2 optional  
**Estimated Completion**: 2-3 weeks from start  
**Total New Code**: ~1200-1500 lines (9 tools + analytics module + tests)
