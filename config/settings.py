"""
Configuration settings for LifeTracker application.
"""
from pathlib import Path

# Database configuration
DB_FILE = Path("lifetracker.db")
DATABASE_URL = f"sqlite:///{DB_FILE}"

# Data storage path (legacy JSON for migration)
DATA_FILE = Path("dynamic_activity_log_2026.json")

# Backup directory
BACKUP_DIR = Path("backups")

# Ensure backup directory exists
BACKUP_DIR.mkdir(exist_ok=True)

# Default timezone
DEFAULT_TIMEZONE = 'America/New_York'
