"""
CRUD operations for daily tasks.
"""
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from models import DailyTask


def save_daily_task(session: Session, date: datetime.date, task_name: str,
                    points: float, trackable: bool = False, unit: str = None,
                    quantity: float = 1.0, completed: bool = False) -> DailyTask:
    """Create or update a daily task"""
    task = session.query(DailyTask).filter_by(date=date, task_name=task_name).first()

    if task:
        # Update existing task
        task.points = points
        task.trackable = trackable
        task.unit = unit
        task.quantity = quantity
        task.completed = completed
        if completed and not task.completed_at:
            task.completed_at = datetime.utcnow()
    else:
        # Create new task
        task = DailyTask(
            date=date,
            task_name=task_name,
            points=points,
            trackable=trackable,
            unit=unit,
            quantity=quantity,
            completed=completed,
            completed_at=datetime.utcnow() if completed else None
        )
        session.add(task)

    session.commit()
    return task


def get_daily_tasks(session: Session, date: datetime.date) -> List[DailyTask]:
    """Get all tasks for a specific date"""
    return session.query(DailyTask).filter_by(date=date).all()


def update_task_completion(session: Session, date: datetime.date, task_name: str,
                          completed: bool, quantity: float = None) -> bool:
    """Update task completion status and quantity"""
    task = session.query(DailyTask).filter_by(date=date, task_name=task_name).first()

    if task:
        task.completed = completed
        if quantity is not None:
            task.quantity = quantity
        if completed and not task.completed_at:
            task.completed_at = datetime.utcnow()
        elif not completed:
            task.completed_at = None
        session.commit()
        return True
    return False


def delete_daily_task(session: Session, date: datetime.date, task_name: str) -> bool:
    """Delete a daily task"""
    task = session.query(DailyTask).filter_by(date=date, task_name=task_name).first()

    if task:
        session.delete(task)
        session.commit()
        return True
    return False


def get_tasks_in_range(session: Session, start_date: datetime.date, end_date: datetime.date) -> List[DailyTask]:
    """Get all tasks within a date range"""
    return session.query(DailyTask).filter(
        DailyTask.date >= start_date,
        DailyTask.date <= end_date
    ).order_by(DailyTask.date.desc()).all()
