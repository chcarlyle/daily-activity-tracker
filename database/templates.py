"""
CRUD operations for task templates.
"""
from typing import List, Dict
from sqlalchemy.orm import Session

from models import TaskTemplate


def save_task_template(session: Session, template_name: str, task_name: str,
                      points: float, trackable: bool = False,
                      unit: str = None, sort_order: int = 0) -> TaskTemplate:
    """Create a task template"""
    template = TaskTemplate(
        template_name=template_name,
        task_name=task_name,
        points=points,
        trackable=trackable,
        unit=unit,
        sort_order=sort_order
    )
    session.add(template)
    session.commit()
    return template


def get_templates_by_name(session: Session, template_name: str) -> List[TaskTemplate]:
    """Get all tasks in a template"""
    return session.query(TaskTemplate).filter_by(template_name=template_name).order_by(TaskTemplate.sort_order).all()


def get_all_template_names(session: Session) -> List[str]:
    """Get list of all unique template names"""
    result = session.query(TaskTemplate.template_name).distinct().all()
    return [r[0] for r in result]


def get_all_templates(session: Session) -> Dict[str, List[Dict]]:
    """Get all templates in the JSON-like format"""
    templates = {}
    template_names = get_all_template_names(session)

    for name in template_names:
        tasks = get_templates_by_name(session, name)
        templates[name] = [
            {
                "name": t.task_name,
                "points": t.points,
                "trackable": t.trackable,
                "unit": t.unit
            }
            for t in tasks
        ]

    return templates


def delete_task_template(session: Session, template_name: str, task_name: str) -> bool:
    """Delete a task from a template"""
    template = session.query(TaskTemplate).filter_by(
        template_name=template_name,
        task_name=task_name
    ).first()

    if template:
        session.delete(template)
        session.commit()
        return True
    return False
