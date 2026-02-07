"""
UI module for LifeTracker Streamlit components.
"""
from ui.sidebar import render_sidebar
from ui.main_content import render_main_content
from ui.tabs import (
    render_analytics_tab,
    render_habits_tab,
    render_goals_tab,
    render_avatar_tab
)

__all__ = [
    "render_sidebar",
    "render_main_content",
    "render_analytics_tab",
    "render_habits_tab",
    "render_goals_tab",
    "render_avatar_tab",
]
