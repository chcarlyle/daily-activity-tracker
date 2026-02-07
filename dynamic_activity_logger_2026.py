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
from ui.sidebar import render_sidebar
from ui.main_content import render_main_content
from ui.tabs import render_analytics_tab, render_habits_tab, render_goals_tab, render_avatar_tab

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
    """Returns `True` if user had correct password."""

    def password_entered():
        """Checks whether password entered by user is correct."""
        if st.session_state["password"] == st.secrets.get("app", {}).get("password", ""):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
        return True

# Uncomment to enable password protection
# if not check_password():
#     st.stop()

# ============================================================================
# LEGACY JSON FUNCTIONS (for compatibility - mostly replaced by database operations)
# ============================================================================

# Helper functions (legacy JSON-based - will be replaced)
def load_data():
    """Load data from JSON file - legacy function"""
    default_data = {
        "daily_checklists": {},
        "checklist_templates": {},
        "time_logs": {},
        "daily_metrics": {},
        "goals": {"weekly": {}, "monthly": {}, "yearly": {}},
        "total_points": 0
    }

    try:
        if DATA_FILE.exists():
            with open(DATA_FILE, 'r') as f:
                loaded_data = json.load(f)
                # Merge with defaults to ensure all keys exist
                for key in default_data:
                    if key not in loaded_data:
                        loaded_data[key] = default_data[key]
                return loaded_data
        else:
            return default_data
    except (json.JSONDecodeError, IOError):
        st.error(f"Error loading data from {DATA_FILE}. Using default data.")
        return default_data
    except Exception as e:
        st.error(f"Unexpected error loading data: {str(e)}")
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
render_sidebar(db_session)

# Main content
render_main_content(db_session)

# Analytics - Consolidated Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Analytics & Trends",
    "🔥 Habits & Streaks",
    "🎯 Goals",
    "🎯 Avatar Alignment"
])

with tab1:
    render_analytics_tab(db_session)

with tab2:
    render_habits_tab(db_session)

with tab3:
    render_goals_tab(db_session)

with tab4:
    render_avatar_tab(db_session)

# Footer
st.divider()
st.markdown("**💡 Tip:** Check the Trends & Insights tab to discover patterns and track your progress over time!")
