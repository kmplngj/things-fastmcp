"""
MCP Prompts for Things 3 Task Management.

This module provides prompt templates for common task management workflows,
organized into 4 categories:
1. Task Creation - Creating tasks with various configurations
2. Project Planning - Setting up projects and planning work
3. Review & Reflection - Analyzing completed work and identifying issues
4. Workflow Automation - Batch operations and intelligent organization

All prompts use FastMCP's @mcp.prompt decorator and return PromptMessage objects.
"""

from typing import Optional, List
from fastmcp import FastMCP
from fastmcp.prompts import PromptMessage
from mcp.types import TextContent  # Correct import path

# Import the FastMCP instance (will be set by fast_server.py)
mcp: Optional[FastMCP] = None


def init_prompts(fastmcp_instance: FastMCP) -> None:
    """
    Initialize prompts module with FastMCP instance.
    
    Args:
        fastmcp_instance: The FastMCP server instance
    """
    global mcp
    mcp = fastmcp_instance


# ============================================================================
# CATEGORY 1: TASK CREATION PROMPTS
# ============================================================================

def create_simple_task_prompt(
    task_name: str,
    notes: Optional[str] = None
) -> PromptMessage:
    """
    Generate a prompt for creating a simple task.
    
    Args:
        task_name: The title of the task
        notes: Optional additional notes
        
    Returns:
        PromptMessage with task creation instructions
        
    Example:
        >>> prompt = create_simple_task_prompt("Buy groceries", "Milk, eggs, bread")
        >>> # LLM receives: Create task "Buy groceries" with notes...
    """
    content = f"""Create a task in Things 3:

**Task**: {task_name}
"""
    
    if notes:
        content += f"**Notes**: {notes}\n"
    
    content += """
Please use the `add-todo` tool with:
- title: "{task_name}"
"""
    
    if notes:
        content += f'- notes: "{notes}"\n'
    
    content += """
This will create the task in your inbox for later organization.
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


def create_task_with_deadline_prompt(
    task_name: str,
    deadline: str,
    project: Optional[str] = None,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None
) -> PromptMessage:
    """
    Generate a prompt for creating a task with a deadline.
    
    Args:
        task_name: The title of the task
        deadline: Deadline in YYYY-MM-DD format or 'today'/'tomorrow'
        project: Optional project name or UUID
        tags: Optional list of tag names
        notes: Optional additional notes
        
    Returns:
        PromptMessage with task creation instructions
        
    Example:
        >>> prompt = create_task_with_deadline_prompt(
        ...     "Submit report",
        ...     "2025-12-31",
        ...     project="Work",
        ...     tags=["urgent", "report"]
        ... )
    """
    content = f"""Create a task in Things 3 with a deadline:

**Task**: {task_name}
**Deadline**: {deadline}
"""
    
    if project:
        content += f"**Project**: {project}\n"
    if tags:
        content += f"**Tags**: {', '.join(tags)}\n"
    if notes:
        content += f"**Notes**: {notes}\n"
    
    content += """
Please use the `add-todo` tool with these parameters:
- title: The task name
- deadline: The deadline date (YYYY-MM-DD, 'today', or 'tomorrow')
"""
    
    if project:
        content += "- project: The project name (will be resolved to UUID)\n"
    if tags:
        content += f"- tags: {tags}\n"
    if notes:
        content += "- notes: Additional details\n"
    
    content += """
The task will be created with the deadline set, helping you track when it's due.
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


def create_recurring_task_prompt(
    task_name: str,
    when: str,
    deadline: Optional[str] = None,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None
) -> PromptMessage:
    """
    Generate a prompt for creating a recurring task.
    
    Args:
        task_name: The title of the task
        when: Scheduling ('today', 'anytime', 'someday', or YYYY-MM-DD)
        deadline: Optional deadline for each occurrence
        tags: Optional list of tag names
        notes: Optional notes with recurrence pattern explanation
        
    Returns:
        PromptMessage with recurring task creation instructions
        
    Example:
        >>> prompt = create_recurring_task_prompt(
        ...     "Weekly team meeting",
        ...     when="today",
        ...     tags=["work", "meetings"],
        ...     notes="Repeats every Monday at 10am"
        ... )
    """
    content = f"""Create a recurring task in Things 3:

**Task**: {task_name}
**Schedule**: {when}
"""
    
    if deadline:
        content += f"**Deadline**: {deadline}\n"
    if tags:
        content += f"**Tags**: {', '.join(tags)}\n"
    if notes:
        content += f"**Notes**: {notes}\n"
    
    content += """
To create this as a recurring task:

1. First, use `add-todo` to create the initial task:
   - title: The task name
   - when: Schedule it appropriately
"""
    
    if deadline:
        content += "   - deadline: Set the first deadline\n"
    if tags:
        content += f"   - tags: {tags}\n"
    
    content += """
2. After creation, the user should:
   - Open Things 3 manually
   - Select the task
   - Use "Make Repeating" (⌘R) to set the recurrence pattern
   
Note: Things 3's URL scheme doesn't support creating recurring tasks directly.
This prompt helps you create the base task that can then be made recurring.
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


def create_task_with_checklist_prompt(
    task_name: str,
    checklist_items: List[str],
    project: Optional[str] = None,
    when: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> PromptMessage:
    """
    Generate a prompt for creating a task with a checklist.
    
    Args:
        task_name: The title of the task
        checklist_items: List of checklist item titles
        project: Optional project name or UUID
        when: Optional scheduling ('today', 'tomorrow', etc.)
        tags: Optional list of tag names
        
    Returns:
        PromptMessage with checklist task creation instructions
        
    Example:
        >>> prompt = create_task_with_checklist_prompt(
        ...     "Prepare presentation",
        ...     ["Create slides", "Write script", "Practice delivery"],
        ...     project="Work",
        ...     when="today"
        ... )
    """
    content = f"""Create a task in Things 3 with a checklist:

**Task**: {task_name}
**Checklist Items**:
"""
    
    for i, item in enumerate(checklist_items, 1):
        content += f"{i}. {item}\n"
    
    if project:
        content += f"\n**Project**: {project}"
    if when:
        content += f"\n**Schedule**: {when}"
    if tags:
        content += f"\n**Tags**: {', '.join(tags)}"
    
    content += """

Please use the `add-todo` tool with these parameters:
- title: The task name
- checklist_items: List of checklist items (as shown above)
"""
    
    if project:
        content += "- project: The project name\n"
    if when:
        content += "- when: The scheduling option\n"
    if tags:
        content += f"- tags: {tags}\n"
    
    content += """
This will create a task with all checklist items already added, making it easy
to track sub-steps within the task.
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


def brainstorm_project_tasks_prompt(
    project_name: str,
    project_goal: str,
    context: Optional[str] = None
) -> PromptMessage:
    """
    Generate a prompt to brainstorm tasks for a project.
    
    Args:
        project_name: The name of the project
        project_goal: The main goal or objective of the project
        context: Optional additional context about the project
        
    Returns:
        PromptMessage asking for task suggestions
        
    Example:
        >>> prompt = brainstorm_project_tasks_prompt(
        ...     "Website Redesign",
        ...     "Modernize company website to improve UX",
        ...     context="Current site uses outdated tech stack"
        ... )
    """
    content = f"""Help me brainstorm tasks for a new project in Things 3:

**Project**: {project_name}
**Goal**: {project_goal}
"""
    
    if context:
        content += f"**Context**: {context}\n"
    
    content += """

Please suggest:

1. **Major Phases** (3-5 high-level phases)
   - What are the main stages of this project?
   - These will become headings in Things 3

2. **Initial Tasks** (5-10 concrete tasks)
   - What are the first actions to take?
   - Be specific and actionable
   - Assign to appropriate phases

3. **Dependencies**
   - Which tasks need to happen first?
   - Any parallel work streams?

4. **Recommended Tags**
   - 2-4 tags to organize this work
   - Consider priority, category, or theme

After you provide suggestions, I can use these tools:
- `add-project` to create the project
- `manage-heading` to add phase headings
- `add-todo` to create the tasks
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


# ============================================================================
# CATEGORY 2: PROJECT PLANNING PROMPTS
# ============================================================================

def start_new_project_prompt(
    project_name: str,
    goal: str,
    deadline: Optional[str] = None,
    area: Optional[str] = None
) -> PromptMessage:
    """
    Generate a prompt for starting a new project.
    
    Args:
        project_name: The name of the project
        goal: The main objective or purpose
        deadline: Optional target completion date
        area: Optional area to assign the project to
        
    Returns:
        PromptMessage with project setup instructions
        
    Example:
        >>> prompt = start_new_project_prompt(
        ...     "Q1 Marketing Campaign",
        ...     "Launch new product line",
        ...     deadline="2026-03-31",
        ...     area="Marketing"
        ... )
    """
    content = f"""Let's set up a new project in Things 3:

**Project**: {project_name}
**Goal**: {goal}
"""
    
    if deadline:
        content += f"**Target Completion**: {deadline}\n"
    if area:
        content += f"**Area**: {area}\n"
    
    content += """

Please help me:

1. **Break Down the Goal** into major phases (3-5 phases)
   - What are the main stages needed to achieve this goal?
   - Each phase will become a heading in the project

2. **Suggest Initial Tasks** for the first phase
   - 3-5 concrete, actionable tasks to get started
   - Be specific about what needs to be done

3. **Recommend Tags** for this project
   - 2-3 relevant tags to help organize and find related work
   - Consider priority level, category, or theme

4. **Identify Success Criteria**
   - How will we know this project is complete?
   - What does success look like?

After you provide the breakdown, I'll use these tools to set it up:
- `add-project`: Create the project structure
- `manage-heading`: Add phase headings
- `add-todo`: Create the initial tasks
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


def create_project_with_phases_prompt(
    project_name: str,
    phases: List[str],
    area: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> PromptMessage:
    """
    Generate a prompt for creating a project with predefined phases.
    
    Args:
        project_name: The name of the project
        phases: List of phase names (will become headings)
        area: Optional area to assign the project to
        tags: Optional list of tag names
        
    Returns:
        PromptMessage with phased project creation instructions
        
    Example:
        >>> prompt = create_project_with_phases_prompt(
        ...     "Product Launch",
        ...     ["Planning", "Development", "Testing", "Release"],
        ...     area="Product",
        ...     tags=["launch", "priority"]
        ... )
    """
    content = f"""Create a project in Things 3 with phases:

**Project**: {project_name}
**Phases**:
"""
    
    for i, phase in enumerate(phases, 1):
        content += f"{i}. {phase}\n"
    
    if area:
        content += f"\n**Area**: {area}"
    if tags:
        content += f"\n**Tags**: {', '.join(tags)}"
    
    content += """

To set this up, please follow these steps:

**Step 1**: Create the project
```
Use `add-project` tool:
- title: project_name
"""
    
    if area:
        content += "- area: area_name\n"
    if tags:
        content += f"- tags: {tags}\n"
    
    content += """
```

**Step 2**: Add phase headings
For each phase, use `manage-heading` tool:
- action: "add"
- project: project_name (or UUID from step 1)
- heading_title: phase_name

This creates a structured project where you can organize tasks by phase.
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


def daily_standup_review_prompt(
    focus_areas: Optional[List[str]] = None
) -> PromptMessage:
    """
    Generate a prompt for daily standup review.
    
    Args:
        focus_areas: Optional list of areas to focus on (projects, tags, or areas)
        
    Returns:
        PromptMessage for reviewing today's work
        
    Example:
        >>> prompt = daily_standup_review_prompt(focus_areas=["Work", "Personal"])
    """
    content = """Let's do a quick daily standup review of my Things 3 tasks:

Please gather and analyze:

1. **Today's Tasks** (`list-items` with list_type="today")
   - What's on my plate for today?
   - How many tasks total?
   - Any overdue items that rolled over?

2. **Recently Completed** (`list-items` with list_type="logbook", limit=10)
   - What did I finish recently?
   - Any patterns in completion?

3. **Upcoming This Week** (`list-items` with list_type="upcoming", limit=20)
   - What's coming up soon?
   - Any potential bottlenecks?

"""
    
    if focus_areas:
        content += f"""4. **Focus Areas**: {', '.join(focus_areas)}
   - Filter results to these specific areas/tags
   - Any area that needs more attention?

"""
    
    content += """Then provide a standup-style summary:
- ✅ What I completed recently
- 🎯 What I'm working on today
- 📅 What's coming up this week
- ⚠️ Any blockers or concerns
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


def weekly_review_prompt(
    days: int = 7
) -> PromptMessage:
    """
    Generate a prompt for weekly review.
    
    Args:
        days: Number of days to review (default: 7)
        
    Returns:
        PromptMessage for comprehensive weekly review
        
    Example:
        >>> prompt = weekly_review_prompt(days=7)
    """
    content = f"""Let's do a comprehensive weekly review of my Things 3 productivity:

**Review Period**: Last {days} days

Please analyze:

1. **Completed Tasks** (`list-items` with list_type="logbook", limit={days * 10})
   - Total completed in the last {days} days
   - Breakdown by project/area
   - Most productive days

2. **Current State** 
   - Inbox: How many items waiting to be organized?
   - Today: What's still on today's list?
   - Upcoming: What's scheduled for next week?

3. **Project Progress** (`list-items` with list_type="projects")
   - Active projects and their completion status
   - Any stalled projects? (no activity in {days} days)
   - Projects close to completion?

4. **Areas of Life Balance** (`list-items` with list_type="areas")
   - Which areas got the most attention?
   - Which areas need more focus?

Then provide insights:
- 📊 **Productivity Summary**: Key metrics and trends
- 🏆 **Wins**: Major accomplishments this week
- 🎯 **Focus Areas**: Where did I spend my time?
- ⚠️ **Attention Needed**: Projects or areas lagging behind
- 💡 **Recommendations**: What to prioritize next week
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


# ============================================================================
# CATEGORY 3: REVIEW & REFLECTION PROMPTS
# ============================================================================

def reflect_on_completed_tasks_prompt(
    days: int = 7,
    project: Optional[str] = None
) -> PromptMessage:
    """
    Generate a prompt for reflecting on completed tasks.
    
    Args:
        days: Number of days to review
        project: Optional project to focus on
        
    Returns:
        PromptMessage for task completion reflection
        
    Example:
        >>> prompt = reflect_on_completed_tasks_prompt(days=14, project="Website Redesign")
    """
    content = f"""Let's reflect on my completed tasks from the last {days} days:

Please use `list-items` with:
- list_type: "logbook"
- limit: {days * 5}  # Estimate ~5 tasks/day

"""
    
    if project:
        content += f"""- filters: Focus on project "{project}"

"""
    
    content += """Then analyze and help me understand:

1. **Productivity Patterns**
   - What types of tasks did I complete most?
   - Which tags appear most frequently?
   - Any clusters by day of week?

2. **Time Allocation**
   - Which projects/areas got the most attention?
   - Is this aligned with my priorities?
   - Any surprises in where time went?

3. **Completion Velocity**
   - How many tasks completed per day on average?
   - Any tasks that took longer than expected?
   - Quick wins vs. long-running tasks?

4. **Success Factors**
   - What helped me complete these tasks?
   - Tasks with clear deadlines vs. open-ended?
   - Project-based vs. standalone tasks?

5. **Improvement Areas**
   - What patterns suggest I could improve?
   - Tasks that got delayed or stalled?
   - Areas to streamline?

Provide actionable insights to help me work more effectively.
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


def identify_stalled_projects_prompt(
    inactive_days: int = 14
) -> PromptMessage:
    """
    Generate a prompt to identify stalled projects.
    
    Args:
        inactive_days: Number of days without activity to consider "stalled"
        
    Returns:
        PromptMessage for finding inactive projects
        
    Example:
        >>> prompt = identify_stalled_projects_prompt(inactive_days=30)
    """
    content = f"""Help me identify stalled projects in Things 3:

**Definition**: Projects with no activity (no new tasks, no completions) in the last {inactive_days} days

Please:

1. **Get All Projects** using `list-items` with list_type="projects"

2. **For Each Project**, check:
   - When was the last task added?
   - When was the last task completed?
   - How many incomplete tasks remain?
   - Is there a deadline approaching?

3. **Categorize Projects**:
   - 🔴 **Critical Stalled**: {inactive_days}+ days, has deadline, many incomplete tasks
   - 🟡 **Attention Needed**: {inactive_days}+ days, no deadline, some incomplete tasks
   - 🟢 **Someday/Maybe**: Intentionally on hold
   - ⚪ **Active**: Recent activity

4. **For Stalled Projects**, suggest:
   - Should it be reactivated? Next steps?
   - Should it be moved to Someday?
   - Should it be canceled/archived?
   - What's blocking progress?

5. **Provide Recommendations**:
   - Which projects need immediate attention?
   - Which projects could be simplified?
   - Which projects should be closed?

Help me clean up my project list and focus on what matters.
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


def review_overdue_items_prompt() -> PromptMessage:
    """
    Generate a prompt for reviewing overdue items.
    
    Returns:
        PromptMessage for overdue item review
        
    Example:
        >>> prompt = review_overdue_items_prompt()
    """
    content = """Let's review all overdue items in Things 3:

Please use the `deadline-items` tool with:
- status: "overdue"

Then analyze:

1. **Severity Triage**
   - How many days overdue for each item?
   - Group by severity: 1-3 days, 4-7 days, 8+ days

2. **Category Analysis**
   - Which projects have the most overdue items?
   - Which areas are affected?
   - Any patterns in tags?

3. **Root Cause Analysis**
   - Were deadlines realistic?
   - Tasks too large/complex?
   - Dependencies blocking progress?
   - Simply forgotten?

4. **Action Plan**
   For each overdue item, suggest:
   - ✅ **Complete Now**: Can be done quickly
   - 📅 **Reschedule**: Needs new realistic deadline
   - 🔨 **Break Down**: Too large, needs subtasks
   - ❌ **Cancel**: No longer relevant
   - 🔄 **Delegate**: Should be someone else's task

5. **Prevention Strategy**
   - How to avoid similar situations?
   - Better deadline estimation?
   - Earlier warning system?
   - Different project structure?

Help me clear the backlog and improve my deadline management.
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


# ============================================================================
# CATEGORY 4: WORKFLOW AUTOMATION PROMPTS
# ============================================================================

def batch_schedule_tasks_prompt(
    filter_type: str,
    filter_value: str,
    schedule_to: str
) -> PromptMessage:
    """
    Generate a prompt for batch scheduling tasks.
    
    Args:
        filter_type: How to find tasks ("tag", "project", "area", "inbox")
        filter_value: The value to filter by (tag name, project name, etc.)
        schedule_to: Where to schedule ('today', 'tomorrow', 'anytime', etc.)
        
    Returns:
        PromptMessage for batch scheduling operation
        
    Example:
        >>> prompt = batch_schedule_tasks_prompt("tag", "quick-wins", "today")
    """
    content = f"""Let's batch schedule tasks based on a filter:

**Filter**: {filter_type} = "{filter_value}"
**Schedule To**: {schedule_to}

Please follow these steps:

1. **Find Matching Tasks** using `list-items`:
   - list_type: "{filter_type}"
"""
    
    if filter_type != "inbox":
        content += f'   - filters: {{"name": "{filter_value}"}}\n'
    
    content += """   - Show only incomplete tasks

2. **Preview the Selection**:
   - List the first 10 matching tasks
   - Show total count
   - Estimate time impact (if these all go to "today", is that realistic?)

3. **Confirm the Operation**:
   - Ask: "Should I schedule these X tasks to '{schedule_to}'?"
   - Wait for confirmation

4. **Execute Batch Update** using `update-todo` for each task:
   - Set when="{schedule_to}"
   - Report progress every 10 tasks
   - Show success/failure count

5. **Summary**:
   - Total tasks scheduled
   - Any failures
   - Next steps suggestion

This helps you quickly organize groups of related tasks.
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


def organize_inbox_prompt() -> PromptMessage:
    """
    Generate a prompt for organizing inbox items.
    
    Returns:
        PromptMessage for inbox organization workflow
        
    Example:
        >>> prompt = organize_inbox_prompt()
    """
    content = """Let's organize my Things 3 inbox:

Please use `list-items` with list_type="inbox" to see what needs organizing.

For each inbox item, help me decide:

1. **Categorize**:
   - 📋 Task: Actionable, can be done
   - 📁 Project: Larger effort, needs breakdown
   - 📌 Reference: Information to keep but not actionable
   - 🗑️ Delete: No longer relevant

2. **For Tasks**, suggest:
   - **Project**: Where does it belong?
   - **Area**: What life area? (Work, Personal, etc.)
   - **Tags**: 1-2 relevant tags
   - **When**: today, tomorrow, anytime, someday?
   - **Deadline**: Does it need one?

3. **For Projects**, suggest:
   - **Area**: What life area?
   - **Tags**: Project classification
   - **First 3 Tasks**: What are the next actions?
   - **When**: When to start?

4. **Batch Processing**:
   - Group similar items together
   - Process one category at a time
   - Show progress as we go

5. **Execute Changes** using:
   - `update-todo`: Move tasks to projects/areas
   - `add-project`: Create new projects
   - `add-todo`: Add tasks to projects

Goal: Get inbox to zero or near-zero, with everything properly organized.
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


def suggest_next_actions_prompt(
    context: Optional[str] = None,
    time_available: Optional[str] = None
) -> PromptMessage:
    """
    Generate a prompt for suggesting next actions.
    
    Args:
        context: Optional context about current situation
        time_available: Optional time constraint ("15 minutes", "1 hour", etc.)
        
    Returns:
        PromptMessage for intelligent next action suggestions
        
    Example:
        >>> prompt = suggest_next_actions_prompt(
        ...     context="Just finished a meeting",
        ...     time_available="30 minutes"
        ... )
    """
    content = """Help me decide what to work on next:

"""
    
    if context:
        content += f"**Current Context**: {context}\n"
    if time_available:
        content += f"**Time Available**: {time_available}\n"
    
    content += """
Please analyze:

1. **Today's Tasks** (`list-items` with list_type="today")
   - What's still pending today?
   - Any time-sensitive items?
   - Quick wins available?

2. **Deadlines** (`deadline-items` with status="upcoming")
   - What's due soon (next 3 days)?
   - Any urgent items approaching?

3. **Priority Assessment**:
   - Importance: What has biggest impact?
   - Urgency: What needs to happen soonest?
   - Energy: What matches my current energy level?
"""
    
    if time_available:
        content += f"   - Time: What fits in {time_available}?\n"
    
    content += """
4. **Context Matching**:
"""
    
    if context:
        content += f"   - Given context: {context}\n"
    
    content += """   - What makes sense to do right now?
   - Any momentum from previous work?
   - Can I batch similar tasks?

5. **Recommend Top 3 Actions**:
   For each, explain:
   - Why this task now?
   - Estimated time needed
   - Expected outcome/benefit
   - Tools needed

Help me make the best use of my available time.
"""
    
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=content)
    )


# ============================================================================
# PROMPT REGISTRATION
# ============================================================================

PROMPT_REGISTRY = {
    # Task Creation
    "create-simple-task": {
        "function": create_simple_task_prompt,
        "description": "Generate prompt for creating a simple task",
        "category": "task_creation",
        "tags": {"things3", "task_creation", "basic"}
    },
    "create-task-with-deadline": {
        "function": create_task_with_deadline_prompt,
        "description": "Generate prompt for creating a task with deadline",
        "category": "task_creation",
        "tags": {"things3", "task_creation", "deadline"}
    },
    "create-recurring-task": {
        "function": create_recurring_task_prompt,
        "description": "Generate prompt for creating a recurring task",
        "category": "task_creation",
        "tags": {"things3", "task_creation", "recurring"}
    },
    "create-task-with-checklist": {
        "function": create_task_with_checklist_prompt,
        "description": "Generate prompt for creating a task with checklist",
        "category": "task_creation",
        "tags": {"things3", "task_creation", "checklist"}
    },
    "brainstorm-project-tasks": {
        "function": brainstorm_project_tasks_prompt,
        "description": "Generate prompt to brainstorm tasks for a project",
        "category": "task_creation",
        "tags": {"things3", "task_creation", "brainstorm", "project"}
    },
    
    # Project Planning
    "start-new-project": {
        "function": start_new_project_prompt,
        "description": "Generate prompt for starting a new project",
        "category": "project_planning",
        "tags": {"things3", "project_planning", "setup"}
    },
    "create-project-with-phases": {
        "function": create_project_with_phases_prompt,
        "description": "Generate prompt for creating phased project",
        "category": "project_planning",
        "tags": {"things3", "project_planning", "phases"}
    },
    "daily-standup-review": {
        "function": daily_standup_review_prompt,
        "description": "Generate prompt for daily standup review",
        "category": "project_planning",
        "tags": {"things3", "project_planning", "review", "daily"}
    },
    "weekly-review": {
        "function": weekly_review_prompt,
        "description": "Generate prompt for weekly review",
        "category": "project_planning",
        "tags": {"things3", "project_planning", "review", "weekly"}
    },
    
    # Review & Reflection
    "reflect-on-completed-tasks": {
        "function": reflect_on_completed_tasks_prompt,
        "description": "Generate prompt for reflecting on completed work",
        "category": "review",
        "tags": {"things3", "review", "reflection", "analytics"}
    },
    "identify-stalled-projects": {
        "function": identify_stalled_projects_prompt,
        "description": "Generate prompt to find inactive projects",
        "category": "review",
        "tags": {"things3", "review", "projects", "maintenance"}
    },
    "review-overdue-items": {
        "function": review_overdue_items_prompt,
        "description": "Generate prompt for reviewing overdue tasks",
        "category": "review",
        "tags": {"things3", "review", "deadlines", "overdue"}
    },
    
    # Workflow Automation
    "batch-schedule-tasks": {
        "function": batch_schedule_tasks_prompt,
        "description": "Generate prompt for batch scheduling tasks",
        "category": "workflow",
        "tags": {"things3", "workflow", "automation", "batch"}
    },
    "organize-inbox": {
        "function": organize_inbox_prompt,
        "description": "Generate prompt for organizing inbox",
        "category": "workflow",
        "tags": {"things3", "workflow", "inbox", "organization"}
    },
    "suggest-next-actions": {
        "function": suggest_next_actions_prompt,
        "description": "Generate prompt for intelligent action suggestions",
        "category": "workflow",
        "tags": {"things3", "workflow", "productivity", "ai"}
    },
}


def register_all_prompts(mcp_instance: FastMCP) -> None:
    """
    Register all prompts with the FastMCP server.
    
    Args:
        mcp_instance: The FastMCP server instance
    """
    global mcp
    mcp = mcp_instance
    
    # Register each prompt using the decorator
    for prompt_name, prompt_info in PROMPT_REGISTRY.items():
        function = prompt_info["function"]
        description = prompt_info["description"]
        tags = prompt_info["tags"]
        
        # Apply the @mcp.prompt decorator dynamically
        decorated_function = mcp.prompt(
            name=prompt_name,
            description=description,
            tags=tags
        )(function)
        
        # Store the decorated function back
        PROMPT_REGISTRY[prompt_name]["decorated"] = decorated_function
