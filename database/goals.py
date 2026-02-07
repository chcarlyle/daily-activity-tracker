"""
CRUD operations for user goals.
"""
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from models import Goal


def save_goal(session: Session, name: str, goal_type: str, target_points: float,
             description: str = None, created_date: datetime.date = None) -> Goal:
    """Create a new goal"""
    if created_date is None:
        created_date = datetime.now(ZoneInfo("America/New_York")).date()

    goal = Goal(
        name=name,
        goal_type=goal_type,
        target_points=target_points,
        description=description,
        created_date=created_date
    )
    session.add(goal)
    session.commit()
    return goal


def get_goals_by_type(session: Session, goal_type: str) -> List[Goal]:
    """Get all goals of a specific type"""
    return session.query(Goal).filter_by(goal_type=goal_type, completed=False).all()


def delete_goal(session: Session, goal_id: int) -> bool:
    """Delete a goal"""
    goal = session.query(Goal).filter_by(id=goal_id).first()

    if goal:
        session.delete(goal)
        session.commit()
        return True
    return False
