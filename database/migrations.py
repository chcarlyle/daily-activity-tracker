"""
Database migration functions for LifeTracker.
Handles JSON to SQLite migration and data export.
"""
from datetime import datetime
from typing import Tuple
import json
import shutil
import streamlit as st

from config.settings import DATA_FILE, DB_FILE
from models import User, DailyTask, TaskTemplate, DailyMetric, Goal
from database.connection import init_database, get_db_session
from database.tasks import save_daily_task
from database.templates import save_task_template, get_all_templates
from database.metrics import save_daily_metric
from database.goals import save_goal, get_goals_by_type


def migrate_json_to_database() -> Tuple[bool, str]:
    """
    Auto-migrate JSON data to SQLite database on first run.
    Returns: (success: bool, message: str)
    """
    try:
        # Check if migration is needed (JSON exists but DB doesn't)
        json_exists = DATA_FILE.exists()
        db_exists = DB_FILE.exists()

        if not json_exists:
            # No JSON file, just initialize database
            init_database()
            return True, "Database initialized (no JSON data to migrate)"

        if db_exists:
            # Database already exists, no migration needed
            return True, "Database already exists"

        # Need to migrate!
        st.info("📦 Migrating your data to database format... This will only happen once.")

        # 1. Create backup of JSON with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = DATA_FILE.parent / f"{DATA_FILE.stem}_backup_{timestamp}.json"
        shutil.copy2(DATA_FILE, backup_file)
        st.success(f"✅ Created backup: {backup_file.name}")

        # 2. Load JSON data
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)

        # 3. Initialize database
        init_database()
        session = get_db_session()

        try:
            # 4. Migrate user settings
            user = session.query(User).first()
            if user:
                user.total_points = data.get('total_points', 0.0)
                session.commit()

            # 5. Migrate task templates
            template_count = 0
            for template_name, tasks in data.get('checklist_templates', {}).items():
                for idx, task in enumerate(tasks):
                    save_task_template(
                        session,
                        template_name=template_name,
                        task_name=task['name'],
                        points=task['points'],
                        trackable=task.get('trackable', False),
                        unit=task.get('unit'),
                        sort_order=idx
                    )
                    template_count += 1

            st.success(f"✅ Migrated {template_count} task templates")

            # 6. Migrate daily checklists
            task_count = 0
            for date_str, day_data in data.get('daily_checklists', {}).items():
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

                    for task in day_data.get('tasks', []):
                        completed = task['name'] in day_data.get('completed', [])
                        quantity = day_data.get('quantities', {}).get(task['name'], 1.0)

                        save_daily_task(
                            session,
                            date=date_obj,
                            task_name=task['name'],
                            points=task['points'],
                            trackable=task.get('trackable', False),
                            unit=task.get('unit'),
                            quantity=quantity,
                            completed=completed
                        )
                        task_count += 1
                except ValueError as e:
                    st.warning(f"⚠️ Skipping invalid date: {date_str}")
                    continue

            st.success(f"✅ Migrated {task_count} daily tasks")

            # 7. Migrate daily metrics
            metric_count = 0
            for date_str, metrics in data.get('daily_metrics', {}).items():
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    save_daily_metric(
                        session,
                        date=date_obj,
                        mood=metrics.get('mood'),
                        energy=metrics.get('energy')
                    )
                    metric_count += 1
                except ValueError:
                    continue

            st.success(f"✅ Migrated {metric_count} daily metrics")

            # 8. Migrate goals
            goal_count = 0
            for goal_type, goals_dict in data.get('goals', {}).items():
                for goal_name, goal_data in goals_dict.items():
                    try:
                        created_date_str = goal_data.get('created', datetime.now().strftime('%Y-%m-%d'))
                        created_date = datetime.strptime(created_date_str, '%Y-%m-%d').date()

                        save_goal(
                            session,
                            name=goal_name,
                            goal_type=goal_type,
                            target_points=goal_data.get('target', 100),
                            description=goal_data.get('description'),
                            created_date=created_date
                        )
                        goal_count += 1
                    except Exception as e:
                        st.warning(f"⚠️ Skipping goal {goal_name}: {str(e)}")
                        continue

            st.success(f"✅ Migrated {goal_count} goals")

            # 9. Validation
            total_tasks_db = session.query(DailyTask).count()
            total_templates_db = session.query(TaskTemplate).count()
            total_metrics_db = session.query(DailyMetric).count()
            total_goals_db = session.query(Goal).count()

            st.info(f"""
            **Migration Summary:**
            - Tasks: {total_tasks_db}
            - Templates: {total_templates_db}
            - Metrics: {total_metrics_db}
            - Goals: {total_goals_db}
            """)

            # 10. Rename JSON file to mark as migrated
            migrated_file = DATA_FILE.parent / f"{DATA_FILE.stem}.migrated"
            DATA_FILE.rename(migrated_file)

            session.close()

            return True, f"✅ Migration successful! Migrated {total_tasks_db} tasks, {total_templates_db} templates, {total_metrics_db} metrics, {total_goals_db} goals"

        except Exception as e:
            session.rollback()
            session.close()
            raise e

    except Exception as e:
        error_msg = f"❌ Migration failed: {str(e)}"
        st.error(error_msg)
        st.error("Please restore from backup and contact support.")
        return False, error_msg


def export_database_to_json(session) -> str:
    """Export database to JSON format (backward compatibility)"""
    from sqlalchemy.orm import Session

    export = {
        "daily_checklists": {},
        "checklist_templates": {},
        "time_logs": {},
        "daily_metrics": {},
        "goals": {"weekly": {}, "monthly": {}, "yearly": {}},
        "total_points": 0
    }

    # Export user total_points
    user = session.query(User).first()
    if user:
        export["total_points"] = user.total_points

    # Export task templates
    templates = get_all_templates(session)
    export["checklist_templates"] = templates

    # Export daily tasks
    all_tasks = session.query(DailyTask).order_by(DailyTask.date).all()
    for task in all_tasks:
        date_str = task.date.strftime('%Y-%m-%d')

        if date_str not in export["daily_checklists"]:
            export["daily_checklists"][date_str] = {
                "tasks": [],
                "completed": [],
                "quantities": {}
            }

        task_dict = {
            "name": task.task_name,
            "points": task.points,
            "trackable": task.trackable
        }
        if task.unit:
            task_dict["unit"] = task.unit

        export["daily_checklists"][date_str]["tasks"].append(task_dict)

        if task.completed:
            export["daily_checklists"][date_str]["completed"].append(task.task_name)

        if task.trackable and task.quantity != 1.0:
            export["daily_checklists"][date_str]["quantities"][task.task_name] = task.quantity

    # Export metrics
    all_metrics = session.query(DailyMetric).all()
    for metric in all_metrics:
        date_str = metric.date.strftime('%Y-%m-%d')
        export["daily_metrics"][date_str] = {}
        if metric.mood:
            export["daily_metrics"][date_str]["mood"] = metric.mood
        if metric.energy:
            export["daily_metrics"][date_str]["energy"] = metric.energy

    # Export goals
    for goal_type in ["weekly", "monthly", "yearly"]:
        goals = get_goals_by_type(session, goal_type)
        for goal in goals:
            export["goals"][goal_type][goal.name] = {
                "type": "points",
                "target": goal.target_points,
                "created": goal.created_date.strftime('%Y-%m-%d')
            }
            if goal.description:
                export["goals"][goal_type][goal.name]["description"] = goal.description

    return json.dumps(export, indent=2)
