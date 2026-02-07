"""
Main content UI component for LifeTracker.
Handles date navigation, task management, and daily dashboard.
"""
import streamlit as st
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from analytics.calculations import get_day_points, get_positive_day_streak
from database.tasks import get_daily_tasks, save_daily_task, update_task_completion, delete_daily_task
from database.metrics import get_daily_metric, save_daily_metric
from database.templates import get_all_templates


def render_main_content(db_session: Session):
    """
    Render the main content area with today's tasks and dashboard.

    Args:
        db_session: Active database session
    """
    st.title("📖 LifeTracker")

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
    positive_pts, negative_pts = get_day_points(db_session, today, separate=True)
    net_pts = positive_pts + negative_pts

    # Get today's tasks for completion rate
    today_tasks = get_daily_tasks(db_session, today)
    completion_rate = 0
    if today_tasks:
        completed_count = sum(1 for t in today_tasks if t.completed)
        completion_rate = (completed_count / len(today_tasks)) * 100

    positive_streak = get_positive_day_streak(db_session, today_actual)

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
                quick_pts = st.number_input("Points", -50, 50, 10)

                quick_trackable = st.checkbox("Trackable (with multiplier)?", value=False)
                quick_unit = ""
                if quick_trackable:
                    quick_unit = st.text_input("Unit (e.g., 'hours', 'reps', 'times')", value="times")

                if st.form_submit_button("Add Task", use_container_width=True):
                    if quick_name:
                        save_daily_task(
                            db_session,
                            date=today,
                            task_name=quick_name,
                            points=quick_pts,
                            trackable=quick_trackable,
                            unit=quick_unit if quick_trackable else None,
                            completed=False
                        )
                        st.rerun()

    # Task List - Clean and simple
    st.markdown("### Tasks")

    if not today_tasks:
        st.info("No tasks yet - add some using the button above!")
    else:
        # Show completion summary
        completed_count = len([t for t in today_tasks if t.completed])
        st.write(f"**Completed: {completed_count}/{len(today_tasks)}**")
        st.write("")  # Add spacing

        # Simple list view - no category grouping
        for task in today_tasks:
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

            # Delete button in its own small column
            task_col4 = st.columns([19, 1])[1]
            with task_col4:
                if st.button("🗑️", key=f"del_{today_str}_{task.task_name}", help=f"Delete {task.task_name}"):
                    delete_daily_task(db_session, today, task.task_name)
                    st.rerun()

            st.write("")  # Add spacing between tasks

    st.markdown("---")
