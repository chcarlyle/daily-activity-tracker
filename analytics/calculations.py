"""
Analytics and calculation functions for LifeTracker.
Handles point calculations, streaks, consistency metrics, and task analysis.
"""
from datetime import datetime, timedelta
from typing import List, Tuple, Union
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from models import DailyTask


def get_day_points(session: Session, date: datetime.date, separate: bool = False) -> Union[float, Tuple[float, float]]:
    """
    Calculate points for a day from database, optionally separating positive and negative.

    Args:
        session: Database session
        date: Date to calculate points for
        separate: If True, return (positive, negative) tuple; if False, return net total

    Returns:
        Net points (float) or tuple of (positive_points, negative_points)
    """
    tasks = session.query(DailyTask).filter_by(date=date, completed=True).all()

    positive = 0.0
    negative = 0.0

    for task in tasks:
        points = task.points
        if task.trackable:
            points = points * task.quantity

        if points > 0:
            positive += points
        else:
            negative += points

    if separate:
        return (positive, negative)
    return positive + negative


def get_task_streak(session: Session, task_name: str, end_date: datetime.date, days_back: int = 90) -> Tuple[int, int]:
    """
    Calculate current streak and longest streak for a specific task.

    Args:
        session: Database session
        task_name: Name of task to analyze
        end_date: End date for analysis
        days_back: Number of days to look back

    Returns:
        Tuple of (current_streak, longest_streak)
    """
    start_date = end_date - timedelta(days=days_back)

    # Get all tasks with this name in the date range
    tasks = session.query(DailyTask).filter(
        DailyTask.task_name == task_name,
        DailyTask.date >= start_date,
        DailyTask.date <= end_date
    ).order_by(DailyTask.date.desc()).all()

    # Create a lookup dict by date
    task_by_date = {task.date: task for task in tasks}

    current_streak = 0
    longest_streak = 0
    temp_streak = 0

    # Calculate current streak (from end_date backwards)
    for i in range(days_back):
        check_date = end_date - timedelta(days=i)
        task = task_by_date.get(check_date)

        if task:
            if task.completed:
                if i == current_streak:  # Consecutive from end
                    current_streak += 1
                temp_streak += 1
                if temp_streak > longest_streak:
                    longest_streak = temp_streak
            else:
                temp_streak = 0
                if i < current_streak:  # Break in current streak
                    break
        else:
            # No task on this day - doesn't break streak if task wasn't scheduled
            pass

    return current_streak, longest_streak


def get_positive_day_streak(session: Session, end_date: datetime.date, days_back: int = 90) -> int:
    """
    Calculate current streak of positive net point days.

    Args:
        session: Database session
        end_date: End date for analysis
        days_back: Number of days to look back

    Returns:
        Current streak of consecutive positive days
    """
    current_streak = 0

    for i in range(days_back):
        check_date = end_date - timedelta(days=i)
        net_points = get_day_points(session, check_date)

        # Check if there are any tasks for this day
        has_tasks = session.query(DailyTask).filter_by(date=check_date).count() > 0

        if net_points > 0:
            current_streak += 1
        elif has_tasks:
            # Day exists with tasks but wasn't positive - break streak
            break

    return current_streak


def get_task_consistency(session: Session, task_name: str, end_date: datetime.date, days_back: int = 30) -> float:
    """
    Calculate consistency percentage for a task over a period.

    Args:
        session: Database session
        task_name: Name of task to analyze
        end_date: End date for analysis
        days_back: Number of days to look back

    Returns:
        Consistency percentage (0-100)
    """
    start_date = end_date - timedelta(days=days_back)

    # Get all instances of this task in the period
    tasks = session.query(DailyTask).filter(
        DailyTask.task_name == task_name,
        DailyTask.date >= start_date,
        DailyTask.date <= end_date
    ).all()

    if not tasks:
        return 0.0

    days_with_task = len(tasks)
    days_completed = sum(1 for task in tasks if task.completed)

    return (days_completed / days_with_task) * 100 if days_with_task > 0 else 0.0


def get_all_unique_tasks(session: Session, days_back: int = 30) -> List[str]:
    """
    Get all unique task names from recent history.

    Args:
        session: Database session
        days_back: Number of days to look back

    Returns:
        Sorted list of unique task names
    """
    end_date = datetime.now(ZoneInfo("America/New_York")).date()
    start_date = end_date - timedelta(days=days_back)

    result = session.query(DailyTask.task_name).filter(
        DailyTask.date >= start_date,
        DailyTask.date <= end_date
    ).distinct().all()

    return sorted([r[0] for r in result])
