"""
Avatar Alignment tab UI component for LifeTracker.
Displays avatar alignment analysis, manual LLM prompt generation, and analysis history.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from models import AvatarAlignment
from database.avatars import get_active_avatar, get_alignment_history
from services.avatar_service import prepare_avatar_analysis_data, generate_avatar_prompt


def render_avatar_tab(db_session: Session):
    """
    Render the Avatar Alignment Analysis tab.

    Args:
        db_session: Active database session
    """
    st.header("🎯 Avatar Alignment Analysis")
    st.caption("See how well your behavior aligns with your ideal self")

    today_actual = datetime.now(ZoneInfo("America/New_York")).date()

    # Get current avatar
    current_avatar = get_active_avatar(db_session)

    if not current_avatar:
        st.warning("⚠️ No avatar defined yet!")
        st.info("👉 Define your avatar in the sidebar under '🎯 My Avatar (Ideal Self)' to get started.")
    else:
        # Display current avatar
        st.subheader(f"Your Avatar: {current_avatar.name}")
        with st.expander("📝 Avatar Description", expanded=False):
            st.write(current_avatar.description)

        st.divider()

        # Analysis controls
        st.subheader("Generate Analysis Prompt")
        st.caption("Copy the prompt below and paste it into Claude.ai (or any LLM) to get your alignment analysis")

        if st.button("📋 Generate Prompt", use_container_width=False, type="primary"):
            st.session_state.show_prompt = True

        if st.session_state.get("show_prompt", False):
            end_date = today_actual
            start_date = end_date - timedelta(days=30)

            # Prepare data and generate prompt
            analysis_data = prepare_avatar_analysis_data(db_session, start_date, end_date)
            prompt = generate_avatar_prompt(current_avatar.description, analysis_data)

            st.info("📝 **Instructions:** Copy the prompt below, paste it into Claude.ai or another LLM, then paste the response back here.")

            # Display copyable prompt
            st.text_area(
                "Prompt for LLM",
                value=prompt,
                height=300,
                help="Copy this entire prompt and paste into Claude.ai"
            )

            st.divider()

            # Manual response input
            st.write("**Paste LLM Response Here:**")
            st.caption("After getting the analysis from your LLM, paste the JSON response below and click Save")

            llm_response = st.text_area(
                "LLM Response (JSON)",
                height=200,
                placeholder='{"alignment_score": 75, "summary": "...", "recommendations": [...], ...}',
                key="llm_response_input"
            )

            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("💾 Save Analysis", use_container_width=True):
                    if llm_response:
                        try:
                            # Parse and validate JSON
                            result = json.loads(llm_response.strip())

                            # Create alignment record
                            alignment = AvatarAlignment(
                                avatar_id=current_avatar.id,
                                analysis_date=datetime.now().date(),
                                start_date=start_date,
                                end_date=end_date,
                                alignment_score=result['alignment_score'],
                                alignment_summary=result['summary'],
                                recommendations=json.dumps(result['recommendations']),
                                trend=result.get('trend', 'stable'),
                                llm_model='manual-entry',
                                llm_prompt_version='v1.0'
                            )
                            db_session.add(alignment)
                            db_session.commit()

                            st.success("✅ Analysis saved!")
                            st.session_state.show_prompt = False
                            st.rerun()
                        except json.JSONDecodeError:
                            st.error("❌ Invalid JSON. Make sure you copied the complete response from the LLM.")
                        except KeyError as e:
                            st.error(f"❌ Missing required field: {e}")
                        except Exception as e:
                            st.error(f"❌ Error saving analysis: {str(e)}")
                    else:
                        st.warning("Please paste the LLM response first")

        st.divider()

        # Get alignment history
        alignments = get_alignment_history(db_session, current_avatar.id, limit=10)

        if not alignments:
            st.info("🔍 No alignment analyses yet. Click 'Generate Prompt' to get your first insight!")
        else:
            # Latest alignment results
            latest = alignments[0]

            st.subheader("Latest Analysis Results")
            st.caption(f"Analysis Date: {latest.analysis_date.strftime('%B %d, %Y')}")
            st.caption(f"Period: {latest.start_date.strftime('%b %d')} - {latest.end_date.strftime('%b %d, %Y')}")

            # Alignment score with color coding
            score = latest.alignment_score
            if score >= 80:
                score_color = "🟢"
                score_label = "Excellent"
            elif score >= 60:
                score_color = "🟡"
                score_label = "Good"
            elif score >= 40:
                score_color = "🟠"
                score_label = "Fair"
            else:
                score_color = "🔴"
                score_label = "Needs Work"

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Alignment Score", f"{score}%", help=score_label)
                st.write(f"{score_color} {score_label}")
            with col2:
                trend_emoji = {"improving": "📈", "stable": "➡️", "declining": "📉"}
                st.metric("Trend", latest.trend.title(), help="Compared to previous analyses")
                st.write(f"{trend_emoji.get(latest.trend, '➡️')} {latest.trend.title()}")
            with col3:
                days_analyzed = (latest.end_date - latest.start_date).days
                st.metric("Days Analyzed", f"{days_analyzed}")

            st.divider()

            # Summary
            st.subheader("📝 Summary")
            st.write(latest.alignment_summary)

            st.divider()

            # Recommendations
            st.subheader("💡 Recommendations")
            recommendations = json.loads(latest.recommendations)
            for i, rec in enumerate(recommendations, 1):
                st.markdown(f"{i}. {rec}")

            st.divider()

            # Alignment history chart
            if len(alignments) > 1:
                st.subheader("📊 Alignment History")

                history_data = []
                for alignment in reversed(alignments):
                    history_data.append({
                        "Date": alignment.analysis_date,
                        "Score": alignment.alignment_score
                    })

                df_history = pd.DataFrame(history_data)

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_history['Date'],
                    y=df_history['Score'],
                    mode='lines+markers',
                    name='Alignment Score',
                    line=dict(color='#1f77b4', width=3),
                    marker=dict(size=8)
                ))

                fig.update_layout(
                    xaxis_title="Analysis Date",
                    yaxis_title="Alignment Score (%)",
                    yaxis_range=[0, 100],
                    height=300,
                    hovermode='x unified'
                )

                st.plotly_chart(fig, use_container_width=True)

            # View all analyses
            if len(alignments) > 1:
                with st.expander(f"📜 View All Analyses ({len(alignments)})", expanded=False):
                    for alignment in alignments:
                        st.write(f"**{alignment.analysis_date.strftime('%B %d, %Y')}** - Score: {alignment.alignment_score}%")
                        st.caption(alignment.alignment_summary)
                        st.divider()
