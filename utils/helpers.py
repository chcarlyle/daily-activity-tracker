"""
Helper utility functions for LifeTracker.
"""
from datetime import timedelta


def get_week_start(date):
    """Get the start of the week (Monday) for a given date."""
    return date - timedelta(days=date.weekday())
