"""
Database connection management and initialization for LifeTracker.
"""
from datetime import datetime
from pathlib import Path
from typing import Tuple
import shutil
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from zoneinfo import ZoneInfo

from models import Base, User, SystemMetadata
from config.settings import DATABASE_URL, DB_FILE

# Global database engine and session factory
_engine = None
_SessionLocal = None


def init_database():
    """Initialize database engine and create all tables"""
    global _engine, _SessionLocal

    if _engine is None:
        # SQLite connection args to prevent stale connections and data loss
        connect_args = {
            "check_same_thread": False,  # Required for Streamlit's threading model
            "timeout": 30  # Increase timeout to 30 seconds
        }
        _engine = create_engine(
            DATABASE_URL,
            echo=False,
            connect_args=connect_args,
            pool_pre_ping=True,  # Verify connections are alive before using
            pool_recycle=3600  # Recycle connections after 1 hour
        )
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

        # Run category removal migration if needed
        # Note: This only runs once when tables are first created
        # The migration function itself checks if it's already been run

    return _engine


def get_db_session() -> Session:
    """Get a new database session"""
    if _SessionLocal is None:
        init_database()
    return _SessionLocal()


def migrate_remove_category_column() -> Tuple[bool, str]:
    """One-time migration to remove category column from database schema."""
    try:
        # Check if already completed
        session = get_db_session()
        metadata = session.query(SystemMetadata).filter_by(
            key='migration_remove_category'
        ).first()
        if metadata and metadata.value == 'completed':
            session.close()
            return True, "Migration already completed"

        # Create backup
        timestamp = datetime.now(ZoneInfo("America/New_York")).strftime("%Y%m%d_%H%M%S")
        backup_file = DB_FILE.parent / f"backup_before_category_removal_{timestamp}.db"

        # Check if database file exists
        if DB_FILE.exists():
            shutil.copy2(DB_FILE, backup_file)
        else:
            # No database yet, nothing to migrate
            session.close()
            return True, "No database to migrate"

        # Close all connections
        session.close()
        global _engine, _SessionLocal
        if _engine:
            _engine.dispose()
            _engine = None
            _SessionLocal = None

        # Execute SQLite migration
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Check if migration is needed (category column exists)
        cursor.execute("PRAGMA table_info(daily_tasks);")
        columns = [col[1] for col in cursor.fetchall()]
        if 'category' not in columns:
            # Already migrated
            conn.close()
            init_database()
            return True, "Migration not needed - category column already removed"

        # Drop category index
        cursor.execute("DROP INDEX IF EXISTS idx_daily_tasks_category;")

        # Recreate daily_tasks without category
        cursor.execute("""
            CREATE TABLE daily_tasks_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                task_name VARCHAR NOT NULL,
                points FLOAT NOT NULL,
                trackable BOOLEAN DEFAULT 0,
                unit VARCHAR,
                completed BOOLEAN DEFAULT 0,
                quantity FLOAT DEFAULT 1.0,
                completed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            INSERT INTO daily_tasks_new
            SELECT id, date, task_name, points, trackable, unit,
                   completed, quantity, completed_at, created_at
            FROM daily_tasks;
        """)

        cursor.execute("DROP TABLE daily_tasks;")
        cursor.execute("ALTER TABLE daily_tasks_new RENAME TO daily_tasks;")

        # Recreate indexes
        cursor.execute("CREATE INDEX idx_daily_tasks_date ON daily_tasks (date);")
        cursor.execute("CREATE INDEX idx_daily_tasks_completed ON daily_tasks (completed);")
        cursor.execute("CREATE INDEX idx_daily_tasks_date_completed ON daily_tasks (date, completed);")

        # Recreate task_templates without category
        cursor.execute("""
            CREATE TABLE task_templates_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name VARCHAR NOT NULL,
                task_name VARCHAR NOT NULL,
                points FLOAT NOT NULL,
                trackable BOOLEAN DEFAULT 0,
                unit VARCHAR,
                sort_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            INSERT INTO task_templates_new
            SELECT id, template_name, task_name, points, trackable,
                   unit, sort_order, created_at
            FROM task_templates;
        """)

        cursor.execute("DROP TABLE task_templates;")
        cursor.execute("ALTER TABLE task_templates_new RENAME TO task_templates;")
        cursor.execute("CREATE INDEX idx_task_templates_template ON task_templates (template_name);")

        conn.commit()
        conn.close()

        # Reinitialize database
        init_database()

        # Mark complete
        session = get_db_session()
        session.add(SystemMetadata(key='migration_remove_category', value='completed'))
        session.commit()
        session.close()

        return True, f"Migration successful. Backup: {backup_file.name}"

    except Exception as e:
        return False, f"Migration failed: {str(e)}"
