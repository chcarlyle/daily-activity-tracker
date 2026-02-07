"""
CRUD operations for daily metrics (mood, energy, notes).
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from models import DailyMetric


def save_daily_metric(session: Session, date: datetime.date, mood: int = None,
                     energy: int = None, notes: str = None) -> DailyMetric:
    """Create or update daily metrics"""
    metric = session.query(DailyMetric).filter_by(date=date).first()

    if metric:
        if mood is not None:
            metric.mood = mood
        if energy is not None:
            metric.energy = energy
        if notes is not None:
            metric.notes = notes
        metric.updated_at = datetime.utcnow()
    else:
        metric = DailyMetric(date=date, mood=mood, energy=energy, notes=notes)
        session.add(metric)

    session.commit()
    return metric


def get_daily_metric(session: Session, date: datetime.date) -> Optional[DailyMetric]:
    """Get metrics for a specific date"""
    return session.query(DailyMetric).filter_by(date=date).first()


def get_metrics_in_range(session: Session, start_date: datetime.date, end_date: datetime.date) -> List[DailyMetric]:
    """Get metrics within a date range"""
    return session.query(DailyMetric).filter(
        DailyMetric.date >= start_date,
        DailyMetric.date <= end_date
    ).order_by(DailyMetric.date).all()
