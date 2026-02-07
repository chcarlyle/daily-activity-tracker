"""
Backup and data import/export service for LifeTracker.
Handles database backups, JSON export, and data import.
"""
import json
import shutil
from datetime import datetime
from typing import Optional
import streamlit as st

from config.settings import DB_FILE, BACKUP_DIR


def create_backup() -> bool:
    """
    Create a timestamped backup of the database file.
    Maintains only the last 30 backups.

    Returns:
        True if backup successful, False otherwise
    """
    try:
        if not DB_FILE.exists():
            return False

        # Create backup directory if it doesn't exist
        BACKUP_DIR.mkdir(exist_ok=True)

        # Create timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"backup_{timestamp}.db"

        # Copy current database file to backup
        shutil.copy2(DB_FILE, backup_file)

        # Keep only last 30 backups
        backups = sorted(BACKUP_DIR.glob("backup_*.db"))
        if len(backups) > 30:
            for old_backup in backups[:-30]:
                old_backup.unlink()

        return True
    except Exception as e:
        st.error(f"Failed to create backup: {str(e)}")
        return False


def check_and_create_daily_backup(data: dict) -> bool:
    """
    Create a backup once per day (legacy JSON-based tracker).

    Args:
        data: Legacy data dictionary with last_backup_date field

    Returns:
        True if backup was created, False otherwise
    """
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


def export_data_for_download(data: dict) -> Optional[str]:
    """
    Export data as downloadable JSON string.

    Args:
        data: Dictionary to export

    Returns:
        JSON string or None if export failed
    """
    try:
        json_string = json.dumps(data, indent=2)
        return json_string
    except Exception as e:
        st.error(f"Failed to export data: {str(e)}")
        return None


def import_data_from_file(uploaded_file) -> Optional[dict]:
    """
    Import data from uploaded JSON file.
    Validates required fields before returning.

    Args:
        uploaded_file: Streamlit UploadedFile object

    Returns:
        Imported data dictionary or None if import failed
    """
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
