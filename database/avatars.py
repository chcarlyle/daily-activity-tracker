"""
CRUD operations for avatars and avatar alignments.
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from models import Avatar, AvatarAlignment


def save_avatar(session: Session, name: str, description: str) -> Avatar:
    """Create or update avatar (deactivates previous avatars)"""
    # Deactivate all existing avatars
    session.query(Avatar).update({"is_active": False})

    # Create new active avatar
    avatar = Avatar(name=name, description=description, is_active=True)
    session.add(avatar)
    session.commit()
    return avatar


def get_active_avatar(session: Session) -> Optional[Avatar]:
    """Get the currently active avatar"""
    return session.query(Avatar).filter_by(is_active=True).first()


def delete_avatar(session: Session, avatar_id: int) -> bool:
    """Delete avatar and its alignments (cascade)"""
    avatar = session.query(Avatar).filter_by(id=avatar_id).first()

    if avatar:
        session.delete(avatar)
        session.commit()
        return True
    return False


def get_alignment_history(session: Session, avatar_id: int, limit: int = 10) -> List[AvatarAlignment]:
    """Get recent alignment analysis history for an avatar"""
    return session.query(AvatarAlignment)\
        .filter_by(avatar_id=avatar_id)\
        .order_by(AvatarAlignment.analysis_date.desc())\
        .limit(limit)\
        .all()
