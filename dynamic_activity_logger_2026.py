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

# Data storage path
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

# Helper functions
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

# Sidebar
with st.sidebar:
    st.title("⭐ Daily Tracker")
    
    # Display current stats (removed level/progress bar)
    st.metric("Total Points", data.get("total_points", 0))
    
    st.divider()
    
    # Manage Templates
    with st.expander("📋 Manage Templates"):
        st.write("**Create/Edit Task Templates**")
        
        template_name = st.text_input("Template Name", placeholder="e.g., Morning Routine")
        
        if template_name:
            if template_name not in data["checklist_templates"]:
                data["checklist_templates"][template_name] = []
            
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
                    new_task = {
                        "name": task_name,
                        "category": task_category,
                        "points": task_points,
                        "trackable": task_trackable
                    }
                    if task_trackable:
                        new_task["unit"] = task_unit
                    
                    data["checklist_templates"][template_name].append(new_task)
                    save_data(data)
                    st.success(f"Added '{task_name}' to {template_name}")
                    st.rerun()
            
            # Show existing tasks
            if data["checklist_templates"][template_name]:
                for idx, task in enumerate(data["checklist_templates"][template_name]):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"• {task['name']} ({task['points']}pts)")
                    with col2:
                        if st.button("🗑️", key=f"del_{template_name}_{idx}"):
                            data["checklist_templates"][template_name].pop(idx)
                            save_data(data)
                            st.rerun()
    
    # Backup & Export
    with st.expander("💾 Backup & Export"):
        st.write("**Export Data**")
        if st.button("📥 Download Backup (JSON)", use_container_width=True):
            json_string = export_data_for_download(data)
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
st.title("📖 Dynamic Daily Activity Logger")
st.markdown("*Flexible day-by-day tracking with custom checklists*")

# Date Navigation
st.header("📅 Date Selection")

# Initialize session state for selected date
if "selected_date" not in st.session_state:
    st.session_state.selected_date = datetime.now(ZoneInfo("America/New_York")).date()

today_actual = datetime.now(ZoneInfo("America/New_York")).date()

# Date navigation controls
col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

with col1:
    if st.button("⏮️ -7 Days"):
        st.session_state.selected_date = st.session_state.selected_date - timedelta(days=7)
        st.rerun()

with col2:
    if st.button("◀️ Previous"):
        st.session_state.selected_date = st.session_state.selected_date - timedelta(days=1)
        st.rerun()

with col3:
    selected_date = st.date_input(
        "Select Date",
        value=st.session_state.selected_date,
        key="date_picker"
    )
    if selected_date != st.session_state.selected_date:
        st.session_state.selected_date = selected_date
        st.rerun()

with col4:
    if st.button("▶️ Next"):
        next_date = st.session_state.selected_date + timedelta(days=1)
        st.session_state.selected_date = next_date
        st.rerun()

with col5:
    if st.button("📍 Today"):
        st.session_state.selected_date = today_actual
        st.rerun()

# Use selected date instead of today
today = st.session_state.selected_date
today_str = today.strftime("%Y-%m-%d")

# Show if viewing past/future
if today < today_actual:
    days_ago = (today_actual - today).days
    st.info(f"📆 Viewing {days_ago} day{'s' if days_ago > 1 else ''} ago")
elif today > today_actual:
    days_ahead = (today - today_actual).days
    st.info(f"📅 Planning ahead: {days_ahead} day{'s' if days_ahead > 1 else ''} from now")

# Initialize today's data
if today_str not in data["daily_checklists"]:
    data["daily_checklists"][today_str] = {"tasks": [], "completed": [], "quantities": {}}
if today_str not in data["daily_metrics"]:
    data["daily_metrics"][today_str] = {"mood": 5, "energy": 5, "notes": ""}

# Day Context
date_display = "Today" if today == today_actual else today.strftime("%A, %B %d, %Y")
st.header(f"🗓️ {date_display}")

col1, col2 = st.columns(2)

with col1:
    mood_val = st.slider("😊 Mood", 1, 10, value=data["daily_metrics"][today_str].get("mood", 5))
    if mood_val != data["daily_metrics"][today_str].get("mood"):
        data["daily_metrics"][today_str]["mood"] = mood_val
        save_data(data)

with col2:
    energy_val = st.slider("⚡ Energy", 1, 10, value=data["daily_metrics"][today_str].get("energy", 5))
    if energy_val != data["daily_metrics"][today_str].get("energy"):
        data["daily_metrics"][today_str]["energy"] = energy_val
        save_data(data)

st.divider()

# Build Today's Checklist
checklist_header = "Today's Checklist" if today == today_actual else f"Checklist for {today.strftime('%b %d')}"
st.header(f"✅ {checklist_header}")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Add Tasks from Templates")
    
    template_cols = st.columns(len(data["checklist_templates"]))
    
    for idx, (template_name, tasks) in enumerate(data["checklist_templates"].items()):
        with template_cols[idx]:
            if st.button(f"➕ {template_name}", use_container_width=True):
                # Add all tasks from template
                existing_task_names = {task["name"] for task in data["daily_checklists"][today_str]["tasks"]}
                for task in tasks:
                    if task["name"] not in existing_task_names:
                        data["daily_checklists"][today_str]["tasks"].append(task)
                save_data(data)
                st.rerun()

with col2:
    st.subheader("Quick Add Task")
    with st.form("quick_add"):
        quick_name = st.text_input("Task")
        quick_col1, quick_col2, quick_col3 = st.columns(3)
        with quick_col1:
            quick_cat = st.selectbox("Cat", ["Spiritual", "Social", "Physical", "Intellectual", "Other"], label_visibility="collapsed")
        with quick_col2:
            quick_pts = st.number_input("Pts", -50, 50, 10, label_visibility="collapsed")
        with quick_col3:
            quick_track = st.checkbox("×", help="Trackable with multiplier?")
        
        quick_unit = ""
        if quick_track:
            quick_unit = st.text_input("Unit", value="times", placeholder="hours, reps, etc.")
        
        if st.form_submit_button("Add"):
            new_task = {
                "name": quick_name,
                "category": quick_cat,
                "points": quick_pts,
                "trackable": quick_track
            }
            if quick_track:
                new_task["unit"] = quick_unit
            
            data["daily_checklists"][today_str]["tasks"].append(new_task)
            save_data(data)
            st.rerun()

st.divider()

# Display and check off tasks
tasks_header = "Today's Tasks" if today == today_actual else f"Tasks for {today.strftime('%b %d')}"
st.subheader(f"📝 {tasks_header}")

if not data["daily_checklists"][today_str]["tasks"]:
    st.info("👆 Add some tasks from templates above, or create a custom task")
else:
    # Group by category
    categories = {}
    for task in data["daily_checklists"][today_str]["tasks"]:
        cat = task["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(task)
    
    # Display by category
    cat_cols = st.columns(len(categories))
    
    for idx, (category, tasks) in enumerate(categories.items()):
        with cat_cols[idx]:
            # Category emoji
            emoji = {"Spiritual": "✨", "Social": "👥", "Physical": "💪", 
                    "Intellectual": "🧠", "Other": "🏠"}.get(category, "📌")
            st.markdown(f"### {emoji} {category}")
            
            for task in tasks:
                is_completed = task["name"] in data["daily_checklists"][today_str]["completed"]
                
                # Get quantity if trackable
                quantity = data["daily_checklists"][today_str].get("quantities", {}).get(task["name"], 1)
                
                # Calculate points
                base_points = task["points"]
                if task.get("trackable", False):
                    base_points = base_points * quantity

                adjusted_points = base_points

                # Display task
                if task.get("trackable", False):
                    # Trackable task - show quantity input
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        if st.checkbox(
                            task["name"],
                            value=is_completed,
                            key=f"task_{today_str}_{task['name']}"
                        ):
                            if task["name"] not in data["daily_checklists"][today_str]["completed"]:
                                data["daily_checklists"][today_str]["completed"].append(task["name"])
                                save_data(data)
                        else:
                            if task["name"] in data["daily_checklists"][today_str]["completed"]:
                                data["daily_checklists"][today_str]["completed"].remove(task["name"])
                                save_data(data)
                    
                    with col2:
                        new_quantity = st.number_input(
                            task.get("unit", "qty"),
                            min_value=0.0,
                            max_value=100.0,
                            value=float(quantity),
                            step=0.5 if task["points"] < 0 else 1.0,
                            format="%.1f",
                            key=f"qty_{today_str}_{task['name']}",
                            label_visibility="collapsed"
                        )
                        
                        if new_quantity != quantity:
                            if "quantities" not in data["daily_checklists"][today_str]:
                                data["daily_checklists"][today_str]["quantities"] = {}
                            data["daily_checklists"][today_str]["quantities"][task["name"]] = new_quantity
                            save_data(data)
                    
                    with col3:
                        color = "green" if adjusted_points > 0 else "red"
                        st.markdown(f":{color}[{adjusted_points:+.1f}]")
                        st.caption(f"{task['points']:+.1f} × {new_quantity:.1f}")
                
                else:
                    # Non-trackable task - simple checkbox
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if st.checkbox(
                            task["name"],
                            value=is_completed,
                            key=f"task_{today_str}_{task['name']}"
                        ):
                            if task["name"] not in data["daily_checklists"][today_str]["completed"]:
                                data["daily_checklists"][today_str]["completed"].append(task["name"])
                                save_data(data)
                        else:
                            if task["name"] in data["daily_checklists"][today_str]["completed"]:
                                data["daily_checklists"][today_str]["completed"].remove(task["name"])
                                save_data(data)
                    
                    with col2:
                        color = "green" if task["points"] > 0 else "red"
                        st.markdown(f":{color}[{adjusted_points:+.1f}]")
            
            # Task action buttons
            st.write("")
            for task in tasks:
                btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 2])

                with btn_col1:
                    # Edit points
                    with st.popover(f"✏️ Edit", use_container_width=True):
                        st.write(f"**{task['name'][:25]}**")
                        new_points = st.number_input(
                            "Points",
                            min_value=-50,
                            max_value=50,
                            value=task["points"],
                            key=f"edit_pts_{today_str}_{task['name']}"
                        )
                        if st.button("💾 Save", key=f"save_pts_{today_str}_{task['name']}"):
                            for t in data["daily_checklists"][today_str]["tasks"]:
                                if t["name"] == task["name"]:
                                    t["points"] = new_points
                                    break
                            save_data(data)
                            st.rerun()

                with btn_col2:
                    # Save to template
                    with st.popover(f"📋 Save", use_container_width=True):
                        st.write(f"**Save to Template**")
                        st.caption(task['name'][:30])
                        template_list = list(data["checklist_templates"].keys())
                        template_list.append("+ New Template")

                        selected_template = st.selectbox(
                            "Template",
                            template_list,
                            key=f"tmpl_{today_str}_{task['name']}"
                        )

                        if selected_template == "+ New Template":
                            new_template_name = st.text_input("Template Name", key=f"new_tmpl_{today_str}_{task['name']}")
                            if st.button("Create & Add", key=f"create_tmpl_{today_str}_{task['name']}") and new_template_name:
                                data["checklist_templates"][new_template_name] = [task.copy()]
                                save_data(data)
                                st.success("✅ Template created!")
                                st.rerun()
                        else:
                            if st.button("Add to Template", key=f"add_tmpl_{today_str}_{task['name']}"):
                                # Check if task already exists
                                task_names = [t["name"] for t in data["checklist_templates"][selected_template]]
                                if task["name"] not in task_names:
                                    data["checklist_templates"][selected_template].append(task.copy())
                                    save_data(data)
                                    st.success("✅ Added to template!")
                                    st.rerun()
                                else:
                                    st.warning("Task already in template")

                with btn_col3:
                    # Delete task
                    if st.button(f"🗑️ Delete", key=f"remove_{today_str}_{task['name']}", use_container_width=True):
                        data["daily_checklists"][today_str]["tasks"] = [
                            t for t in data["daily_checklists"][today_str]["tasks"]
                            if t["name"] != task["name"]
                        ]
                        if task["name"] in data["daily_checklists"][today_str]["completed"]:
                            data["daily_checklists"][today_str]["completed"].remove(task["name"])
                        save_data(data)
                        st.rerun()

st.divider()

# Today's Summary
summary_header = "Today's Summary" if today == today_actual else f"Summary for {today.strftime('%b %d')}"
st.subheader(f"📊 {summary_header}")

positive_pts, negative_pts = get_day_points(today_str, separate=True)
net_pts = positive_pts + negative_pts

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("✅ Positive Points", f"+{positive_pts:.1f}")
with col2:
    st.metric("❌ Negative Points", f"{negative_pts:.1f}")
with col3:
    st.metric("🌟 Net Points", f"{net_pts:+.1f}")
with col4:
    completion_rate = 0
    if data["daily_checklists"][today_str]["tasks"]:
        completion_rate = len(data["daily_checklists"][today_str]["completed"]) / len(data["daily_checklists"][today_str]["tasks"]) * 100
    st.metric("Completion", f"{completion_rate:.0f}%")

st.divider()

# Visualizations
tab1, tab2, tab3 = st.tabs([
    "📈 Trends & Insights",
    "📊 Category Balance",
    "📅 History"
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

with tab3:
    st.header("📅 History")

    # Show past days with their checklists
    for i in range(1, 15):  # Last 14 days (increased from 7)
        check_date = today_actual - timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")

        if date_str in data["daily_checklists"] and data["daily_checklists"][date_str]["tasks"]:
            with st.expander(f"{check_date.strftime('%A, %B %d')}"):
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
