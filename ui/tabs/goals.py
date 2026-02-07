"""
Goals & Review tab UI component for LifeTracker.
Displays goal tracking, weekly review, and historical task data.
"""
import streamlit as st
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from analytics.calculations import get_day_points
from database.goals import get_goals_by_type, save_goal, delete_goal
from database.tasks import get_daily_tasks
from utils.helpers import get_week_start


def render_goals_tab(db_session: Session):
    """
    Render the Goals & Review tab.

    Args:
        db_session: Active database session
    """
    st.header("🎯 Goals & Review")
    st.caption("Set goals and reflect on your progress")

    today_actual = datetime.now(ZoneInfo("America/New_York")).date()

    # Goal setting section
    st.subheader("🎯 Goals")

    goal_type = st.selectbox("Goal Type", ["weekly", "monthly", "yearly"])

    # Display existing goals from database
    existing_goals = get_goals_by_type(db_session, goal_type)
    if existing_goals:
        st.write(f"**Current {goal_type.title()} Goals:**")
        goals_to_delete = []
        for goal in existing_goals:
            goal_name = goal.name
            target = goal.target_points
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                # Calculate progress based on goal period
                if goal_type == "weekly":
                    week_start = get_week_start(today_actual)
                    current = 0
                    for i in range(7):
                        check_date = week_start + timedelta(days=i)
                        if check_date <= today_actual:
                            current += get_day_points(db_session, check_date)
                elif goal_type == "monthly":
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

            with col2:
                if progress_pct >= 100:
                    st.success("✅ Done!")
                else:
                    remaining = target - current
                    st.info(f"{remaining:.0f} left")

            with col3:
                if st.button("🗑️", key=f"delete_goal_{goal_type}_{goal_name}"):
                    goals_to_delete.append(goal.id)

        # Delete marked goals
        for goal_id in goals_to_delete:
            delete_goal(db_session, goal_id)
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
                name=new_goal_name,
                goal_type=goal_type,
                target_points=new_goal_target,
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
        for i in range(1, 15):  # Last 14 days
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
