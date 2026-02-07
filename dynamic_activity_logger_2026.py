import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict, Any, Tuple, Union
import json
from pathlib import Path
import shutil

# Import from local modules
from sqlalchemy.orm import Session
from models import (
    Base, User, TaskTemplate, DailyTask, DailyMetric,
    Goal, Avatar, AvatarAlignment, StreakCache, SystemMetadata
)
from config.settings import DATABASE_URL, DB_FILE, DATA_FILE, BACKUP_DIR, DEFAULT_TIMEZONE
from config.styles import MOBILE_CSS
from database.connection import init_database, get_db_session, migrate_remove_category_column
from database.tasks import (
    save_daily_task, get_daily_tasks, update_task_completion,
    delete_daily_task, get_tasks_in_range
)
from database.templates import (
    save_task_template, get_templates_by_name, get_all_template_names,
    get_all_templates, delete_task_template
)
from database.metrics import save_daily_metric, get_daily_metric, get_metrics_in_range
from database.goals import save_goal, get_goals_by_type, delete_goal
from database.avatars import save_avatar, get_active_avatar, delete_avatar
from database.migrations import migrate_json_to_database, export_database_to_json
from analytics.calculations import (
    get_day_points, get_task_streak, get_positive_day_streak,
    get_task_consistency, get_all_unique_tasks
)
from services.avatar_service import prepare_avatar_analysis_data, generate_avatar_prompt
from services.backup_service import (
    create_backup, check_and_create_daily_backup,
    export_data_for_download, import_data_from_file
)

# Page config - must be first Streamlit command
st.set_page_config(
    page_title="Daily Activity Tracker",
    page_icon="⭐",
    layout="wide",
    initial_sidebar_state="expanded",  # Show sidebar by default
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Personal Daily Activity Tracker"
    }
)

# Apply mobile optimization CSS
st.markdown(MOBILE_CSS, unsafe_allow_html=True)

# Optional: Simple password protection
# Uncomment and set password in Streamlit Cloud secrets
def check_password():
    """Returns `True` if the user had the correct password."""
    
    # Skip password in development
    if not st.secrets.get("passwords"):
        return True
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["passwords"]["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    # First run, show input for password
    if "password_correct" not in st.session_state:
        st.text_input(
            "🔒 Enter Password", 
            type="password", 
            on_change=password_entered, 
            key="password",
            help="Contact admin for password"
        )
        st.stop()
        return False
    
    # Password incorrect, show input + error
    elif not st.session_state["password_correct"]:
        st.text_input(
            "🔒 Enter Password", 
            type="password", 
            on_change=password_entered, 
            key="password",
            help="Contact admin for password"
        )
        st.error("😕 Password incorrect")
        st.stop()
        return False
    
    # Password correct
    else:
        return True

# Run password check
if not check_password():
    st.stop()

# ============================================================================
# LEGACY JSON DATA FUNCTIONS (for migration and backup)
# ============================================================================

# Initialize data structure
def load_data():
    """Load data with error handling and automatic recovery"""
    default_data = {
        "daily_checklists": {},  # {date: {tasks: [], completed: [], quantities: {task_name: count}}}
        "checklist_templates": {
            "Morning Routine": [
                {"name": "Scripture Study (15 min)", "points": 15},
                {"name": "Personal Prayer (morning)", "points": 5},
                {"name": "Brush Teeth (morning)", "points": 1},
                {"name": "Shower", "points": 3},
                {"name": "Make Bed", "points": 5},
            ],
            "Evening Routine": [
                {"name": "Personal Prayer (evening)", "points": 5},
                {"name": "Reading (15 min)", "points": 10},
                {"name": "Brush Teeth (evening)", "points": 2},
            ],
            "Personal Development": [
                {"name": "Job Application", "points": 1, "trackable": True, "unit": "applications"},
                {"name": "Independent Project (30 min)", "points": 10, "trackable": False},
                {"name": "Piano", "points": 10, "trackable": False},
            ],
            "Negative Habits": [
                {"name": "Phone Screen Time (per hour)", "points": -2.5, "trackable": True, "unit": "hours"},
                {"name": "Phone Screen Time After Bed", "points": -5, "trackable": True, "unit": "hours"},
                {"name": "18+ Content", "points": -10, "trackable": True, "unit": "events"},
            ]
        },
        "time_logs": {},
        "daily_metrics": {},
        "goals": {"weekly": {}, "monthly": {}, "yearly": {}},
        "total_points": 0,
        "last_backup_date": None
    }

    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)

            # Add missing fields from default data
            for key, value in default_data.items():
                if key not in data:
                    data[key] = value

            return data

        except json.JSONDecodeError:
            st.error("⚠️ Data file is corrupted! Attempting to restore from backup...")

            # Try to find most recent backup
            if BACKUP_DIR.exists():
                backups = sorted(BACKUP_DIR.glob("backup_*.json"), reverse=True)
                for backup in backups:
                    try:
                        with open(backup, 'r') as f:
                            data = json.load(f)
                        st.success(f"✅ Restored from backup: {backup.name}")

                        # Add missing fields
                        for key, value in default_data.items():
                            if key not in data:
                                data[key] = value

                        # Save the restored data
                        save_data(data)
                        return data
                    except:
                        continue

            st.warning("⚠️ Could not restore from backup. Starting with fresh data.")
            return default_data

        except Exception as e:
            st.error(f"⚠️ Error loading data: {str(e)}")
            return default_data
    else:
        # First time - create new data file
        return default_data

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.error(f"Failed to save data: {str(e)}")
        return False
    return True


# OLD JSON CODE - DISABLED (using database now)
# data = load_data()
# check_and_create_daily_backup(data)


# ============================================================================
# LEGACY JSON FUNCTIONS (for compatibility - mostly replaced by database operations)
# ============================================================================

# Helper functions (legacy JSON-based - will be replaced)
# Helper functions (legacy JSON-based - will be replaced)
def get_day_points(date_str, separate=False):
    """Calculate points for a day, optionally separating positive and negative"""
    if date_str not in data["daily_checklists"]:
        return (0, 0) if separate else 0

    completed = data["daily_checklists"][date_str].get("completed", [])
    tasks = data["daily_checklists"][date_str].get("tasks", [])
    quantities = data["daily_checklists"][date_str].get("quantities", {})

    positive = 0
    negative = 0

    for task in tasks:
        if task["name"] in completed:
            points = task["points"]

            # Check if this task is trackable (has a multiplier)
            if task.get("trackable", False):
                quantity = quantities.get(task["name"], 1)
                points = points * quantity

            if points > 0:
                positive += points
            else:
                negative += points

    if separate:
        return (positive, negative)
    return positive + negative

def get_week_start(date):
    return date - timedelta(days=date.weekday())

def get_task_streak(task_name, end_date, days_back=90):
    """Calculate current streak and longest streak for a specific task"""
    current_streak = 0
    longest_streak = 0
    temp_streak = 0

    for i in range(days_back):
        check_date = end_date - timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")

        if date_str in data["daily_checklists"]:
            completed = data["daily_checklists"][date_str].get("completed", [])
            tasks = data["daily_checklists"][date_str].get("tasks", [])

            # Check if task exists for this day and was completed
            task_exists = any(t["name"] == task_name for t in tasks)
            task_completed = task_name in completed

            if task_exists:
                if task_completed:
                    temp_streak += 1
                    if i < days_back:  # Only count towards current streak if recent
                        if temp_streak > current_streak and i == current_streak:
                            current_streak = temp_streak
                    if temp_streak > longest_streak:
                        longest_streak = temp_streak
                else:
                    temp_streak = 0

    # Recalculate current streak properly
    current_streak = 0
    for i in range(days_back):
        check_date = end_date - timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")

        if date_str in data["daily_checklists"]:
            completed = data["daily_checklists"][date_str].get("completed", [])
            tasks = data["daily_checklists"][date_str].get("tasks", [])

            task_exists = any(t["name"] == task_name for t in tasks)
            task_completed = task_name in completed

            if task_exists and task_completed:
                current_streak += 1
            elif task_exists:
                break

    return current_streak, longest_streak

def get_positive_day_streak(end_date, days_back=90):
    """Calculate current streak of positive net point days"""
    current_streak = 0

    for i in range(days_back):
        check_date = end_date - timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")

        net_points = get_day_points(date_str)

        if net_points > 0:
            current_streak += 1
        elif date_str in data["daily_checklists"] and data["daily_checklists"][date_str].get("tasks"):
            # Day exists with tasks but wasn't positive
            break

    return current_streak

def get_task_consistency(task_name, end_date, days_back=30):
    """Calculate consistency percentage for a task over a period"""
    days_with_task = 0
    days_completed = 0

    for i in range(days_back):
        check_date = end_date - timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")

        if date_str in data["daily_checklists"]:
            tasks = data["daily_checklists"][date_str].get("tasks", [])
            completed = data["daily_checklists"][date_str].get("completed", [])

            task_exists = any(t["name"] == task_name for t in tasks)

            if task_exists:
                days_with_task += 1
                if task_name in completed:
                    days_completed += 1

    if days_with_task == 0:
        return 0

    return (days_completed / days_with_task) * 100

def get_all_unique_tasks(days_back=30):
    """Get all unique tasks from recent history"""
    unique_tasks = set()
    end_date = datetime.now(ZoneInfo("America/New_York")).date()

    for i in range(days_back):
        check_date = end_date - timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")

        if date_str in data["daily_checklists"]:
            tasks = data["daily_checklists"][date_str].get("tasks", [])
            for task in tasks:
                unique_tasks.add(task["name"])

    return sorted(list(unique_tasks))

# ============================================================================
# DATABASE INITIALIZATION AND MIGRATION
# ============================================================================

# Run migration if needed (one-time, automatic)
if not DB_FILE.exists() and DATA_FILE.exists():
    success, message = migrate_json_to_database()
    if success:
        st.success(message)
    else:
        st.error("Migration failed! App may not function correctly.")
        st.stop()
elif not DB_FILE.exists():
    # No JSON, no DB - initialize fresh database
    init_database()
    st.info("✨ Welcome to LifeTracker! Database initialized.")

# Run database migration if needed (one-time category removal)
if 'migration_run' not in st.session_state:
    success, message = migrate_remove_category_column()
    if not success:
        st.error(f"❌ Database migration failed: {message}")
        st.error("Please contact support or restore from backup.")
        st.stop()
    elif "Migration successful" in message:
        st.success(f"✅ {message}")
    st.session_state.migration_run = True

# Initialize database session in session state
if 'db_session' not in st.session_state:
    st.session_state.db_session = get_db_session()

db_session = st.session_state.db_session

# Sidebar
with st.sidebar:
    st.title("⭐ Daily Tracker")

    # Display current stats (removed level/progress bar)
    user = db_session.query(User).first()
    total_points = user.total_points if user else 0
    st.metric("Total Points", int(total_points))
    
    st.divider()
    
    # Manage Templates
    with st.expander("📋 Manage Templates"):
        st.write("**Create/Edit Task Templates**")

        template_name = st.text_input("Template Name", placeholder="e.g., Morning Routine")

        if template_name:
            st.write(f"**Tasks in '{template_name}':**")

            # Add new task to template
            with st.form(f"add_task_{template_name}"):
                col1, col2 = st.columns(2)
                with col1:
                    task_name = st.text_input("Task Name")
                    task_points = st.number_input("Points", min_value=-50, max_value=50, value=10)
                with col2:
                    task_trackable = st.checkbox("Trackable (with multiplier)?", value=False)
                    task_unit = ""
                    if task_trackable:
                        task_unit = st.text_input("Unit (e.g., 'hours', 'reps', 'times')", value="times")

                if st.form_submit_button("Add Task"):
                    if task_name:
                        save_task_template(
                            db_session,
                            template_name=template_name,
                            task_name=task_name,
                            points=task_points,
                            trackable=task_trackable,
                            unit=task_unit if task_trackable else None
                        )
                        st.success(f"Added '{task_name}' to {template_name}")
                        st.rerun()

            # Show existing tasks
            existing_tasks = get_templates_by_name(db_session, template_name)
            if existing_tasks:
                for task in existing_tasks:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"• {task.task_name} ({task.points}pts)")
                    with col2:
                        if st.button("🗑️", key=f"del_{template_name}_{task.id}"):
                            delete_task_template(db_session, template_name, task.task_name)
                            st.rerun()
    
    # Backup & Export
    with st.expander("💾 Backup & Export"):
        st.write("**Export Data**")
        if st.button("📥 Download Backup (JSON)", use_container_width=True):
            json_string = export_database_to_json(db_session)
            if json_string:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="⬇️ Download",
                    data=json_string,
                    file_name=f"lifetracker_backup_{timestamp}.json",
                    mime="application/json"
                )

        if st.button("🔄 Create Manual Backup", use_container_width=True):
            if create_backup():
                st.success("✅ Backup created successfully!")
            else:
                st.error("❌ Failed to create backup")

        st.divider()
        st.write("**Import Data**")
        st.info("💡 Import from JSON coming soon! Use export for now to backup your data.")

    # Avatar Management
    with st.expander("🎯 My Avatar (Ideal Self)"):
        st.write("**Define Your Ideal Self**")
        st.caption("Describe who you want to become. Claude AI will analyze if your behavior aligns with this avatar.")

        # Get current active avatar
        current_avatar = get_active_avatar(db_session)

        # Avatar form
        avatar_name = st.text_input(
            "Avatar Name",
            value=current_avatar.name if current_avatar else "",
            placeholder="e.g., My Best Self"
        )

        avatar_description = st.text_area(
            "Avatar Description",
            value=current_avatar.description if current_avatar else "",
            placeholder="I am someone who prioritizes spiritual growth through daily scripture study, maintains physical health through exercise, nurtures meaningful relationships, and contributes to society...",
            height=150
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Avatar", use_container_width=True):
                if avatar_name and avatar_description:
                    save_avatar(db_session, avatar_name, avatar_description)
                    st.success("✅ Avatar saved!")
                    st.rerun()
                else:
                    st.warning("Please provide both name and description")

        with col2:
            if current_avatar and st.button("🗑️ Delete Avatar", use_container_width=True):
                if delete_avatar(db_session, current_avatar.id):
                    st.success("Avatar deleted")
                    st.rerun()

        if current_avatar:
            st.divider()
            st.info(f"💡 Current Avatar: **{current_avatar.name}**")
            st.caption(f"Created: {current_avatar.created_at.strftime('%Y-%m-%d')}")

# Main content
st.title("📖 LifeTracker")

# Date Navigation (more compact)

# Initialize session state for selected date
if "selected_date" not in st.session_state:
    st.session_state.selected_date = datetime.now(ZoneInfo("America/New_York")).date()

today_actual = datetime.now(ZoneInfo("America/New_York")).date()

# Use selected date
today = st.session_state.selected_date
today_str = today.strftime("%Y-%m-%d")

# Compact date navigation in a single row
date_col1, date_col2, date_col3, date_col4 = st.columns([1, 3, 1, 1])

with date_col1:
    if st.button("◀️"):
        st.session_state.selected_date = st.session_state.selected_date - timedelta(days=1)
        st.rerun()

with date_col2:
    date_display = "Today" if today == today_actual else today.strftime("%A, %B %d, %Y")
    if today < today_actual:
        days_ago = (today_actual - today).days
        date_display = f"{today.strftime('%a, %b %d')} ({days_ago}d ago)"
    elif today > today_actual:
        days_ahead = (today - today_actual).days
        date_display = f"{today.strftime('%a, %b %d')} (in {days_ahead}d)"

    selected_date = st.date_input(
        "Date",
        value=st.session_state.selected_date,
        key="date_picker",
        label_visibility="collapsed"
    )
    if selected_date != st.session_state.selected_date:
        st.session_state.selected_date = selected_date
        st.rerun()

    st.caption(date_display)

with date_col3:
    if st.button("▶️"):
        st.session_state.selected_date = st.session_state.selected_date + timedelta(days=1)
        st.rerun()

with date_col4:
    if st.button("Today"):
        st.session_state.selected_date = today_actual
        st.rerun()

# Quick Dashboard
st.markdown("###")  # Spacing

# Get today's stats from database
positive_pts, negative_pts = get_day_points(db_session, today, separate=True)
net_pts = positive_pts + negative_pts

# Get today's tasks for completion rate
today_tasks = get_daily_tasks(db_session, today)
completion_rate = 0
if today_tasks:
    completed_count = sum(1 for t in today_tasks if t.completed)
    completion_rate = (completed_count / len(today_tasks)) * 100

positive_streak = get_positive_day_streak(db_session, today_actual)

# Dashboard metrics in a clean row
dash_col1, dash_col2, dash_col3, dash_col4, dash_col5, dash_col6 = st.columns(6)

with dash_col1:
    st.metric("Points", f"{net_pts:+.0f}", delta=f"{net_pts:+.0f}" if net_pts != 0 else None, delta_color="normal" if net_pts > 0 else "inverse")

with dash_col2:
    st.metric("Completed", f"{completion_rate:.0f}%")

with dash_col3:
    st.metric("Streak", f"🔥 {positive_streak}")

with dash_col4:
    # Get existing metric or use default
    existing_metric = get_daily_metric(db_session, today)
    current_mood = existing_metric.mood if existing_metric and existing_metric.mood else 5

    mood_val = st.select_slider("😊", options=list(range(1, 11)), value=current_mood, label_visibility="collapsed", key="mood_quick")
    st.caption("Mood")
    if mood_val != current_mood:
        save_daily_metric(db_session, today, mood=mood_val)

with dash_col5:
    # Get existing metric or use default
    current_energy = existing_metric.energy if existing_metric and existing_metric.energy else 5

    energy_val = st.select_slider("⚡", options=list(range(1, 11)), value=current_energy, label_visibility="collapsed", key="energy_quick")
    st.caption("Energy")
    if energy_val != current_energy:
        save_daily_metric(db_session, today, energy=energy_val)

with dash_col6:
    # Quick template loader
    if st.button("⚡ Load All Templates", use_container_width=True, help="Add all template tasks at once"):
        existing_tasks = get_daily_tasks(db_session, today)
        existing_task_names = {t.task_name for t in existing_tasks}

        # Get all templates from database
        all_templates = get_all_templates(db_session)
        for template_name, tasks in all_templates.items():
            for task in tasks:
                if task["name"] not in existing_task_names:
                    save_daily_task(
                        db_session,
                        date=today,
                        task_name=task["name"],
                        category=task["category"],
                        points=task["points"],
                        trackable=task.get("trackable", False),
                        unit=task.get("unit"),
                        completed=False
                    )
        st.rerun()

st.markdown("---")  # Cleaner divider

# Task Entry - Simple and clean
with st.expander("➕ Add Tasks", expanded=len(today_tasks) == 0):
    add_col1, add_col2 = st.columns([2, 1])

    with add_col1:
        st.write("**From Templates:**")
        all_templates = get_all_templates(db_session)

        if all_templates:
            template_row_cols = st.columns(len(all_templates))
            for idx, (template_name, tasks) in enumerate(all_templates.items()):
                with template_row_cols[idx]:
                    if st.button(f"{template_name}", use_container_width=True, key=f"add_template_{idx}"):
                        existing_tasks = get_daily_tasks(db_session, today)
                        existing_task_names = {t.task_name for t in existing_tasks}

                        for task in tasks:
                            if task["name"] not in existing_task_names:
                                save_daily_task(
                                    db_session,
                                    date=today,
                                    task_name=task["name"],
                                    category=task["category"],
                                    points=task["points"],
                                    trackable=task.get("trackable", False),
                                    unit=task.get("unit"),
                                    completed=False
                                )
                        st.rerun()
        else:
            st.info("No templates yet - create one in the sidebar!")

    with add_col2:
        st.write("**Custom Task:**")
        with st.form("quick_add", border=False):
            quick_name = st.text_input("Task name", placeholder="e.g., Meditation")
            quick_pts = st.number_input("Points", -50, 50, 10)

            quick_trackable = st.checkbox("Trackable (with multiplier)?", value=False)
            quick_unit = ""
            if quick_trackable:
                quick_unit = st.text_input("Unit (e.g., 'hours', 'reps', 'times')", value="times")

            if st.form_submit_button("Add Task", use_container_width=True):
                if quick_name:
                    save_daily_task(
                        db_session,
                        date=today,
                        task_name=quick_name,
                        points=quick_pts,
                        trackable=quick_trackable,
                        unit=quick_unit if quick_trackable else None,
                        completed=False
                    )
                    st.rerun()

# Task List - Clean and simple
st.markdown("### Tasks")

if not today_tasks:
    st.info("No tasks yet - add some using the button above!")
else:
    # Show completion summary
    completed_count = len([t for t in today_tasks if t.completed])
    st.write(f"**Completed: {completed_count}/{len(today_tasks)}**")
    st.write("")  # Add spacing

    # Simple list view - no category grouping
    for task in today_tasks:
        # Calculate points
        base_points = task.points
        if task.trackable:
            base_points = base_points * task.quantity
        adjusted_points = base_points

        # Simplified task row
        task_col1, task_col2, task_col3 = st.columns([4, 2, 1])

        with task_col1:
            new_completion = st.checkbox(
                task.task_name,
                value=task.completed,
                key=f"task_{today_str}_{task.task_name}"
            )
            if new_completion != task.completed:
                update_task_completion(db_session, today, task.task_name, new_completion)
                st.rerun()

        with task_col2:
            if task.trackable:
                new_quantity = st.number_input(
                    task.unit if task.unit else "qty",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(task.quantity),
                    step=0.5 if task.points < 0 else 1.0,
                    format="%.1f",
                    key=f"qty_{today_str}_{task.task_name}",
                    label_visibility="collapsed"
                )
                if new_quantity != task.quantity:
                    update_task_completion(db_session, today, task.task_name, task.completed, new_quantity)
                    st.rerun()
                st.caption(f"{task.points:+.1f} × {new_quantity:.1f}")

        with task_col3:
            color = "green" if adjusted_points > 0 else "red"
            st.markdown(f":{color}[**{adjusted_points:+.0f}**]")

        # Delete button in its own small column
        task_col4 = st.columns([19, 1])[1]
        with task_col4:
            if st.button("🗑️", key=f"del_{today_str}_{task.task_name}", help=f"Delete {task.task_name}"):
                delete_daily_task(db_session, today, task.task_name)
                st.rerun()

        st.write("")  # Add spacing between tasks

st.markdown("---")

# Analytics - Consolidated Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Analytics & Trends",
    "🔥 Habits & Streaks",
    "🎯 Goals",
    "🎯 Avatar Alignment"
])

with tab1:
    st.header("Trends & Insights")
    st.caption("Track your progress and discover patterns")

    # Last 30 days
    chart_data = []
    for i in range(30):
        check_date = today_actual - timedelta(days=29-i)

        pos, neg = get_day_points(db_session, check_date, separate=True)

        # Get mood and energy if available
        metric = get_daily_metric(db_session, check_date)
        mood = metric.mood if metric else None
        energy = metric.energy if metric else None

        chart_data.append({
            "Date": check_date,
            "Positive": pos,
            "Negative": abs(neg),
            "Net": pos + neg,
            "Mood": mood,
            "Energy": energy
        })

    df_chart = pd.DataFrame(chart_data)

    # Net points trend with 7-day moving average
    st.subheader("Net Points Trend")

    df_chart['7-Day Avg'] = df_chart['Net'].rolling(window=7, min_periods=1).mean()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_chart['Date'],
        y=df_chart['Net'],
        mode='markers+lines',
        name='Daily Net Points',
        line=dict(color='lightblue', width=1),
        marker=dict(size=6)
    ))

    fig.add_trace(go.Scatter(
        x=df_chart['Date'],
        y=df_chart['7-Day Avg'],
        mode='lines',
        name='7-Day Average',
        line=dict(color='blue', width=3)
    ))

    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    fig.update_layout(
        title='Net Points Over Time (30 Days)',
        xaxis_title='Date',
        yaxis_title='Points',
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)

    # Positive vs Negative
    st.subheader("Positive vs Negative Points")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_chart['Date'],
        y=df_chart['Positive'],
        name='Positive Points',
        marker_color='lightgreen'
    ))

    fig.add_trace(go.Bar(
        x=df_chart['Date'],
        y=df_chart['Negative'],
        name='Negative Points',
        marker_color='lightcoral'
    ))

    fig.update_layout(
        barmode='group',
        xaxis_title='Date',
        yaxis_title='Points',
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)

    # Weekly comparison
    st.subheader("Weekly Comparison")

    # Calculate weekly totals
    df_chart['Week'] = df_chart['Date'].apply(lambda x: f"Week of {get_week_start(x).strftime('%b %d')}")
    weekly_data = df_chart.groupby('Week').agg({
        'Net': 'sum',
        'Positive': 'sum',
        'Negative': 'sum'
    }).reset_index()

    col1, col2, col3 = st.columns(3)
    with col1:
        if len(weekly_data) > 0:
            st.metric("This Week", f"{weekly_data.iloc[-1]['Net']:+.1f} pts")
    with col2:
        if len(weekly_data) > 1:
            last_week = weekly_data.iloc[-2]['Net']
            st.metric("Last Week", f"{last_week:+.1f} pts")
    with col3:
        if len(weekly_data) > 1:
            change = weekly_data.iloc[-1]['Net'] - weekly_data.iloc[-2]['Net']
            st.metric("Week-over-Week", f"{change:+.1f} pts", delta=f"{change:+.1f}")

    # Insights
    st.subheader("📊 Insights")

    insights = []

    # Calculate streaks
    positive_days = (df_chart['Net'] > 0).sum()
    total_days = len(df_chart[df_chart['Net'] != 0])

    if total_days > 0:
        positive_rate = (positive_days / total_days) * 100
        insights.append(f"✅ You've had positive net points on **{positive_rate:.0f}%** of logged days")

    # Mood correlation
    df_with_mood = df_chart.dropna(subset=['Mood', 'Net'])
    if len(df_with_mood) > 5:
        correlation = df_with_mood['Mood'].corr(df_with_mood['Net'])
        if correlation > 0.3:
            insights.append(f"😊 Your mood tends to be **higher** on days with more points (correlation: {correlation:.2f})")
        elif correlation < -0.3:
            insights.append(f"🤔 Interestingly, your mood shows a **negative** correlation with points ({correlation:.2f})")

    # Energy correlation
    df_with_energy = df_chart.dropna(subset=['Energy', 'Net'])
    if len(df_with_energy) > 5:
        correlation = df_with_energy['Energy'].corr(df_with_energy['Net'])
        if correlation > 0.3:
            insights.append(f"⚡ Higher energy correlates with better performance (correlation: {correlation:.2f})")

    # Trend detection
    if len(df_chart) >= 14:
        recent_avg = df_chart.tail(7)['Net'].mean()
        older_avg = df_chart.iloc[-14:-7]['Net'].mean()
        if recent_avg > older_avg * 1.2:
            insights.append(f"📈 You're on an **upward trend** - last 7 days averaging {recent_avg:.1f} vs {older_avg:.1f} the week before!")
        elif recent_avg < older_avg * 0.8:
            insights.append(f"📉 Recent dip detected - last 7 days averaging {recent_avg:.1f} vs {older_avg:.1f} the week before")

    # Best/worst days
    if len(df_chart[df_chart['Net'] != 0]) > 0:
        best_day = df_chart.loc[df_chart['Net'].idxmax()]
        worst_day = df_chart.loc[df_chart['Net'].idxmin()]
        insights.append(f"⭐ Best day: **{best_day['Date'].strftime('%b %d')}** ({best_day['Net']:+.1f} pts)")
        insights.append(f"⬇️ Lowest day: **{worst_day['Date'].strftime('%b %d')}** ({worst_day['Net']:+.1f} pts)")

    for insight in insights:
        st.markdown(f"- {insight}")

with tab2:
    st.header("🔥 Streaks & Habits")
    st.caption("Track your consistency and build strong habits")

    # Overall positive day streak
    positive_streak = get_positive_day_streak(db_session, today_actual)

    st.subheader("📊 Overall Performance")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("🔥 Current Positive Day Streak", f"{positive_streak} days")

    with col2:
        # Calculate best day streak ever
        best_streak = 0
        temp_streak = 0
        for i in range(180):  # Check last 6 months
            check_date = today_actual - timedelta(days=i)
            day_pts = get_day_points(db_session, check_date)
            tasks_exist = len(get_daily_tasks(db_session, check_date)) > 0

            if day_pts > 0:
                temp_streak += 1
                if temp_streak > best_streak:
                    best_streak = temp_streak
            elif tasks_exist:
                temp_streak = 0
        st.metric("⭐ Best Streak Ever", f"{best_streak} days")

    with col3:
        # Overall consistency (days with positive net points)
        logged_days = 0
        positive_days = 0
        for i in range(30):
            check_date = today_actual - timedelta(days=i)
            tasks = get_daily_tasks(db_session, check_date)
            if tasks:
                logged_days += 1
                if get_day_points(db_session, check_date) > 0:
                    positive_days += 1
        consistency = (positive_days / logged_days * 100) if logged_days > 0 else 0
        st.metric("📈 30-Day Win Rate", f"{consistency:.0f}%")

    st.divider()

    # Individual task streaks and consistency
    st.subheader("📋 Task Performance (Last 30 Days)")

    unique_tasks = get_all_unique_tasks(db_session, 30)

    if unique_tasks:
        # Calculate stats for each task
        task_stats = []
        for task_name in unique_tasks:
            current_streak, longest_streak = get_task_streak(db_session, task_name, today_actual, 90)
            consistency = get_task_consistency(db_session, task_name, today_actual, 30)

            task_stats.append({
                "Task": task_name,
                "Current Streak": current_streak,
                "Longest Streak": longest_streak,
                "Consistency": consistency
            })

        # Sort by current streak descending
        task_stats.sort(key=lambda x: (x["Current Streak"], x["Consistency"]), reverse=True)

        df_streaks = pd.DataFrame(task_stats)

        # Format the dataframe
        df_display = df_streaks.copy()
        df_display["Current Streak"] = df_display["Current Streak"].apply(lambda x: f"🔥 {x} days" if x > 0 else "-")
        df_display["Longest Streak"] = df_display["Longest Streak"].apply(lambda x: f"⭐ {x} days")
        df_display["Consistency"] = df_display["Consistency"].apply(lambda x: f"{x:.0f}%")

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.divider()

        # Streak insights
        st.subheader("💡 Habit Insights")

        insights = []

        # Best performers
        top_tasks = [t for t in task_stats if t["Current Streak"] >= 7]
        if top_tasks:
            task_names = ", ".join([f"**{t['Task']}**" for t in top_tasks[:3]])
            insights.append(f"🌟 Strong habits: {task_names} - Keep it up!")

        # Tasks with high consistency but no streak
        consistent_no_streak = [t for t in task_stats if t["Consistency"] >= 80 and t["Current Streak"] == 0]
        if consistent_no_streak:
            task_name = consistent_no_streak[0]["Task"]
            insights.append(f"💪 **{task_name}** has high consistency but streak broke - easy to restart!")

        # Tasks needing attention
        low_consistency = [t for t in task_stats if t["Consistency"] < 50 and t["Consistency"] > 0]
        if low_consistency:
            task_name = low_consistency[0]["Task"]
            insights.append(f"⚠️ **{task_name}** needs attention - only {low_consistency[0]['Consistency']:.0f}% consistency")

        # Habit strength classification
        establishing = [t for t in task_stats if 50 <= t["Consistency"] < 80]
        established = [t for t in task_stats if t["Consistency"] >= 80]

        if established:
            insights.append(f"✅ You have **{len(established)}** established habit{'s' if len(established) != 1 else ''} (80%+ consistency)")

        if establishing:
            insights.append(f"🔨 You're building **{len(establishing)}** habit{'s' if len(establishing) != 1 else ''} (50-80% consistency)")

        for insight in insights:
            st.markdown(f"- {insight}")

    else:
        st.info("Start completing tasks to see streak and consistency data!")

with tab3:
    st.header("🎯 Goals & Review")
    st.caption("Set goals and reflect on your progress")

    # Goal setting section
    st.subheader("🎯 Goals")

    goal_type = st.selectbox("Goal Type", ["Weekly", "Monthly", "Yearly"])

    goal_key = goal_type.lower()

    # Display existing goals from database
    existing_goals = get_goals_by_type(db_session, goal_type)
    if existing_goals:
        st.write(f"**Current {goal_type} Goals:**")
        goals_to_delete = []
        for goal in existing_goals:
            goal_name = goal.goal_name
            goal_info = {"type": "points", "target": goal.target_value or 0}
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                # Calculate progress if it's a point goal
                if goal_info.get("type") == "points":
                    target = goal_info.get("target", 0)
                    # Calculate current progress based on goal period
                    if goal_type == "Weekly":
                        week_start = get_week_start(today_actual)
                        current = 0
                        for i in range(7):
                            check_date = week_start + timedelta(days=i)
                            if check_date <= today_actual:
                                current += get_day_points(db_session, check_date)
                    elif goal_type == "Monthly":
                        month_start = today_actual.replace(day=1)
                        current = 0
                        check_date = month_start
                        while check_date <= today_actual:
                            current += get_day_points(db_session, check_date)
                            check_date += timedelta(days=1)
                    else:  # Yearly
                        year_start = today_actual.replace(month=1, day=1)
                        current = 0
                        check_date = year_start
                        while check_date <= today_actual:
                            current += get_day_points(db_session, check_date)
                            check_date += timedelta(days=1)

                    progress_pct = (current / target * 100) if target > 0 else 0
                    st.write(f"**{goal_name}**")
                    st.progress(min(progress_pct / 100, 1.0))
                    st.caption(f"{current:.0f} / {target:.0f} points ({progress_pct:.0f}%)")
                else:
                    st.write(f"**{goal_name}**: {goal_info.get('description', 'No description')}")

            with col2:
                if goal_info.get("type") == "points":
                    if progress_pct >= 100:
                        st.success("✅ Done!")
                    else:
                        remaining = target - current
                        st.info(f"{remaining:.0f} left")

            with col3:
                if st.button("🗑️", key=f"delete_goal_{goal_type}_{goal_name}"):
                    goals_to_delete.append(goal_name)

        # Delete marked goals
        for goal_name in goals_to_delete:
            delete_goal(db_session, goal_type, goal_name)
            st.rerun()

    st.divider()

    # Add new goal
    st.write("**Add New Goal:**")

    col1, col2 = st.columns([2, 1])

    with col1:
        new_goal_name = st.text_input("Goal Name", key=f"new_goal_name_{goal_type}")

    with col2:
        new_goal_target = st.number_input("Target Points", min_value=1, value=100, key=f"new_goal_target_{goal_type}")

    if st.button("➕ Add Goal", key=f"add_goal_{goal_type}"):
        if new_goal_name:
            save_goal(
                db_session,
                goal_type=goal_type,
                goal_name=new_goal_name,
                target_value=new_goal_target,
                description=f"{new_goal_target} points"
            )
            st.success(f"✅ Added goal: {new_goal_name}")
            st.rerun()
        else:
            st.warning("Please enter a goal name")

    st.divider()

    # Weekly review section
    st.subheader("📝 Weekly Review")

    week_start = get_week_start(today_actual)
    week_end = week_start + timedelta(days=6)

    st.write(f"**Week of {week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}**")

    # Weekly stats
    week_points = 0
    week_positive_days = 0
    week_logged_days = 0

    for i in range(7):
        check_date = week_start + timedelta(days=i)
        if check_date <= today_actual:
            tasks = get_daily_tasks(db_session, check_date)
            if tasks:
                week_logged_days += 1
                day_points = get_day_points(db_session, check_date)
                week_points += day_points
                if day_points > 0:
                    week_positive_days += 1

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Points", f"{week_points:.0f}")
    with col2:
        st.metric("Positive Days", f"{week_positive_days}/{week_logged_days}")
    with col3:
        avg_points = week_points / week_logged_days if week_logged_days > 0 else 0
        st.metric("Avg Points/Day", f"{avg_points:.1f}")

    # Review prompts
    st.write("**Reflection Questions:**")
    st.markdown("""
    - What were your biggest wins this week?
    - What challenges did you face?
    - What patterns did you notice?
    - What will you focus on next week?
    """)

    st.info("💡 Tip: Use this weekly review to adjust your goals and habits")

    st.divider()

    # History section - compact
    with st.expander("📅 View Past Days", expanded=False):
        # Show past days with their checklists
        for i in range(1, 15):  # Last 14 days (increased from 7)
            check_date = today_actual - timedelta(days=i)

            tasks = get_daily_tasks(db_session, check_date)
            if tasks:
                st.write(f"**{check_date.strftime('%A, %B %d')}**")
                pos, neg = get_day_points(db_session, check_date, separate=True)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Positive", f"+{pos:.1f}")
                with col2:
                    st.metric("Negative", f"{neg:.1f}")
                with col3:
                    st.metric("Net", f"{pos+neg:+.1f}")

                # Show task list
                st.write("**Completed:**")
                for task in tasks:
                    if task.completed:
                        points = task.points
                        if task.trackable and task.quantity:
                            points = points * task.quantity
                            st.write(f"✅ {task.task_name} (×{task.quantity:.1f}) ({points:+.1f}pts)")
                        else:
                            st.write(f"✅ {task.task_name} ({points:+.1f}pts)")

                st.write("**Not Completed:**")
                for task in tasks:
                    if not task.completed:
                        st.write(f"❌ {task.task_name} ({task.points:+}pts)")

with tab4:
    st.header("🎯 Avatar Alignment Analysis")
    st.caption("See how well your behavior aligns with your ideal self")

    # Get current avatar
    current_avatar = get_active_avatar(db_session)

    if not current_avatar:
        st.warning("⚠️ No avatar defined yet!")
        st.info("👉 Define your avatar in the sidebar under '🎯 My Avatar (Ideal Self)' to get started.")
    else:
        # Display current avatar
        st.subheader(f"Your Avatar: {current_avatar.name}")
        with st.expander("📝 Avatar Description", expanded=False):
            st.write(current_avatar.description)

        st.divider()

        # Analysis controls
        st.subheader("Generate Analysis Prompt")
        st.caption("Copy the prompt below and paste it into Claude.ai (or any LLM) to get your alignment analysis")

        if st.button("📋 Generate Prompt", use_container_width=False, type="primary"):
            st.session_state.show_prompt = True

        if st.session_state.get("show_prompt", False):
            end_date = today_actual
            start_date = end_date - timedelta(days=30)

            # Prepare data and generate prompt
            analysis_data = prepare_avatar_analysis_data(db_session, start_date, end_date)
            prompt = generate_avatar_prompt(current_avatar.description, analysis_data)

            st.info("📝 **Instructions:** Copy the prompt below, paste it into Claude.ai or another LLM, then paste the response back here.")

            # Display copyable prompt
            st.text_area(
                "Prompt for LLM",
                value=prompt,
                height=300,
                help="Copy this entire prompt and paste into Claude.ai"
            )

            st.divider()

            # Manual response input
            st.write("**Paste LLM Response Here:**")
            st.caption("After getting the analysis from your LLM, paste the JSON response below and click Save")

            llm_response = st.text_area(
                "LLM Response (JSON)",
                height=200,
                placeholder='{"alignment_score": 75, "summary": "...", "recommendations": [...], ...}',
                key="llm_response_input"
            )

            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("💾 Save Analysis", use_container_width=True):
                    if llm_response:
                        try:
                            # Parse and validate JSON
                            result = json.loads(llm_response.strip())

                            # Create alignment record
                            alignment = AvatarAlignment(
                                avatar_id=current_avatar.id,
                                analysis_date=datetime.now().date(),
                                start_date=start_date,
                                end_date=end_date,
                                alignment_score=result['alignment_score'],
                                alignment_summary=result['summary'],
                                recommendations=json.dumps(result['recommendations']),
                                trend=result.get('trend', 'stable'),
                                llm_model='manual-entry',
                                llm_prompt_version='v1.0'
                            )
                            db_session.add(alignment)
                            db_session.commit()

                            st.success("✅ Analysis saved!")
                            st.session_state.show_prompt = False
                            st.rerun()
                        except json.JSONDecodeError:
                            st.error("❌ Invalid JSON. Make sure you copied the complete response from the LLM.")
                        except KeyError as e:
                            st.error(f"❌ Missing required field: {e}")
                        except Exception as e:
                            st.error(f"❌ Error saving analysis: {str(e)}")
                    else:
                        st.warning("Please paste the LLM response first")

        st.divider()

        # Get alignment history
        alignments = get_alignment_history(db_session, current_avatar.id, limit=10)

        if not alignments:
            st.info("🔍 No alignment analyses yet. Click 'Run Analysis' to get your first insight!")
        else:
            # Latest alignment results
            latest = alignments[0]

            st.subheader("Latest Analysis Results")
            st.caption(f"Analysis Date: {latest.analysis_date.strftime('%B %d, %Y')}")
            st.caption(f"Period: {latest.start_date.strftime('%b %d')} - {latest.end_date.strftime('%b %d, %Y')}")

            # Alignment score with color coding
            score = latest.alignment_score
            if score >= 80:
                score_color = "🟢"
                score_label = "Excellent"
            elif score >= 60:
                score_color = "🟡"
                score_label = "Good"
            elif score >= 40:
                score_color = "🟠"
                score_label = "Fair"
            else:
                score_color = "🔴"
                score_label = "Needs Work"

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Alignment Score", f"{score}%", help=score_label)
                st.write(f"{score_color} {score_label}")
            with col2:
                trend_emoji = {"improving": "📈", "stable": "➡️", "declining": "📉"}
                st.metric("Trend", latest.trend.title(), help="Compared to previous analyses")
                st.write(f"{trend_emoji.get(latest.trend, '➡️')} {latest.trend.title()}")
            with col3:
                days_analyzed = (latest.end_date - latest.start_date).days
                st.metric("Days Analyzed", f"{days_analyzed}")

            st.divider()

            # Summary
            st.subheader("📝 Summary")
            st.write(latest.alignment_summary)

            st.divider()

            # Recommendations
            st.subheader("💡 Recommendations")
            recommendations = json.loads(latest.recommendations)
            for i, rec in enumerate(recommendations, 1):
                st.markdown(f"{i}. {rec}")

            st.divider()

            # Alignment history chart
            if len(alignments) > 1:
                st.subheader("📊 Alignment History")

                history_data = []
                for alignment in reversed(alignments):
                    history_data.append({
                        "Date": alignment.analysis_date,
                        "Score": alignment.alignment_score
                    })

                df_history = pd.DataFrame(history_data)

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_history['Date'],
                    y=df_history['Score'],
                    mode='lines+markers',
                    name='Alignment Score',
                    line=dict(color='#1f77b4', width=3),
                    marker=dict(size=8)
                ))

                fig.update_layout(
                    xaxis_title="Analysis Date",
                    yaxis_title="Alignment Score (%)",
                    yaxis_range=[0, 100],
                    height=300,
                    hovermode='x unified'
                )

                st.plotly_chart(fig, use_container_width=True)

            # View all analyses
            if len(alignments) > 1:
                with st.expander(f"📜 View All Analyses ({len(alignments)})", expanded=False):
                    for alignment in alignments:
                        st.write(f"**{alignment.analysis_date.strftime('%B %d, %Y')}** - Score: {alignment.alignment_score}%")
                        st.caption(alignment.alignment_summary)
                        st.divider()

# Footer
st.divider()
st.markdown("**💡 Tip:** Check the Trends & Insights tab to discover patterns and track your progress over time!")
