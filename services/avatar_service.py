"""
Avatar alignment analysis service for LifeTracker.
Prepares data and generates prompts for LLM-based avatar alignment analysis.
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session

from database.tasks import get_tasks_in_range
from database.metrics import get_metrics_in_range
from analytics.calculations import (
    get_day_points,
    get_positive_day_streak,
    get_all_unique_tasks,
    get_task_consistency
)


def prepare_avatar_analysis_data(session: Session, start_date: datetime.date, end_date: datetime.date) -> Dict[str, Any]:
    """
    Format tracking data for LLM avatar alignment analysis.

    Args:
        session: Database session
        start_date: Start of analysis period
        end_date: End of analysis period

    Returns:
        Dictionary with structured analysis data including task patterns,
        wellbeing metrics, and challenges
    """
    # Get all tasks in the period
    tasks = get_tasks_in_range(session, start_date, end_date)
    metrics = get_metrics_in_range(session, start_date, end_date)

    # Calculate task patterns
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.completed)
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Task name breakdown - analyze individual task patterns
    task_breakdown = {}
    for task in tasks:
        task_name = task.task_name
        if task_name not in task_breakdown:
            task_breakdown[task_name] = {
                "total_instances": 0,
                "completed_instances": 0,
                "total_points": 0.0
            }

        task_breakdown[task_name]["total_instances"] += 1
        if task.completed:
            task_breakdown[task_name]["completed_instances"] += 1
            task_breakdown[task_name]["total_points"] += task.points * task.quantity

    # Get top tasks by points and consistency
    top_tasks_by_points = sorted(
        [(name, data["total_points"]) for name, data in task_breakdown.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]

    top_tasks_by_consistency = sorted(
        [(name, data["completed_instances"] / data["total_instances"] * 100)
         for name, data in task_breakdown.items() if data["total_instances"] > 0],
        key=lambda x: x[1],
        reverse=True
    )[:10]

    # Streaks
    current_positive_days = get_positive_day_streak(session, end_date)

    # Get top habits (tasks with highest completion rate)
    unique_tasks = get_all_unique_tasks(session, (end_date - start_date).days)
    task_consistencies = [
        (task_name, get_task_consistency(session, task_name, end_date, (end_date - start_date).days))
        for task_name in unique_tasks
    ]
    task_consistencies.sort(key=lambda x: x[1], reverse=True)
    top_habits = [name for name, _ in task_consistencies[:5] if _ > 50]

    # Mood and energy
    mood_values = [m.mood for m in metrics if m.mood is not None]
    energy_values = [m.energy for m in metrics if m.energy is not None]

    avg_mood = sum(mood_values) / len(mood_values) if mood_values else None
    avg_energy = sum(energy_values) / len(energy_values) if energy_values else None

    # Negative habits
    negative_tasks = [t for t in tasks if t.completed and t.points < 0]
    negative_point_sources = {}
    for task in negative_tasks:
        points = task.points * task.quantity
        if task.task_name in negative_point_sources:
            negative_point_sources[task.task_name] += points
        else:
            negative_point_sources[task.task_name] = points

    negative_list = [f"{name}: {pts:+.1f}pts" for name, pts in sorted(negative_point_sources.items(), key=lambda x: x[1])]

    # Days with negative net points
    days_with_negative_net = 0
    current_day = start_date
    while current_day <= end_date:
        if get_day_points(session, current_day) < 0:
            days_with_negative_net += 1
        current_day += timedelta(days=1)

    return {
        "task_patterns": {
            "total_tasks": total_tasks,
            "completion_rate": completion_rate,
            "top_tasks_by_points": top_tasks_by_points,
            "top_tasks_by_consistency": top_tasks_by_consistency,
            "task_breakdown": task_breakdown,
            "streaks": {
                "current_positive_days": current_positive_days,
                "top_habits": top_habits
            }
        },
        "wellbeing": {
            "avg_mood": avg_mood,
            "avg_energy": avg_energy
        },
        "challenges": {
            "negative_point_sources": negative_list,
            "days_with_negative_net": days_with_negative_net
        }
    }


def generate_avatar_prompt(avatar_description: str, analysis_data: dict) -> str:
    """
    Generate prompt for Claude API to analyze avatar alignment.

    Args:
        avatar_description: Description of the user's ideal self/avatar
        analysis_data: Structured analysis data from prepare_avatar_analysis_data()

    Returns:
        Formatted prompt string for LLM analysis
    """
    return f"""You are analyzing whether a user's behavior aligns with their ideal self.

Avatar (Ideal Self):
{avatar_description}

Behavior Data (Last 30 days):
{json.dumps(analysis_data, indent=2)}

Analyze the behavior data and determine how well it aligns with the avatar description. Return ONLY valid JSON with this exact structure (no markdown, no code blocks):
{{
  "alignment_score": <number 0-100>,
  "summary": "<2-3 sentences on overall alignment>",
  "recommendations": ["<specific action 1>", "<specific action 2>", "<specific action 3>"],
  "trend": "<improving|declining|stable>",
  "key_strengths": ["<strength 1>", "<strength 2>"],
  "areas_for_growth": ["<area 1>", "<area 2>"]
}}"""
