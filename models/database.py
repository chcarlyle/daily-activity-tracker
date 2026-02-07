"""
SQLAlchemy database models for LifeTracker application.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime,
    Text, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User configuration and totals"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    total_points = Column(Float, default=0.0)
    timezone = Column(String, default='America/New_York')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskTemplate(Base):
    """Task templates for quick daily task creation"""
    __tablename__ = 'task_templates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_name = Column(String, nullable=False)
    task_name = Column(String, nullable=False)
    points = Column(Float, nullable=False)
    trackable = Column(Boolean, default=False)
    unit = Column(String, nullable=True)  # e.g., 'hours', 'reps', 'times'
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_task_templates_template', 'template_name'),
    )


class DailyTask(Base):
    """Individual task instances for specific dates"""
    __tablename__ = 'daily_tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    task_name = Column(String, nullable=False)
    points = Column(Float, nullable=False)
    trackable = Column(Boolean, default=False)
    unit = Column(String, nullable=True)
    completed = Column(Boolean, default=False)
    quantity = Column(Float, default=1.0)  # multiplier for trackable tasks
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_daily_tasks_date', 'date', postgresql_using='btree'),
        Index('idx_daily_tasks_completed', 'completed'),
        Index('idx_daily_tasks_date_completed', 'date', 'completed'),  # Composite for streak queries
    )


class DailyMetric(Base):
    """Daily mood and energy tracking"""
    __tablename__ = 'daily_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, unique=True, nullable=False)
    mood = Column(Integer, nullable=True)
    energy = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint('mood >= 1 AND mood <= 10'),
        CheckConstraint('energy >= 1 AND energy <= 10'),
        Index('idx_daily_metrics_date', 'date', postgresql_using='btree'),
    )


class Goal(Base):
    """User goals (weekly, monthly, yearly)"""
    __tablename__ = 'goals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    goal_type = Column(String, nullable=False)  # 'weekly', 'monthly', 'yearly'
    target_points = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    created_date = Column(Date, nullable=False)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(goal_type.in_(['weekly', 'monthly', 'yearly'])),
        Index('idx_goals_type', 'goal_type'),
        Index('idx_goals_completed', 'completed'),
    )


class Avatar(Base):
    """User's ideal self definition for LLM alignment analysis"""
    __tablename__ = 'avatars'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, default='My Ideal Self')
    description = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    alignments = relationship('AvatarAlignment', back_populates='avatar', cascade='all, delete-orphan')


class AvatarAlignment(Base):
    """LLM analysis results of user behavior vs avatar"""
    __tablename__ = 'avatar_alignments'

    id = Column(Integer, primary_key=True, autoincrement=True)
    avatar_id = Column(Integer, ForeignKey('avatars.id', ondelete='CASCADE'), nullable=False)
    analysis_date = Column(Date, nullable=False)
    start_date = Column(Date, nullable=False)  # beginning of analyzed period
    end_date = Column(Date, nullable=False)    # end of analyzed period
    alignment_score = Column(Float, nullable=True)  # 0-100 score from LLM
    alignment_summary = Column(Text, nullable=True)  # LLM's summary
    recommendations = Column(Text, nullable=True)  # JSON array of recommendations
    trend = Column(String, nullable=True)  # 'improving', 'declining', 'stable'
    llm_model = Column(String, nullable=True)  # e.g., 'claude-3-sonnet'
    llm_prompt_version = Column(String, nullable=True)  # track prompt changes
    created_at = Column(DateTime, default=datetime.utcnow)

    avatar = relationship('Avatar', back_populates='alignments')

    __table_args__ = (
        Index('idx_avatar_alignments_date', 'analysis_date', postgresql_using='btree'),
        Index('idx_avatar_alignments_avatar', 'avatar_id'),
    )


class StreakCache(Base):
    """Cached streak calculations for performance"""
    __tablename__ = 'streak_cache'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String, unique=True, nullable=False)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_calculated_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_streak_cache_task', 'task_name'),
    )


class SystemMetadata(Base):
    """System metadata and configuration"""
    __tablename__ = 'system_metadata'

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
