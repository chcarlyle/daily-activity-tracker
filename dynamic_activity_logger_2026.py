import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import shutil

# Page config - must be first Streamlit command
st.set_page_config(
    page_title="Daily Activity Tracker",
    page_icon="⭐",
    layout="wide",
    initial_sidebar_state="collapsed",  # Hide sidebar on mobile by default
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "Personal Daily Activity Tracker"
    }
)

# Mobile optimization CSS
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* PWA meta tags */
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Activity Tracker">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    
    /* Mobile-friendly touch targets */
    .stCheckbox {
        font-size: 18px !important;
        padding: 12px 0 !important;
    }
    
    .stCheckbox > label {
        padding: 10px !important;
    }
    
    /* Bigger buttons */
    .stButton button {
        height: 48px !important;
        font-size: 16px !important;
        border-radius: 8px !important;
    }
    
    /* Better spacing on mobile */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem 1rem 10rem 1rem !important;
        }
        
        /* Stack columns on mobile */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }
    }
    
    /* Number inputs more touch-friendly */
    .stNumberInput input {
        height: 44px !important;
        font-size: 18px !important;
    }
    
    /* Better form styling */
    .stTextInput input, .stSelectbox select {
        height: 44px !important;
        font-size: 16px !important;
    }
</style>
""", unsafe_allow_html=True)

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
# DATABASE MODELS (SQLAlchemy)
# ============================================================================

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, DateTime, Text, ForeignKey, func, Index, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from typing import Optional, List, Dict, Any, Tuple, Union

Base = declarative_base()

class User(Base):
    """User configuration and totals"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    total_points = Column(Float, default=0.0)
    timezone = Column(String, default='America/New_York')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TaskTemplate(Base):
    """Task templates for quick daily task creation"""
    __tablename__ = 'task_templates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_name = Column(String, nullable=False)
    task_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    points = Column(Float, nullable=False)
    trackable = Column(Boolean, default=False)
    unit = Column(String, nullable=True)  # e.g., 'hours', 'reps', 'times'
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(category.in_(['Spiritual', 'Social', 'Physical', 'Intellectual', 'Other'])),
        Index('idx_task_templates_template', 'template_name'),
    )

class DailyTask(Base):
    """Individual task instances for specific dates"""
    __tablename__ = 'daily_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    task_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    points = Column(Float, nullable=False)
    trackable = Column(Boolean, default=False)
    unit = Column(String, nullable=True)
    completed = Column(Boolean, default=False)
    quantity = Column(Float, default=1.0)  # multiplier for trackable tasks
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(category.in_(['Spiritual', 'Social', 'Physical', 'Intellectual', 'Other'])),
        Index('idx_daily_tasks_date', 'date', postgresql_using='btree'),
        Index('idx_daily_tasks_category', 'category'),
        Index('idx_daily_tasks_completed', 'completed'),
        Index('idx_daily_tasks_date_completed', 'date', 'completed'),  # Composite for streak queries
    )

class DailyMetric(Base):
    """Daily mood and energy tracking"""
    __tablename__ = 'daily_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, unique=True, nullable=False)
    mood = Column(Integer, nullable=True)
    energy = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint('mood >= 1 AND mood <= 10'),
        CheckConstraint('energy >= 1 AND energy <= 10'),
        Index('idx_daily_metrics_date', 'date', postgresql_using='btree'),
    )

class Goal(Base):
    """User goals (weekly, monthly, yearly)"""
    __tablename__ = 'goals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    goal_type = Column(String, nullable=False)  # 'weekly', 'monthly', 'yearly'
    target_points = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    created_date = Column(Date, nullable=False)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(goal_type.in_(['weekly', 'monthly', 'yearly'])),
        Index('idx_goals_type', 'goal_type'),
        Index('idx_goals_completed', 'completed'),
    )

class Avatar(Base):
    """User's ideal self definition for LLM alignment analysis"""
    __tablename__ = 'avatars'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, default='My Ideal Self')
    description = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    alignments = relationship('AvatarAlignment', back_populates='avatar', cascade='all, delete-orphan')

class AvatarAlignment(Base):
    """LLM analysis results of user behavior vs avatar"""
    __tablename__ = 'avatar_alignments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    avatar_id = Column(Integer, ForeignKey('avatars.id', ondelete='CASCADE'), nullable=False)
    analysis_date = Column(Date, nullable=False)
    start_date = Column(Date, nullable=False)  # beginning of analyzed period
    end_date = Column(Date, nullable=False)    # end of analyzed period
    alignment_score = Column(Float, nullable=True)  # 0-100 score from LLM
    alignment_summary = Column(Text, nullable=True)  # LLM's summary
    recommendations = Column(Text, nullable=True)  # JSON array of recommendations
    trend = Column(String, nullable=True)  # 'improving', 'declining', 'stable'
    llm_model = Column(String, nullable=True)  # e.g., 'claude-3-sonnet'
    llm_prompt_version = Column(String, nullable=True)  # track prompt changes
    created_at = Column(DateTime, default=datetime.utcnow)

    avatar = relationship('Avatar', back_populates='alignments')

    __table_args__ = (
        Index('idx_avatar_alignments_date', 'analysis_date', postgresql_using='btree'),
        Index('idx_avatar_alignments_avatar', 'avatar_id'),
    )

class StreakCache(Base):
    """Cached streak calculations for performance"""
    __tablename__ = 'streak_cache'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String, unique=True, nullable=False)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_calculated_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_streak_cache_task', 'task_name'),
    )

class SystemMetadata(Base):
    """System metadata and configuration"""
    __tablename__ = 'system_metadata'

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database configuration
DB_FILE = Path("lifetracker.db")
DATABASE_URL = f"sqlite:///{DB_FILE}"

# Data storage path (legacy JSON for migration)
DATA_FILE = Path("dynamic_activity_log_2026.json")
BACKUP_DIR = Path("backups")

# Initialize data structure
def load_data():
    """Load data with error handling and automatic recovery"""
    default_data = {
        "daily_checklists": {},  # {date: {tasks: [], completed: [], quantities: {task_name: count}}}
        "checklist_templates": {
            "Morning Routine": [
                {"name": "Scripture Study (15 min)", "category": "Spiritual", "points": 15},
                {"name": "Personal Prayer (morning)", "category": "Spiritual", "points": 5},
                {"name": "Brush Teeth (morning)", "category": "Physical", "points": 1},
                {"name": "Shower", "category": "Physical", "points": 3},
                {"name": "Make Bed", "category": "Other", "points": 5},
            ],
            "Evening Routine": [
                {"name": "Personal Prayer (evening)", "category": "Spiritual", "points": 5},
                {"name": "Reading (15 min)", "category": "Intellectual", "points": 10},
                {"name": "Brush Teeth (evening)", "category": "Physical", "points": 2},
            ],
            "Personal Development": [
                {"name": "Job Application", "category": "Intellectual", "points": 1, "trackable": True, "unit": "applications"},
                {"name": "Independent Project (30 min)", "category": "Intellectual", "points": 10, "trackable": False},
                {"name": "Piano", "category": "Intellectual", "points": 10, "trackable": False},
            ],
            "Negative Habits": [
                {"name": "Phone Screen Time (per hour)", "category": "Spiritual", "points": -2.5, "trackable": True, "unit": "hours"},
                {"name": "Phone Screen Time After Bed", "category": "Spiritual", "points": -5, "trackable": True, "unit": "hours"},
                {"name": "18+ Content", "category": "Spiritual", "points": -10, "trackable": True, "unit": "events"},
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

def create_backup():
    """Create a timestamped backup of the data file"""
    try:
        if not DATA_FILE.exists():
            return False

        # Create backup directory if it doesn't exist
        BACKUP_DIR.mkdir(exist_ok=True)

        # Create timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"backup_{timestamp}.json"

        # Copy current data file to backup
        shutil.copy2(DATA_FILE, backup_file)

        # Keep only last 30 backups
        backups = sorted(BACKUP_DIR.glob("backup_*.json"))
        if len(backups) > 30:
            for old_backup in backups[:-30]:
                old_backup.unlink()

        return True
    except Exception as e:
        st.error(f"Failed to create backup: {str(e)}")
        return False

def check_and_create_daily_backup(data):
    """Create a backup once per day"""
    try:
        today = datetime.now().strftime("%Y-%m-%d")

        # Check if we already backed up today
        if "last_backup_date" not in data:
            data["last_backup_date"] = None

        if data["last_backup_date"] != today:
            if create_backup():
                data["last_backup_date"] = today
                return True
    except Exception:
        pass
    return False

def export_data_for_download(data):
    """Export data as downloadable JSON"""
    try:
        json_string = json.dumps(data, indent=2)
        return json_string
    except Exception as e:
        st.error(f"Failed to export data: {str(e)}")
        return None

def import_data_from_file(uploaded_file):
    """Import data from uploaded JSON file"""
    try:
        content = uploaded_file.read().decode('utf-8')
        imported_data = json.loads(content)

        # Basic validation - check for required keys
        required_keys = ["daily_checklists", "checklist_templates"]
        if not all(key in imported_data for key in required_keys):
            st.error("Invalid backup file: missing required data fields")
            return None

        return imported_data
    except json.JSONDecodeError:
        st.error("Invalid JSON file")
        return None
    except Exception as e:
        st.error(f"Failed to import data: {str(e)}")
        return None

# Load data
data = load_data()

# Create daily backup if needed
check_and_create_daily_backup(data)

# ============================================================================
# DATABASE HELPER FUNCTIONS
# ============================================================================

# Global database engine and session factory
_engine = None
_SessionLocal = None

def init_database():
    """Initialize database engine and create all tables"""
    global _engine, _SessionLocal

    if _engine is None:
        _engine = create_engine(DATABASE_URL, echo=False)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        Base.metadata.create_all(bind=_engine)

        # Initialize user if not exists
        session = _SessionLocal()
        try:
            user = session.query(User).first()
            if not user:
                user = User(total_points=0.0)
                session.add(user)
                session.commit()
        finally:
            session.close()

    return _engine

def get_db_session() -> Session:
    """Get a new database session"""
    if _SessionLocal is None:
        init_database()
    return _SessionLocal()

# ============================================================================
# CRUD Operations for Daily Tasks
# ============================================================================

def save_daily_task(session: Session, date: datetime.date, task_name: str, category: str,
                    points: float, trackable: bool = False, unit: str = None,
                    quantity: float = 1.0, completed: bool = False) -> DailyTask:
    """Create or update a daily task"""
    task = session.query(DailyTask).filter_by(date=date, task_name=task_name).first()

    if task:
        # Update existing task
        task.category = category
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
            category=category,
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

# ============================================================================
# CRUD Operations for Templates
# ============================================================================

def save_task_template(session: Session, template_name: str, task_name: str,
                      category: str, points: float, trackable: bool = False,
                      unit: str = None, sort_order: int = 0) -> TaskTemplate:
    """Create a task template"""
    template = TaskTemplate(
        template_name=template_name,
        task_name=task_name,
        category=category,
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
                "category": t.category,
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

# ============================================================================
# CRUD Operations for Metrics
# ============================================================================

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

# ============================================================================
# CRUD Operations for Goals
# ============================================================================

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

# ============================================================================
# CRUD Operations for Avatars
# ============================================================================

def save_avatar(session: Session, name: str, description: str) -> Avatar:
    """Create or update avatar (deactivates previous avatars)"""
    # Deactivate all existing avatars
    session.query(Avatar).update({"is_active": False})

    # Create new active avatar
    avatar = Avatar(name=name, description=description, is_active=True)
    session.add(avatar)
    session.commit()
    return avatar

def get_active_avatar(session: Session) -> Optional[Avatar]:
    """Get the currently active avatar"""
    return session.query(Avatar).filter_by(is_active=True).first()

def delete_avatar(session: Session, avatar_id: int) -> bool:
    """Delete avatar and its alignments (cascade)"""
    avatar = session.query(Avatar).filter_by(id=avatar_id).first()

    if avatar:
        session.delete(avatar)
        session.commit()
        return True
    return False

# ============================================================================
# DATABASE ANALYTICS FUNCTIONS
# ============================================================================

def get_day_points_db(session: Session, date: datetime.date, separate: bool = False) -> Union[float, Tuple[float, float]]:
    """Calculate points for a day from database, optionally separating positive and negative"""
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

def get_category_points_db(session: Session, date: datetime.date, category: str) -> float:
    """Get points for a specific category on a date from database"""
    tasks = session.query(DailyTask).filter_by(
        date=date,
        category=category,
        completed=True
    ).all()

    total = 0.0
    for task in tasks:
        points = task.points
        if task.trackable:
            points = points * task.quantity
        total += points

    return total

def get_task_streak_db(session: Session, task_name: str, end_date: datetime.date, days_back: int = 90) -> Tuple[int, int]:
    """Calculate current streak and longest streak for a specific task from database"""
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

def get_positive_day_streak_db(session: Session, end_date: datetime.date, days_back: int = 90) -> int:
    """Calculate current streak of positive net point days from database"""
    current_streak = 0

    for i in range(days_back):
        check_date = end_date - timedelta(days=i)
        net_points = get_day_points_db(session, check_date)

        # Check if there are any tasks for this day
        has_tasks = session.query(DailyTask).filter_by(date=check_date).count() > 0

        if net_points > 0:
            current_streak += 1
        elif has_tasks:
            # Day exists with tasks but wasn't positive - break streak
            break

    return current_streak

def get_task_consistency_db(session: Session, task_name: str, end_date: datetime.date, days_back: int = 30) -> float:
    """Calculate consistency percentage for a task over a period from database"""
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

def get_all_unique_tasks_db(session: Session, days_back: int = 30) -> List[str]:
    """Get all unique task names from recent history from database"""
    end_date = datetime.now(ZoneInfo("America/New_York")).date()
    start_date = end_date - timedelta(days=days_back)

    result = session.query(DailyTask.task_name).filter(
        DailyTask.date >= start_date,
        DailyTask.date <= end_date
    ).distinct().all()

    return sorted([r[0] for r in result])

def prepare_avatar_analysis_data(session: Session, start_date: datetime.date, end_date: datetime.date) -> Dict[str, Any]:
    """Format tracking data for LLM avatar alignment analysis"""
    # Get all tasks in the period
    tasks = get_tasks_in_range(session, start_date, end_date)
    metrics = get_metrics_in_range(session, start_date, end_date)

    # Calculate task patterns
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.completed)
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Category breakdown
    categories = {}
    for category in ['Spiritual', 'Social', 'Physical', 'Intellectual', 'Other']:
        cat_tasks = [t for t in tasks if t.category == category]
        cat_completed = [t for t in cat_tasks if t.completed]
        cat_points = sum(t.points * t.quantity for t in cat_completed)

        categories[category] = {
            "completed": len(cat_completed),
            "total": len(cat_tasks),
            "points": cat_points
        }

    # Streaks
    current_positive_days = get_positive_day_streak_db(session, end_date)

    # Get top habits (tasks with highest completion rate)
    unique_tasks = get_all_unique_tasks_db(session, (end_date - start_date).days)
    task_consistencies = [
        (task_name, get_task_consistency_db(session, task_name, end_date, (end_date - start_date).days))
        for task_name in unique_tasks
    ]
    task_consistencies.sort(key=lambda x: x[1], reverse=True)
    top_habits = [name for name, _ in task_consistencies[:5] if _ > 50]

    # Mood and energy
    mood_values = [m.mood for m in metrics if m.mood is not None]
    energy_values = [m.energy for m in metrics if m.energy is not None]

    avg_mood = sum(mood_values) / len(mood_values) if mood_values else None
    avg_energy = sum(energy_values) / len(energy_values) if energy_values else None

    # Negative habits
    negative_tasks = [t for t in tasks if t.completed and t.points < 0]
    negative_point_sources = {}
    for task in negative_tasks:
        points = task.points * task.quantity
        if task.task_name in negative_point_sources:
            negative_point_sources[task.task_name] += points
        else:
            negative_point_sources[task.task_name] = points

    negative_list = [f"{name}: {pts:+.1f}pts" for name, pts in sorted(negative_point_sources.items(), key=lambda x: x[1])]

    # Days with negative net points
    days_with_negative_net = 0
    current_day = start_date
    while current_day <= end_date:
        if get_day_points_db(session, current_day) < 0:
            days_with_negative_net += 1
        current_day += timedelta(days=1)

    return {
        "task_patterns": {
            "total_tasks": total_tasks,
            "completion_rate": completion_rate,
            "by_category": categories,
            "streaks": {
                "current_positive_days": current_positive_days,
                "top_habits": top_habits
            }
        },
        "wellbeing": {
            "avg_mood": avg_mood,
            "avg_energy": avg_energy
        },
        "challenges": {
            "negative_point_sources": negative_list,
            "days_with_negative_net": days_with_negative_net
        }
    }

# AVATAR ALIGNMENT PROMPT TEMPLATE (for future Claude API integration)
#
# def generate_avatar_prompt(avatar_description: str, analysis_data: dict) -> str:
#     return f"""You are analyzing whether a user's behavior aligns with their ideal self.
#
# Avatar (Ideal Self):
# {avatar_description}
#
# Behavior Data (Last 30 days):
# {json.dumps(analysis_data, indent=2)}
#
# Analyze and return JSON:
# {{
#   "alignment_score": 0-100,
#   "summary": "2-3 sentences on alignment",
#   "recommendations": ["specific action 1", "specific action 2", "specific action 3"],
#   "trend": "improving|declining|stable",
#   "key_strengths": ["strength 1", "strength 2"],
#   "areas_for_growth": ["area 1", "area 2"]
# }}
# """
#
# def analyze_avatar_alignment(session: Session, avatar_id: int, start_date: datetime.date, end_date: datetime.date):
#     """Call Claude API to analyze avatar alignment (FUTURE IMPLEMENTATION)"""
#     # avatar = session.query(Avatar).filter_by(id=avatar_id).first()
#     # analysis_data = prepare_avatar_analysis_data(session, start_date, end_date)
#     # prompt = generate_avatar_prompt(avatar.description, analysis_data)
#     #
#     # # Call Anthropic API
#     # import anthropic
#     # client = anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"])
#     # response = client.messages.create(
#     #     model="claude-3-5-sonnet-20241022",
#     #     max_tokens=1024,
#     #     messages=[{"role": "user", "content": prompt}]
#     # )
#     #
#     # # Parse response and save to database
#     # result = json.loads(response.content[0].text)
#     # alignment = AvatarAlignment(
#     #     avatar_id=avatar_id,
#     #     analysis_date=datetime.now().date(),
#     #     start_date=start_date,
#     #     end_date=end_date,
#     #     alignment_score=result['alignment_score'],
#     #     alignment_summary=result['summary'],
#     #     recommendations=json.dumps(result['recommendations']),
#     #     trend=result['trend'],
#     #     llm_model='claude-3-5-sonnet',
#     #     llm_prompt_version='v1.0'
#     # )
#     # session.add(alignment)
#     # session.commit()
#     pass

# ============================================================================
# DATABASE MIGRATION LOGIC
# ============================================================================

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
                        category=task['category'],
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
                            category=task['category'],
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

def export_database_to_json(session: Session) -> str:
    """Export database to JSON format (backward compatibility)"""
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
            "category": task.category,
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

def get_category_points(date_str, category):
    """Get points for a specific category on a date"""
    if date_str not in data["daily_checklists"]:
        return 0

    completed = data["daily_checklists"][date_str].get("completed", [])
    tasks = data["daily_checklists"][date_str].get("tasks", [])
    quantities = data["daily_checklists"][date_str].get("quantities", {})

    total = 0
    for task in tasks:
        if task["name"] in completed and task["category"] == category:
            points = task["points"]
            if task.get("trackable", False):
                quantity = quantities.get(task["name"], 1)
                points = points * quantity
            total += points

    return total

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
                    task_category = st.selectbox("Category",
                        ["Spiritual", "Social", "Physical", "Intellectual", "Other"])
                with col2:
                    task_points = st.number_input("Points", min_value=-50, max_value=50, value=10)
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
                            category=task_category,
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
        uploaded_file = st.file_uploader("Upload backup JSON", type=['json'])
        if uploaded_file is not None:
            imported_data = import_data_from_file(uploaded_file)
            if imported_data:
                if st.button("⚠️ Replace Current Data", type="primary"):
                    # Create backup before importing
                    create_backup()
                    data.clear()
                    data.update(imported_data)
                    save_data(data)
                    st.success("✅ Data imported successfully!")
                    st.rerun()
                st.warning("This will replace all current data. A backup will be created first.")

    # LLM Export
    with st.expander("🤖 Export for LLM"):
        if st.button("Generate Export"):
            st.info("Export functionality available - see original version")

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
positive_pts, negative_pts = get_day_points_db(db_session, today, separate=True)
net_pts = positive_pts + negative_pts

# Get today's tasks for completion rate
today_tasks = get_daily_tasks(db_session, today)
completion_rate = 0
if today_tasks:
    completed_count = sum(1 for t in today_tasks if t.completed)
    completion_rate = (completed_count / len(today_tasks)) * 100

positive_streak = get_positive_day_streak_db(db_session, today_actual)

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
            quick_col1, quick_col2 = st.columns([2, 1])
            with quick_col1:
                quick_cat = st.selectbox("Category", ["Spiritual", "Social", "Physical", "Intellectual", "Other"])
            with quick_col2:
                quick_pts = st.number_input("Points", -50, 50, 10)

            if st.form_submit_button("Add Task", use_container_width=True):
                if quick_name:
                    save_daily_task(
                        db_session,
                        date=today,
                        task_name=quick_name,
                        category=quick_cat,
                        points=quick_pts,
                        trackable=False,
                        completed=False
                    )
                    st.rerun()

# Task List - Clean and simple
st.markdown("### Tasks")

if not today_tasks:
    st.info("No tasks yet - add some using the button above!")
else:
    # Group by category
    categories = {}
    for task in today_tasks:
        cat = task.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(task)

    # Simple list view - better for mobile
    for category, tasks in categories.items():
        emoji = {"Spiritual": "✨", "Social": "👥", "Physical": "💪",
                "Intellectual": "🧠", "Other": "🏠"}.get(category, "📌")

        completed_count = len([t for t in tasks if t.completed])
        with st.expander(f"{emoji} **{category}** ({completed_count}/{len(tasks)})", expanded=True):
            for task in tasks:
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

            # Simple action row
            st.write("")
            action_cols = st.columns(len(tasks))
            for idx, task in enumerate(tasks):
                with action_cols[idx]:
                    if st.button("🗑️", key=f"del_{today_str}_{task.task_name}_{idx}", help=f"Delete {task.task_name}"):
                        delete_daily_task(db_session, today, task.task_name)
                        st.rerun()

st.markdown("---")

# Analytics - Consolidated Tabs
tab1, tab2, tab3 = st.tabs([
    "📊 Analytics & Trends",
    "🔥 Habits & Streaks",
    "🎯 Goals"
])

with tab1:
    st.header("Trends & Insights")
    st.caption("Track your progress and discover patterns")

    # Last 30 days
    chart_data = []
    for i in range(30):
        check_date = today_actual - timedelta(days=29-i)
        date_str = check_date.strftime("%Y-%m-%d")

        pos, neg = get_day_points(date_str, separate=True)

        # Get mood and energy if available
        mood = data["daily_metrics"].get(date_str, {}).get("mood", None)
        energy = data["daily_metrics"].get(date_str, {}).get("energy", None)

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
    st.header("Category Balance")
    st.caption("See how you're doing across different life areas")

    # Calculate category stats for last 30 days
    categories = ["Spiritual", "Social", "Physical", "Intellectual", "Other"]
    category_data = {cat: [] for cat in categories}

    for i in range(30):
        check_date = today_actual - timedelta(days=29-i)
        date_str = check_date.strftime("%Y-%m-%d")

        for category in categories:
            points = get_category_points(date_str, category)
            category_data[category].append({
                "Date": check_date,
                "Points": points
            })

    # Total points by category
    st.subheader("Total Points by Category (30 Days)")

    category_totals = []
    for category in categories:
        total = sum(d["Points"] for d in category_data[category])
        avg = total / 30
        category_totals.append({
            "Category": category,
            "Total": total,
            "Average/Day": avg
        })

    df_totals = pd.DataFrame(category_totals)

    fig = go.Figure(data=[
        go.Bar(
            x=df_totals['Category'],
            y=df_totals['Total'],
            marker_color=['#9C27B0', '#2196F3', '#4CAF50', '#FF9800', '#607D8B'],
            text=df_totals['Total'].round(1),
            textposition='outside'
        )
    ])

    fig.update_layout(
        xaxis_title='Category',
        yaxis_title='Total Points',
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # Category breakdown table
    st.dataframe(df_totals, use_container_width=True, hide_index=True)

    # Category trends over time
    st.subheader("Category Trends")

    # Create line chart for each category
    trend_data = []
    for category in categories:
        for day_data in category_data[category]:
            trend_data.append({
                "Date": day_data["Date"],
                "Category": category,
                "Points": day_data["Points"]
            })

    df_trends = pd.DataFrame(trend_data)

    fig = go.Figure()

    colors = {'Spiritual': '#9C27B0', 'Social': '#2196F3', 'Physical': '#4CAF50',
              'Intellectual': '#FF9800', 'Other': '#607D8B'}

    for category in categories:
        cat_data = df_trends[df_trends['Category'] == category]
        fig.add_trace(go.Scatter(
            x=cat_data['Date'],
            y=cat_data['Points'],
            mode='lines',
            name=category,
            line=dict(color=colors[category], width=2)
        ))

    fig.update_layout(
        xaxis_title='Date',
        yaxis_title='Points',
        hovermode='x unified'
    )

    st.plotly_chart(fig, use_container_width=True)

    # Balance insights
    st.subheader("⚖️ Balance Insights")

    balance_insights = []

    # Find strongest and weakest categories
    strongest = df_totals.loc[df_totals['Total'].idxmax()]
    weakest = df_totals.loc[df_totals['Total'].idxmin()]

    if strongest['Total'] > 0:
        balance_insights.append(f"💪 **{strongest['Category']}** is your strongest area with {strongest['Total']:.1f} total points")

    if weakest['Total'] < strongest['Total'] * 0.3:
        balance_insights.append(f"⚠️ **{weakest['Category']}** needs attention - only {weakest['Total']:.1f} points vs {strongest['Total']:.1f} in {strongest['Category']}")

    # Check for balance
    std_dev = df_totals['Total'].std()
    mean_val = df_totals['Total'].mean()
    if mean_val > 0 and std_dev / mean_val < 0.5:
        balance_insights.append("✅ Good balance across categories!")
    elif mean_val > 0:
        balance_insights.append("📊 Your focus is concentrated in a few areas - consider broadening")

    # Category-specific insights
    for _, row in df_totals.iterrows():
        if row['Average/Day'] < 1 and row['Total'] > 0:
            balance_insights.append(f"💡 Tip: You're averaging less than 1 point/day in **{row['Category']}**")

    for insight in balance_insights:
        st.markdown(f"- {insight}")

with tab2:
    st.header("🔥 Streaks & Habits")
    st.caption("Track your consistency and build strong habits")

    # Overall positive day streak
    positive_streak = get_positive_day_streak(today_actual)

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
            date_str = check_date.strftime("%Y-%m-%d")
            if get_day_points(date_str) > 0:
                temp_streak += 1
                if temp_streak > best_streak:
                    best_streak = temp_streak
            elif date_str in data["daily_checklists"] and data["daily_checklists"][date_str].get("tasks"):
                temp_streak = 0
        st.metric("⭐ Best Streak Ever", f"{best_streak} days")

    with col3:
        # Overall consistency (days with positive net points)
        logged_days = 0
        positive_days = 0
        for i in range(30):
            check_date = today_actual - timedelta(days=i)
            date_str = check_date.strftime("%Y-%m-%d")
            if date_str in data["daily_checklists"] and data["daily_checklists"][date_str].get("tasks"):
                logged_days += 1
                if get_day_points(date_str) > 0:
                    positive_days += 1
        consistency = (positive_days / logged_days * 100) if logged_days > 0 else 0
        st.metric("📈 30-Day Win Rate", f"{consistency:.0f}%")

    st.divider()

    # Individual task streaks and consistency
    st.subheader("📋 Task Performance (Last 30 Days)")

    unique_tasks = get_all_unique_tasks(30)

    if unique_tasks:
        # Calculate stats for each task
        task_stats = []
        for task_name in unique_tasks:
            current_streak, longest_streak = get_task_streak(task_name, today_actual, 90)
            consistency = get_task_consistency(task_name, today_actual, 30)

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

    # Display existing goals
    if data["goals"][goal_key]:
        st.write(f"**Current {goal_type} Goals:**")
        goals_to_delete = []
        for goal_name, goal_info in data["goals"][goal_key].items():
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
                                date_str = check_date.strftime("%Y-%m-%d")
                                current += get_day_points(date_str)
                    elif goal_type == "Monthly":
                        month_start = today_actual.replace(day=1)
                        current = 0
                        check_date = month_start
                        while check_date <= today_actual:
                            date_str = check_date.strftime("%Y-%m-%d")
                            current += get_day_points(date_str)
                            check_date += timedelta(days=1)
                    else:  # Yearly
                        year_start = today_actual.replace(month=1, day=1)
                        current = 0
                        check_date = year_start
                        while check_date <= today_actual:
                            date_str = check_date.strftime("%Y-%m-%d")
                            current += get_day_points(date_str)
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
            del data["goals"][goal_key][goal_name]
            save_data(data)
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
            data["goals"][goal_key][new_goal_name] = {
                "type": "points",
                "target": new_goal_target,
                "created": datetime.now().strftime("%Y-%m-%d")
            }
            save_data(data)
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
            date_str = check_date.strftime("%Y-%m-%d")
            if date_str in data["daily_checklists"] and data["daily_checklists"][date_str].get("tasks"):
                week_logged_days += 1
                day_points = get_day_points(date_str)
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
            date_str = check_date.strftime("%Y-%m-%d")

            if date_str in data["daily_checklists"] and data["daily_checklists"][date_str]["tasks"]:
                st.write(f"**{check_date.strftime('%A, %B %d')}**")
                pos, neg = get_day_points(date_str, separate=True)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Positive", f"+{pos:.1f}")
                with col2:
                    st.metric("Negative", f"{neg:.1f}")
                with col3:
                    st.metric("Net", f"{pos+neg:+.1f}")
                with col4:
                    # Quick action to copy all tasks to today
                    if st.button("📋 Copy All to Today", key=f"copy_all_{date_str}"):
                        today_str_actual = today_actual.strftime("%Y-%m-%d")
                        if today_str_actual not in data["daily_checklists"]:
                            data["daily_checklists"][today_str_actual] = {"tasks": [], "completed": [], "quantities": {}}

                        existing_names = {t["name"] for t in data["daily_checklists"][today_str_actual]["tasks"]}
                        tasks_to_copy = data["daily_checklists"][date_str]["tasks"]

                        for task in tasks_to_copy:
                            if task["name"] not in existing_names:
                                data["daily_checklists"][today_str_actual]["tasks"].append(task.copy())

                        save_data(data)
                        st.success(f"✅ Copied {len(tasks_to_copy)} tasks to today!")
                        st.rerun()

                completed = data["daily_checklists"][date_str].get("completed", [])
                tasks = data["daily_checklists"][date_str]["tasks"]
                quantities = data["daily_checklists"][date_str].get("quantities", {})

                st.write("**Completed:**")
                for task in tasks:
                    if task["name"] in completed:
                        points = task["points"]
                        display_text = f"✅ {task['name']}"

                        if task.get("trackable", False):
                            quantity = quantities.get(task["name"], 1)
                            points = points * quantity
                            display_text += f" (×{quantity:.1f})"

                        display_text += f" ({points:+.1f}pts)"

                        # Add button to copy individual task to today
                        task_col1, task_col2 = st.columns([4, 1])
                        with task_col1:
                            st.write(display_text)
                        with task_col2:
                            if st.button("📋", key=f"copy_{date_str}_{task['name']}", help="Copy to today"):
                                today_str_actual = today_actual.strftime("%Y-%m-%d")
                                if today_str_actual not in data["daily_checklists"]:
                                    data["daily_checklists"][today_str_actual] = {"tasks": [], "completed": [], "quantities": {}}

                                existing_names = {t["name"] for t in data["daily_checklists"][today_str_actual]["tasks"]}
                                if task["name"] not in existing_names:
                                    data["daily_checklists"][today_str_actual]["tasks"].append(task.copy())
                                    save_data(data)
                                    st.rerun()

                st.write("**Not Completed:**")
                for task in tasks:
                    if task["name"] not in completed:
                        st.write(f"❌ {task['name']} ({task['points']:+}pts)")

# Footer
st.divider()
st.markdown("**💡 Tip:** Check the Trends & Insights tab to discover patterns and track your progress over time!")
