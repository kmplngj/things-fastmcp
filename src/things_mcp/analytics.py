"""
Analytics and intelligence layer for Things MCP server.
Provides productivity insights, project health monitoring, and tag analysis.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import re

from .logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class ProductivityStats:
    """Overall productivity metrics for a time period."""
    period_days: int
    completed_count: int
    incomplete_count: int
    completion_rate: float  # 0-1
    avg_completion_hours: float
    overdue_count: int
    trend: str  # "improving", "declining", "stable"
    top_productive_tags: List[Tuple[str, int]]  # (tag, completed_count)


@dataclass
class VelocityPeriod:
    """Completion data for a single time period."""
    period_start: str  # ISO date
    period_end: str
    completed_count: int
    created_count: int


@dataclass
class ProjectVelocity:
    """Project velocity (completion rate over time)."""
    project_uuid: str
    project_title: str
    interval: str  # daily, weekly, monthly
    periods: List[VelocityPeriod]
    avg_velocity: float  # tasks/period
    trend: str  # "accelerating", "decelerating", "stable"


@dataclass
class CompletionTimeStats:
    """Time-to-completion statistics for a group."""
    group_name: str  # "overall", or specific tag/project/area
    count: int
    avg_hours: float
    median_hours: float
    p90_hours: float
    min_hours: float
    max_hours: float


@dataclass
class TagProductivityMetric:
    """Productivity metrics for a specific tag."""
    tag_name: str
    total_tasks: int
    completed_tasks: int
    completion_rate: float  # 0-1
    avg_completion_hours: float


@dataclass
class StalledProject:
    """Project with no recent activity."""
    uuid: str
    title: str
    last_activity_date: str  # ISO date
    days_inactive: int
    incomplete_count: int
    notes: Optional[str]


@dataclass
class ProjectHealth:
    """Comprehensive project health metrics."""
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


@dataclass
class TagRelationship:
    """Co-occurrence relationship between two tags."""
    tag1: str
    tag2: str
    co_occurrence_count: int
    tag1_total: int
    tag2_total: int
    strength: float  # 0-1, how often they appear together


@dataclass
class TagSuggestion:
    """Suggested tag with confidence score."""
    tag_name: str
    confidence: float  # 0-1
    matching_keywords: List[str]
    example_tasks: List[str]  # Similar task titles


# ============================================================================
# Productivity Analytics Functions
# ============================================================================

def calculate_productivity_stats(
    days: int = 30,
    logbook_items: Optional[List[Dict]] = None,
    incomplete_items: Optional[List[Dict]] = None
) -> ProductivityStats:
    """
    Calculate overall productivity statistics.
    
    Args:
        days: Number of days to analyze
        logbook_items: Completed items (fetched externally for progress reporting)
        incomplete_items: Incomplete items (fetched externally)
        
    Returns:
        ProductivityStats dataclass
    """
    logger.info(f"Calculating productivity stats for {days} days")
    
    # Filter logbook to date range
    cutoff_date = datetime.now() - timedelta(days=days)
    completed_in_period = [
        item for item in (logbook_items or [])
        if item.get('stop_date') and 
        datetime.fromisoformat(item['stop_date']) >= cutoff_date
    ]
    
    completed_count = len(completed_in_period)
    incomplete = incomplete_items or []
    incomplete_count = len(incomplete)
    total = completed_count + incomplete_count
    
    completion_rate = completed_count / total if total > 0 else 0.0
    
    # Calculate average completion time
    completion_times = []
    for item in completed_in_period:
        if item.get('created') and item.get('stop_date'):
            created = datetime.fromisoformat(item['created'])
            stopped = datetime.fromisoformat(item['stop_date'])
            hours = (stopped - created).total_seconds() / 3600
            completion_times.append(hours)
    
    avg_completion_hours = sum(completion_times) / len(completion_times) if completion_times else 0.0
    
    # Count overdue items
    today = datetime.now().date()
    overdue_count = sum(
        1 for item in incomplete
        if item.get('deadline') and 
        datetime.fromisoformat(item['deadline']).date() < today
    )
    
    # Calculate trend (compare to previous period)
    previous_cutoff = cutoff_date - timedelta(days=days)
    completed_previous = [
        item for item in (logbook_items or [])
        if item.get('stop_date') and
        previous_cutoff <= datetime.fromisoformat(item['stop_date']) < cutoff_date
    ]
    
    prev_count = len(completed_previous)
    if prev_count == 0:
        trend = "stable"
    else:
        change = (completed_count - prev_count) / prev_count
        if change > 0.1:
            trend = "improving"
        elif change < -0.1:
            trend = "declining"
        else:
            trend = "stable"
    
    # Top productive tags
    tag_counts: Dict[str, int] = defaultdict(int)
    for item in completed_in_period:
        for tag in item.get('tags', []):
            tag_counts[tag] += 1
    
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return ProductivityStats(
        period_days=days,
        completed_count=completed_count,
        incomplete_count=incomplete_count,
        completion_rate=completion_rate,
        avg_completion_hours=avg_completion_hours,
        overdue_count=overdue_count,
        trend=trend,
        top_productive_tags=top_tags
    )


def calculate_project_velocity(
    project: Dict,
    interval: str = "weekly",
    periods: int = 4
) -> ProjectVelocity:
    """
    Calculate project velocity (completion rate over time).
    
    Args:
        project: Project dict with items (include_items=True)
        interval: Time interval (daily, weekly, monthly)
        periods: Number of periods to analyze
        
    Returns:
        ProjectVelocity dataclass
    """
    logger.info(f"Calculating velocity for project {project.get('title')} ({interval})")
    
    # Determine period length
    if interval == "daily":
        period_delta = timedelta(days=1)
    elif interval == "weekly":
        period_delta = timedelta(weeks=1)
    else:  # monthly
        period_delta = timedelta(days=30)
    
    # Build period ranges
    now = datetime.now()
    period_ranges = []
    for i in range(periods):
        end = now - (period_delta * i)
        start = end - period_delta
        period_ranges.append((start, end))
    
    period_ranges.reverse()  # Oldest first
    
    # Count completions and creations per period
    velocity_periods = []
    items = project.get('items', [])
    
    for start, end in period_ranges:
        completed = sum(
            1 for item in items
            if item.get('status') == 'completed' and
            item.get('stop_date') and
            start <= datetime.fromisoformat(item['stop_date']) < end
        )
        
        created = sum(
            1 for item in items
            if item.get('created') and
            start <= datetime.fromisoformat(item['created']) < end
        )
        
        velocity_periods.append(VelocityPeriod(
            period_start=start.date().isoformat(),
            period_end=end.date().isoformat(),
            completed_count=completed,
            created_count=created
        ))
    
    # Calculate average velocity and trend
    completion_counts = [p.completed_count for p in velocity_periods]
    avg_velocity = sum(completion_counts) / len(completion_counts) if completion_counts else 0.0
    
    # Determine trend (first half vs second half)
    if len(completion_counts) >= 2:
        mid = len(completion_counts) // 2
        first_half_avg = sum(completion_counts[:mid]) / mid
        second_half_avg = sum(completion_counts[mid:]) / (len(completion_counts) - mid)
        
        if second_half_avg > first_half_avg * 1.2:
            trend = "accelerating"
        elif second_half_avg < first_half_avg * 0.8:
            trend = "decelerating"
        else:
            trend = "stable"
    else:
        trend = "stable"
    
    return ProjectVelocity(
        project_uuid=project['uuid'],
        project_title=project['title'],
        interval=interval,
        periods=velocity_periods,
        avg_velocity=avg_velocity,
        trend=trend
    )


def calculate_time_to_completion(
    completed_items: List[Dict],
    group_by: str = "overall",
    limit: int = 100
) -> List[CompletionTimeStats]:
    """
    Calculate average time to completion statistics.
    
    Args:
        completed_items: List of completed todo items
        group_by: How to group (overall, tag, project, area)
        limit: Maximum number of items to analyze
        
    Returns:
        List of CompletionTimeStats for each group
    """
    logger.info(f"Calculating time to completion, group_by={group_by}, limit={limit}")
    
    # Limit items to analyze
    items_to_analyze = completed_items[:limit] if limit else completed_items
    
    # Calculate completion times in hours
    completion_times: Dict[str, List[float]] = defaultdict(list)
    
    for item in items_to_analyze:
        if not item.get('created') or not item.get('stop_date'):
            continue
        
        try:
            created = datetime.fromisoformat(item['created'])
            stopped = datetime.fromisoformat(item['stop_date'])
            hours = (stopped - created).total_seconds() / 3600
            
            if group_by == "overall":
                completion_times["overall"].append(hours)
            elif group_by == "tag":
                for tag in item.get('tags', []):
                    completion_times[tag].append(hours)
            elif group_by == "project":
                project_name = item.get('project', 'No Project')
                completion_times[project_name].append(hours)
            elif group_by == "area":
                area_name = item.get('area', 'No Area')
                completion_times[area_name].append(hours)
        except (ValueError, TypeError) as e:
            logger.debug(f"Skipping item with invalid dates: {e}")
            continue
    
    # Calculate statistics for each group
    results = []
    for group_name, times in completion_times.items():
        if not times:
            continue
        
        stats = calculate_statistics(times)
        results.append(CompletionTimeStats(
            group_name=group_name,
            count=len(times),
            avg_hours=stats['mean'],
            median_hours=stats['median'],
            p90_hours=stats['p90'],
            min_hours=stats['min'],
            max_hours=stats['max']
        ))
    
    # Sort by count (most tasks first)
    results.sort(key=lambda x: x.count, reverse=True)
    return results


def calculate_tag_productivity(
    all_items: List[Dict],
    min_tasks: int = 3
) -> List[TagProductivityMetric]:
    """
    Calculate productivity metrics for each tag.
    
    Analyzes completion rates, average time to completion, and task counts
    for each tag to identify most productive tags.
    
    Args:
        all_items: All items (completed + incomplete) to analyze
        min_tasks: Minimum tasks required for tag to be included (default: 3)
        
    Returns:
        List of TagProductivityMetric sorted by completion rate (descending)
    """
    logger.info(f"Calculating tag productivity, min_tasks={min_tasks}")
    
    try:
        # Group items by tag
        tag_data: Dict[str, Dict[str, Any]] = {}
        
        for item in all_items:
            tags = item.get('tags', [])
            if not tags:
                continue
                
            status = item.get('status')
            completed = status == 'completed'
            
            # Calculate completion time if available
            completion_hours = None
            if completed:
                created_str = item.get('creationDate')
                stopped_str = item.get('stopDate')
                if created_str and stopped_str:
                    try:
                        created = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                        stopped = datetime.fromisoformat(stopped_str.replace('Z', '+00:00'))
                        completion_hours = (stopped - created).total_seconds() / 3600
                    except (ValueError, AttributeError):
                        pass
            
            # Update stats for each tag
            for tag in tags:
                if tag not in tag_data:
                    tag_data[tag] = {
                        'total': 0,
                        'completed': 0,
                        'completion_times': []
                    }
                
                tag_data[tag]['total'] += 1
                if completed:
                    tag_data[tag]['completed'] += 1
                    if completion_hours is not None:
                        tag_data[tag]['completion_times'].append(completion_hours)
        
        # Calculate metrics for each tag
        metrics = []
        for tag_name, data in tag_data.items():
            total = data['total']
            
            # Skip tags with too few tasks
            if total < min_tasks:
                continue
            
            completed = data['completed']
            completion_rate = (completed / total * 100) if total > 0 else 0.0
            
            # Calculate average completion time
            times = data['completion_times']
            avg_completion_hours = sum(times) / len(times) if times else None
            
            metrics.append(TagProductivityMetric(
                tag_name=tag_name,
                total_tasks=total,
                completed_tasks=completed,
                completion_rate=completion_rate / 100,  # Convert to 0-1 range
                avg_completion_hours=avg_completion_hours if avg_completion_hours is not None else 0.0
            ))
        
        # Sort by completion rate (descending), then by total count
        metrics.sort(key=lambda x: (x.completion_rate, x.total_tasks), reverse=True)
        
        logger.info(f"Calculated productivity for {len(metrics)} tags")
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating tag productivity: {e}", exc_info=True)
        return []


def calculate_stalled_projects(
    projects: List[Dict],
    min_inactive_days: int = 14
) -> List[StalledProject]:
    """
    Identify projects with no recent activity.
    
    Analyzes all projects to find those with no modifications or completions
    in the specified time period.
    
    Args:
        projects: List of project dictionaries to analyze
        min_inactive_days: Minimum days of inactivity to be considered stalled (default: 14)
        
    Returns:
        List of StalledProject sorted by days inactive (descending)
    """
    logger.info(f"Calculating stalled projects, min_inactive_days={min_inactive_days}")
    
    try:
        today = datetime.now().date()
        stalled = []
        
        for project in projects:
            # Skip completed or canceled projects
            status = project.get('status')
            if status in ['completed', 'canceled']:
                continue
            
            # Get last activity date (most recent of modified or stop date)
            modified_str = project.get('userModificationDate')
            stopped_str = project.get('stopDate')
            
            last_activity = None
            try:
                if modified_str:
                    modified = datetime.fromisoformat(modified_str.replace('Z', '+00:00')).date()
                    last_activity = modified
                
                if stopped_str:
                    stopped = datetime.fromisoformat(stopped_str.replace('Z', '+00:00')).date()
                    if last_activity is None or stopped > last_activity:
                        last_activity = stopped
                
                # If no dates available, use creation date
                if last_activity is None:
                    created_str = project.get('creationDate')
                    if created_str:
                        last_activity = datetime.fromisoformat(created_str.replace('Z', '+00:00')).date()
            except (ValueError, AttributeError):
                continue
            
            if last_activity is None:
                continue
            
            # Calculate days inactive
            days_inactive = (today - last_activity).days
            
            # Only include if meets threshold
            if days_inactive < min_inactive_days:
                continue
            
            # Count incomplete items in project
            items = project.get('items', [])
            incomplete_count = sum(1 for item in items if item.get('status') not in ['completed', 'canceled'])
            
            stalled.append(StalledProject(
                uuid=project.get('uuid', ''),
                title=project.get('title', 'Untitled'),
                last_activity_date=last_activity.isoformat(),
                days_inactive=days_inactive,
                incomplete_count=incomplete_count,
                notes=project.get('notes')
            ))
        
        # Sort by days inactive (most stalled first)
        stalled.sort(key=lambda x: x.days_inactive, reverse=True)
        
        logger.info(f"Found {len(stalled)} stalled projects")
        return stalled
        
    except Exception as e:
        logger.error(f"Error calculating stalled projects: {e}", exc_info=True)
        return []


def calculate_project_health(projects: List[Dict]) -> List[ProjectHealth]:
    """
    Calculate comprehensive health metrics for all projects.
    
    Analyzes completion rates, velocity, inactivity, overdue tasks,
    and scope creep to generate health scores and recommendations.
    
    Args:
        projects: List of project dictionaries with items
        
    Returns:
        List of ProjectHealth sorted by health score (ascending - worst first)
    """
    logger.info(f"Calculating project health for {len(projects)} projects")
    
    try:
        today = datetime.now().date()
        health_reports = []
        
        for project in projects:
            # Skip completed or canceled projects
            status = project.get('status')
            if status in ['completed', 'canceled']:
                continue
            
            uuid = project.get('uuid', '')
            title = project.get('title', 'Untitled')
            items = project.get('items', [])
            
            # Calculate basic metrics
            total_tasks = len([i for i in items if i.get('type') == 'to-do'])
            completed_tasks = len([i for i in items if i.get('type') == 'to-do' and i.get('status') == 'completed'])
            incomplete_tasks = total_tasks - completed_tasks
            
            completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0.0
            
            # Calculate velocity (tasks/week) - look at last 30 days
            thirty_days_ago = today - timedelta(days=30)
            recent_completions = 0
            
            for item in items:
                if item.get('status') == 'completed':
                    stopped_str = item.get('stopDate')
                    if stopped_str:
                        try:
                            stopped = datetime.fromisoformat(stopped_str.replace('Z', '+00:00')).date()
                            if stopped >= thirty_days_ago:
                                recent_completions += 1
                        except (ValueError, AttributeError):
                            pass
            
            velocity = (recent_completions / 30) * 7  # Convert to tasks/week
            
            # Calculate days inactive
            modified_str = project.get('userModificationDate')
            last_activity = None
            if modified_str:
                try:
                    last_activity = datetime.fromisoformat(modified_str.replace('Z', '+00:00')).date()
                except (ValueError, AttributeError):
                    pass
            
            if last_activity is None:
                created_str = project.get('creationDate')
                if created_str:
                    try:
                        last_activity = datetime.fromisoformat(created_str.replace('Z', '+00:00')).date()
                    except (ValueError, AttributeError):
                        pass
            
            days_inactive = (today - last_activity).days if last_activity else 0
            
            # Count overdue tasks
            overdue_count = 0
            for item in items:
                if item.get('status') not in ['completed', 'canceled']:
                    deadline_str = item.get('deadline')
                    if deadline_str:
                        try:
                            deadline = datetime.fromisoformat(deadline_str.replace('Z', '+00:00')).date()
                            if deadline < today:
                                overdue_count += 1
                        except (ValueError, AttributeError):
                            pass
            
            # Calculate scope creep (added vs completed ratio in last 30 days)
            added_count = 0
            for item in items:
                created_str = item.get('creationDate')
                if created_str:
                    try:
                        created = datetime.fromisoformat(created_str.replace('Z', '+00:00')).date()
                        if created >= thirty_days_ago:
                            added_count += 1
                    except (ValueError, AttributeError):
                        pass
            
            scope_creep_ratio = added_count / recent_completions if recent_completions > 0 else 1.0
            
            # Calculate health score
            health_score = calculate_health_score(
                completion_rate=completion_rate,
                days_inactive=days_inactive,
                overdue_count=overdue_count,
                scope_creep_ratio=scope_creep_ratio
            )
            
            # Generate recommendations
            recommendations = []
            if health_score < 50:
                recommendations.append("⚠️ Project needs immediate attention")
            if overdue_count > 0:
                recommendations.append(f"Address {overdue_count} overdue task(s)")
            if days_inactive > 14:
                recommendations.append(f"No activity for {days_inactive} days - review or archive")
            if velocity < 0.5 and incomplete_tasks > 5:
                recommendations.append("Low velocity - consider breaking down tasks")
            if scope_creep_ratio > 1.5:
                recommendations.append("Scope creep detected - focus on completion")
            if completion_rate > 0.8 and incomplete_tasks < 3:
                recommendations.append("✅ Nearly done! Push to completion")
            
            # Estimate completion date (if velocity > 0)
            estimated_completion = None
            if velocity > 0 and incomplete_tasks > 0:
                weeks_remaining = incomplete_tasks / velocity
                estimated_date = today + timedelta(weeks=weeks_remaining)
                estimated_completion = estimated_date.isoformat()
            
            health_reports.append(ProjectHealth(
                project_uuid=uuid,
                project_title=title,
                health_score=health_score,
                completion_rate=completion_rate,
                velocity=velocity,
                days_inactive=days_inactive,
                overdue_count=overdue_count,
                scope_creep_ratio=scope_creep_ratio,
                estimated_completion_date=estimated_completion,
                recommendations=recommendations
            ))
        
        # Sort by health score (worst first)
        health_reports.sort(key=lambda x: x.health_score)
        
        logger.info(f"Calculated health for {len(health_reports)} active projects")
        return health_reports
        
    except Exception as e:
        logger.error(f"Error calculating project health: {e}", exc_info=True)
        return []


def calculate_tag_relationships(
    logbook_items: List[Dict],
    incomplete_items: List[Dict],
    min_cooccurrence: int = 3
) -> List[TagRelationship]:
    """
    Calculate tag co-occurrence relationships.
    
    Analyzes which tags frequently appear together on the same items
    to discover implicit connections between different work areas.
    
    Args:
        logbook_items: Completed items from database
        incomplete_items: Incomplete items from database
        min_cooccurrence: Minimum number of times tags must appear together
        
    Returns:
        List of TagRelationship objects sorted by co-occurrence count (descending)
        
    Example:
        relationships = calculate_tag_relationships(
            logbook_items=logbook,
            incomplete_items=incomplete,
            min_cooccurrence=5
        )
        # Returns: [
        #   TagRelationship(tag1='work', tag2='urgent', co_occurrence_count=15, confidence=0.75),
        #   TagRelationship(tag1='personal', tag2='shopping', co_occurrence_count=8, confidence=0.62),
        #   ...
        # ]
    """
    logger.info(f"Calculating tag relationships from {len(logbook_items)} completed + {len(incomplete_items)} incomplete items")
    
    try:
        # Combine all items for analysis
        all_items = logbook_items + incomplete_items
        
        # Build co-occurrence matrix
        cooccurrence, tag_counts = build_cooccurrence_matrix(all_items)
        
        # Convert to TagRelationship objects
        relationships = []
        for (tag1, tag2), count in cooccurrence.items():
            if count < min_cooccurrence:
                continue
            
            # Get individual tag counts
            count1 = tag_counts.get(tag1, 0)
            count2 = tag_counts.get(tag2, 0)
            
            # Calculate strength (Jaccard similarity: intersection / union)
            union = count1 + count2 - count
            strength = count / union if union > 0 else 0.0
            
            relationships.append(TagRelationship(
                tag1=tag1,
                tag2=tag2,
                co_occurrence_count=count,
                tag1_total=count1,
                tag2_total=count2,
                strength=round(strength, 2)
            ))
        
        # Sort by co-occurrence count (descending)
        relationships.sort(key=lambda x: x.co_occurrence_count, reverse=True)
        
        logger.info(f"Found {len(relationships)} tag relationships (min co-occurrence: {min_cooccurrence})")
        
        return relationships
    
    except Exception as e:
        logger.error(f"Error calculating tag relationships: {e}", exc_info=True)
        return []


def calculate_tag_suggestions(
    item_title: str,
    item_notes: str,
    existing_tags: List[str],
    logbook_items: List[Dict],
    incomplete_items: List[Dict],
    max_suggestions: int = 5
) -> List[TagSuggestion]:
    """
    Suggest tags for an item based on title/notes and tag relationships.
    
    Uses keyword extraction and co-occurrence analysis to recommend
    relevant tags the user might want to apply.
    
    Args:
        item_title: Title of the item
        item_notes: Notes/description of the item (optional)
        existing_tags: Tags already on the item (to avoid suggesting duplicates)
        logbook_items: Completed items for analysis
        incomplete_items: Incomplete items for analysis
        max_suggestions: Maximum number of suggestions (default: 5)
        
    Returns:
        List of TagSuggestion objects sorted by confidence (descending)
        
    Example:
        suggestions = calculate_tag_suggestions(
            item_title="Buy groceries",
            item_notes="milk, eggs, bread",
            existing_tags=[],
            logbook_items=logbook,
            incomplete_items=incomplete,
            max_suggestions=3
        )
        # Returns: [
        #   TagSuggestion(tag_name='shopping', confidence=0.85, matching_keywords=['buy', 'groceries'], example_tasks=['Buy shoes', 'Buy gifts']),
        #   TagSuggestion(tag_name='personal', confidence=0.62, matching_keywords=['buy'], example_tasks=['Buy birthday gift']),
        #   ...
        # ]
    """
    logger.info(f"Calculating tag suggestions for: '{item_title}'")
    
    try:
        # Extract keywords from title and notes
        text = f"{item_title} {item_notes}".strip()
        keywords = extract_keywords(text, min_length=3)
        
        if not keywords:
            logger.info("No keywords extracted, returning empty suggestions")
            return []
        
        logger.info(f"Extracted {len(keywords)} keywords: {keywords}")
        
        # Get all unique tags from database
        all_items = logbook_items + incomplete_items
        all_tags = set()
        for item in all_items:
            all_tags.update(item.get('tags', []))
        
        # Remove existing tags from candidates
        candidate_tags = all_tags - set(existing_tags)
        
        if not candidate_tags:
            logger.info("No candidate tags available")
            return []
        
        # Calculate tag relationships for context
        relationships = calculate_tag_relationships(
            logbook_items=logbook_items,
            incomplete_items=incomplete_items,
            min_cooccurrence=2
        )
        
        # Build relationship map for existing tags
        relationship_map: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        for rel in relationships:
            relationship_map[rel.tag1].append((rel.tag2, rel.strength))
            relationship_map[rel.tag2].append((rel.tag1, rel.strength))
        
        # Score each candidate tag
        suggestions: List[Tuple[str, float, List[str]]] = []
        for tag in candidate_tags:
            score = 0.0
            matching_keywords = []
            
            # 1. Keyword matching (substring match)
            tag_lower = tag.lower()
            for keyword in keywords:
                if keyword in tag_lower or tag_lower in keyword:
                    score += 0.4
                    matching_keywords.append(keyword)
            
            # 2. Relationship bonus (if related to existing tags)
            for existing_tag in existing_tags:
                for related_tag, strength in relationship_map.get(existing_tag, []):
                    if related_tag == tag:
                        score += strength * 0.6
            
            # Only include if there's some match
            if score > 0:
                suggestions.append((tag, score, matching_keywords))
        
        # Sort by score (descending) and limit
        suggestions.sort(key=lambda x: x[1], reverse=True)
        suggestions = suggestions[:max_suggestions]
        
        # Find example tasks for each suggestion
        results = []
        for tag_name, confidence, keywords_matched in suggestions:
            # Find 3 example tasks with this tag
            example_tasks = []
            for item in all_items:
                if tag_name in item.get('tags', []):
                    example_tasks.append(item.get('title', ''))
                    if len(example_tasks) >= 3:
                        break
            
            results.append(TagSuggestion(
                tag_name=tag_name,
                confidence=min(confidence, 1.0),  # Cap at 1.0
                matching_keywords=keywords_matched,
                example_tasks=example_tasks
            ))
        
        logger.info(f"Generated {len(results)} tag suggestions")
        
        return results
    
    except Exception as e:
        logger.error(f"Error calculating tag suggestions: {e}", exc_info=True)
        return []


# ============================================================================
# Helper Functions
# ============================================================================

def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """
    Extract keywords from text for tag suggestion.
    
    Args:
        text: Input text (title + notes)
        min_length: Minimum keyword length
        
    Returns:
        List of lowercase keywords
    """
    # Remove punctuation and split
    text = text.lower()
    words = re.findall(r'\b[a-z]+\b', text)
    
    # Filter common words and short words
    common_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
        'this', 'that', 'these', 'those', 'my', 'your', 'his', 'her', 'its'
    }
    
    keywords = [
        word for word in words
        if len(word) >= min_length and word not in common_words
    ]
    
    return keywords


def build_cooccurrence_matrix(
    tasks: List[Dict]
) -> Tuple[Dict[Tuple[str, str], int], Dict[str, int]]:
    """
    Build tag co-occurrence matrix.
    
    Args:
        tasks: List of task dicts with 'tags' field
        
    Returns:
        Tuple of (co_occurrence_dict, tag_counts_dict)
    """
    logger.info(f"Building co-occurrence matrix from {len(tasks)} tasks")
    
    cooccurrence: Dict[Tuple[str, str], int] = defaultdict(int)
    tag_counts: Dict[str, int] = defaultdict(int)
    
    for task in tasks:
        tags = task.get('tags', [])
        
        # Count individual tags
        for tag in tags:
            tag_counts[tag] += 1
        
        # Count co-occurrences (pairs)
        for i, tag1 in enumerate(tags):
            for tag2 in tags[i+1:]:
                # Always store in alphabetical order for consistency
                pair = tuple(sorted([tag1, tag2]))
                cooccurrence[pair] += 1
    
    return dict(cooccurrence), dict(tag_counts)


def generate_ascii_chart(
    values: List[int],
    labels: List[str],
    max_width: int = 40
) -> str:
    """
    Generate ASCII bar chart.
    
    Args:
        values: List of values to chart
        labels: List of labels for each value
        max_width: Maximum bar width in characters
        
    Returns:
        Formatted ASCII chart string
    """
    if not values:
        return "(No data)"
    
    max_val = max(values)
    if max_val == 0:
        max_val = 1  # Avoid division by zero
    
    lines = []
    for label, value in zip(labels, values):
        bar_width = int((value / max_val) * max_width)
        bar = "█" * bar_width + "░" * (max_width - bar_width)
        lines.append(f"{label}: {bar} {value}")
    
    return "\n".join(lines)


def calculate_health_score(
    completion_rate: float,
    days_inactive: int,
    overdue_count: int,
    scope_creep_ratio: float
) -> int:
    """
    Calculate project health score (0-100).
    
    Args:
        completion_rate: 0-1
        days_inactive: Days since last activity
        overdue_count: Number of overdue tasks
        scope_creep_ratio: New tasks / completed tasks ratio
        
    Returns:
        Health score (0-100)
    """
    score = 100.0
    
    # Deduct for overdue tasks (max -30)
    score -= min(overdue_count * 5, 30)
    
    # Deduct for inactivity (max -20)
    if days_inactive > 14:
        score -= min((days_inactive - 14) * 2, 20)
    
    # Bonus for high completion rate
    if completion_rate > 0.75:
        score += 10
    
    # Deduct for scope creep
    if scope_creep_ratio > 1.5:  # Adding much faster than completing
        score -= 15
    
    return max(0, min(100, int(score)))


def calculate_statistics(values: List[float]) -> Dict[str, float]:
    """
    Calculate statistical metrics for a list of values.
    
    Args:
        values: List of numeric values
        
    Returns:
        Dict with mean, median, p90, min, max
    """
    if not values:
        return {
            'mean': 0.0,
            'median': 0.0,
            'p90': 0.0,
            'min': 0.0,
            'max': 0.0
        }
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    
    return {
        'mean': sum(values) / n,
        'median': sorted_values[n // 2] if n % 2 == 1 else (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2,
        'p90': sorted_values[int(n * 0.9)] if n > 0 else 0.0,
        'min': min(values),
        'max': max(values)
    }
