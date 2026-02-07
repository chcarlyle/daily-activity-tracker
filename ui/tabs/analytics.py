"""
Analytics & Trends tab UI component for LifeTracker.
Displays charts, trends, and insights about user's progress.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta, datetime
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from analytics.calculations import get_day_points
from database.metrics import get_daily_metric
from utils.helpers import get_week_start


def render_analytics_tab(db_session: Session):
    """
    Render the Analytics & Trends tab.

    Args:
        db_session: Active database session
    """
    st.header("Trends & Insights")
    st.caption("Track your progress and discover patterns")

    today_actual = datetime.now(ZoneInfo("America/New_York")).date()

    # Last 30 days
    chart_data = []
    for i in range(30):
        check_date = today_actual - timedelta(days=29-i)

        pos, neg = get_day_points(db_session, check_date, separate=True)

        # Get mood and energy if available
        metric = get_daily_metric(db_session, check_date)
        mood = metric.mood if metric else None
        energy = metric.energy if metric else None

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
