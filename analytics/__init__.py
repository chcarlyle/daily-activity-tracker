"""
Analytics module for LifeTracker.
"""
from analytics.calculations import (
    get_day_points,
    get_task_streak,
    get_positive_day_streak,
    get_task_consistency,
    get_all_unique_tasks,
)

__all__ = [
    "get_day_points",
    "get_task_streak",
    "get_positive_day_streak",
    "get_task_consistency",
    "get_all_unique_tasks",
]
