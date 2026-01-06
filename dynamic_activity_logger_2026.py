import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from pathlib import Path
from scipy import stats
from sklearn.linear_model import LinearRegression

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

# Day type configurations
DAY_TYPE_CONFIG = {
    "normal": {
        "name": "Normal Day",
        "description": "Regular day with full expectations",
        "point_multiplier": 1.0,
        "negative_tolerance": 1.0,
        "color": "#4CAF50"
    },
    "travel": {
        "name": "School Day",
        "description": "Classes - increase overall focus",
        "point_multiplier": 1.25,
        "negative_tolerance": 0.75,  # Negatives count more
        "color": "#2196F3"
    },
    "sabbath": {
        "name": "Sabbath",
        "description": "Sunday - rest and worship focus",
        "point_multiplier": 1.0,
        "negative_tolerance": 0.5,  # Stricter on negatives
        "color": "#FFD700"
    },
    "sick": {
        "name": "Sick Day",
        "description": "Not feeling well - minimal expectations",
        "point_multiplier": 0.3,
        "negative_tolerance": 5.0,  # Very lenient
        "color": "#FF9800"
    },
    "high_performance": {
        "name": "High Performance",
        "description": "Going all out - maximum effort day",
        "point_multiplier": 1.5,
        "negative_tolerance": 0.5,
        "color": "#9C27B0"
    }
}

# Initialize data structure
def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            # Add new fields if they don't exist
            if "day_types" not in data:
                data["day_types"] = {}
            if "daily_checklists" not in data:
                data["daily_checklists"] = {}
            if "checklist_templates" not in data:
                data["checklist_templates"] = {
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
                    ]
                }
            return data
    else:
        return {
            "daily_checklists": {},  # {date: {tasks: [], completed: [], quantities: {task_name: count}}}
            "day_types": {},  # {date: "normal/travel/sabbath/sick/high_performance"}
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
            "running_log": {},
            "running_goals": {
                "weekly_mileage_target": 0,
                "race_date": None,
                "race_distance": 50.0,
                "total_training_miles": 0
            },
            "time_logs": {},
            "daily_metrics": {},
            "goals": {"weekly": {}, "monthly": {}, "yearly": {}},
            "total_points": 0
        }

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Load data
data = load_data()

# Helper functions
def get_day_points(date_str, separate=False):
    """Calculate points for a day, optionally separating positive and negative"""
    if date_str not in data["daily_checklists"]:
        return (0, 0) if separate else 0
    
    day_type = data["day_types"].get(date_str, "normal")
    config = DAY_TYPE_CONFIG[day_type]
    
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
                positive += points * config["point_multiplier"]
            else:
                negative += points / config["negative_tolerance"]
    
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
    
    # LLM Export
    with st.expander("🤖 Export for LLM"):
        if st.button("Generate Export"):
            st.info("Export functionality available - see original version")

# Main content
st.title("📖 Dynamic Daily Activity Logger")
st.markdown("*Flexible day-by-day tracking with custom checklists*")

# Today's setup
today = datetime.now().date()
today_str = today.strftime("%Y-%m-%d")

# Initialize today's data
if today_str not in data["daily_checklists"]:
    data["daily_checklists"][today_str] = {"tasks": [], "completed": [], "quantities": {}}
if today_str not in data["day_types"]:
    data["day_types"][today_str] = "normal"
if today_str not in data["daily_metrics"]:
    data["daily_metrics"][today_str] = {"mood": 5, "energy": 5, "notes": ""}
if today_str not in data["running_log"]:
    data["running_log"][today_str] = {"distance_miles": 0.0, "type": "easy", "notes": ""}

# Day Type Selection
st.header("🗓️ Today's Context")
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    day_type = st.selectbox(
        "What kind of day is today?",
        list(DAY_TYPE_CONFIG.keys()),
        format_func=lambda x: f"{DAY_TYPE_CONFIG[x]['name']} - {DAY_TYPE_CONFIG[x]['description']}",
        index=list(DAY_TYPE_CONFIG.keys()).index(data["day_types"][today_str])
    )
    
    if day_type != data["day_types"][today_str]:
        data["day_types"][today_str] = day_type
        save_data(data)
        st.rerun()
    
    config = DAY_TYPE_CONFIG[day_type]
    st.info(f"📊 Point Multiplier: {config['point_multiplier']}x | Negative Tolerance: {1/config['negative_tolerance']:.0%} impact")

with col2:
    mood_val = st.slider("😊 Mood", 1, 10, value=data["daily_metrics"][today_str].get("mood", 5))
    if mood_val != data["daily_metrics"][today_str].get("mood"):
        data["daily_metrics"][today_str]["mood"] = mood_val
        save_data(data)

with col3:
    energy_val = st.slider("⚡ Energy", 1, 10, value=data["daily_metrics"][today_str].get("energy", 5))
    if energy_val != data["daily_metrics"][today_str].get("energy"):
        data["daily_metrics"][today_str]["energy"] = energy_val
        save_data(data)

st.divider()

# Build Today's Checklist
st.header("✅ Today's Checklist")

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
st.subheader("📝 Today's Tasks")

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
                
                # Calculate adjusted points
                base_points = task["points"]
                if task.get("trackable", False):
                    base_points = base_points * quantity
                
                adjusted_points = base_points
                if base_points > 0:
                    adjusted_points *= config["point_multiplier"]
                else:
                    adjusted_points /= config["negative_tolerance"]
                
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
            
            # Remove task buttons
            st.write("")
            for task in tasks:
                if st.button(f"🗑️ {task['name'][:20]}...", key=f"remove_{today_str}_{task['name']}"):
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
st.subheader("📊 Today's Summary")

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
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Positive vs Negative",
    "🗓️ Day Type Patterns",
    "🏃 Running Tracker",
    "📅 History"
])

with tab1:
    st.header("Positive vs Negative Tracking")
    st.caption("See your good habits and bad habits side by side")
    
    # Last 30 days
    chart_data = []
    for i in range(30):
        check_date = today - timedelta(days=29-i)
        date_str = check_date.strftime("%Y-%m-%d")
        
        pos, neg = get_day_points(date_str, separate=True)
        
        chart_data.append({
            "Date": check_date,
            "Positive": pos,
            "Negative": abs(neg),  # Make positive for visualization
            "Net": pos + neg
        })
    
    df_chart = pd.DataFrame(chart_data)
    
    # Stacked bar chart
    st.subheader("Daily Positive vs Negative Points")
    
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
        title='Positive vs Negative Points (Last 30 Days)',
        xaxis_title='Date',
        yaxis_title='Points',
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Net points trend
    st.subheader("Net Points Trend")
    
    fig = px.line(df_chart, x='Date', y='Net',
                  title='Net Points Over Time',
                  markers=True)
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary stats
    st.subheader("30-Day Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        avg_positive = df_chart['Positive'].mean()
        st.metric("Avg Positive/Day", f"+{avg_positive:.1f}")
    with col2:
        avg_negative = df_chart['Negative'].mean()
        st.metric("Avg Negative/Day", f"-{avg_negative:.1f}")
    with col3:
        ratio = avg_positive / avg_negative if avg_negative > 0 else 0
        st.metric("Positive:Negative Ratio", f"{ratio:.1f}:1")

with tab2:
    st.header("Day Type Analysis")
    st.caption("How different day types affect your performance")
    
    # Calculate stats by day type
    day_type_stats = {}
    for date_str, day_type in data["day_types"].items():
        if day_type not in day_type_stats:
            day_type_stats[day_type] = {"positive": [], "negative": [], "net": []}
        
        pos, neg = get_day_points(date_str, separate=True)
        day_type_stats[day_type]["positive"].append(pos)
        day_type_stats[day_type]["negative"].append(abs(neg))
        day_type_stats[day_type]["net"].append(pos + neg)
    
    # Create summary DataFrame
    summary_data = []
    for day_type, stats in day_type_stats.items():
        if stats["positive"]:
            summary_data.append({
                "Day Type": DAY_TYPE_CONFIG[day_type]["name"],
                "Count": len(stats["positive"]),
                "Avg Positive": np.mean(stats["positive"]),
                "Avg Negative": np.mean(stats["negative"]),
                "Avg Net": np.mean(stats["net"])
            })
    
    if summary_data:
        df_summary = pd.DataFrame(summary_data)
        
        st.dataframe(df_summary, use_container_width=True, hide_index=True)
        
        # Visualization
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df_summary['Day Type'],
            y=df_summary['Avg Positive'],
            name='Avg Positive',
            marker_color='lightgreen'
        ))
        
        fig.add_trace(go.Bar(
            x=df_summary['Day Type'],
            y=df_summary['Avg Negative'],
            name='Avg Negative',
            marker_color='lightcoral'
        ))
        
        fig.update_layout(
            barmode='group',
            title='Average Points by Day Type',
            xaxis_title='Day Type',
            yaxis_title='Average Points'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Track more days to see day type patterns")

with tab3:
    st.header("🏃 Running Tracker")
    
    # Running tracker UI (simplified version from before)
    col1, col2 = st.columns(2)
    
    with col1:
        distance = st.number_input(
            "Today's Distance (miles)",
            min_value=0.0,
            max_value=50.0,
            value=float(data["running_log"][today_str].get("distance_miles", 0.0)),
            step=0.1,
            format="%.1f"
        )
        
        if distance != data["running_log"][today_str].get("distance_miles"):
            data["running_log"][today_str]["distance_miles"] = distance
            save_data(data)
    
    with col2:
        run_type = st.selectbox(
            "Run Type",
            ["easy", "long_run", "tempo", "intervals", "recovery", "race"],
            index=["easy", "long_run", "tempo", "intervals", "recovery", "race"].index(
                data["running_log"][today_str].get("type", "easy")
            )
        )
        
        if run_type != data["running_log"][today_str].get("type"):
            data["running_log"][today_str]["type"] = run_type
            save_data(data)
    
    # Weekly mileage
    week_start = get_week_start(today)
    weekly_miles = 0
    
    for i in range(7):
        check_date = week_start + timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")
        if date_str in data["running_log"]:
            weekly_miles += data["running_log"][date_str].get("distance_miles", 0)
    
    st.metric("This Week's Mileage", f"{weekly_miles:.1f} miles")
    
    # Cumulative
    total_miles = sum(run.get("distance_miles", 0) for run in data["running_log"].values())
    st.metric("Total Training Miles", f"{total_miles:.1f} miles")

with tab4:
    st.header("📅 History")
    
    # Show past days with their checklists
    for i in range(1, 8):  # Last 7 days
        check_date = today - timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")
        
        if date_str in data["daily_checklists"] and data["daily_checklists"][date_str]["tasks"]:
            with st.expander(f"{check_date.strftime('%A, %B %d')} - {data['day_types'].get(date_str, 'normal')}"):
                pos, neg = get_day_points(date_str, separate=True)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Positive", f"+{pos:.1f}")
                with col2:
                    st.metric("Negative", f"{neg:.1f}")
                with col3:
                    st.metric("Net", f"{pos+neg:+.1f}")
                
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
                        st.write(display_text)
                
                st.write("**Not Completed:**")
                for task in tasks:
                    if task["name"] not in completed:
                        st.write(f"❌ {task['name']} ({task['points']:+}pts)")

# Footer
st.divider()
st.markdown("**💡 Tip:** Different day types = different expectations. Travel days with high screen time won't hurt as much!")
