import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

# Page config
st.set_page_config(page_title="Daily Activity Logger", page_icon="⭐", layout="wide")

# Data storage path
DATA_FILE = Path("activity_log_2026.json")

# Initialize data structure with LDS-focused activities
def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    else:
        return {
            "activities": {
                # SPIRITUAL
                "Scripture Study (15+ min)": {"category": "Spiritual", "points": 20, "color": "#FFD700"},
                "Scripture Study (5-15 min)": {"category": "Spiritual", "points": 10, "color": "#FFD700"},
                "Personal Prayer (morning)": {"category": "Spiritual", "points": 10, "color": "#FFD700"},
                "Personal Prayer (evening)": {"category": "Spiritual", "points": 10, "color": "#FFD700"},
                "Family Prayer": {"category": "Spiritual", "points": 5, "color": "#FFD700"},
                "Attended Church": {"category": "Spiritual", "points": 25, "color": "#FFD700"},
                "Temple Attendance": {"category": "Spiritual", "points": 30, "color": "#FFD700"},
                "Seminary/Institute": {"category": "Spiritual", "points": 15, "color": "#FFD700"},
                "Sabbath Day Observance": {"category": "Spiritual", "points": 15, "color": "#FFD700"},
                "Gospel Study/General Conference": {"category": "Spiritual", "points": 15, "color": "#FFD700"},
                "Missionary Work/Service": {"category": "Spiritual", "points": 20, "color": "#FFD700"},
                
                # PHYSICAL
                "Exercise (30+ min)": {"category": "Physical", "points": 20, "color": "#4CAF50"},
                "Exercise (15-30 min)": {"category": "Physical", "points": 10, "color": "#4CAF50"},
                "Healthy Meals (3+)": {"category": "Physical", "points": 10, "color": "#4CAF50"},
                "8+ Hours Sleep": {"category": "Physical", "points": 15, "color": "#4CAF50"},
                "Outdoor Activity": {"category": "Physical", "points": 10, "color": "#4CAF50"},
                "No Junk Food": {"category": "Physical", "points": 5, "color": "#4CAF50"},
                
                # SOCIAL
                "Quality Family Time (30+ min)": {"category": "Social", "points": 15, "color": "#2196F3"},
                "Meaningful Conversation": {"category": "Social", "points": 10, "color": "#2196F3"},
                "Service to Others": {"category": "Social", "points": 15, "color": "#2196F3"},
                "Called/Texted Friend": {"category": "Social", "points": 5, "color": "#2196F3"},
                "Family Home Evening": {"category": "Social", "points": 20, "color": "#2196F3"},
                "Date Night/Quality Time with Spouse": {"category": "Social", "points": 15, "color": "#2196F3"},
                
                # INTELLECTUAL
                "Reading (30+ min)": {"category": "Intellectual", "points": 15, "color": "#9C27B0"},
                "Learning New Skill": {"category": "Intellectual", "points": 20, "color": "#9C27B0"},
                "Professional Development": {"category": "Intellectual", "points": 15, "color": "#9C27B0"},
                "Creative Project": {"category": "Intellectual", "points": 15, "color": "#9C27B0"},
                "Journaling": {"category": "Intellectual", "points": 10, "color": "#9C27B0"},
                
                # NEGATIVE POINTS (Screen Time & Distractions)
                "Social Media (30+ min)": {"category": "Spiritual", "points": -15, "color": "#F44336"},
                "Social Media (15-30 min)": {"category": "Spiritual", "points": -10, "color": "#F44336"},
                "Excessive Phone Use (2+ hrs)": {"category": "Spiritual", "points": -20, "color": "#F44336"},
                "TV/Streaming (2+ hrs)": {"category": "Spiritual", "points": -15, "color": "#F44336"},
                "Gaming (2+ hrs)": {"category": "Spiritual", "points": -15, "color": "#F44336"},
                "Stayed up past midnight": {"category": "Physical", "points": -10, "color": "#F44336"},
                "Skipped Exercise": {"category": "Physical", "points": -5, "color": "#F44336"},
            },
            "daily_logs": {},
            "total_points": 0,
            "level": 1
        }

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Load data
data = load_data()

# Helper functions
def calculate_level(points):
    if points < 0:
        return 1
    return int(points / 200) + 1

def get_points_to_next_level(points):
    if points < 0:
        return 200
    current_level = calculate_level(points)
    return (current_level * 200) - points

def get_category_points_today(category, today_str):
    total = 0
    if today_str in data["daily_logs"]:
        for activity, count in data["daily_logs"][today_str].items():
            if activity in data["activities"] and data["activities"][activity]["category"] == category:
                total += data["activities"][activity]["points"] * count
    return total

def get_week_start(date):
    return date - timedelta(days=date.weekday())

# Sidebar - Activity Management
with st.sidebar:
    st.title("⭐ Activity Logger")
    
    # Display current stats
    st.metric("Total Points", data["total_points"])
    st.metric("Level", data["level"])
    progress_val = min(1.0, max(0.0, 1 - (get_points_to_next_level(data["total_points"]) / 200)))
    st.progress(progress_val)
    st.caption(f"{get_points_to_next_level(data['total_points'])} points to level {data['level'] + 1}")
    
    st.divider()
    
    # Add new activity
    with st.expander("➕ Add New Activity"):
        new_activity = st.text_input("Activity Name")
        new_category = st.selectbox("Category", ["Spiritual", "Social", "Physical", "Intellectual"])
        new_points = st.number_input("Point Value", min_value=-50, max_value=50, value=10, 
                                      help="Use negative values for activities to avoid")
        new_color = st.color_picker("Color", "#FFD700")
        
        if st.button("Add Activity"):
            if new_activity and new_activity not in data["activities"]:
                data["activities"][new_activity] = {
                    "category": new_category,
                    "points": new_points,
                    "color": new_color
                }
                save_data(data)
                st.success(f"Added {new_activity}!")
                st.rerun()
    
    # Remove activity
    with st.expander("🗑️ Remove Activity"):
        activity_to_remove = st.selectbox("Select activity to remove", list(data["activities"].keys()))
        if st.button("Remove"):
            del data["activities"][activity_to_remove]
            save_data(data)
            st.success(f"Removed {activity_to_remove}!")
            st.rerun()

# Main content
st.title("📖 Daily Activity Logger - LDS Youth Framework")
st.markdown("*Spiritual • Social • Physical • Intellectual*")

# Today's Logging Section
st.header("📅 Today's Activities")
today = datetime.now().date()
today_str = today.strftime("%Y-%m-%d")

if today_str not in data["daily_logs"]:
    data["daily_logs"][today_str] = {}

# Category columns for better organization
spiritual_col, social_col = st.columns(2)
physical_col, intellectual_col = st.columns(2)

# Group activities by category
spiritual_activities = {k: v for k, v in data["activities"].items() if v["category"] == "Spiritual"}
social_activities = {k: v for k, v in data["activities"].items() if v["category"] == "Social"}
physical_activities = {k: v for k, v in data["activities"].items() if v["category"] == "Physical"}
intellectual_activities = {k: v for k, v in data["activities"].items() if v["category"] == "Intellectual"}

with spiritual_col:
    st.subheader("✨ Spiritual")
    for activity_name, activity_info in spiritual_activities.items():
        current_count = data["daily_logs"][today_str].get(activity_name, 0)
        points_display = f"+{activity_info['points']}" if activity_info['points'] > 0 else str(activity_info['points'])
        new_count = st.number_input(
            f"{activity_name} ({points_display}pts)", 
            min_value=0, 
            max_value=10, 
            value=current_count,
            key=f"spiritual_{activity_name}"
        )
        
        if new_count != current_count:
            old_points = activity_info['points'] * current_count
            new_points = activity_info['points'] * new_count
            data["total_points"] += (new_points - old_points)
            data["level"] = calculate_level(data["total_points"])
            
            if new_count > 0:
                data["daily_logs"][today_str][activity_name] = new_count
            elif activity_name in data["daily_logs"][today_str]:
                del data["daily_logs"][today_str][activity_name]
            
            save_data(data)

with social_col:
    st.subheader("👥 Social")
    for activity_name, activity_info in social_activities.items():
        current_count = data["daily_logs"][today_str].get(activity_name, 0)
        points_display = f"+{activity_info['points']}" if activity_info['points'] > 0 else str(activity_info['points'])
        new_count = st.number_input(
            f"{activity_name} ({points_display}pts)", 
            min_value=0, 
            max_value=10, 
            value=current_count,
            key=f"social_{activity_name}"
        )
        
        if new_count != current_count:
            old_points = activity_info['points'] * current_count
            new_points = activity_info['points'] * new_count
            data["total_points"] += (new_points - old_points)
            data["level"] = calculate_level(data["total_points"])
            
            if new_count > 0:
                data["daily_logs"][today_str][activity_name] = new_count
            elif activity_name in data["daily_logs"][today_str]:
                del data["daily_logs"][today_str][activity_name]
            
            save_data(data)

with physical_col:
    st.subheader("💪 Physical")
    for activity_name, activity_info in physical_activities.items():
        current_count = data["daily_logs"][today_str].get(activity_name, 0)
        points_display = f"+{activity_info['points']}" if activity_info['points'] > 0 else str(activity_info['points'])
        new_count = st.number_input(
            f"{activity_name} ({points_display}pts)", 
            min_value=0, 
            max_value=10, 
            value=current_count,
            key=f"physical_{activity_name}"
        )
        
        if new_count != current_count:
            old_points = activity_info['points'] * current_count
            new_points = activity_info['points'] * new_count
            data["total_points"] += (new_points - old_points)
            data["level"] = calculate_level(data["total_points"])
            
            if new_count > 0:
                data["daily_logs"][today_str][activity_name] = new_count
            elif activity_name in data["daily_logs"][today_str]:
                del data["daily_logs"][today_str][activity_name]
            
            save_data(data)

with intellectual_col:
    st.subheader("🧠 Intellectual")
    for activity_name, activity_info in intellectual_activities.items():
        current_count = data["daily_logs"][today_str].get(activity_name, 0)
        points_display = f"+{activity_info['points']}" if activity_info['points'] > 0 else str(activity_info['points'])
        new_count = st.number_input(
            f"{activity_name} ({points_display}pts)", 
            min_value=0, 
            max_value=10, 
            value=current_count,
            key=f"intellectual_{activity_name}"
        )
        
        if new_count != current_count:
            old_points = activity_info['points'] * current_count
            new_points = activity_info['points'] * new_count
            data["total_points"] += (new_points - old_points)
            data["level"] = calculate_level(data["total_points"])
            
            if new_count > 0:
                data["daily_logs"][today_str][activity_name] = new_count
            elif activity_name in data["daily_logs"][today_str]:
                del data["daily_logs"][today_str][activity_name]
            
            save_data(data)

# Today's Summary
st.divider()
st.subheader("Today's Summary")

col1, col2, col3, col4 = st.columns(4)

spiritual_pts = get_category_points_today("Spiritual", today_str)
social_pts = get_category_points_today("Social", today_str)
physical_pts = get_category_points_today("Physical", today_str)
intellectual_pts = get_category_points_today("Intellectual", today_str)

with col1:
    st.metric("✨ Spiritual", f"{spiritual_pts} pts")
with col2:
    st.metric("👥 Social", f"{social_pts} pts")
with col3:
    st.metric("💪 Physical", f"{physical_pts} pts")
with col4:
    st.metric("🧠 Intellectual", f"{intellectual_pts} pts")

today_total = spiritual_pts + social_pts + physical_pts + intellectual_pts
st.metric("🌟 Today's Total", f"{today_total} pts", delta=f"Level {data['level']}")

st.divider()

# Visualizations
tab1, tab2, tab3, tab4 = st.tabs(["📊 Category Balance", "📈 Weekly Trends", "📅 Calendar View", "🏆 Achievements"])

with tab1:
    st.header("Category Balance")
    
    # Today's balance
    today_balance = pd.DataFrame([
        {"Category": "Spiritual", "Points": spiritual_pts, "Color": "#FFD700"},
        {"Category": "Social", "Points": social_pts, "Color": "#2196F3"},
        {"Category": "Physical", "Points": physical_pts, "Color": "#4CAF50"},
        {"Category": "Intellectual", "Points": intellectual_pts, "Color": "#9C27B0"}
    ])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Today's Distribution")
        fig = px.bar(today_balance, x='Category', y='Points', color='Category',
                    color_discrete_map={
                        "Spiritual": "#FFD700",
                        "Social": "#2196F3",
                        "Physical": "#4CAF50",
                        "Intellectual": "#9C27B0"
                    })
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Category Proportions")
        # Only show positive values in pie chart
        positive_balance = today_balance[today_balance['Points'] > 0]
        if not positive_balance.empty:
            fig = px.pie(positive_balance, values='Points', names='Category',
                        color='Category',
                        color_discrete_map={
                            "Spiritual": "#FFD700",
                            "Social": "#2196F3",
                            "Physical": "#4CAF50",
                            "Intellectual": "#9C27B0"
                        })
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Log some activities to see distribution")
    
    # Weekly balance
    st.subheader("This Week's Balance")
    week_start = get_week_start(today)
    week_data = {"Spiritual": 0, "Social": 0, "Physical": 0, "Intellectual": 0}
    
    for i in range(7):
        check_date = week_start + timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")
        
        for category in ["Spiritual", "Social", "Physical", "Intellectual"]:
            week_data[category] += get_category_points_today(category, date_str)
    
    week_df = pd.DataFrame([
        {"Category": cat, "Points": pts} for cat, pts in week_data.items()
    ])
    
    fig = px.bar(week_df, x='Category', y='Points', 
                 color='Category',
                 color_discrete_map={
                     "Spiritual": "#FFD700",
                     "Social": "#2196F3",
                     "Physical": "#4CAF50",
                     "Intellectual": "#9C27B0"
                 },
                 title="Weekly Points by Category")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("📈 Weekly Trends")
    
    # Calculate daily totals for the past 4 weeks
    trend_data = []
    for i in range(28):
        check_date = today - timedelta(days=27-i)
        date_str = check_date.strftime("%Y-%m-%d")
        
        daily_total = 0
        category_totals = {"Spiritual": 0, "Social": 0, "Physical": 0, "Intellectual": 0}
        
        if date_str in data["daily_logs"]:
            for activity, count in data["daily_logs"][date_str].items():
                if activity in data["activities"]:
                    points = data["activities"][activity]["points"] * count
                    daily_total += points
                    category = data["activities"][activity]["category"]
                    category_totals[category] += points
        
        trend_data.append({
            "Date": check_date,
            "Total Points": daily_total,
            "Spiritual": category_totals["Spiritual"],
            "Social": category_totals["Social"],
            "Physical": category_totals["Physical"],
            "Intellectual": category_totals["Intellectual"]
        })
    
    df_trends = pd.DataFrame(trend_data)
    
    # Total points over time
    fig = px.line(df_trends, x='Date', y='Total Points', 
                  title='Daily Points Over Time',
                  markers=True)
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)
    
    # Stacked area chart by category
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_trends['Date'], y=df_trends['Spiritual'], 
                            fill='tonexty', name='Spiritual',
                            line=dict(color='#FFD700')))
    fig.add_trace(go.Scatter(x=df_trends['Date'], y=df_trends['Social'], 
                            fill='tonexty', name='Social',
                            line=dict(color='#2196F3')))
    fig.add_trace(go.Scatter(x=df_trends['Date'], y=df_trends['Physical'], 
                            fill='tonexty', name='Physical',
                            line=dict(color='#4CAF50')))
    fig.add_trace(go.Scatter(x=df_trends['Date'], y=df_trends['Intellectual'], 
                            fill='tonexty', name='Intellectual',
                            line=dict(color='#9C27B0')))
    
    fig.update_layout(title='Points by Category Over Time')
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("📅 Calendar View")
    
    # Create calendar heatmap
    start_date = datetime(2026, 1, 1).date()
    end_date = today
    
    cal_data = []
    for single_date in pd.date_range(start=start_date, end=end_date):
        date = single_date.date()
        date_str = date.strftime("%Y-%m-%d")
        
        daily_total = 0
        if date_str in data["daily_logs"]:
            for activity, count in data["daily_logs"][date_str].items():
                if activity in data["activities"]:
                    daily_total += data["activities"][activity]["points"] * count
        
        cal_data.append({
            "Date": date,
            "Points": daily_total,
            "Week": date.isocalendar()[1],
            "Weekday": date.strftime("%A")
        })
    
    df_cal = pd.DataFrame(cal_data)
    
    if not df_cal.empty:
        # Pivot for heatmap
        df_pivot = df_cal.pivot_table(values='Points', index='Weekday', columns='Week', aggfunc='sum', fill_value=0)
        
        # Reorder days
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        df_pivot = df_pivot.reindex(day_order)
        
        fig = px.imshow(df_pivot, 
                       labels=dict(x="Week of Year", y="Day of Week", color="Points"),
                       color_continuous_scale='RdYlGn',
                       color_continuous_midpoint=0,
                       title='Daily Points Heatmap')
        st.plotly_chart(fig, use_container_width=True)
        
        # Best and worst days
        st.subheader("Day of Week Analysis")
        dow_stats = df_cal.groupby('Weekday')['Points'].agg(['mean', 'sum']).reset_index()
        dow_stats['Weekday'] = pd.Categorical(dow_stats['Weekday'], categories=day_order, ordered=True)
        dow_stats = dow_stats.sort_values('Weekday')
        
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(dow_stats, x='Weekday', y='mean', 
                        title='Average Points by Day of Week')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(dow_stats, x='Weekday', y='sum',
                        title='Total Points by Day of Week')
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.header("🏆 Achievements & Milestones")
    
    # Calculate stats
    total_days_logged = len(data["daily_logs"])
    total_positive_points = sum(max(0, sum(data["activities"][act]["points"] * count 
                                           for act, count in logs.items() 
                                           if act in data["activities"]))
                                for logs in data["daily_logs"].values())
    
    # Spiritual-specific stats
    scripture_days = sum(1 for logs in data["daily_logs"].values() 
                        if any("Scripture Study" in act for act in logs.keys()))
    prayer_days = sum(1 for logs in data["daily_logs"].values()
                     if any("Prayer" in act for act in logs.keys()))
    church_attendance = sum(logs.get("Attended Church", 0) 
                           for logs in data["daily_logs"].values())
    temple_attendance = sum(logs.get("Temple Attendance", 0)
                           for logs in data["daily_logs"].values())
    
    achievements = []
    
    # Point-based achievements
    if data["total_points"] >= 100:
        achievements.append({"name": "Centurion", "desc": "Earned 100+ points", "icon": "💯"})
    if data["total_points"] >= 500:
        achievements.append({"name": "Dedicated Disciple", "desc": "Earned 500+ points", "icon": "⭐"})
    if data["total_points"] >= 1000:
        achievements.append({"name": "Stripling Warrior", "desc": "Earned 1000+ points", "icon": "🛡️"})
    if data["total_points"] >= 2000:
        achievements.append({"name": "Captain Moroni", "desc": "Earned 2000+ points", "icon": "👑"})
    
    # Spiritual achievements
    if scripture_days >= 7:
        achievements.append({"name": "Word of God", "desc": "7 days of scripture study", "icon": "📖"})
    if scripture_days >= 30:
        achievements.append({"name": "Feasting on the Word", "desc": "30 days of scripture study", "icon": "📚"})
    if prayer_days >= 14:
        achievements.append({"name": "Prayer Warrior", "desc": "14 days of prayer", "icon": "🙏"})
    if church_attendance >= 4:
        achievements.append({"name": "Sabbath Observer", "desc": "4+ church attendances", "icon": "⛪"})
    if temple_attendance >= 1:
        achievements.append({"name": "Temple Patron", "desc": "Visited the temple", "icon": "🏛️"})
    if temple_attendance >= 5:
        achievements.append({"name": "House of the Lord", "desc": "5+ temple visits", "icon": "✨"})
    
    # Consistency achievements
    if total_days_logged >= 7:
        achievements.append({"name": "Week Strong", "desc": "Logged 7 days", "icon": "📅"})
    if total_days_logged >= 30:
        achievements.append({"name": "Monthly Momentum", "desc": "Logged 30 days", "icon": "🗓️"})
    if total_days_logged >= 90:
        achievements.append({"name": "Quarterly Champion", "desc": "Logged 90 days", "icon": "🎯"})
    
    # Display achievements
    if achievements:
        cols = st.columns(4)
        for idx, achievement in enumerate(achievements):
            with cols[idx % 4]:
                st.markdown(f"""
                <div style='text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px; margin: 10px 0;'>
                    <div style='font-size: 48px;'>{achievement['icon']}</div>
                    <div style='font-weight: bold; margin-top: 10px;'>{achievement['name']}</div>
                    <div style='font-size: 12px; color: #666;'>{achievement['desc']}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Start logging your daily activities to unlock achievements! 💪")
    
    st.divider()
    
    # Overall stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Days Logged", total_days_logged)
    with col2:
        st.metric("Scripture Study Days", scripture_days)
    with col3:
        st.metric("Church Attendance", church_attendance)
    with col4:
        st.metric("Temple Visits", temple_attendance)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_daily = data["total_points"] / max(total_days_logged, 1)
        st.metric("Avg Daily Points", f"{avg_daily:.1f}")
    with col2:
        st.metric("Prayer Days", prayer_days)
    with col3:
        st.metric("Total Positive Points", total_positive_points)
    with col4:
        best_day_points = max((sum(data["activities"][act]["points"] * count 
                                  for act, count in logs.items() 
                                  if act in data["activities"])
                              for logs in data["daily_logs"].values()), default=0)
        st.metric("Best Day", f"{best_day_points} pts")

# Footer
st.divider()
st.markdown("---")
st.markdown("**💡 Remember:** *'By small and simple things are great things brought to pass.' - Alma 37:6*")
st.markdown("**Focus on spiritual health, reduce screen time, and maintain physical wellness through balanced daily activities.**")
