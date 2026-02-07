"""
Habits & Streaks tab UI component for LifeTracker.
Displays task streaks, consistency metrics, and habit insights.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from analytics.calculations import (
    get_positive_day_streak,
    get_day_points,
    get_task_streak,
    get_task_consistency,
    get_all_unique_tasks
)
from database.tasks import get_daily_tasks


def render_habits_tab(db_session: Session):
    """
    Render the Habits & Streaks tab.

    Args:
        db_session: Active database session
    """
    st.header("🔥 Streaks & Habits")
    st.caption("Track your consistency and build strong habits")

    today_actual = datetime.now(ZoneInfo("America/New_York")).date()

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
            consistency_pct = get_task_consistency(db_session, task_name, today_actual, 30)

            task_stats.append({
                "Task": task_name,
                "Current Streak": current_streak,
                "Longest Streak": longest_streak,
                "Consistency": consistency_pct
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
