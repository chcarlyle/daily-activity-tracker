"""
Sidebar UI component for LifeTracker.
Handles templates, backup/export, and avatar management.
"""
import streamlit as st
from datetime import datetime
from sqlalchemy.orm import Session

from models import User
from database.templates import save_task_template, get_templates_by_name, delete_task_template
from database.migrations import export_database_to_json
from database.avatars import get_active_avatar, save_avatar, delete_avatar
from services.backup_service import create_backup


def render_sidebar(db_session: Session):
    """
    Render the sidebar with all controls and management sections.

    Args:
        db_session: Active database session
    """
    with st.sidebar:
        st.title("⭐ Daily Tracker")

        # Display current stats (removed level/progress bar)
        user = db_session.query(User).first()
        total_points = user.total_points if user else 0
        st.metric("Total Points", int(total_points))

        st.divider()

        # Manage Templates
        _render_template_manager(db_session)

        # Backup & Export
        _render_backup_export(db_session)

        # Avatar Management
        _render_avatar_manager(db_session)


def _render_template_manager(db_session: Session):
    """Render the template management section in sidebar."""
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
                    task_points = st.number_input("Points", min_value=-50, max_value=50, value=10)
                with col2:
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


def _render_backup_export(db_session: Session):
    """Render the backup and export section in sidebar."""
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
        st.info("💡 Import from JSON coming soon! Use export for now to backup your data.")


def _render_avatar_manager(db_session: Session):
    """Render the avatar management section in sidebar."""
    with st.expander("🎯 My Avatar (Ideal Self)"):
        st.write("**Define Your Ideal Self**")
        st.caption("Describe who you want to become. Claude AI will analyze if your behavior aligns with this avatar.")

        # Get current active avatar
        current_avatar = get_active_avatar(db_session)

        # Avatar form
        avatar_name = st.text_input(
            "Avatar Name",
            value=current_avatar.name if current_avatar else "",
            placeholder="e.g., My Best Self"
        )

        avatar_description = st.text_area(
            "Avatar Description",
            value=current_avatar.description if current_avatar else "",
            placeholder="I am someone who prioritizes spiritual growth through daily scripture study, maintains physical health through exercise, nurtures meaningful relationships, and contributes to society...",
            height=150
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Avatar", use_container_width=True):
                if avatar_name and avatar_description:
                    save_avatar(db_session, avatar_name, avatar_description)
                    st.success("✅ Avatar saved!")
                    st.rerun()
                else:
                    st.warning("Please provide both name and description")

        with col2:
            if current_avatar and st.button("🗑️ Delete Avatar", use_container_width=True):
                if delete_avatar(db_session, current_avatar.id):
                    st.success("Avatar deleted")
                    st.rerun()

        if current_avatar:
            st.divider()
            st.info(f"💡 Current Avatar: **{current_avatar.name}**")
            st.caption(f"Created: {current_avatar.created_at.strftime('%Y-%m-%d')}")
